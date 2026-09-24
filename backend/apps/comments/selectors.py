"""Read-side queries (Selector pattern): all list/sort logic in one place.

Sortable fields per task: user_name, email, created_at — asc or desc.
Default ordering is LIFO (Meta.ordering). Pagination: 25 top-level / page.
"""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db.models import QuerySet

from apps.comments.models import Comment

SORTABLE_FIELDS = {"user_name", "email", "created_at"}
LIST_CACHE_VERSION_KEY = "comments:list:version"


def parse_sort_param(raw: str | None) -> list[str]:
    """Parse a `?sort=` value into ORM ordering.

    Args:
        raw: Raw query value, e.g. "user_name,-created_at".

    Returns:
        List of ORM order fields; unknown input falls back to LIFO.
    """
    if not raw:
        return ["-created_at"]
    fields = [f.strip() for f in raw.split(",") if f.strip()]
    cleaned = [f for f in fields if f.lstrip("-") in SORTABLE_FIELDS]
    return cleaned or ["-created_at"]


def list_cache_key(sort: str | None, page: int) -> str:
    """Build a versioned cache key for a comment list page.

    Args:
        sort: Raw `?sort=` value.
        page: 1-based page number.

    Returns:
        Cache key invalidated by every create via version bump.
    """
    version = cache.get_or_set(LIST_CACHE_VERSION_KEY, 1)
    return f"comments:list:v{version}:{sort or ''}:{page}"


def bump_list_cache_version() -> None:
    """Invalidate all cached list pages by bumping the key version."""
    try:
        cache.incr(LIST_CACHE_VERSION_KEY)
    except ValueError:
        cache.set(LIST_CACHE_VERSION_KEY, 1, timeout=None)


def list_cache_ttl() -> int:
    """Return the list cache TTL in seconds.

    Returns:
        TTL from settings.
    """
    return settings.COMMENTS_LIST_CACHE_TTL


def top_level_qs(sort: str | None = None) -> QuerySet[Comment]:
    """Return top-level comments ordered by the requested sort.

    Args:
        sort: Raw `?sort=` value; None means LIFO default.

    Returns:
        Queryset of comments with no parent, in the requested order.
    """
    return Comment.objects.filter(level=0).order_by(*parse_sort_param(sort))


def subtree_for_parents(parent_ids: list[int]) -> QuerySet[Comment]:
    """Return descendants of the given top-level ids in thread order.

    Args:
        parent_ids: Pks of the top-level comments on the page.

    Returns:
        Queryset of all descendants (any depth), ordered parent-first.
    """
    if not parent_ids:
        return Comment.objects.none()
    return Comment.objects.filter(
        tree_id__in=Comment.objects.filter(pk__in=parent_ids).values_list("tree_id", flat=True)
    ).exclude(pk__in=parent_ids).select_related("parent").order_by("tree_id", "lft")
