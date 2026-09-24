"""Integration tests: list cache hit and invalidation on create."""

from __future__ import annotations

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.comments import selectors
from apps.comments.models import Comment
from apps.comments.tests.helpers import post_comment


class ListCacheVersionTests(TestCase):
    def test_bump_changes_key(self):
        """Bumping the version retires the previous cache key."""
        before = selectors.list_cache_key(None, 1)
        selectors.bump_list_cache_version()
        self.assertNotEqual(before, selectors.list_cache_key(None, 1))


class ListCacheTests(TestCase):
    def test_second_identical_list_hits_cache(self):
        """A repeated list request touches no comment tables."""
        Comment.objects.all().delete()
        post_comment(self.client)
        self.client.get("/api/comments/")
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/comments/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            [q for q in ctx if "comments_comment" in q["sql"]],
            "cached list must not query comment tables",
        )

    def test_create_invalidates_cache(self):
        """A new comment appears in the list right after creation."""
        Comment.objects.all().delete()
        before = self.client.get("/api/comments/").json()["count"]
        post_comment(self.client)
        after = self.client.get("/api/comments/").json()["count"]
        self.assertEqual(after, before + 1)
