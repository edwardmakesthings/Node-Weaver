"""Truncate and slice operations — limit string length or extract substrings."""

from typing import Any, Dict, List

from .base import Operation


class TruncateOperation(Operation):
    """Truncate a string to a maximum length, or extract a substring slice.

    Modes:
        truncate_start: Keep the first N characters.
        truncate_end: Keep the last N characters.
        slice: Keep characters from position X to Y (0-based, inclusive).
    """

    def __init__(self) -> None:
        self.mode: str = "truncate_start"
        self.max_length: int = 10
        self.from_pos: int = 0
        self.to_pos: int = 10

    @property
    def name(self) -> str:
        return "Truncate / Slice"

    def transform(self, text: str) -> str:
        if self.mode == "truncate_start":
            return text[:self.max_length]

        if self.mode == "truncate_end":
            return text[-self.max_length:] if self.max_length > 0 else ""

        if self.mode == "slice":
            start = max(self.from_pos, 0)
            end = self.to_pos + 1  # inclusive → exclusive
            return text[start:end]

        return text

    def get_config(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "max_length": self.max_length,
            "from_pos": self.from_pos,
            "to_pos": self.to_pos,
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        self.mode = config.get("mode", "truncate_start")
        self.max_length = config.get("max_length", 10)
        self.from_pos = config.get("from_pos", 0)
        self.to_pos = config.get("to_pos", 10)

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "mode",
                "label": "Mode",
                "type": "choice",
                "default": "truncate_start",
                "options": [
                    ("truncate_start", "Keep First N"),
                    ("truncate_end", "Keep Last N"),
                    ("slice", "Slice (From / To)"),
                ],
            },
            {
                "name": "max_length", "label": "Max Length", "type": "int",
                "default": 10, "min": 0,
                "visible_when": {"field": "mode", "value": ["truncate_start", "truncate_end"]},
            },
            {
                "name": "from_pos", "label": "From Position", "type": "int",
                "default": 0, "min": 0,
                "visible_when": {"field": "mode", "value": "slice"},
            },
            {
                "name": "to_pos", "label": "To Position", "type": "int",
                "default": 10, "min": 0,
                "visible_when": {"field": "mode", "value": "slice"},
            },
        ]
