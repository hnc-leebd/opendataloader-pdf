"""
Layout analysis model adapter.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from ..config import LayoutConfig
from .base import BaseModelAdapter

logger = logging.getLogger(__name__)


class LayoutAdapter(BaseModelAdapter):
    """Adapter for layout analysis models.

    Uses docling's layout model to detect document structure
    including paragraphs, headings, figures, and other elements.
    """

    def __init__(self, config: Optional[LayoutConfig] = None) -> None:
        super().__init__()
        self.config = config or LayoutConfig()

    def _load_model(self) -> None:
        """Load the layout analysis model."""
        try:
            from docling.models.layout_model import LayoutModel

            self._model = LayoutModel()
            logger.info("Loaded docling LayoutModel")
        except ImportError as e:
            raise ImportError(
                "docling is not installed. Install with: pip install docling"
            ) from e

    def process(self, image_path: Path, page_number: int) -> dict[str, Any]:
        """Analyze layout of a page image.

        Args:
            image_path: Path to the page image.
            page_number: The page number (0-indexed).

        Returns:
            Dictionary with detected layout elements in JSON schema format.
        """
        self.ensure_loaded()

        from PIL import Image

        img = Image.open(image_path)
        img_width, img_height = img.size

        try:
            layout_result = self._analyze_layout(img)
        except Exception as e:
            logger.warning(f"Layout analysis failed for page {page_number}: {e}")
            return {"elements": [], "source": "layout"}

        elements: list[dict[str, Any]] = []

        for region in layout_result:
            element = self._convert_region_to_schema(
                region, page_number, img_width, img_height
            )
            if element:
                elements.append(element)

        return {"elements": elements, "source": "layout"}

    def _analyze_layout(self, img: Any) -> list[Any]:
        """Run layout analysis on the image.

        Args:
            img: PIL Image object.

        Returns:
            List of detected layout regions.
        """
        try:
            result = self._model.predict(img)
            return result.regions if hasattr(result, "regions") else []
        except AttributeError:
            return self._model(img) if callable(self._model) else []

    def _convert_region_to_schema(
        self,
        region: Any,
        page_number: int,
        img_width: int,
        img_height: int,
    ) -> Optional[dict[str, Any]]:
        """Convert layout region to JSON schema format.

        Args:
            region: Docling layout region.
            page_number: The page number (0-indexed).
            img_width: Image width in pixels.
            img_height: Image height in pixels.

        Returns:
            Element dictionary in JSON schema format.
        """
        try:
            # Get region type
            region_type = self._get_region_type(region)

            # Get bounding box
            bbox = self._get_region_bbox(region, img_width, img_height)

            element: dict[str, Any] = {
                "type": region_type,
                "page number": page_number + 1,  # 1-indexed
                "bounding box": bbox,
            }

            # Add type-specific fields
            if region_type in ("paragraph", "heading", "caption", "list item"):
                element.update(
                    {
                        "content": getattr(region, "text", ""),
                        "font": "detected",
                        "font size": 12,
                        "text color": "#000000",
                    }
                )

                # Add heading level if applicable
                if region_type == "heading":
                    level = getattr(region, "level", 1)
                    element["level"] = level

            elif region_type == "image":
                element.update(
                    {
                        "source": "",  # Will be filled during merge
                        "format": "png",
                    }
                )

            elif region_type == "list":
                element["kids"] = []

            return element

        except Exception as e:
            logger.warning(f"Failed to convert region: {e}")
            return None

    def _get_region_type(self, region: Any) -> str:
        """Map docling region type to JSON schema type.

        Args:
            region: Docling layout region.

        Returns:
            JSON schema element type.
        """
        type_mapping = {
            "text": "paragraph",
            "paragraph": "paragraph",
            "title": "heading",
            "heading": "heading",
            "section_header": "heading",
            "caption": "caption",
            "figure": "image",
            "image": "image",
            "table": "table",
            "list": "list",
            "list_item": "list item",
            "formula": "formula",
            "page_header": "header",
            "page_footer": "footer",
        }

        raw_type = getattr(region, "type", "paragraph")
        if isinstance(raw_type, str):
            return type_mapping.get(raw_type.lower(), "paragraph")
        return "paragraph"

    def _get_region_bbox(
        self,
        region: Any,
        img_width: int,
        img_height: int,
    ) -> list[float]:
        """Extract bounding box from region."""
        if hasattr(region, "bbox"):
            bbox = region.bbox
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
