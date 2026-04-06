"""Numbering operation — add sequential numbers to items."""

from typing import Any, Dict, List

from .base import Operation


class NumberingOperation(Operation):
    """Add a sequential number to each item in the batch.

    The number is derived from the item's position in the list,
    set via ``set_item_context()`` by the pipeline before each
    ``transform()`` call.

    Modes:
        prefix: Number before the original text.
        suffix: Number after the original text.
        insert: Number inserted at a character position.

    Configuration:
        start: First number in the sequence.
        increment: Step between consecutive items.
        padding: Minimum digit width (zero-padded).
        separator: String placed between the number and original text.
        position: Character index for insert mode.
    """

    def __init__(self) -> None:
        self.mode: str = "suffix"
        self.start: int = 1
        self.increment: int = 1
        self.padding: int = 1
        self.separator: str = "_"
        self.position: int = 0
        self._index: int = 0
        self._total: int = 1

    @property
    def name(self) -> str:
        return "Numbering"

    def set_item_context(self, index: int, total: int) -> None:
        self._index = index
        self._total = total

    def _formatted_number(self) -> str:
        value = self.start + (self._index * self.increment)
        return str(value).zfill(self.padding)

    def transform(self, text: str) -> str:
        num = self._formatted_number()

        if self.mode == "prefix":
            return num + self.separator + text

        if self.mode == "suffix":
            return text + self.separator + num

        if self.mode == "insert":
            pos = max(0, min(self.position, len(text)))
            return text[:pos] + self.separator + num + self.separator + text[pos:]

        return text

    def get_config(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "start": self.start,
            "increment": self.increment,
            "padding": self.padding,
            "separator": self.separator,
            "position": self.position,
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        self.mode = config.get("mode", "suffix")
        self.start = config.get("start", 1)
        self.increment = config.get("increment", 1)
        self.padding = config.get("padding", 1)
        self.separator = config.get("separator", "_")
        self.position = config.get("position", 0)

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "mode",
                "label": "Number Position",
                "type": "choice",
                "default": "suffix",
                "options": [
                    ("prefix", "Prefix"),
                    ("suffix", "Suffix"),
                    ("insert", "Insert at Position"),
                ],
            },
            {"name": "start", "label": "Start At", "type": "int", "default": 1},
            {"name": "increment", "label": "Increment", "type": "int", "default": 1},
            {"name": "padding", "label": "Padding (digits)", "type": "int", "default": 1, "min": 1, "max": 10},
            {"name": "separator", "label": "Separator", "type": "text", "default": "_"},
            {
                "name": "position", "label": "Insert Position", "type": "int",
                "default": 0, "min": 0,
                "visible_when": {"field": "mode", "value": "insert"},
            },
        ]
