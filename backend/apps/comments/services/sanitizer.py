"""XSS-safe sanitizer for the task's allowed subset: a/code/i/strong.

Rules from the task:
- only <a href="" title="">, <code>, <i>, <strong> are allowed;
- tags must be properly closed, result must be valid XHTML;
- everything else is escaped.
"""

from __future__ import annotations

import re

import bleach

TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^<>]*>")
ALLOWED_TAGS = ["a", "code", "i", "strong"]
ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}
ALLOWED_PROTOCOLS = ["http", "https"]


class UnclosedTagError(ValueError):
    pass


def validate_tag_balance(raw: str) -> None:
    """Check that every allowed tag is properly opened and closed.

    Args:
        raw: Raw user markup.

    Raises:
        UnclosedTagError: On unclosed tags or mismatched closing tags.
    """
    stack: list[str] = []
    for is_close, name in _allowed_tag_events(raw):
        if not is_close:
            stack.append(name)
        elif not stack or stack.pop() != name:
            raise UnclosedTagError(f"Mismatched closing tag: </{name}>")
    if stack:
        raise UnclosedTagError(f"Unclosed tags: {stack}")


def _allowed_tag_events(raw: str):
    """Yield tag events for allowed tags in document order.

    Args:
        raw: Raw user markup.

    Yields:
        Tuples of (is_close, name) for each allowed tag occurrence.
    """
    for match in TAG_RE.finditer(raw):
        name = match.group(2).lower()
        if name in ALLOWED_TAGS:
            yield bool(match.group(1)), name


def sanitize(raw: str) -> str:
    """Validate tag balance and return XSS-safe XHTML.

    Args:
        raw: Raw user markup.

    Returns:
        Sanitized markup with allowed tags only; everything else escaped.

    Raises:
        UnclosedTagError: When allowed tags are unclosed or mismatched.
    """
    validate_tag_balance(raw)
    return bleach.clean(
        raw,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=False,  # disallowed tags are escaped, not stripped 
    )
