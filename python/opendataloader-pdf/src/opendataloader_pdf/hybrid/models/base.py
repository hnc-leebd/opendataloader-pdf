"""
Base class and registry for model adapters.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, TypeVar

T = TypeVar("T", bound="BaseModelAdapter")


class ModelRegistry:
    """Singleton registry for model adapters.

    Ensures each model type is instantiated only once (lazy loading).
    """

    _instances: dict[str, "BaseModelAdapter"] = {}

    @classmethod
    def get(cls, adapter_class: type[T], **kwargs: Any) -> T:
        """Get or create a model adapter instance.

        Args:
            adapter_class: The adapter class to instantiate.
            **kwargs: Configuration arguments for the adapter.

        Returns:
            The adapter instance.
        """
        key = adapter_class.__name__
        if key not in cls._instances:
            cls._instances[key] = adapter_class(**kwargs)
        return cls._instances[key]  # type: ignore

    @classmethod
    def clear(cls) -> None:
        """Clear all cached model instances."""
        cls._instances.clear()


class BaseModelAdapter(ABC):
    """Abstract base class for AI model adapters.

    All model adapters must implement the process method.
    Models are loaded lazily on first use.
    """

    def __init__(self) -> None:
        self._model: Optional[Any] = None

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._model is not None

    def ensure_loaded(self) -> None:
        """Ensure the model is loaded."""
        if not self.is_loaded:
            self._load_model()

    @abstractmethod
    def _load_model(self) -> None:
        """Load the model. Called lazily on first use."""
        pass

    @abstractmethod
    def process(self, image_path: Path, page_number: int) -> dict[str, Any]:
        """Process a page image and return extracted content.

        Args:
            image_path: Path to the page image file.
            page_number: The page number (0-indexed).

        Returns:
            Dictionary containing extracted content in JSON schema format.
        """
        pass

    def cleanup(self) -> None:
        """Clean up model resources."""
        self._model = None
