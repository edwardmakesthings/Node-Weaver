"""StringWeaver operation pipeline."""

from typing import List, Tuple

import hou

from .operations.base import Operation
from .providers.base import Provider, WorkItem


class Pipeline:
    """Applies a sequence of operations to a list of work items.

    The pipeline takes items collected by a provider and transforms
    them through an ordered list of operations. It supports preview
    (dry run) and execute (with Houdini undo group).

    Example:
        >>> pipeline = Pipeline()
        >>> pipeline.set_items(provider.get_items(nodes))
        >>> pipeline.add_operation(replace_op)
        >>> for item, preview in pipeline.preview():
        ...     print(f"{item.original_value} -> {preview}")
        >>> pipeline.execute(provider)
    """

    def __init__(self) -> None:
        self._operations: List[Operation] = []
        self._items: List[WorkItem] = []

    @property
    def operations(self) -> List[Operation]:
        return list(self._operations)

    @property
    def items(self) -> List[WorkItem]:
        return list(self._items)

    def set_items(self, items: List[WorkItem]) -> None:
        self._items = list(items)

    def clear_items(self) -> None:
        self._items.clear()

    def set_operations(self, operations: List[Operation]) -> None:
        """Replace the current operation list.

        Args:
            operations: New ordered list of operations.
        """
        self._operations = list(operations)

    def add_operation(self, operation: Operation) -> None:
        self._operations.append(operation)

    def remove_operation(self, index: int) -> None:
        if 0 <= index < len(self._operations):
            self._operations.pop(index)

    def move_operation(self, from_index: int, to_index: int) -> None:
        if not (0 <= from_index < len(self._operations)):
            return
        to_index = max(0, min(to_index, len(self._operations) - 1))
        op = self._operations.pop(from_index)
        self._operations.insert(to_index, op)

    def clear_operations(self) -> None:
        self._operations.clear()

    def preview(self) -> List[Tuple[WorkItem, str]]:
        """Run all operations on all items without applying changes.

        Returns:
            List of (item, preview_value) tuples.
        """
        results: List[Tuple[WorkItem, str]] = []
        total = len(self._items)
        for i, item in enumerate(self._items):
            value = item.original_value
            for op in self._operations:
                op.set_item_context(i, total)
                value = op.transform(value)
            results.append((item, value))
        return results

    def preview_single(self, text: str) -> str:
        """Run all operations on a single string.

        Args:
            text: Input string.

        Returns:
            Transformed string.
        """
        for op in self._operations:
            text = op.transform(text)
        return text

    def execute(self, provider: Provider) -> int:
        """Apply all operations and write results back via the provider.

        Wraps all changes in a single Houdini undo group so the
        entire batch can be undone with one Ctrl+Z.

        Args:
            provider: Provider to use for writing values back.

        Returns:
            Number of items that were changed.
        """
        previews = self.preview()
        changed = 0

        with hou.undos.group("StringWeaver Batch Operation"):
            for item, new_value in previews:
                if new_value != item.original_value:
                    provider.apply_value(item, new_value)
                    changed += 1

        return changed
