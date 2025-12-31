"""
Hybrid pipeline for PDF processing with AI models.
"""

import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, List, Optional, Union
from docling.document_converter import DocumentConverter
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
        pdf_path: Union[str, List[str]],
        output_dir: Optional[str] = None,
        password: Optional[str] = None,
        format: Optional[Union[str, List[str]]] = None,
        quiet: bool = False,
        content_safety_off: Optional[Union[str, List[str]]] = None,
        keep_line_breaks: bool = False,
        replace_invalid_chars: Optional[str] = None,
        use_struct_tree: bool = False,
    ) -> dict[str, Any]:
        """Process a PDF using the hybrid pipeline.

        Args:
            pdf_path: Path to the input PDF file or list of paths.
            output_dir: Output directory. Uses temp dir if not specified.
            password: Password for encrypted PDF files.
            format: Output format(s). Can be a single format string or list of formats.
            quiet: If True, suppress output messages.
            content_safety_off: Content safety setting(s) to disable.
            keep_line_breaks: If True, keeps line breaks in the output.
            replace_invalid_chars: Character to replace invalid or unrecognized characters with.
            use_struct_tree: If True, enable processing structure tree.

        Returns:
            Merged JSON output following OpenDataLoader schema.
        """
        # Handle list of paths - for now, process only the first one
        if isinstance(pdf_path, list):
            pdf_path = pdf_path[0]
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Initialize metrics
        self._metrics = PipelineMetrics()
        self._metrics.start_pipeline()

        # Set up temporary work directory for JAR output
        work_dir = self._setup_work_dir()

        # Set up user output directory if specified
        user_output_dir: Optional[Path] = None
        if output_dir:
            user_output_dir = Path(output_dir)
            user_output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Phase 1: Run JAR with --hybrid (output to temp work_dir)
            logger.info(f"Running JAR preprocessing for {pdf_path.name}")
            with MetricsContext(self._metrics.jar_phase):
                self._run_jar_hybrid(
                    pdf_path,
                    work_dir,
                    password,
                    format=format,
                    quiet=quiet,
                    content_safety_off=content_safety_off,
                    keep_line_breaks=keep_line_breaks,
                    replace_invalid_chars=replace_invalid_chars,
                    use_struct_tree=use_struct_tree,
                )

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
                self._metrics.ai_page_range = page_numbers

                with MetricsContext(self._metrics.ai_phase, len(ai_pages)):
                    ai_results = self._process_ai_pages(
                        ai_pages, triage, pdf_path, work_dir, format
                    )

            # Phase 4: Merge results
            with MetricsContext(self._metrics.merge_phase, len(all_pages)):
                merger = ResultMerger(work_dir)
                result = merger.merge(ai_results)

            # Normalize format to list
            output_formats: list[str] = []
            if format:
                if isinstance(format, str):
                    output_formats = [format]
                else:
                    output_formats = list(format)
            if not output_formats:
                output_formats = ["json"]

            # Write output to user-specified directory
            if user_output_dir:
                output_path = user_output_dir / f"{pdf_path.stem}.json"
                merger.write_output(result, output_path, formats=output_formats)

                # Copy intermediate files if keep_intermediate is True
                if self.config.keep_intermediate:
                    self._copy_intermediate_files(work_dir, user_output_dir)

            self._metrics.stop_pipeline()

            # Log metrics summary
            if logger.isEnabledFor(logging.INFO):
                logger.info(self._metrics.summary())

            return result

        finally:
            # Cleanup temp directory (JAR intermediate files)
            if not self.config.keep_intermediate and self._temp_dir:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
                self._temp_dir = None

    def _setup_work_dir(self) -> Path:
        """Set up the temporary working directory for JAR intermediate files.

        Returns:
            Path to temporary working directory.
        """
        if self.config.temp_dir:
            self._temp_dir = Path(self.config.temp_dir)
        else:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="hybrid_"))

        self._temp_dir.mkdir(parents=True, exist_ok=True)
        return self._temp_dir

    def _copy_intermediate_files(self, work_dir: Path, output_dir: Path) -> None:
        """Copy intermediate files from work directory to output directory.

        Args:
            work_dir: Temporary working directory with intermediate files.
            output_dir: User-specified output directory.
        """
        intermediate_files = ["triage.json", "all_pages.json"]
        for filename in intermediate_files:
            src = work_dir / filename
            if src.exists():
                dst = output_dir / filename
                shutil.copy2(src, dst)

        # Copy ai_pages directory if exists
        ai_pages_src = work_dir / "ai_pages"
        if ai_pages_src.exists() and ai_pages_src.is_dir():
            ai_pages_dst = output_dir / "ai_pages"
            if ai_pages_dst.exists():
                shutil.rmtree(ai_pages_dst)
            shutil.copytree(ai_pages_src, ai_pages_dst)

    def _run_jar_hybrid(
        self,
        pdf_path: Path,
        output_dir: Path,
        password: Optional[str],
        format: Optional[Union[str, List[str]]] = None,
        quiet: bool = False,
        content_safety_off: Optional[Union[str, List[str]]] = None,
        keep_line_breaks: bool = False,
        replace_invalid_chars: Optional[str] = None,
        use_struct_tree: bool = False,
    ) -> None:
        """Run JAR with --hybrid flag.

        Args:
            pdf_path: Path to input PDF.
            output_dir: Output directory.
            password: PDF password if encrypted.
            format: Output format(s).
            quiet: If True, suppress output messages.
            content_safety_off: Content safety setting(s) to disable.
            keep_line_breaks: If True, keeps line breaks in the output.
            replace_invalid_chars: Character to replace invalid characters with.
            use_struct_tree: If True, enable processing structure tree.
        """
        args = [
            str(pdf_path),
            "--output-dir",
            str(output_dir),
            "--hybrid",
        ]
        if password:
            args.extend(["--password", password])
        if format:
            if isinstance(format, list):
                for fmt in format:
                    args.extend(["--format", fmt])
            else:
                args.extend(["--format", format])
        if content_safety_off:
            if isinstance(content_safety_off, list):
                for cso in content_safety_off:
                    args.extend(["--content-safety-off", cso])
            else:
                args.extend(["--content-safety-off", content_safety_off])
        if keep_line_breaks:
            args.append("--keep-line-breaks")
        if replace_invalid_chars:
            args.extend(["--replace-invalid-chars", replace_invalid_chars])
        if use_struct_tree:
            args.append("--use-struct-tree")

        run_jar(args, quiet=quiet)

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
        work_dir: Path,
        format: Optional[Union[str, List[str]]] = None,
    ) -> dict[int, dict[str, Any]]:
        """Process AI-path pages with docling DocumentConverter.

        Processes each AI page individually for better performance when
        AI pages are sparse (e.g., pages 1,3,5,7,9 instead of range 1-9).

        Args:
            ai_pages: List of page info for AI processing.
            triage: Full triage data.
            pdf_path: Path to the original PDF file.
            work_dir: Working directory for output files.
            format: Output format(s) - json, html, markdown, etc.

        Returns:
            Dictionary mapping page index (0-indexed) to processing results.
        """
        import time

        if not ai_pages:
            return {}

        # Normalize format to list
        formats: list[str] = []
        if format:
            if isinstance(format, str):
                formats = [format]
            else:
                formats = list(format)
        if not formats:
            formats = ["json"]

        # Get page numbers (1-indexed from triage)
        page_numbers = sorted([p["page"] for p in ai_pages])
        logger.info(f"Processing {len(page_numbers)} AI pages with docling: {page_numbers}")

        init_start = time.perf_counter()
        converter = DocumentConverter()
        init_time = time.perf_counter() - init_start
        logger.debug(f"DocumentConverter init: {init_time:.2f}s")

        results: dict[int, dict[str, Any]] = {}

        # Prepare output directory for AI pages
        ai_output_dir = work_dir / "ai_pages"
        ai_output_dir.mkdir(parents=True, exist_ok=True)

        # Process each AI page individually
        for page_num in page_numbers:
            try:
                page_start = time.perf_counter()
                conv_result = converter.convert(
                    str(pdf_path),
                    page_range=(page_num, page_num),
                )
                convert_time = time.perf_counter() - page_start
                doc = conv_result.document

                page_idx = page_num - 1  # Convert to 0-indexed
                results[page_idx] = {"elements": [], "page": page_idx}

                for item, _level in doc.iterate_items():
                    element = self._convert_docling_item(item, page_idx)
                    if element:
                        results[page_idx]["elements"].append(element)

                # Export to requested formats
                self._export_ai_page(
                    doc, page_num, ai_output_dir, formats, pdf_path.stem
                )

                logger.debug(f"Page {page_num}: convert={convert_time:.2f}s")

            except Exception as e:
                logger.error(f"Error processing page {page_num} with docling: {e}")

        return results

    def _export_ai_page(
        self,
        doc: Any,
        page_num: int,
        output_dir: Path,
        formats: list[str],
        pdf_stem: str,
    ) -> None:
        """Export AI-processed page to requested formats.

        Args:
            doc: Docling document object.
            page_num: Page number (1-indexed).
            output_dir: Directory to write output files.
            formats: List of output formats.
            pdf_stem: PDF filename without extension.
        """
        base_name = f"{pdf_stem}_page_{page_num}"

        for fmt in formats:
            try:
                if fmt == "json":
                    # JSON is handled by the main merge process
                    pass
                elif fmt in ("markdown", "md", "markdown-with-html", "markdown-with-images"):
                    md_content = doc.export_to_markdown()
                    md_path = output_dir / f"{base_name}.md"
                    md_path.write_text(md_content, encoding="utf-8")
                elif fmt == "html":
                    html_content = doc.export_to_html()
                    html_path = output_dir / f"{base_name}.html"
                    html_path.write_text(html_content, encoding="utf-8")
                elif fmt == "text":
                    text_content = doc.export_to_text()
                    text_path = output_dir / f"{base_name}.txt"
                    text_path.write_text(text_content, encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to export page {page_num} to {fmt}: {e}")

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
            element["font"] = ""
            element["font size"] = 0
            element["text color"] = "[0.0]"

        return element
