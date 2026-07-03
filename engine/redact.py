import re
from typing import List


class Redactor:
    """Replaces client-identifying terms with a single alias before any content leaves the
    sovereign boundary. Whole-token, case-insensitive; longer terms first so a name that
    contains a shorter one does not leave a fragment behind."""

    def __init__(self, alias: str, terms: List[str]):
        self.alias = alias
        ordered = sorted({t for t in terms if t}, key=len, reverse=True)
        if ordered:
            pattern = "|".join(re.escape(t) for t in ordered)
            self._rx = re.compile(r"(?<!\w)(?:" + pattern + r")(?!\w)", re.IGNORECASE)
        else:
            self._rx = None

    def redact(self, text: str) -> str:
        if self._rx is None:
            return text
        return self._rx.sub(self.alias, text)
