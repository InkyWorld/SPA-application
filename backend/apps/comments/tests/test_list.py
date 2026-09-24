"""Integration tests: listing, sorting, pagination, preview, uploads, misc."""

from __future__ import annotations

import tempfile
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.comments.models import Comment
from apps.comments.tests.helpers import login_as, make_png, post_comment


class CommentListTests(TestCase):
    def setUp(self):
        """Start each test from a clean slate with three known comments."""
        Comment.objects.all().delete()
        for name in ("bob", "alice", "carol"):
            Comment.objects.create(user_name=name, email=f"{name}@x.cc", text="hi")

    def test_default_order_is_lifo(self):
        """Newest top-level comments come first without ?sort=."""
        names = [
            c["user_name"] for c in self.client.get("/api/comments/").json()["results"]
        ]
        self.assertEqual(names, ["carol", "alice", "bob"])

    def test_sort_user_name_both_directions(self):
        """User name sorting works ascending and descending."""
        asc = [
            c["user_name"]
            for c in self.client.get("/api/comments/?sort=user_name").json()["results"]
        ]
        desc = [
            c["user_name"]
            for c in self.client.get("/api/comments/?sort=-user_name").json()["results"]
        ]
        self.assertEqual(asc, ["alice", "bob", "carol"])
        self.assertEqual(desc, ["carol", "bob", "alice"])

    def test_sort_email(self):
        """E-mail sorting orders top-level comments ascending."""
        rows = self.client.get("/api/comments/?sort=email").json()["results"]
        self.assertEqual(
            [c["email"] for c in rows], ["alice@x.cc", "bob@x.cc", "carol@x.cc"]
        )

    def test_sort_created_at_explicit(self):
        """Explicit date sorting works in both directions."""
        asc = [
            c["user_name"]
            for c in self.client.get("/api/comments/?sort=created_at").json()["results"]
        ]
        desc = [
            c["user_name"]
            for c in self.client.get("/api/comments/?sort=-created_at").json()["results"]
        ]
        self.assertEqual(asc, ["bob", "alice", "carol"])
        self.assertEqual(desc, ["carol", "alice", "bob"])

    def test_unknown_sort_falls_back_to_lifo(self):
        """Unknown sort fields degrade to default LIFO order."""
        names = [
            c["user_name"]
            for c in self.client.get("/api/comments/?sort=hacked").json()["results"]
        ]
        self.assertEqual(names, ["carol", "alice", "bob"])

    def test_pagination_25_per_page(self):
        """33 tops split into pages of 25 and 8 with correct links."""
        for i in range(30):
            Comment.objects.create(
                user_name=f"u{i:02d}", email=f"u{i:02d}@x.cc", text="hi"
            )
        page1 = self.client.get("/api/comments/").json()
        page2 = self.client.get("/api/comments/?page=2").json()
        self.assertEqual(page1["count"], 33)
        self.assertEqual(len(page1["results"]), 25)
        self.assertEqual(len(page2["results"]), 8)
        self.assertIsNotNone(page1["next"])
        self.assertIsNone(page1["previous"])
        self.assertIsNone(page2["next"])
        self.assertIsNotNone(page2["previous"])

    def test_attachment_names_exposed(self):
        """List output carries the attached file name and URL."""
        Comment.objects.all().delete()
        name = f"n_{uuid.uuid4().hex[:6]}.txt"
        key_response = post_comment(
            self.client, file=SimpleUploadedFile(name, b"hi", "text/plain")
        )
        self.assertEqual(key_response.status_code, 201)
        node = self.client.get("/api/comments/").json()["results"][0]
        self.assertEqual(node["file_name"], name)
        self.assertTrue(node["file_url"].endswith(".txt"))


class PreviewTests(TestCase):
    def setUp(self):
        """Preview requires login, like posting does."""
        login_as(self.client)

    def test_preview_without_saving(self):
        """Preview returns sanitized HTML and creates nothing."""
        response = self.client.post(
            "/api/comments/preview/",
            {"text": "<strong>x</strong>"},
            content_type="application/json",
        )
        self.assertEqual(response.json(), {"html": "<strong>x</strong>"})
        self.assertEqual(Comment.objects.count(), 0)

    def test_preview_escapes_disallowed(self):
        """Preview escapes disallowed tags instead of rejecting them."""
        response = self.client.post(
            "/api/comments/preview/",
            {"text": "<script>alert(1)</script>"},
            content_type="application/json",
        )
        self.assertIn("&lt;script&gt;", response.json()["html"])

    def test_preview_unclosed_rejected(self):
        """Preview with unbalanced markup returns 400."""
        response = self.client.post(
            "/api/comments/preview/",
            {"text": "<strong>oops"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class FileUploadTests(TestCase):
    def setUp(self):
        """Redirect uploads to a temp dir for the test."""
        self._tmp = tempfile.TemporaryDirectory()
        self._override = override_settings(MEDIA_ROOT=self._tmp.name)
        self._override.enable()

    def tearDown(self):
        """Restore media settings and drop the temp dir."""
        self._override.disable()
        self._tmp.cleanup()

    def test_big_image_is_downscaled(self):
        """Oversized uploads are stored within 320x240."""
        response = post_comment(self.client, file=make_png("big.png", 800, 600))
        self.assertEqual(response.status_code, 201)
        comment = Comment.objects.get(pk=response.json()["id"])
        with Image.open(comment.image.path) as img:
            self.assertLessEqual(img.width, 320)
            self.assertLessEqual(img.height, 240)

    def test_image_name_exposed(self):
        """List output carries the image name and a /media/ URL."""
        response = post_comment(self.client, file=make_png("pic.png", 10, 10))
        node = self.client.get("/api/comments/").json()["results"][0]
        self.assertEqual(node["image_name"], "pic.png")
        self.assertIn("/media/", node["image_url"])
        self.assertEqual(response.status_code, 201)

    def test_txt_ok_and_too_big_rejected(self):
        """Small TXT passes while files over 100 kB return 400."""
        small = SimpleUploadedFile("a.txt", b"hello", "text/plain")
        self.assertEqual(post_comment(self.client, file=small).status_code, 201)
        big = SimpleUploadedFile("b.txt", b"x" * (100 * 1024 + 1), "text/plain")
        self.assertEqual(post_comment(self.client, file=big).status_code, 400)

    def test_bad_extension_rejected(self):
        """Uploads with unknown extensions return 400."""
        exe = SimpleUploadedFile("a.exe", b"junk", "application/octet-stream")
        self.assertEqual(post_comment(self.client, file=exe).status_code, 400)


class MiscTests(TestCase):
    def test_cors_header_present(self):
        """API responses carry the permissive CORS header."""
        response = self.client.get("/api/comments/")
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")

    def test_schema_endpoint(self):
        """Generated OpenAPI schema lists the comment endpoints."""
        response = self.client.get("/api/schema/", HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/comments/", paths)
        self.assertIn("/api/register/", paths)

    def test_docs_ui_served(self):
        """Swagger UI page renders."""
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)
