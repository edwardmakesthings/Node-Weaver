"""Case transformation operations."""

import re
from typing import Any, Dict, List

from .base import Operation


class CaseOperation(Operation):
    """Convert string case (lower, upper, title, camel, snake, pascal)."""

    MODES = {
        "lower": "lowercase",
        "upper": "UPPERCASE",
        "title": "Title Case",
        "camel": "camelCase",
        "snake": "snake_case",
        "pascal": "PascalCase",
    }

    def __init__(self) -> None:
        self.mode: str = "lower"

    @property
    def name(self) -> str:
        return "Change Case"

    def transform(self, text: str) -> str:
        if self.mode == "lower":
            return text.lower()
        if self.mode == "upper":
            return text.upper()
        if self.mode == "title":
            return text.title()
        if self.mode == "snake":
            return self._to_snake(text)
        if self.mode == "camel":
            return self._to_camel(text)
        if self.mode == "pascal":
            return self._to_pascal(text)
        return text

    @staticmethod
    def _to_snake(text: str) -> str:
        s = re.sub(r'[\s\-\.]+', '_', text)
        s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)
        s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
        return s.lower().strip('_')

    @staticmethod
    def _to_camel(text: str) -> str:
        parts = re.split(r'[\s_\-\.]+', text)
        if not parts:
            return text
        return parts[0].lower() + ''.join(w.capitalize() for w in parts[1:])

    @staticmethod
    def _to_pascal(text: str) -> str:
        parts = re.split(r'[\s_\-\.]+', text)
        return ''.join(w.capitalize() for w in parts)

    def get_config(self) -> Dict[str, Any]:
        return {"mode": self.mode}

    def set_config(self, config: Dict[str, Any]) -> None:
        self.mode = config.get("mode", "lower")

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "mode",
                "label": "Case Style",
                "type": "choice",
                "default": "lower",
                "options": list(cls.MODES.items()),
            },
        ]
