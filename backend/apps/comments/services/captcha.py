"""django-simple-captcha integration.

Issuance: package views (see urls.py: refresh + image).
This module provides:
- alnum_challenge: [A-Za-z0-9] generator (the package default is A-Z only,
  the task requires digits too). Wired via CAPTCHA_CHALLENGE_FUNCT setting.
- verify_captcha: one-time check with the exact semantics of the package's
  own CaptchaField (burn on first attempt, expiry enforced).
"""

from __future__ import annotations

import random
import string

from captcha.conf import settings as captcha_settings
from captcha.models import CaptchaStore
from django.utils import timezone
from rest_framework import serializers

CHARS = string.ascii_letters + string.digits


def alnum_challenge():
    """Generate a (challenge, response) pair of [A-Za-z0-9] chars.

    Returns:
        Tuple of (display text, expected answer); the display text
        is uppercased while the answer keeps the original case.
    """
    raw = "".join(random.choice(CHARS) for _ in range(captcha_settings.CAPTCHA_LENGTH))
    return raw.upper(), raw


def verify_captcha(key: str, value: str) -> None:
    """Check a CAPTCHA answer against the package store (one-time use).

    Args:
        key: Challenge key issued by the refresh endpoint.
        value: Answer typed by the user (compared case-insensitively).

    Raises:
        serializers.ValidationError: When the key is unknown/expired
            or the answer is wrong. The stored challenge is deleted
            on the first attempt either way.
    """
    CaptchaStore().remove_expired()
    response = (value or "").strip().lower()
    store = CaptchaStore.objects.filter(
        hashkey=key, expiration__gt=timezone.now()
    ).first()
    if store is not None:
        store.delete()
    if store is None or store.response != response:
        raise serializers.ValidationError("Invalid CAPTCHA.")
