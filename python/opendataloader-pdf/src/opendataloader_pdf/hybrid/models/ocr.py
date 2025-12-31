"""
OCR model adapter for text extraction from images.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from ..config import OCRConfig
from .base import BaseModelAdapter

logger = logging.getLogger(__name__)


class OCRAdapter(BaseModelAdapter):
    """Adapter for OCR models (RapidOCR or Tesseract).

    Extracts text from page images when the page is identified
    as needing OCR (scanned content, image-heavy pages, etc.).
    """

    def __init__(self, config: Optional[OCRConfig] = None) -> None:
        super().__init__()
        self.config = config or OCRConfig()
        self._engine_name = self.config.engine

    def _load_model(self) -> None:
        """Load the OCR engine."""
        if self._engine_name == "rapidocr":
            self._load_rapidocr()
        elif self._engine_name == "tesseract":
            self._load_tesseract()
        else:
            raise ValueError(f"Unknown OCR engine: {self._engine_name}")

    def _load_rapidocr(self) -> None:
        """Load RapidOCR engine."""
        try:
            from rapidocr_onnxruntime import RapidOCR

            self._model = RapidOCR()
            logger.info("Loaded RapidOCR engine")
        except ImportError as e:
            raise ImportError(
                "RapidOCR is not installed. Install with: pip install rapidocr-onnxruntime"
            ) from e

    def _load_tesseract(self) -> None:
        """Load Tesseract engine via pytesseract."""
        try:
            import pytesseract

            # Verify tesseract is installed
            pytesseract.get_tesseract_version()
            self._model = pytesseract
            logger.info("Loaded Tesseract engine")
        except ImportError as e:
            raise ImportError(
                "pytesseract is not installed. Install with: pip install pytesseract"
            ) from e

    def process(self, image_path: Path, page_number: int) -> dict[str, Any]:
        """Extract text from a page image using OCR.

        Args:
            image_path: Path to the page image.
            page_number: The page number (0-indexed).

        Returns:
            Dictionary with extracted text blocks in JSON schema format.
        """
        self.ensure_loaded()

        if self._engine_name == "rapidocr":
            return self._process_rapidocr(image_path, page_number)
        else:
            return self._process_tesseract(image_path, page_number)

    def _process_rapidocr(self, image_path: Path, page_number: int) -> dict[str, Any]:
        """Process image with RapidOCR."""
        from PIL import Image

        img = Image.open(image_path)
        result, _ = self._model(img)

        elements: list[dict[str, Any]] = []

        if result:
            for box, text, confidence in result:
                if confidence < 0.3:  # Skip low confidence results
                    continue

                # box is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]
                bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]

                elements.append(
                    {
                        "type": "paragraph",
                        "page number": page_number + 1,  # 1-indexed for output
                        "bounding box": bbox,
                        "content": text,
                        "font": "OCR",
                        "font size": 12,  # Default, actual size unknown from OCR
                        "text color": "#000000",
                        "hidden text": False,
                    }
                )

        return {"elements": elements, "source": "ocr"}

    def _process_tesseract(self, image_path: Path, page_number: int) -> dict[str, Any]:
        """Process image with Tesseract."""
        from PIL import Image

        img = Image.open(image_path)
        lang = self.config.language

        # Get detailed data with bounding boxes
        data = self._model.image_to_data(img, lang=lang, output_type=self._model.Output.DICT)

        elements: list[dict[str, Any]] = []
        current_line: list[str] = []
        current_bbox: Optional[list[float]] = None

        for i, text in enumerate(data["text"]):
            if not text.strip():
                # Empty text, possibly end of line
                if current_line and current_bbox:
                    elements.append(
                        {
                            "type": "paragraph",
                            "page number": page_number + 1,
                            "bounding box": current_bbox,
                            "content": " ".join(current_line),
                            "font": "OCR",
                            "font size": 12,
                            "text color": "#000000",
                            "hidden text": False,
                        }
                    )
                    current_line = []
                    current_bbox = None
                continue

            conf = int(data["conf"][i])
            if conf < 30:  # Skip low confidence
                continue

            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            bbox = [x, y, x + w, y + h]

            if current_bbox is None:
                current_bbox = bbox
                current_line = [text]
            else:
                # Extend bounding box
                current_bbox[0] = min(current_bbox[0], bbox[0])
                current_bbox[1] = min(current_bbox[1], bbox[1])
                current_bbox[2] = max(current_bbox[2], bbox[2])
                current_bbox[3] = max(current_bbox[3], bbox[3])
                current_line.append(text)

        # Add remaining line
        if current_line and current_bbox:
            elements.append(
                {
                    "type": "paragraph",
                    "page number": page_number + 1,
                    "bounding box": current_bbox,
                    "content": " ".join(current_line),
                    "font": "OCR",
                    "font size": 12,
                    "text color": "#000000",
                    "hidden text": False,
                }
            )

        return {"elements": elements, "source": "ocr"}
