"""Regex extract operation - keep only the matched portion of a string."""

import re
from typing import Any, Dict, List

from .base import Operation


class RegexExtractOperation(Operation):
    """Extract the portion of a string matching a regex pattern.

    When a capture group is present the first group is returned;
    otherwise the entire match is used.  If nothing matches, the
    fallback value is returned (empty string by default).
    """

    def __init__(self) -> None:
        self.pattern: str = ""
        self.fallback: str = ""

    @property
    def name(self) -> str:
        return "Regex Extract"

    def transform(self, text: str) -> str:
        if not self.pattern:
            return text

        try:
            match = re.search(self.pattern, text)
        except re.error:
            return text

        if match is None:
            return self.fallback

        # Use first capture group if present, otherwise full match
        if match.lastindex:
            return match.group(1)
        return match.group(0)

    def get_config(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "fallback": self.fallback,
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        self.pattern = config.get("pattern", "")
        self.fallback = config.get("fallback", "")

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "pattern", "label": "Pattern", "type": "text", "default": ""},
            {"name": "fallback", "label": "No Match", "type": "text", "default": ""},
        ]
