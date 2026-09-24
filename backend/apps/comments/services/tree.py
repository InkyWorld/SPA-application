"""Build a nested tree from a flat queryset (avoids N+1, no recursion in SQL)."""

from __future__ import annotations

from apps.comments.models import Comment


def build_tree(comments: list[Comment]) -> list[dict]:
    """Group a flat comment list into nested {comment, replies} nodes.

    Args:
        comments: Flat list of comments, each with a real pk
            (production invariant: the input always comes from the DB).

    Returns:
        Forest of root nodes; each node holds the comment and its
        recursively nested replies.
    """
    by_parent: dict[int | None, list[Comment]] = {}
    for comment in comments:
        by_parent.setdefault(comment.parent_id, []).append(comment)
    return [_node(c, by_parent) for c in by_parent.get(None, [])]


def _node(comment: Comment, by_parent: dict) -> dict:
    """Recursively wrap a comment with its nested replies.

    Args:
        comment: Comment to wrap.
        by_parent: Mapping of parent pk to child comment lists.

    Returns:
        Dict with the comment and its nested "replies" list.
    """
    return {
        "comment": comment,
        "replies": [_node(c, by_parent) for c in by_parent.get(comment.pk, [])],
    }
