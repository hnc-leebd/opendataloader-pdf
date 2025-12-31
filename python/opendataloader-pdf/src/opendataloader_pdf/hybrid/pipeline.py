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

        # Set up output directory
        work_dir = self._setup_work_dir(output_dir)

        try:
            # Phase 1: Run JAR with --hybrid
            logger.info(f"Running JAR preprocessing for {pdf_path.name}")
            self._run_jar_hybrid(pdf_path, work_dir, password)

            # Phase 2: Load triage results
            triage = self._load_triage(work_dir)
            ai_pages = self._get_ai_pages(triage)
            logger.info(f"Found {len(ai_pages)} pages requiring AI processing")

            # Phase 3: Process AI pages
            ai_results: dict[int, dict[str, Any]] = {}
            if ai_pages:
                ai_results = self._process_ai_pages(work_dir, ai_pages, triage)

            # Phase 4: Merge results
            merger = ResultMerger(work_dir)
            result = merger.merge(ai_results)

            # Write output if output_dir was specified
            if output_dir:
                output_path = work_dir / f"{pdf_path.stem}.json"
                merger.write_output(result, output_path)

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
        work_dir: Path,
        ai_pages: list[dict[str, Any]],
        triage: dict[str, Any],
    ) -> dict[int, dict[str, Any]]:
        """Process AI-path pages with docling DocumentConverter.

        Args:
            work_dir: Working directory containing page images.
            ai_pages: List of page info for AI processing.
            triage: Full triage data.

        Returns:
            Dictionary mapping page index (0-indexed) to processing results.
        """
        ai_pages_dir = work_dir / "ai_pages"
        if not ai_pages_dir.exists():
            logger.warning("ai_pages directory not found")
            return {}

        results: dict[int, dict[str, Any]] = {}

        # Initialize docling DocumentConverter once
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()

        for page_info in ai_pages:
            page_num = page_info["page"]  # 1-indexed
            page_idx = page_num - 1  # Convert to 0-indexed

            image_path = ai_pages_dir / f"page_{page_num:03d}.png"
            if not image_path.exists():
                logger.warning(f"Page image not found: {image_path}")
                continue

            try:
                result = self._process_single_page_with_docling(
                    converter, image_path, page_idx
                )
                results[page_idx] = result
            except Exception as e:
                logger.error(f"Error processing page {page_idx}: {e}")

        return results

    def _process_single_page_with_docling(
        self,
        converter: Any,
        image_path: Path,
        page_idx: int,
    ) -> dict[str, Any]:
        """Process a single AI-path page using docling.

        Args:
            converter: Docling DocumentConverter instance.
            image_path: Path to page image.
            page_idx: Page index (0-indexed).

        Returns:
            Extracted elements from docling.
        """
        # Convert image with docling
        conv_result = converter.convert(str(image_path))
        doc = conv_result.document

        elements: list[dict[str, Any]] = []

        # Extract text items from docling document
        for item, _level in doc.iterate_items():
            element = self._convert_docling_item(item, page_idx)
            if element:
                elements.append(element)

        return {"elements": elements, "page": page_idx}

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
