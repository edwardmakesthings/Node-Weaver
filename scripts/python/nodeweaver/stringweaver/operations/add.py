"""Add text operation — prefix, suffix, or insert at position."""

from typing import Any, Dict, List

from .base import Operation


class AddOperation(Operation):
    """Add text as a prefix, suffix, or inserted at a specific position.

    Modes:
        prefix: Prepend text to the beginning.
        suffix: Append text to the end.
        insert: Insert text at a 0-based character position.
    """

    def __init__(self) -> None:
        self.text: str = ""
        self.placement: str = "prefix"
        self.position: int = 0

    @property
    def name(self) -> str:
        return "Add Text"

    def transform(self, text: str) -> str:
        if not self.text:
            return text
        if self.placement == "prefix":
            return self.text + text
        if self.placement == "suffix":
            return text + self.text
        # insert
        pos = max(0, min(self.position, len(text)))
        return text[:pos] + self.text + text[pos:]

    def get_config(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "placement": self.placement,
            "position": self.position,
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        self.text = config.get("text", "")
        self.placement = config.get("placement", "prefix")
        self.position = config.get("position", 0)

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "text", "label": "Text", "type": "text", "default": ""},
            {
                "name": "placement",
                "label": "Placement",
                "type": "choice",
                "default": "prefix",
                "options": [
                    ("prefix", "Prefix"),
                    ("suffix", "Suffix"),
                    ("insert", "Insert at Position"),
                ],
            },
            {
                "name": "position",
                "label": "Position (0-based)",
                "type": "int",
                "default": 0,
                "min": 0,
                "visible_when": {"field": "placement", "value": "insert"},
            },
        ]
