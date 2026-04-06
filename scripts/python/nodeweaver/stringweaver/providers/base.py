"""Base provider and work item definitions for StringWeaver."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import hou


@dataclass
class WorkItem:
    """A single item to be processed by the pipeline.

    Attributes:
        source_path: Display path (node path, parameter path, or file path).
        original_value: The string value before any operations.
        node: The Houdini node this item came from (None for file-based items).
        parm: Optional parameter reference (for parameter providers).
    """
    source_path: str
    original_value: str
    node: Optional[hou.Node] = None
    parm: Optional[hou.Parm] = None


class Provider(ABC):
    """Extracts string values from Houdini objects for processing.

    Providers bridge Houdini's data model and StringWeaver's
    string-based operations. Each provider type knows how to
    read values from and write values back to a specific source.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name for this provider."""

    @property
    def needs_node_scope(self) -> bool:
        """Whether this provider collects from Houdini nodes.

        Override to return False for providers that work with
        external data (e.g. file paths on disk).
        """
        return True

    @abstractmethod
    def get_items(self, nodes: List[hou.Node]) -> List[WorkItem]:
        """Extract processable items from the given nodes.

        Args:
            nodes: Houdini nodes to extract values from.

        Returns:
            List of WorkItems with their current string values.
        """

    @abstractmethod
    def apply_value(self, item: WorkItem, new_value: str) -> None:
        """Write a transformed value back to Houdini.

        Args:
            item: The work item to update.
            new_value: The new string value to set.
        """
