"""Base class for StringWeaver string transformation operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class Operation(ABC):
    """A single string transformation step.

    Operations are pure string transformers with no knowledge of Houdini.
    This keeps them testable, composable, and reusable.

    Subclasses must implement:
        name: Display name for the operation type.
        transform: The actual string transformation.
        get_config / set_config: Serialization of operation parameters.
        config_fields: Field descriptors for dynamic UI generation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name for this operation type."""

    @abstractmethod
    def transform(self, text: str) -> str:
        """Apply this operation to a string.

        Args:
            text: Input string to transform.

        Returns:
            Transformed string.
        """

    def set_item_context(self, index: int, total: int) -> None:
        """Called by the pipeline before transform() for each item.

        Override in operations that need positional awareness
        (e.g. numbering). Default is a no-op.

        Args:
            index: Zero-based position of the current item.
            total: Total number of items in the batch.
        """

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Return current configuration as a serializable dict."""

    @abstractmethod
    def set_config(self, config: Dict[str, Any]) -> None:
        """Restore configuration from a dict."""

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        """Field descriptors for automatic UI generation.

        Each field is a dict with:
            name: Config key (must match get_config/set_config keys).
            label: Display label.
            type: One of "text", "bool", "choice".
            default: Default value.
            options: For "choice" type, list of (value, label) tuples.

        Returns:
            List of field descriptor dicts.
        """
        return []
