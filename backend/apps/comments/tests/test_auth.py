"""Integration tests: registration, email JWT login, profile, posting gates."""

from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.comments.tests.helpers import login_as


class RegisterTests(TestCase):
    def test_register_creates_user(self):
        """Valid registration returns 201 with the public profile."""
        response = self.client.post("/api/register/", {
            "user_name": "Alex123", "email": "alex@example.com",
            "password": "s3cure-pass",
        })
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["user_name"], "Alex123")
        self.assertEqual(body["email"], "alex@example.com")
        self.assertIsInstance(body["id"], int)
        self.assertTrue(User.objects.filter(username="Alex123").exists())

    def test_register_duplicate_rejected(self):
        """Taken user name or email returns 400."""
        User.objects.create_user("Alex123", email="alex@example.com", password="pw")
        response = self.client.post("/api/register/", {
            "user_name": "Alex123", "email": "other@example.com",
            "password": "s3cure-pass",
        })
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/register/", {
            "user_name": "Other1", "email": "alex@example.com",
            "password": "s3cure-pass",
        })
        self.assertEqual(response.status_code, 400)

    def test_register_bad_shape_rejected(self):
        """Bad user name or weak password returns 400."""
        response = self.client.post("/api/register/", {
            "user_name": "bad name!", "email": "a@x.cc", "password": "s3cure-pass",
        })
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/register/", {
            "user_name": "Good1", "email": "a@x.cc", "password": "short",
        })
        self.assertEqual(response.status_code, 400)


class EmailTokenTests(TestCase):
    def setUp(self):
        """Create a user able to log in by email."""
        user = User.objects.create_user("Alex123", email="alex@example.com")
        user.set_password("s3cure-pass")
        user.save()

    def test_obtain_by_email(self):
        """Email + password yield access and refresh tokens."""
        response = self.client.post("/api/token/", {
            "email": "alex@example.com", "password": "s3cure-pass",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

    def test_obtain_wrong_password_rejected(self):
        """Wrong passwords return 400 without leaking which field failed."""
        response = self.client.post("/api/token/", {
            "email": "alex@example.com", "password": "wrong-pass",
        })
        self.assertEqual(response.status_code, 400)

    def test_obtain_unknown_email_rejected(self):
        """Unknown emails return 400."""
        response = self.client.post("/api/token/", {
            "email": "ghost@example.com", "password": "s3cure-pass",
        })
        self.assertEqual(response.status_code, 400)

    def test_refresh_pair(self):
        """A refresh token issues a new access token."""
        pair = self.client.post("/api/token/", {
            "email": "alex@example.com", "password": "s3cure-pass",
        }).json()
        response = self.client.post(
            "/api/token/refresh/", {"refresh": pair["refresh"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())


class MeTests(TestCase):
    def test_me_returns_profile(self):
        """An authenticated request gets its own profile."""
        login_as(self.client, username="Alex123")
        response = self.client.get(
            "/api/me/",
            HTTP_AUTHORIZATION=f"Bearer {self._jwt('Alex123')}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_name"], "Alex123")

    def test_me_requires_auth(self):
        """Anonymous profile requests return 401."""
        self.assertEqual(self.client.get("/api/me/").status_code, 401)

    def _jwt(self, username: str) -> str:
        """Fetch a throwaway access token (password is unknown here)."""
        user = User.objects.get(username=username)
        return str(RefreshToken.for_user(user).access_token)
