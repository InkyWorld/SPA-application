"""Shared helpers for integration tests."""

from __future__ import annotations

import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from captcha.models import CaptchaStore

XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def login_as(client, username: str = "tester") -> User:
    """Create (once) and session-login a user on the test client.

    Args:
        client: Django test client.
        username: Login name for the user.

    Returns:
        The logged-in user.
    """
    user, _ = User.objects.get_or_create(
        username=username, defaults={"email": f"{username}@x.cc"}
    )
    client.force_login(user)
    return user


def fresh_captcha(client) -> tuple[str, str]:
    """Issue via the package refresh endpoint, read the answer from its store."""
    response = client.get("/api/captcha/refresh/", **XHR)
    assert response.status_code == 200, response.content
    key = response.json()["key"]
    code = CaptchaStore.objects.get(hashkey=key).response
    assert code, "captcha must be stored"
    return key, code


def post_comment(client, **overrides):
    """Post a valid comment, logging in first unless already authenticated."""
    if "_auth_user_id" not in client.session:
        login_as(client)
    key, code = fresh_captcha(client)
    payload = {
        "text": "<strong>hello</strong>",
        "captcha_key": key,
        "captcha_value": code,
    }
    payload.update(overrides)
    return client.post("/api/comments/", payload)


def make_png(name: str, width: int, height: int) -> SimpleUploadedFile:
    """Build an in-memory PNG upload of the given size."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), "image/png")
