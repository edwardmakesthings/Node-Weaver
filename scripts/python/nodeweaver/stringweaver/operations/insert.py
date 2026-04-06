"""Insert text at a specific character position."""

from typing import Any, Dict, List

from .base import Operation


class InsertOperation(Operation):
    """Insert text at an arbitrary character position.

    Position is 0-based. 0 is the same as prefix, a value beyond
    the string length acts as suffix.
    """

    def __init__(self) -> None:
        self.text: str = ""
        self.position: int = 0

    @property
    def name(self) -> str:
        return "Insert at Position"

    def transform(self, text: str) -> str:
        if not self.text:
            return text
        pos = max(0, min(self.position, len(text)))
        return text[:pos] + self.text + text[pos:]

    def get_config(self) -> Dict[str, Any]:
        return {"text": self.text, "position": self.position}

    def set_config(self, config: Dict[str, Any]) -> None:
        self.text = config.get("text", "")
        self.position = config.get("position", 0)

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "text", "label": "Text to Insert", "type": "text", "default": ""},
            {"name": "position", "label": "Position (0-based)", "type": "int", "default": 0, "min": 0},
        ]
