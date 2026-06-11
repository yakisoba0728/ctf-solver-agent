"""Flag pattern matching — extract and validate CTF flags from text."""

from __future__ import annotations

import re

DEFAULT_FLAG_PATTERN = r"([Ff][Ll][Aa][Gg]|[Cc][Tt][Ff])\{([^}]+)\}"


def extract_flags(text: str, pattern: str = DEFAULT_FLAG_PATTERN) -> list[str]:
    """Extract unique flags from text using regex pattern. Preserves order."""
    seen: set[str] = set()
    results: list[str] = []
    for match in re.finditer(pattern, text):
        flag = match.group(0)
        if flag not in seen:
            seen.add(flag)
            results.append(flag)
    return results
