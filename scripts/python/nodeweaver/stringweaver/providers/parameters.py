"""Providers for Houdini parameter values."""

from typing import List

import hou

from .base import Provider, WorkItem


class StringParameterProvider(Provider):
    """Reads and writes string parameter values."""

    def __init__(self) -> None:
        self.use_labels: bool = True

    @property
    def name(self) -> str:
        return "String Parameters"

    def get_items(self, nodes: List[hou.Node]) -> List[WorkItem]:
        items: List[WorkItem] = []
        for node in nodes:
            for parm in node.parms():
                if not isinstance(parm.parmTemplate(), hou.StringParmTemplate):
                    continue
                value = parm.eval()
                if not value:
                    continue
                if self.use_labels:
                    display = parm.parmTemplate().label()
                    source = f"{node.path()}/{display}"
                else:
                    source = parm.path()
                items.append(WorkItem(
                    node=node,
                    source_path=source,
                    original_value=str(value),
                    parm=parm,
                ))
        return items

    def apply_value(self, item: WorkItem, new_value: str) -> None:
        if item.parm is not None and new_value != item.original_value:
            item.parm.set(new_value)


class ExpressionProvider(Provider):
    """Reads and writes parameter expression values."""

    def __init__(self) -> None:
        self.use_labels: bool = True

    @property
    def name(self) -> str:
        return "Expressions"

    def get_items(self, nodes: List[hou.Node]) -> List[WorkItem]:
        items: List[WorkItem] = []
        for node in nodes:
            for parm in node.parms():
                try:
                    expr = parm.expression()
                except hou.OperationFailed:
                    continue
                if not expr:
                    continue
                if self.use_labels:
                    display = parm.parmTemplate().label()
                    source = f"{node.path()}/{display}"
                else:
                    source = parm.path()
                items.append(WorkItem(
                    node=node,
                    source_path=source,
                    original_value=expr,
                    parm=parm,
                ))
        return items

    def apply_value(self, item: WorkItem, new_value: str) -> None:
        if item.parm is None or new_value == item.original_value:
            return
        try:
            lang = item.parm.expressionLanguage()
        except hou.OperationFailed:
            lang = hou.exprLanguage.Python
        item.parm.setExpression(new_value, lang)
