"""Integration tests: celery queue tasks and beat schedule."""

from __future__ import annotations

import io
import tempfile
from datetime import timedelta

from django.conf import settings as dj_settings
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from captcha.models import CaptchaStore

from apps.comments.models import Comment
from apps.comments.tasks import cleanup_expired_captchas, resize_comment_image


class QueueTasksTests(TestCase):
    def setUp(self):
        """Redirect uploads to a temp dir for the test."""
        self._tmp = tempfile.TemporaryDirectory()
        self._override = override_settings(MEDIA_ROOT=self._tmp.name)
        self._override.enable()

    def tearDown(self):
        """Restore media settings and drop the temp dir."""
        self._override.disable()
        self._tmp.cleanup()

    def test_resize_task_downscales(self):
        """The resize task fits a stored image into 320x240 in place."""
        buf = io.BytesIO()
        Image.new("RGB", (800, 600), "red").save(buf, format="PNG")
        comment = Comment.objects.create(user_name="t1", email="t@x.cc", text="hi")
        comment.image.save("big.png", ContentFile(buf.getvalue()))
        self.assertTrue(resize_comment_image(comment.pk))
        with Image.open(comment.image.path) as img:
            self.assertLessEqual(img.width, 320)
            self.assertLessEqual(img.height, 240)

    def test_resize_missing_comment_returns_false(self):
        """Resizing a deleted comment is a no-op, not an error."""
        self.assertFalse(resize_comment_image(999999))

    def test_cleanup_task_deletes_only_expired(self):
        """Beat cleanup removes expired rows and reports the count."""
        CaptchaStore.objects.create(
            challenge="OLD", response="aa11",
            expiration=timezone.now() - timedelta(minutes=1),
        )
        fresh = CaptchaStore.objects.create(
            challenge="NEW", response="bb22",
            expiration=timezone.now() + timedelta(minutes=5),
        )
        self.assertEqual(cleanup_expired_captchas(), 1)
        self.assertTrue(CaptchaStore.objects.filter(pk=fresh.pk).exists())

    def test_beat_schedule_registered(self):
        """Periodic captcha cleanup is scheduled every 5 minutes."""
        entry = dj_settings.CELERY_BEAT_SCHEDULE["cleanup-expired-captchas"]
        self.assertEqual(entry["task"], "apps.comments.tasks.cleanup_expired_captchas")
        self.assertEqual(entry["schedule"], 300.0)
