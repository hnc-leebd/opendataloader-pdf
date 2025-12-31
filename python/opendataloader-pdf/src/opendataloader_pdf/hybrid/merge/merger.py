"""
Result merger for combining fast-path and AI-path results.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResultMerger:
    """Merges fast-path JAR extraction with AI model results.

    Combines results from:
    - fast_pages.json: JAR extraction for fast-path pages
    - AI model outputs: OCR, Table, Layout for AI-path pages

    Produces a unified JSON output following the OpenDataLoader schema.
    """

    def __init__(self, output_dir: Path) -> None:
        """Initialize the merger.

        Args:
            output_dir: Directory containing triage.json and fast_pages.json.
        """
        self.output_dir = output_dir
        self._triage: Optional[dict[str, Any]] = None
        self._fast_pages: Optional[dict[str, Any]] = None

    def load_fast_results(self) -> dict[str, Any]:
        """Load fast_pages.json from output directory.

        Returns:
            Parsed fast pages content.
        """
        fast_pages_path = self.output_dir / "fast_pages.json"
        if not fast_pages_path.exists():
            logger.warning(f"fast_pages.json not found at {fast_pages_path}")
            return {"kids": []}

        with open(fast_pages_path) as f:
            self._fast_pages = json.load(f)
        return self._fast_pages

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
        """Merge fast-path and AI-path results into unified output.

        Args:
            ai_results: Dictionary mapping page numbers (0-indexed) to AI results.
            document_info: Optional document metadata to include.

        Returns:
            Unified JSON output following OpenDataLoader schema.
        """
        # Load fast pages if not already loaded
        if self._fast_pages is None:
            self.load_fast_results()

        # Load triage if not already loaded
        if self._triage is None:
            self.load_triage()

        # Build page routing map
        page_routing = self._build_page_routing()

        # Start with document info from fast_pages or provided
        result = self._init_result(document_info)

        # Merge content by page
        all_elements = self._merge_elements(page_routing, ai_results)

        # Sort by page number and reading order
        result["kids"] = self._sort_elements(all_elements)

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

        # Use fast_pages metadata if available
        if self._fast_pages:
            return {
                "file name": self._fast_pages.get("file name", ""),
                "number of pages": self._fast_pages.get("number of pages", 0),
                "author": self._fast_pages.get("author"),
                "title": self._fast_pages.get("title"),
                "creation date": self._fast_pages.get("creation date"),
                "modification date": self._fast_pages.get("modification date"),
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
        """Merge elements from fast and AI paths.

        Args:
            page_routing: Map of page number to processing path.
            ai_results: AI processing results by page.

        Returns:
            List of all content elements.
        """
        elements: list[dict[str, Any]] = []

        # Group fast_pages elements by page
        fast_by_page: dict[int, list[dict[str, Any]]] = {}
        if self._fast_pages and "kids" in self._fast_pages:
            for element in self._fast_pages["kids"]:
                page_num = element.get("page number", 1)
                if page_num not in fast_by_page:
                    fast_by_page[page_num] = []
                fast_by_page[page_num].append(element)

        # Determine all page numbers
        all_pages = set(page_routing.keys())
        all_pages.update(fast_by_page.keys())
        all_pages.update(p + 1 for p in ai_results.keys())  # AI uses 0-indexed

        for page_num in sorted(all_pages):
            path = page_routing.get(page_num, "fast")

            if path == "ai":
                # Use AI results for this page
                ai_page_idx = page_num - 1  # Convert to 0-indexed
                if ai_page_idx in ai_results:
                    ai_result = ai_results[ai_page_idx]
                    for element in ai_result.get("elements", []):
                        # Ensure page number is set
                        element["page number"] = page_num
                        elements.append(element)
                else:
                    logger.warning(f"AI result missing for page {page_num}")
            else:
                # Use fast-path results
                if page_num in fast_by_page:
                    elements.extend(fast_by_page[page_num])

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

    def write_output(self, result: dict[str, Any], output_path: Path) -> None:
        """Write merged result to file.

        Args:
            result: Merged result dictionary.
            output_path: Path to write output JSON.
        """
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"Wrote merged output to {output_path}")
