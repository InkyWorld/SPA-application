"""Background queue: heavy/scheduled work off the request cycle."""

from __future__ import annotations

from captcha.models import CaptchaStore
from celery import shared_task
from django.utils import timezone

from apps.comments.models import Comment
from apps.comments.services import files as file_rules


@shared_task
def resize_comment_image(comment_id: int) -> bool:
    """Downscale an attached image after create (async in prod, eager in tests).

    Args:
        comment_id: Pk of the comment holding the image.

    Returns:
        True when an image was resized, False when there is nothing to do.
    """

    try:
        comment = Comment.objects.get(pk=comment_id)
    except Comment.DoesNotExist:
        return False
    if not comment.image or not hasattr(comment.image, "path"):
        return False
    file_rules.resize_image(comment.image.path)
    return True


@shared_task
def cleanup_expired_captchas() -> int:
    """Delete expired CAPTCHA rows (also runs on every verify as a sweep).

    Returns:
        Number of deleted rows.
    """
    deleted, _ = CaptchaStore.objects.filter(expiration__lte=timezone.now()).delete()
    return deleted
