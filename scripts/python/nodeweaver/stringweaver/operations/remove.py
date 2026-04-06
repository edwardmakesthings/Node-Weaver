"""Remove operations — strip characters by position, range, or content."""

from typing import Any, Dict, List

from .base import Operation


class RemoveOperation(Operation):
    """Remove characters from a string by various methods.

    Modes:
        first_n: Remove the first N characters.
        last_n: Remove the last N characters.
        range: Remove characters from position X to Y (inclusive, 1-based).
        characters: Remove all occurrences of specific characters.
        words: Remove all occurrences of specific words.
    """

    def __init__(self) -> None:
        self.mode: str = "first_n"
        self.count: int = 0
        self.from_pos: int = 1
        self.to_pos: int = 1
        self.characters: str = ""
        self.words: str = ""

    @property
    def name(self) -> str:
        return "Remove"

    def transform(self, text: str) -> str:
        if self.mode == "first_n":
            return text[self.count:] if self.count > 0 else text

        if self.mode == "last_n":
            return text[:-self.count] if self.count > 0 else text

        if self.mode == "range":
            start = max(self.from_pos - 1, 0)
            end = max(self.to_pos, start)
            return text[:start] + text[end:]

        if self.mode == "characters":
            if not self.characters:
                return text
            return "".join(c for c in text if c not in self.characters)

        if self.mode == "words":
            if not self.words:
                return text
            result = text
            for word in self.words.split(","):
                word = word.strip()
                if word:
                    result = result.replace(word, "")
            return result

        return text

    def get_config(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "count": self.count,
            "from_pos": self.from_pos,
            "to_pos": self.to_pos,
            "characters": self.characters,
            "words": self.words,
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        self.mode = config.get("mode", "first_n")
        self.count = config.get("count", 0)
        self.from_pos = config.get("from_pos", 1)
        self.to_pos = config.get("to_pos", 1)
        self.characters = config.get("characters", "")
        self.words = config.get("words", "")

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "mode",
                "label": "Remove Mode",
                "type": "choice",
                "default": "first_n",
                "options": [
                    ("first_n", "First N Characters"),
                    ("last_n", "Last N Characters"),
                    ("range", "Character Range"),
                    ("characters", "Specific Characters"),
                    ("words", "Specific Words"),
                ],
            },
            {
                "name": "count", "label": "Count", "type": "int",
                "default": 0, "min": 0,
                "visible_when": {"field": "mode", "value": ["first_n", "last_n"]},
            },
            {
                "name": "from_pos", "label": "From Position", "type": "int",
                "default": 1, "min": 1,
                "visible_when": {"field": "mode", "value": "range"},
            },
            {
                "name": "to_pos", "label": "To Position", "type": "int",
                "default": 1, "min": 1,
                "visible_when": {"field": "mode", "value": "range"},
            },
            {
                "name": "characters", "label": "Characters", "type": "text",
                "default": "",
                "visible_when": {"field": "mode", "value": "characters"},
            },
            {
                "name": "words", "label": "Words (comma-separated)", "type": "text",
                "default": "",
                "visible_when": {"field": "mode", "value": "words"},
            },
        ]


class StripOperation(Operation):
    """Remove specific text from the start and/or end of each value."""

    def __init__(self) -> None:
        self.strip_text: str = ""
        self.mode: str = "both"

    @property
    def name(self) -> str:
        return "Strip Text"

    def transform(self, text: str) -> str:
        if not self.strip_text:
            return text
        result = text
        if self.mode in ("prefix", "both") and result.startswith(self.strip_text):
            result = result[len(self.strip_text):]
        if self.mode in ("suffix", "both") and result.endswith(self.strip_text):
            result = result[:-len(self.strip_text)]
        return result

    def get_config(self) -> Dict[str, Any]:
        return {"strip_text": self.strip_text, "mode": self.mode}

    def set_config(self, config: Dict[str, Any]) -> None:
        self.strip_text = config.get("strip_text", "")
        self.mode = config.get("mode", "both")

    @classmethod
    def config_fields(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "strip_text", "label": "Text to Strip", "type": "text", "default": ""},
            {
                "name": "mode",
                "label": "Strip From",
                "type": "choice",
                "default": "both",
                "options": [
                    ("both", "Both Ends"),
                    ("prefix", "Start Only"),
                    ("suffix", "End Only"),
                ],
            },
        ]
