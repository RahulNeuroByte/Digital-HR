"""Text normalization that preserves meaning without destroying structure."""
from __future__ import annotations

import re


def clean_text(raw: str) -> str:
    """
    Normalize whitespace while keeping paragraph/heading breaks intact.

    - Collapses runs of spaces/tabs.
    - Collapses 3+ blank lines down to a single blank line (keeps
      paragraph separation, drops excessive PDF-export whitespace).
    - Strips trailing whitespace per line.
    """
    if not raw:
        return ""

    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
