"""Integration tests: HTTP API end to end (Django test DB)."""

from __future__ import annotations

import io
import re

from PIL import Image

from django.test import TestCase

from apps.comments.models import Comment
from apps.comments.tests.helpers import XHR, fresh_captcha, login_as, post_comment


class CommentCreateTests(TestCase):
    def test_create_top_level(self):
        """A valid post creates a top-level comment with sanitized text."""
        response = post_comment(self.client)
        self.assertEqual(response.status_code, 201)
        comment = Comment.objects.get(pk=response.json()["id"])
        self.assertIsNone(comment.parent_id)
        self.assertEqual(comment.text, "<strong>hello</strong>")

    def test_author_taken_from_profile(self):
        """Author fields come from the JWT profile, not the payload."""
        user = login_as(self.client, username="profileuser")
        user.email = "profile@x.cc"
        user.save()
        response = post_comment(self.client)
        comment = Comment.objects.get(pk=response.json()["id"])
        self.assertEqual(comment.user_name, "profileuser")
        self.assertEqual(comment.email, "profile@x.cc")

    def test_author_spoof_ignored(self):
        """Submitted user_name/email cannot impersonate another author."""
        response = post_comment(
            self.client, user_name="hacker", email="evil@x.cc"
        )
        comment = Comment.objects.get(pk=response.json()["id"])
        self.assertEqual(comment.user_name, "tester")
        self.assertEqual(comment.email, "tester@x.cc")

    def test_anon_create_rejected(self):
        """Anonymous posting returns 401."""
        key, code = fresh_captcha(self.client)
        response = self.client.post("/api/comments/", {
            "text": "hi", "captcha_key": key, "captcha_value": code,
        })
        self.assertEqual(response.status_code, 401)

    def test_anon_preview_rejected(self):
        """Anonymous preview returns 401."""
        response = self.client.post(
            "/api/comments/preview/", {"text": "hi"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_reply_nests_in_list(self):
        """A reply is stored with its parent and rendered inside its tree."""
        Comment.objects.all().delete()  # ensure a clean slate
        top_id = post_comment(self.client).json()["id"]
        reply = post_comment(self.client, parent_id=top_id, text="<i>reply</i>")
        self.assertEqual(reply.status_code, 201)
        tree = self.client.get("/api/comments/").json()["results"]
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]["replies"][0]["text"], "<i>reply</i>")

    def test_reply_to_missing_parent_rejected(self):
        """Replying to a nonexistent comment returns 400."""
        self.assertEqual(post_comment(self.client, parent_id=999999).status_code, 400)

    def test_bad_username_rejected(self):
        """User names outside [A-Za-z0-9]+ return 400."""
        self.assertEqual(
            post_comment(self.client, user_name="bad name!").status_code, 400
        )

    def test_bad_email_rejected(self):
        """Malformed e-mails return 400."""
        self.assertEqual(post_comment(self.client, email="not-an-email").status_code, 400)

    def test_bad_home_page_rejected(self):
        """Malformed home page URLs return 400."""
        self.assertEqual(post_comment(self.client, home_page="not-a-url").status_code, 400)

    def test_home_page_optional(self):
        """Omitting the home page still creates the comment."""
        payload = post_comment(self.client)
        self.assertEqual(payload.status_code, 201)

    def test_empty_text_rejected(self):
        """Blank comment text returns 400."""
        self.assertEqual(post_comment(self.client, text="   ").status_code, 400)

    def test_unclosed_tags_rejected(self):
        """Unbalanced markup returns 400 instead of being auto-closed."""
        self.assertEqual(
            post_comment(self.client, text="<strong>oops").status_code, 400
        )

    def test_script_is_escaped_not_rejected(self):
        """Disallowed tags are escaped in storage, not rejected."""
        response = post_comment(self.client, text="<script>alert(1)</script>")
        self.assertEqual(response.status_code, 201)
        comment = Comment.objects.get(pk=response.json()["id"])
        self.assertIn("&lt;script&gt;", comment.text)
        self.assertNotIn("<script>", comment.text)

    def test_missing_captcha_rejected(self):
        """Posts without CAPTCHA fields return 400."""
        login_as(self.client)
        response = self.client.post("/api/comments/", {"text": "hi"})
        self.assertEqual(response.status_code, 400)

    def test_bad_captcha_rejected(self):
        """Wrong CAPTCHA answers return 400."""
        response = post_comment(self.client, captcha_value="wrong1")
        self.assertEqual(response.status_code, 400)

    def test_captcha_is_one_time_use(self):
        """A consumed CAPTCHA key cannot create a second comment."""
        login_as(self.client)
        key, code = fresh_captcha(self.client)
        first = self.client.post("/api/comments/", {
            "text": "hi", "captcha_key": key, "captcha_value": code,
        })
        self.assertEqual(first.status_code, 201)
        retry = self.client.post("/api/comments/", {
            "text": "hi", "captcha_key": key, "captcha_value": code,
        })
        self.assertEqual(retry.status_code, 400)


class CaptchaIssueTests(TestCase):
    def test_refresh_returns_key_and_image_url(self):
        """The refresh endpoint issues a key with a loadable PNG image."""
        response = self.client.get("/api/captcha/refresh/", **XHR)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("key", data)
        self.assertIn("image_url", data)
        image = self.client.get(data["image_url"])
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image["Content-Type"], "image/png")
        with Image.open(io.BytesIO(image.content)) as img:
            img.verify()

    def test_refresh_requires_xhr(self):
        """Refresh without the XHR header returns 404 (package behavior)."""
        self.assertEqual(self.client.get("/api/captcha/refresh/").status_code, 404)

    def test_value_is_latin_alnum(self):
        """Issued CAPTCHA values stay within [A-Za-z0-9]+ (task requirement)."""
        key, code = fresh_captcha(self.client)
        self.assertTrue(re.fullmatch(r"[A-Za-z0-9]+", code), code)
