import json

from channels.generic.websocket import AsyncWebsocketConsumer


class CommentsConsumer(AsyncWebsocketConsumer):
    """Push-only socket: server broadcasts `comment.created`, client refetches."""

    async def connect(self):
        """Join the broadcast group and accept the incoming socket."""
        await self.channel_layer.group_add("comments", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        """Leave the broadcast group on socket close.

        Args:
            code: WebSocket close code.
        """
        await self.channel_layer.group_discard("comments", self.channel_name)

    async def comment_created(self, event):
        """Forward a broadcast event to this socket as JSON.

        Args:
            event: Channel layer event holding the new comment id.
        """
        await self.send(text_data=json.dumps({"type": "comment.created", "id": event["id"]}))
