"""React to model changes: broadcast, cache invalidation, background jobs."""

from __future__ import annotations

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
    selectors.bump_list_cache_version()
    events.comment_created(instance.pk)
    if instance.image:
        resize_comment_image.delay(instance.pk)
