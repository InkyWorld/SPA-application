"""Unit tests: pure logic + service rules (Django test DB available, no HTTP)."""

from __future__ import annotations

import io
import re
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework import serializers as drf_serializers

from captcha.models import CaptchaStore

from apps.comments import selectors
from apps.comments.models import Comment
from apps.comments.services import files as file_rules
from apps.comments.services.captcha import alnum_challenge, verify_captcha
from apps.comments.services.comments import CommentCreator, CreateCommentInput
from apps.comments.services.tree import build_tree


def make_upload(name: str, content: bytes, content_type: str) -> SimpleUploadedFile:
    """Build an in-memory upload."""
    return SimpleUploadedFile(name, content, content_type)


def make_png_bytes(width: int, height: int) -> bytes:
    """Render a PNG of the given size."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buf, format="PNG")
    return buf.getvalue()


class ParseSortParamTests(TestCase):
    def test_default_is_lifo(self):
        """Missing or blank sort falls back to newest-first ordering."""
        self.assertEqual(selectors.parse_sort_param(None), ["-created_at"])
        self.assertEqual(selectors.parse_sort_param(""), ["-created_at"])

    def test_single_field_both_directions(self):
        """A single field parses with and without the minus prefix."""
        self.assertEqual(selectors.parse_sort_param("user_name"), ["user_name"])
        self.assertEqual(selectors.parse_sort_param("-email"), ["-email"])

    def test_multiple_fields(self):
        """Comma-separated sorts keep every valid field in order."""
        self.assertEqual(
            selectors.parse_sort_param("user_name,-created_at"),
            ["user_name", "-created_at"],
        )

    def test_unknown_fields_fall_back_to_lifo(self):
        """Unknown fields are dropped; all-unknown input means LIFO."""
        self.assertEqual(selectors.parse_sort_param("hacked"), ["-created_at"])
        self.assertEqual(
            selectors.parse_sort_param("hacked,user_name"), ["user_name"]
        )


class BuildTreeTests(TestCase):
    def test_empty_list(self):
        """Empty input builds an empty forest."""
        self.assertEqual(build_tree([]), [])

    def test_single_top_level(self):
        """A lone top-level comment becomes a root with no replies."""
        top = Comment(user_name="a", email="a@x.cc", text="hi")
        top.pk = 1  # production invariant: list input always comes from the DB
        nodes = build_tree([top])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["replies"], [])

    def test_nesting_and_depth(self):
        """Three levels nest recursively under their parents."""
        top = Comment(user_name="t", email="t@x.cc", text="t")
        top.pk = 1  # production invariant: list input always comes from the DB
        mid = Comment(user_name="m", email="m@x.cc", text="m", parent_id=1)
        mid.pk = 2
        leaf = Comment(user_name="l", email="l@x.cc", text="l", parent_id=2)
        leaf.pk = 3
        nodes = build_tree([top, mid, leaf])
        self.assertEqual(nodes[0]["comment"], top)
        self.assertEqual(nodes[0]["replies"][0]["comment"], mid)
        self.assertEqual(nodes[0]["replies"][0]["replies"][0]["comment"], leaf)

    def test_orphan_reply_is_dropped(self):
        """Replies to absent parents never surface as roots."""
        top = Comment(user_name="t", email="t@x.cc", text="t")
        top.pk = 1
        orphan = Comment(user_name="o", email="o@x.cc", text="o", parent_id=999)
        nodes = build_tree([top, orphan])
        self.assertEqual(len(nodes), 1)


class AlnumChallengeTests(TestCase):
    def test_shape_and_charset(self):
        """Challenges stay within [A-Za-z0-9]+ with an uppercased display."""
        challenge, response = alnum_challenge()
        self.assertTrue(re.fullmatch(r"[A-Za-z0-9]+", challenge))
        self.assertTrue(re.fullmatch(r"[A-Za-z0-9]+", response))
        self.assertEqual(challenge, response.upper())


class VerifyCaptchaTests(TestCase):
    def _stored_key(self, response="ab12", minutes=5):
        """Create a CAPTCHA store row and return its key.

        Args:
            response: Expected answer stored for the challenge.
            minutes: Lifetime of the challenge from now.

        Returns:
            Hashkey identifying the stored challenge.
        """
        store = CaptchaStore.objects.create(
            challenge="AB12",
            response=response,
            expiration=timezone.now() + timedelta(minutes=minutes),
        )
        return store.hashkey

    def test_valid_passes_and_burns(self):
        """A correct answer verifies once and deletes the challenge."""
        key = self._stored_key()
        verify_captcha(key, "ab12")
        self.assertFalse(CaptchaStore.objects.filter(hashkey=key).exists())

    def test_case_insensitive(self):
        """Answers match regardless of letter case."""
        verify_captcha(self._stored_key(response="xy99"), "XY99")

    def test_wrong_value_fails(self):
        """A wrong answer raises ValidationError."""
        with self.assertRaises(drf_serializers.ValidationError):
            verify_captcha(self._stored_key(), "nope")

    def test_wrong_value_burns_store(self):
        """Even a wrong attempt invalidates the challenge (anti-bruteforce)."""
        key = self._stored_key()
        with self.assertRaises(drf_serializers.ValidationError):
            verify_captcha(key, "nope")
        self.assertFalse(CaptchaStore.objects.filter(hashkey=key).exists())

    def test_unknown_key_fails(self):
        """Unknown challenge keys raise ValidationError."""
        with self.assertRaises(drf_serializers.ValidationError):
            verify_captcha("missing", "ab12")

    def test_expired_fails(self):
        """Expired challenges raise ValidationError."""
        with self.assertRaises(drf_serializers.ValidationError):
            verify_captcha(self._stored_key(minutes=-1), "ab12")


class ValidateUploadTests(TestCase):
    def test_none_is_ok(self):
        """No attachment is always valid."""
        file_rules.validate_upload(None)

    def test_valid_png_passes(self):
        """A parseable PNG passes validation."""
        file_rules.validate_upload(make_upload("a.png", make_png_bytes(10, 10), "image/png"))

    def test_uppercase_extension_accepted(self):
        """Extensions match case-insensitively."""
        file_rules.validate_upload(make_upload("A.JPG", make_png_bytes(10, 10), "image/jpeg"))

    def test_fake_image_rejected(self):
        """Non-image bytes with an image extension return the image error."""
        with self.assertRaises(ValidationError) as ctx:
            file_rules.validate_upload(make_upload("a.png", b"not an image", "image/png"))
        self.assertIn("image", ctx.exception.message_dict)

    def test_txt_size_limit(self):
        """TXT files are accepted up to 100 kB and rejected above it."""
        file_rules.validate_upload(make_upload("a.txt", b"x" * 100, "text/plain"))
        with self.assertRaises(ValidationError) as ctx:
            file_rules.validate_upload(
                make_upload("b.txt", b"x" * (100 * 1024 + 1), "text/plain")
            )
        self.assertIn("text_file", ctx.exception.message_dict)

    def test_bad_extension_rejected(self):
        """Unknown extensions return the file error."""
        with self.assertRaises(ValidationError) as ctx:
            file_rules.validate_upload(make_upload("a.exe", b"junk", "application/octet-stream"))
        self.assertIn("file", ctx.exception.message_dict)


class CommentCreatorTests(TestCase):
    def test_sanitizes_and_saves(self):
        """Valid input persists with sanitized text."""
        comment = CommentCreator().execute(
            CreateCommentInput(
                user_name="Bob1", email="b@x.cc", text="<strong>hi</strong>",
            )
        )
        self.assertEqual(comment.text, "<strong>hi</strong>")

    def test_bad_text_raises(self):
        """Unbalanced markup aborts creation with an error."""
        with self.assertRaises(Exception):
            CommentCreator().execute(
                CreateCommentInput(user_name="Bob1", email="b@x.cc", text="<strong>oops")
            )

    def test_reply_links_parent(self):
        """Replies store the parent link with MPTT level 1."""
        creator = CommentCreator()
        top = creator.execute(
            CreateCommentInput(user_name="T1", email="t@x.cc", text="top")
        )
        reply = creator.execute(
            CreateCommentInput(user_name="R1", email="r@x.cc", text="re", parent_id=top.pk)
        )
        self.assertEqual(reply.parent_id, top.pk)
        self.assertEqual(reply.level, 1)
