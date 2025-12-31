"""
Result merger for combining JAR extraction with AI-path results.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResultMerger:
    """Merges JAR extraction with AI model results.

    Combines results from:
    - all_pages.json: JAR extraction for all pages
    - AI model outputs: OCR, Table, Layout for AI-path pages

    For AI-path pages, the AI results replace the JAR extraction.
    Produces a unified JSON output following the OpenDataLoader schema.
    """

    def __init__(self, output_dir: Path) -> None:
        """Initialize the merger.

        Args:
            output_dir: Directory containing triage.json and all_pages.json.
        """
        self.output_dir = output_dir
        self._triage: Optional[dict[str, Any]] = None
        self._all_pages: Optional[dict[str, Any]] = None

    def load_all_pages(self) -> dict[str, Any]:
        """Load all_pages.json from output directory.

        Returns:
            Parsed all pages content.
        """
        all_pages_path = self.output_dir / "all_pages.json"
        if not all_pages_path.exists():
            logger.warning(f"all_pages.json not found at {all_pages_path}")
            return {"kids": []}

        with open(all_pages_path) as f:
            self._all_pages = json.load(f)
        return self._all_pages

    def load_triage(self) -> dict[str, Any]:
        """Load triage.json from output directory.

        Returns:
            Parsed triage content.
        """
        triage_path = self.output_dir / "triage.json"
        if not triage_path.exists():
            logger.warning(f"triage.json not found at {triage_path}")
            return {"pages": []}

        with open(triage_path) as f:
            self._triage = json.load(f)
        return self._triage

    def merge(
        self,
        ai_results: dict[int, dict[str, Any]],
        document_info: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Merge JAR extraction and AI-path results into unified output.

        For AI-path pages, the AI results replace the JAR extraction.
        For fast-path pages, the JAR extraction is used as-is.

        Args:
            ai_results: Dictionary mapping page numbers (0-indexed) to AI results.
            document_info: Optional document metadata to include.

        Returns:
            Unified JSON output following OpenDataLoader schema.
        """
        # Load all pages if not already loaded
        if self._all_pages is None:
            self.load_all_pages()

        # Load triage if not already loaded
        if self._triage is None:
            self.load_triage()

        # Build page routing map
        page_routing = self._build_page_routing()

        # Start with document info from all_pages or provided
        result = self._init_result(document_info)

        # Merge content by page
        all_elements = self._merge_elements(page_routing, ai_results)

        # Sort by page number and reading order
        sorted_elements = self._sort_elements(all_elements)

        # Reassign sequential IDs
        result["kids"] = self._assign_ids(sorted_elements)

        return result

    def _build_page_routing(self) -> dict[int, str]:
        """Build a map of page number to processing path.

        Returns:
            Dictionary mapping page number (1-indexed) to path ("fast" or "ai").
        """
        routing: dict[int, str] = {}
        if self._triage and "pages" in self._triage:
            for page_info in self._triage["pages"]:
                page_num = page_info.get("page", 0)
                path = page_info.get("path", "fast")
                routing[page_num] = path
        return routing

    def _init_result(self, document_info: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Initialize result with document metadata.

        Args:
            document_info: Optional document metadata.

        Returns:
            Initial result dictionary with metadata fields.
        """
        if document_info:
            return {
                "file name": document_info.get("file name", ""),
                "number of pages": document_info.get("number of pages", 0),
                "author": document_info.get("author"),
                "title": document_info.get("title"),
                "creation date": document_info.get("creation date"),
                "modification date": document_info.get("modification date"),
                "kids": [],
            }

        # Use all_pages metadata if available
        if self._all_pages:
            return {
                "file name": self._all_pages.get("file name", ""),
                "number of pages": self._all_pages.get("number of pages", 0),
                "author": self._all_pages.get("author"),
                "title": self._all_pages.get("title"),
                "creation date": self._all_pages.get("creation date"),
                "modification date": self._all_pages.get("modification date"),
                "kids": [],
            }

        return {
            "file name": "",
            "number of pages": 0,
            "author": None,
            "title": None,
            "creation date": None,
            "modification date": None,
            "kids": [],
        }

    def _merge_elements(
        self,
        page_routing: dict[int, str],
        ai_results: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge elements from JAR extraction and AI paths.

        For AI-path pages, AI results replace JAR extraction.
        For fast-path pages, JAR extraction is used.

        Args:
            page_routing: Map of page number to processing path.
            ai_results: AI processing results by page.

        Returns:
            List of all content elements.
        """
        elements: list[dict[str, Any]] = []

        # Group all_pages elements by page
        jar_by_page: dict[int, list[dict[str, Any]]] = {}
        if self._all_pages and "kids" in self._all_pages:
            for element in self._all_pages["kids"]:
                page_num = element.get("page number", 1)
                if page_num not in jar_by_page:
                    jar_by_page[page_num] = []
                jar_by_page[page_num].append(element)

        # Determine all page numbers
        all_page_nums = set(page_routing.keys())
        all_page_nums.update(jar_by_page.keys())
        all_page_nums.update(p + 1 for p in ai_results.keys())  # AI uses 0-indexed

        for page_num in sorted(all_page_nums):
            path = page_routing.get(page_num, "fast")

            if path == "ai":
                # Use AI results for this page (replacing JAR extraction)
                ai_page_idx = page_num - 1  # Convert to 0-indexed
                if ai_page_idx in ai_results:
                    ai_result = ai_results[ai_page_idx]
                    for element in ai_result.get("elements", []):
                        # Ensure page number is set
                        element["page number"] = page_num
                        elements.append(element)
                else:
                    # Fallback to JAR extraction if AI result is missing
                    logger.warning(f"AI result missing for page {page_num}, using JAR extraction")
                    if page_num in jar_by_page:
                        elements.extend(jar_by_page[page_num])
            else:
                # Use JAR extraction for fast-path pages
                if page_num in jar_by_page:
                    elements.extend(jar_by_page[page_num])

        return elements

    def _sort_elements(self, elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort elements by page number and position.

        Args:
            elements: List of content elements.

        Returns:
            Sorted list of elements.
        """
        def sort_key(elem: dict[str, Any]) -> tuple[int, float, float]:
            page = elem.get("page number", 1)
            bbox = elem.get("bounding box", [0, 0, 0, 0])
            # Sort by page, then by y position (top to bottom), then x (left to right)
            y = bbox[1] if len(bbox) > 1 else 0
            x = bbox[0] if len(bbox) > 0 else 0
            return (page, y, x)

        return sorted(elements, key=sort_key)

    def _assign_ids(self, elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Assign sequential IDs to all elements.

        Args:
            elements: List of content elements.

        Returns:
            Elements with sequential IDs starting from 1.
        """
        for idx, element in enumerate(elements, start=1):
            element["id"] = idx
        return elements

    def write_output(
        self,
        result: dict[str, Any],
        output_path: Path,
        formats: Optional[list[str]] = None,
    ) -> None:
        """Write merged result to file(s) in requested formats.

        Args:
            result: Merged result dictionary.
            output_path: Base path for output files (extension will be replaced).
            formats: List of formats to generate. Defaults to ["json"].
                     Supported: "json", "markdown", "md", "html"
        """
        if formats is None:
            formats = ["json"]

        base_path = output_path.with_suffix("")

        for fmt in formats:
            fmt_lower = fmt.lower()
            if fmt_lower == "json":
                json_path = base_path.with_suffix(".json")
                with open(json_path, "w") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                logger.info(f"Wrote JSON output to {json_path}")

            elif fmt_lower in ("markdown", "md"):
                md_path = base_path.with_suffix(".md")
                md_content = self._to_markdown(result)
                with open(md_path, "w") as f:
                    f.write(md_content)
                logger.info(f"Wrote Markdown output to {md_path}")

            elif fmt_lower == "html":
                html_path = base_path.with_suffix(".html")
                html_content = self._to_html(result)
                with open(html_path, "w") as f:
                    f.write(html_content)
                logger.info(f"Wrote HTML output to {html_path}")

    def _to_markdown(self, result: dict[str, Any]) -> str:
        """Convert JSON result to Markdown format.

        Args:
            result: Merged result dictionary.

        Returns:
            Markdown string.
        """
        lines: list[str] = []
        current_page = 0

        for element in result.get("kids", []):
            page_num = element.get("page number", 1)
            elem_type = element.get("type", "")
            content = element.get("content", "")

            # Add page separator
            if page_num != current_page:
                if current_page > 0:
                    lines.append("")
                current_page = page_num

            # Convert by type
            if elem_type == "heading":
                level = element.get("heading level", 1)
                level = min(max(level, 1), 6)  # Clamp to 1-6
                lines.append(f"{'#' * level} {content}")
                lines.append("")
            elif elem_type == "paragraph":
                lines.append(content)
                lines.append("")
            elif elem_type == "list item":
                lines.append(f"- {content}")
            elif elem_type == "table":
                table_md = self._table_to_markdown(element)
                lines.append(table_md)
                lines.append("")
            elif elem_type == "image":
                alt_text = element.get("alt text", "image")
                lines.append(f"![{alt_text}]()")
                lines.append("")
            elif elem_type == "code":
                lines.append("```")
                lines.append(content)
                lines.append("```")
                lines.append("")
            elif content:
                lines.append(content)
                lines.append("")

        return "\n".join(lines)

    def _table_to_markdown(self, table_element: dict[str, Any]) -> str:
        """Convert table element to Markdown table.

        Args:
            table_element: Table element dictionary.

        Returns:
            Markdown table string.
        """
        cells = table_element.get("cells", [])
        if not cells:
            return table_element.get("content", "")

        # Organize cells by row/column
        rows: dict[int, dict[int, str]] = {}
        max_col = 0
        for cell in cells:
            row = cell.get("row", 0)
            col = cell.get("column", 0)
            content = cell.get("content", "")
            if row not in rows:
                rows[row] = {}
            rows[row][col] = content
            max_col = max(max_col, col)

        if not rows:
            return table_element.get("content", "")

        # Build markdown table
        lines: list[str] = []
        for row_idx in sorted(rows.keys()):
            row_cells = []
            for col_idx in range(max_col + 1):
                cell_content = rows[row_idx].get(col_idx, "")
                # Escape pipe characters
                cell_content = cell_content.replace("|", "\\|")
                row_cells.append(cell_content)
            lines.append("| " + " | ".join(row_cells) + " |")

            # Add header separator after first row
            if row_idx == min(rows.keys()):
                lines.append("| " + " | ".join(["---"] * (max_col + 1)) + " |")

        return "\n".join(lines)

    def _to_html(self, result: dict[str, Any]) -> str:
        """Convert JSON result to HTML format.

        Args:
            result: Merged result dictionary.

        Returns:
            HTML string.
        """
        title = result.get("title") or result.get("file name", "Document")
        lines: list[str] = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"  <title>{self._escape_html(title)}</title>",
            '  <meta charset="utf-8">',
            "  <style>",
            "    body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
            "    table { border-collapse: collapse; width: 100%; margin: 1em 0; }",
            "    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "    th { background-color: #f2f2f2; }",
            "    img { max-width: 100%; }",
            "    pre { background-color: #f4f4f4; padding: 10px; overflow-x: auto; }",
            "  </style>",
            "</head>",
            "<body>",
        ]

        for element in result.get("kids", []):
            elem_type = element.get("type", "")
            content = element.get("content", "")

            if elem_type == "heading":
                level = element.get("heading level", 1)
                level = min(max(level, 1), 6)
                lines.append(f"<h{level}>{self._escape_html(content)}</h{level}>")
            elif elem_type == "paragraph":
                lines.append(f"<p>{self._escape_html(content)}</p>")
            elif elem_type == "list item":
                lines.append(f"<li>{self._escape_html(content)}</li>")
            elif elem_type == "table":
                table_html = self._table_to_html(element)
                lines.append(table_html)
            elif elem_type == "image":
                alt_text = element.get("alt text", "image")
                lines.append(f'<img src="" alt="{self._escape_html(alt_text)}">')
            elif elem_type == "code":
                lines.append(f"<pre><code>{self._escape_html(content)}</code></pre>")
            elif content:
                lines.append(f"<p>{self._escape_html(content)}</p>")

        lines.extend(["</body>", "</html>"])
        return "\n".join(lines)

    def _table_to_html(self, table_element: dict[str, Any]) -> str:
        """Convert table element to HTML table.

        Args:
            table_element: Table element dictionary.

        Returns:
            HTML table string.
        """
        cells = table_element.get("cells", [])
        if not cells:
            content = table_element.get("content", "")
            return f"<p>{self._escape_html(content)}</p>"

        # Organize cells by row/column
        rows: dict[int, dict[int, str]] = {}
        max_col = 0
        for cell in cells:
            row = cell.get("row", 0)
            col = cell.get("column", 0)
            content = cell.get("content", "")
            if row not in rows:
                rows[row] = {}
            rows[row][col] = content
            max_col = max(max_col, col)

        if not rows:
            content = table_element.get("content", "")
            return f"<p>{self._escape_html(content)}</p>"

        # Build HTML table
        lines: list[str] = ["<table>"]
        for i, row_idx in enumerate(sorted(rows.keys())):
            tag = "th" if i == 0 else "td"
            lines.append("  <tr>")
            for col_idx in range(max_col + 1):
                cell_content = rows[row_idx].get(col_idx, "")
                lines.append(f"    <{tag}>{self._escape_html(cell_content)}</{tag}>")
            lines.append("  </tr>")
        lines.append("</table>")
        return "\n".join(lines)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.

        Args:
            text: Text to escape.

        Returns:
            Escaped text.
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
