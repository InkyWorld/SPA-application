"""React to model changes: broadcast, cache invalidation, background jobs."""

from __future__ import annotations

from typing import Any, cast

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.comments import selectors
from apps.comments.models import Comment
from apps.comments.services import events
from apps.comments.tasks import resize_comment_image


@receiver(post_save, sender=Comment)
def comment_saved(sender, instance: Comment, created: bool, **kwargs) -> None:
    """Fan out side effects of a newly created comment.

    Args:
        sender: Comment model class.
        instance: Saved comment instance.
        created: True only for inserts (updates are ignored).
        **kwargs: Extra signal arguments.
    """
    if not created:
        return
    transaction.on_commit(lambda: selectors.bump_list_cache_version())
    transaction.on_commit(lambda: events.comment_created(instance.pk))
    if instance.image:
        transaction.on_commit(
            lambda: cast(Any, resize_comment_image).delay(instance.pk)
        )
