"""
Model adapters for AI processing in hybrid pipeline.
"""

from .base import BaseModelAdapter, ModelRegistry
from .layout import LayoutAdapter
from .ocr import OCRAdapter
from .table import TableAdapter

__all__ = [
    "BaseModelAdapter",
    "ModelRegistry",
    "OCRAdapter",
    "TableAdapter",
    "LayoutAdapter",
]
