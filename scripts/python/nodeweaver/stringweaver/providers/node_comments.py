"""Provider for Houdini node comments."""

from typing import List

import hou

from .base import Provider, WorkItem


class NodeCommentProvider(Provider):
    """Reads and writes node comments."""

    @property
    def name(self) -> str:
        return "Node Comments"

    def get_items(self, nodes: List[hou.Node]) -> List[WorkItem]:
        items: List[WorkItem] = []
        for node in nodes:
            comment = node.comment()
            if comment:
                items.append(
                    WorkItem(
                        node=node,
                        source_path=node.path(),
                        original_value=comment,
                    )
                )
        return items

    def apply_value(self, item: WorkItem, new_value: str) -> None:
        if new_value != item.original_value:
            item.node.setComment(new_value)
