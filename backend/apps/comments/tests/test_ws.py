"""Integration tests: WebSocket live updates."""

from __future__ import annotations

import unittest

from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import Client

from apps.comments.tests.helpers import post_comment
from config.asgi import application


class CommentsWsTests(unittest.IsolatedAsyncioTestCase):
    async def test_broadcast_reaches_client(self):
        """A group event is forwarded to the connected socket as JSON."""
        communicator = WebsocketCommunicator(application, "/ws/comments/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await get_channel_layer().group_send(
            "comments", {"type": "comment.created", "id": 1}
        )
        message = await communicator.receive_json_from()
        self.assertEqual(message, {"type": "comment.created", "id": 1})
        await communicator.disconnect()

    async def test_create_notifies_subscribers(self):
        """Creating a comment via HTTP pushes an event to subscribers."""
        communicator = WebsocketCommunicator(application, "/ws/comments/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        response = await database_sync_to_async(post_comment)(Client())
        self.assertEqual(response.status_code, 201)
        message = await communicator.receive_json_from()
        self.assertEqual(
            message, {"type": "comment.created", "id": response.json()["id"]}
        )
        await communicator.disconnect()
