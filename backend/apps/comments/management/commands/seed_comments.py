"""Seed demo comments: tops for 2 pager pages plus nested reply trees."""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.comments.models import Comment
from apps.comments.services.comments import CommentCreator, CreateCommentInput

TEXTS = [
    "Comment <strong>number {n}</strong> with bold text.",
    "Comment number {n} with <i>italic</i> emphasis.",
    "Comment number {n} with <code>print({n})</code> inline code.",
    'Comment number {n} with <a href="https://example.com" title="Example">a link</a>.',
    "Plain comment number {n} without any markup.",
]

REPLY_TEXTS = [
    "Reply <strong>{n}</strong> to this thread.",
    "I <i>agree</i> with reply {n}.",
    "Nested thought <code>{n}</code> one level deeper.",
]

# First TREED_TOPS tops get this reply shape: 2 replies, first one nested twice.
TREED_TOPS = 5


class Command(BaseCommand):
    """Wipe comments and seed fresh demo data (dev/demo only)."""

    help = "Seed N top-level demo comments (default 30 → 2 pages) with reply trees."

    def add_arguments(self, parser):
        """Register the --count CLI option.

        Args:
            parser: Argument parser provided by Django.
        """
        parser.add_argument("--count", type=int, default=30)

    def handle(self, *args, **options):
        """Create tops with spread-out dates, then grow reply trees on them.

        Args:
            *args: Ignored positional CLI args.
            **options: Parsed options, honoring "count".
        """
        count: int = options["count"]
        Comment.objects.all().delete()
        creator = CommentCreator()
        now = timezone.now()
        tops = [creator.execute(self._make_input(i)) for i in range(1, count + 1)]
        for pos, comment in enumerate(tops):
            Comment.objects.filter(pk=comment.pk).update(
                created_at=now - timedelta(days=count - pos)
            )
        # Trees grow on the newest tops so they are visible on page 1 (LIFO).
        fresh = tops[-TREED_TOPS:] if count >= TREED_TOPS else tops
        trees = sum(self._grow_tree(creator, top, pos) for pos, top in enumerate(fresh))
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {count} top-level comments + {trees} replies.")
        )

    @staticmethod
    def _make_input(i: int) -> CreateCommentInput:
        """Build input for demo user number i.

        Args:
            i: 1-based demo user number.

        Returns:
            Use-case input with deterministic name, email and text.
        """
        return CreateCommentInput(
            user_name=f"user{i:02d}",
            email=f"user{i:02d}@example.com",
            home_page="https://example.com" if i % 3 == 0 else "",
            text=TEXTS[i % len(TEXTS)].format(n=i),
        )

    @classmethod
    def _grow_tree(cls, creator: CommentCreator, top: Comment, pos: int) -> int:
        """Grow two replies on top, nesting the first one twice deeper.

        Args:
            creator: Use-case used for every created reply.
            top: Top-level comment to reply to.
            pos: Tree number used in replier names.

        Returns:
            Number of replies created (always 4).
        """
        first = creator.execute(cls._make_reply(top.pk, pos, 0))
        creator.execute(cls._make_reply(top.pk, pos, 1))
        second = creator.execute(cls._make_reply(first.pk, pos, 2))
        creator.execute(cls._make_reply(second.pk, pos, 0))
        return 4

    @staticmethod
    def _make_reply(parent_id: int, pos: int, variant: int) -> CreateCommentInput:
        """Build input for a reply inside tree number pos.

        Args:
            parent_id: Pk of the comment being replied to.
            pos: Tree number used in replier names.
            variant: Text template variant index.

        Returns:
            Use-case input for the reply.
        """
        return CreateCommentInput(
            user_name=f"replier{pos}{variant}",
            email=f"replier{pos}{variant}@example.com",
            text=REPLY_TEXTS[variant % len(REPLY_TEXTS)].format(n=f"{pos}.{variant}"),
            parent_id=parent_id,
        )
