"""
Table detection model adapter.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from ..config import TableConfig
from .base import BaseModelAdapter

logger = logging.getLogger(__name__)


class TableAdapter(BaseModelAdapter):
    """Adapter for table detection models.

    Uses docling's TableFormer model to detect and extract
    table structures from page images.
    """

    def __init__(self, config: Optional[TableConfig] = None) -> None:
        super().__init__()
        self.config = config or TableConfig()

    def _load_model(self) -> None:
        """Load the table detection model."""
        try:
            from docling.models.table_structure_model import TableStructureModel

            self._model = TableStructureModel()
            logger.info("Loaded docling TableStructureModel")
        except ImportError as e:
            raise ImportError(
                "docling is not installed. Install with: pip install docling"
            ) from e

    def process(self, image_path: Path, page_number: int) -> dict[str, Any]:
        """Detect and extract tables from a page image.

        Args:
            image_path: Path to the page image.
            page_number: The page number (0-indexed).

        Returns:
            Dictionary with detected tables in JSON schema format.
        """
        self.ensure_loaded()

        from PIL import Image

        img = Image.open(image_path)
        img_width, img_height = img.size

        # Use docling to detect tables
        try:
            tables = self._detect_tables(img)
        except Exception as e:
            logger.warning(f"Table detection failed for page {page_number}: {e}")
            return {"elements": [], "source": "table"}

        elements: list[dict[str, Any]] = []

        for table in tables:
            table_element = self._convert_table_to_schema(table, page_number, img_width, img_height)
            if table_element:
                elements.append(table_element)

        return {"elements": elements, "source": "table"}

    def _detect_tables(self, img: Any) -> list[dict[str, Any]]:
        """Run table detection on the image.

        Args:
            img: PIL Image object.

        Returns:
            List of detected table structures.
        """
        # Call docling's table structure model
        # The actual API may vary based on docling version
        try:
            result = self._model.predict(img)
            return result.tables if hasattr(result, "tables") else []
        except AttributeError:
            # Fallback for different docling API versions
            return self._model(img) if callable(self._model) else []

    def _convert_table_to_schema(
        self,
        table: Any,
        page_number: int,
        img_width: int,
        img_height: int,
    ) -> Optional[dict[str, Any]]:
        """Convert docling table result to JSON schema format.

        Args:
            table: Docling table detection result.
            page_number: The page number (0-indexed).
            img_width: Image width in pixels.
            img_height: Image height in pixels.

        Returns:
            Table dictionary in JSON schema format, or None if conversion fails.
        """
        try:
            # Extract bounding box (normalize if needed)
            bbox = self._get_table_bbox(table, img_width, img_height)

            # Extract table structure
            rows = self._extract_table_rows(table)

            num_rows = len(rows)
            num_cols = max((len(row.get("cells", [])) for row in rows), default=0)

            return {
                "type": "table",
                "page number": page_number + 1,  # 1-indexed
                "bounding box": bbox,
                "number of rows": num_rows,
                "number of columns": num_cols,
                "rows": rows,
            }
        except Exception as e:
            logger.warning(f"Failed to convert table: {e}")
            return None

    def _get_table_bbox(
        self,
        table: Any,
        img_width: int,
        img_height: int,
    ) -> list[float]:
        """Extract bounding box from table result."""
        if hasattr(table, "bbox"):
            bbox = table.bbox
            # Normalize to image coordinates if needed
            if all(0 <= v <= 1 for v in bbox):
                return [
                    bbox[0] * img_width,
                    bbox[1] * img_height,
                    bbox[2] * img_width,
                    bbox[3] * img_height,
                ]
            return list(bbox)
        return [0, 0, img_width, img_height]

    def _extract_table_rows(self, table: Any) -> list[dict[str, Any]]:
        """Extract row structure from table result."""
        rows: list[dict[str, Any]] = []

        if not hasattr(table, "cells"):
            return rows

        # Group cells by row
        cells_by_row: dict[int, list[Any]] = {}
        for cell in table.cells:
            row_idx = getattr(cell, "row", 0)
            if row_idx not in cells_by_row:
                cells_by_row[row_idx] = []
            cells_by_row[row_idx].append(cell)

        # Convert to schema format
        for row_idx in sorted(cells_by_row.keys()):
            row_cells: list[dict[str, Any]] = []
            for cell in cells_by_row[row_idx]:
                cell_dict = {
                    "row number": getattr(cell, "row", row_idx) + 1,  # 1-indexed
                    "column number": getattr(cell, "col", 0) + 1,
                    "row span": getattr(cell, "row_span", 1),
                    "column span": getattr(cell, "col_span", 1),
                    "kids": [
                        {
                            "type": "paragraph",
                            "content": getattr(cell, "text", ""),
                        }
                    ],
                }
                row_cells.append(cell_dict)
            rows.append({"cells": row_cells})

        return rows
