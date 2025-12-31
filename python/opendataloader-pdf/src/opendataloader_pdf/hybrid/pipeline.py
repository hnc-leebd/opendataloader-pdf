"""
Hybrid pipeline for PDF processing with AI models.
"""

import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

from ..runner import run_jar
from .config import HybridPipelineConfig
from .merge import ResultMerger
from .metrics import MetricsContext, PipelineMetrics

logger = logging.getLogger(__name__)


class HybridPipeline:
    """Pipeline for hybrid PDF processing.

    Combines fast JAR extraction with AI model processing:
    1. Run JAR with --hybrid to triage pages and extract fast-path content
    2. Process AI-path pages with docling models
    3. Merge results into unified output
    """

    def __init__(self, config: Optional[HybridPipelineConfig] = None) -> None:
        """Initialize the pipeline.

        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or HybridPipelineConfig()
        self._temp_dir: Optional[Path] = None
        self._metrics: Optional[PipelineMetrics] = None

    @property
    def metrics(self) -> Optional[PipelineMetrics]:
        """Get metrics from the last pipeline run."""
        return self._metrics

    def process(
        self,
        pdf_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        password: Optional[str] = None,
    ) -> dict[str, Any]:
        """Process a PDF using the hybrid pipeline.

        Args:
            pdf_path: Path to the input PDF file.
            output_dir: Output directory. Uses temp dir if not specified.
            password: Password for encrypted PDF files.

        Returns:
            Merged JSON output following OpenDataLoader schema.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Initialize metrics
        self._metrics = PipelineMetrics()
        self._metrics.start_pipeline()

        # Set up output directory
        work_dir = self._setup_work_dir(output_dir)

        try:
            # Phase 1: Run JAR with --hybrid
            logger.info(f"Running JAR preprocessing for {pdf_path.name}")
            with MetricsContext(self._metrics.jar_phase):
                self._run_jar_hybrid(pdf_path, work_dir, password)

            # Phase 2: Load triage results
            triage = self._load_triage(work_dir)
            all_pages = triage.get("pages", [])
            ai_pages = self._get_ai_pages(triage)
            fast_pages = [p for p in all_pages if p.get("path") == "fast"]

            # Update metrics with page counts
            self._metrics.total_pages = len(all_pages)
            self._metrics.fast_pages = len(fast_pages)
            self._metrics.ai_pages = len(ai_pages)
            self._metrics.jar_phase.items_processed = len(fast_pages)

            logger.info(f"Found {len(ai_pages)} pages requiring AI processing")

            # Phase 3: Process AI pages
            ai_results: dict[int, dict[str, Any]] = {}
            if ai_pages:
                page_numbers = sorted([p["page"] for p in ai_pages])
                self._metrics.ai_page_range = (min(page_numbers), max(page_numbers))

                with MetricsContext(self._metrics.ai_phase, len(ai_pages)):
                    ai_results = self._process_ai_pages(ai_pages, triage, pdf_path)

            # Phase 4: Merge results
            with MetricsContext(self._metrics.merge_phase, len(all_pages)):
                merger = ResultMerger(work_dir)
                result = merger.merge(ai_results)

            # Write output if output_dir was specified
            if output_dir:
                output_path = work_dir / f"{pdf_path.stem}.json"
                merger.write_output(result, output_path)

            self._metrics.stop_pipeline()

            # Log metrics summary
            if logger.isEnabledFor(logging.INFO):
                logger.info(self._metrics.summary())

            return result

        finally:
            # Cleanup temp directory if not keeping intermediate files
            if not self.config.keep_intermediate and self._temp_dir:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
                self._temp_dir = None

    def _setup_work_dir(self, output_dir: Optional[Union[str, Path]]) -> Path:
        """Set up the working directory.

        Args:
            output_dir: User-specified output directory.

        Returns:
            Path to working directory.
        """
        if output_dir:
            work_dir = Path(output_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
            return work_dir

        # Use temp directory
        if self.config.temp_dir:
            self._temp_dir = Path(self.config.temp_dir)
        else:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="hybrid_"))

        self._temp_dir.mkdir(parents=True, exist_ok=True)
        return self._temp_dir

    def _run_jar_hybrid(
        self,
        pdf_path: Path,
        output_dir: Path,
        password: Optional[str],
    ) -> None:
        """Run JAR with --hybrid flag.

        Args:
            pdf_path: Path to input PDF.
            output_dir: Output directory.
            password: PDF password if encrypted.
        """
        args = [
            str(pdf_path),
            "--output-dir",
            str(output_dir),
            "--hybrid",
        ]
        if password:
            args.extend(["--password", password])

        run_jar(args, quiet=False)

    def _load_triage(self, work_dir: Path) -> dict[str, Any]:
        """Load triage.json from work directory.

        Args:
            work_dir: Working directory.

        Returns:
            Parsed triage data.
        """
        triage_path = work_dir / "triage.json"
        if not triage_path.exists():
            logger.warning("triage.json not found, assuming all pages are fast-path")
            return {"pages": []}

        with open(triage_path) as f:
            return json.load(f)

    def _get_ai_pages(self, triage: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract list of pages requiring AI processing.

        Args:
            triage: Triage data from triage.json.

        Returns:
            List of page info dicts for AI-path pages.
        """
        ai_pages = []
        for page_info in triage.get("pages", []):
            if page_info.get("path") == "ai":
                ai_pages.append(page_info)
        return ai_pages

    def _process_ai_pages(
        self,
        ai_pages: list[dict[str, Any]],
        triage: dict[str, Any],
        pdf_path: Path,
    ) -> dict[int, dict[str, Any]]:
        """Process AI-path pages with docling DocumentConverter.

        Processes each AI page individually for better performance when
        AI pages are sparse (e.g., pages 1,3,5,7,9 instead of range 1-9).

        Args:
            ai_pages: List of page info for AI processing.
            triage: Full triage data.
            pdf_path: Path to the original PDF file.

        Returns:
            Dictionary mapping page index (0-indexed) to processing results.
        """
        if not ai_pages:
            return {}

        # Get page numbers (1-indexed from triage)
        page_numbers = sorted([p["page"] for p in ai_pages])
        logger.info(f"Processing {len(page_numbers)} AI pages with docling: {page_numbers}")

        # Initialize docling DocumentConverter
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()

        results: dict[int, dict[str, Any]] = {}

        # Process each AI page individually
        for page_num in page_numbers:
            try:
                conv_result = converter.convert(
                    str(pdf_path),
                    page_range=(page_num, page_num),
                )
                doc = conv_result.document

                page_idx = page_num - 1  # Convert to 0-indexed
                results[page_idx] = {"elements": [], "page": page_idx}

                for item, _level in doc.iterate_items():
                    element = self._convert_docling_item(item, page_idx)
                    if element:
                        results[page_idx]["elements"].append(element)

            except Exception as e:
                logger.error(f"Error processing page {page_num} with docling: {e}")

        return results

    def _get_item_page_number(self, item: Any) -> Optional[int]:
        """Extract page number from a docling item.

        Args:
            item: Docling document item.

        Returns:
            Page number (1-indexed) or None if not available.
        """
        if hasattr(item, "prov") and item.prov:
            prov = item.prov[0] if isinstance(item.prov, list) else item.prov
            if hasattr(prov, "page_no"):
                return prov.page_no
        return None

    def _convert_docling_item(self, item: Any, page_idx: int) -> Optional[dict[str, Any]]:
        """Convert a docling item to OpenDataLoader JSON schema format.

        Args:
            item: Docling document item.
            page_idx: Page index (0-indexed).

        Returns:
            Element dict in JSON schema format, or None if not convertible.
        """
        from docling_core.types.doc.labels import DocItemLabel

        # Map docling labels to our types
        label_to_type = {
            DocItemLabel.TEXT: "paragraph",
            DocItemLabel.PARAGRAPH: "paragraph",
            DocItemLabel.TITLE: "heading",
            DocItemLabel.SECTION_HEADER: "heading",
            DocItemLabel.CAPTION: "caption",
            DocItemLabel.LIST_ITEM: "list item",
            DocItemLabel.TABLE: "table",
            DocItemLabel.PICTURE: "image",
            DocItemLabel.CHART: "image",
            DocItemLabel.FORMULA: "formula",
            DocItemLabel.PAGE_HEADER: "header",
            DocItemLabel.PAGE_FOOTER: "footer",
            DocItemLabel.CODE: "code",
            DocItemLabel.FOOTNOTE: "footnote",
        }

        item_label = getattr(item, "label", None)
        item_type = label_to_type.get(item_label, "paragraph")

        # Get text content
        text = ""
        if hasattr(item, "text"):
            text = item.text or ""

        # Get bounding box if available
        bbox = [0, 0, 0, 0]
        if hasattr(item, "prov") and item.prov:
            prov = item.prov[0] if isinstance(item.prov, list) else item.prov
            if hasattr(prov, "bbox"):
                b = prov.bbox
                bbox = [b.l, b.t, b.r, b.b] if hasattr(b, "l") else list(b)

        element: dict[str, Any] = {
            "type": item_type,
            "page number": page_idx + 1,  # 1-indexed
            "bounding box": bbox,
        }

        if item_type in ("paragraph", "heading", "caption", "list item"):
            element["content"] = text
            element["font"] = "docling"
            element["font size"] = 12
            element["text color"] = "#000000"

        return element
