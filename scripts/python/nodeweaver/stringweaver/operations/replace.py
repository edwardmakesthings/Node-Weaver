"""Find and replace operation."""

import re
from typing import Any, Dict, List

from .base import Operation


class ReplaceOperation(Operation):
    """Replace occurrences of a search string or regex pattern."""

    def __init__(self) -> None:
        self.search: str = ""
        self.replacement: str = ""
        self.case_sensitive: bool = True
        self.use_regex: bool = False

    @property
    def name(self) -> str:
        return "Find & Replace"

    def transform(self, text: str) -> str:
        if not self.search:
            return text

        if self.use_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                return re.sub(self.search, self.replacement, text, flags=flags)
            except re.error:
                return text

        if self.case_sensitive:
            return text.replace(self.search, self.replacement)

        # Case-insensitive non-regex replace
        pattern = re.escape(self.search)
        return re.sub(pattern, self.replacement, text, flags=re.IGNORECASE)

    def get_config(self) -> Dict[str, Any]:
        return {
            "search": self.search,
            "replacement": self.replacement,
            "case_sensitive": self.case_sensitive,
            "use_regex": self.use_regex,
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        self.search = config.get("search", "")
        self.replacement = config.get("replacement", "")
        self.case_sensitive = config.get("case_sensitive", True)
        self.use_regex = config.get("use_regex", False)

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "search", "label": "Search", "type": "text", "default": ""},
            {"name": "replacement", "label": "Replace", "type": "text", "default": ""},
            {"name": "case_sensitive", "label": "Case Sensitive", "type": "bool", "default": True},
            {"name": "use_regex", "label": "Use Regex", "type": "bool", "default": False},
        ]
