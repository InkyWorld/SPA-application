"""Domain events: side effects of a created comment in one place."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def comment_created(comment_id: int) -> None:
    """Push a comment.created event to all WS subscribers.

    Args:
        comment_id: Pk of the newly created comment.
    """
    async_to_sync(get_channel_layer().group_send)("comments", {
        "type": "comment.created", "id": comment_id,
    })
