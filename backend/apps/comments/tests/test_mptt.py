"""Integration tests: MPTT tree integrity (levels, nesting, cascade delete)."""

from __future__ import annotations

from django.test import TestCase

from apps.comments import selectors
from apps.comments.models import Comment
from apps.comments.services.comments import CommentCreator, CreateCommentInput


def make_comment(user_name: str, parent_id: int | None = None) -> Comment:
    """Create a comment and refresh it (MPTT updates tree fields on save).

    Args:
        user_name: Name for the new comment.
        parent_id: Pk of the parent comment, if this is a reply.

    Returns:
        Saved comment with fresh MPTT fields.
    """
    comment = CommentCreator().execute(
        CreateCommentInput(
            user_name=user_name, email=f"{user_name}@x.cc", text="hi",
            parent_id=parent_id,
        )
    )
    comment.refresh_from_db()
    return comment


class MpttIntegrityTests(TestCase):
    def test_levels_and_shared_tree(self):
        """Replies share the root tree with consistent levels and nesting."""
        top = make_comment("top1")
        mid = make_comment("mid1", parent_id=top.pk)
        leaf = make_comment("leaf1", parent_id=mid.pk)
        top.refresh_from_db()
        mid.refresh_from_db()
        leaf.refresh_from_db()
        self.assertEqual((top.level, mid.level, leaf.level), (0, 1, 2))
        self.assertEqual(mid.tree_id, top.tree_id)
        self.assertEqual(leaf.tree_id, top.tree_id)
        self.assertTrue(top.lft < mid.lft < leaf.lft < leaf.rght < mid.rght < top.rght)

    def test_separate_roots_have_distinct_trees(self):
        """Two top-level comments land in different MPTT trees."""
        Comment.objects.all().delete()  # ensure a clean slate
        first = make_comment("root1")
        second = make_comment("root2")
        # Re-fetch: ordered root insertion renumbers existing trees on disk,
        # so in-memory tree fields go stale after later inserts.
        first = Comment.objects.get(pk=first.pk)
        second = Comment.objects.get(pk=second.pk)
        self.assertNotEqual(first.tree_id, second.tree_id)
        self.assertEqual(
            list(selectors.top_level_qs().values_list("pk", flat=True).order_by("pk")),
            sorted([first.pk, second.pk]),
        )

    def test_subtree_selector_excludes_seeds(self):
        """The subtree selector returns descendants only, no seeds or siblings."""
        top = make_comment("top1")
        reply = make_comment("re1", parent_id=top.pk)
        other = make_comment("top2")
        found = list(selectors.subtree_for_parents([top.pk]))
        self.assertEqual([c.pk for c in found], [reply.pk])
        self.assertNotIn(other.pk, [c.pk for c in found])

    def test_cascade_delete_removes_subtree(self):
        """Deleting a top-level comment removes its whole subtree."""
        Comment.objects.all().delete()  # ensure a clean slate
        top = make_comment("top1")
        mid = make_comment("mid1", parent_id=top.pk)
        make_comment("leaf1", parent_id=mid.pk)
        other = make_comment("top2")
        top.delete()
        self.assertEqual(Comment.objects.count(), 1)
        self.assertTrue(Comment.objects.filter(pk=other.pk).exists())
