"""Provider for Houdini node names."""

from typing import List

import hou

from .base import Provider, WorkItem


class NodeNameProvider(Provider):
    """Reads and writes node names."""

    @property
    def name(self) -> str:
        return "Node Names"

    def get_items(self, nodes: List[hou.Node]) -> List[WorkItem]:
        return [
            WorkItem(
                node=node,
                source_path=node.path(),
                original_value=node.name(),
            )
            for node in nodes
        ]

    def apply_value(self, item: WorkItem, new_value: str) -> None:
        if new_value and new_value != item.original_value:
            item.node.setName(new_value, unique_name=True)
