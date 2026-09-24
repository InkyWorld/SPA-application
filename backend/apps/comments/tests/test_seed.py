"""Integration tests: seed_comments management command."""

from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase

from apps.comments.models import Comment


class SeedCommandTests(TestCase):
    def test_default_seeds_two_pages_with_trees(self):
        """Default seed creates 30 tops with nested reply trees."""
        call_command("seed_comments")
        tops = Comment.objects.filter(level=0)
        self.assertEqual(tops.count(), 30)
        with_replies = sum(1 for top in tops if top.get_children().exists())
        self.assertGreater(with_replies, 0)
        deepest = max(
            (reply.level for reply in Comment.objects.exclude(level=0)), default=0
        )
        self.assertGreaterEqual(deepest, 2)

    def test_custom_count(self):
        """The --count option controls how many tops are seeded."""
        call_command("seed_comments", count=3)
        self.assertEqual(Comment.objects.filter(level=0).count(), 3)

    def test_rerun_replaces_data(self):
        """Re-running the seed wipes previous data instead of appending."""
        call_command("seed_comments", count=3)
        call_command("seed_comments", count=2)
        self.assertEqual(Comment.objects.filter(level=0).count(), 2)
