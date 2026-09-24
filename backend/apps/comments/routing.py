from django.urls import path

from apps.comments.consumers import CommentsConsumer

websocket_urlpatterns = [
    path("ws/comments/", CommentsConsumer.as_asgi(), name="comments-consumer"),
]
