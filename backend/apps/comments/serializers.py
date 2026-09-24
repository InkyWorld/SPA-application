"""Transport-layer validation. Business rules live in services/."""

from __future__ import annotations

import os
import re

from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.comments.models import Comment
from apps.comments.services import sanitizer
from apps.comments.services.captcha import verify_captcha

USERNAME_RE = re.compile(r"^[A-Za-z0-9]+$")
CAPTCHA_RE = re.compile(r"^[A-Za-z0-9]+$")


class CommentCreateSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(required=False, allow_null=True)
    # Single attachment slot (image or TXT); the creator routes it by extension.
    file = serializers.FileField(required=False, allow_null=True, write_only=True)
    # Optional: authenticated authors are identified from their JWT profile,
    # anonymous posting is closed by IsAuthenticated on the view.
    user_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    captcha_key = serializers.CharField(write_only=True)
    captcha_value = serializers.CharField(write_only=True)

    class Meta:
        model = Comment
        fields = (
            "id", "parent_id", "user_name", "email", "home_page",
            "text", "file", "captcha_key", "captcha_value",
        )
        read_only_fields = ("id",)

    def validate_user_name(self, value: str) -> str:
        """Accept latin letters and digits only (task requirement).

        Args:
            value: Submitted user name.

        Returns:
            The unchanged value when valid.

        Raises:
            serializers.ValidationError: When other characters are present.
        """
        if not USERNAME_RE.fullmatch(value):
            raise serializers.ValidationError("Only latin letters and digits.")
        return value

    def validate_captcha_value(self, value: str) -> str:
        """Accept latin letters and digits only (task requirement).

        Args:
            value: Submitted CAPTCHA answer.

        Returns:
            The unchanged value when valid.

        Raises:
            serializers.ValidationError: When other characters are present.
        """
        if not CAPTCHA_RE.fullmatch(value):
            raise serializers.ValidationError("Only latin letters and digits.")
        return value

    def validate_text(self, value: str) -> str:
        """Require non-empty text with properly closed allowed tags.

        Args:
            value: Submitted comment text.

        Returns:
            The unchanged value when valid.

        Raises:
            serializers.ValidationError: When empty or tags are unbalanced.
        """
        if not value.strip():
            raise serializers.ValidationError("Text is required.")
        try:
            sanitizer.sanitize(value)
        except sanitizer.UnclosedTagError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def validate(self, attrs):
        """Fill the author from the JWT profile; verify the one-time CAPTCHA.

        Args:
            attrs: Field-validated input including captcha_key/captcha_value.

        Returns:
            Attrs with author resolved and CAPTCHA fields consumed.

        Raises:
            serializers.ValidationError: When anonymous, or the CAPTCHA
                is invalid/expired.
        """
        attrs = super().validate(attrs)
        user = self.context.get("request").user if self.context.get("request") else None
        if user is not None and user.is_authenticated:
            attrs["user_name"] = user.username
            attrs["email"] = user.email
        elif not attrs.get("user_name") or not attrs.get("email"):
            raise serializers.ValidationError("Authentication required to post.")
        verify_captcha(attrs["captcha_key"], attrs["captcha_value"])
        attrs.pop("captcha_key")
        attrs.pop("captcha_value")
        return attrs


class CommentNodeSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    image_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            "id", "parent_id", "user_name", "email", "home_page",
            "text", "image_url", "image_name", "file_url", "file_name",
            "created_at", "replies",
        )

    def get_replies(self, obj) -> list:
        """Serialize nested replies from the prebuilt children map.

        Args:
            obj: Comment being serialized.

        Returns:
            Serialized child comments (empty list for leaves).
        """
        children = self.context.get("children_map", {}).get(obj.pk, [])
        return CommentNodeSerializer(children, many=True, context=self.context).data

    def get_image_url(self, obj) -> str | None:
        """Return the attached image URL.

        Args:
            obj: Comment being serialized.

        Returns:
            Image URL, or None when no image is attached.
        """
        return obj.image.url if obj.image else None

    def get_image_name(self, obj) -> str | None:
        """Return the attached image filename.

        Args:
            obj: Comment being serialized.

        Returns:
            Image filename, or None when no image is attached.
        """
        return os.path.basename(obj.image.name) if obj.image else None

    def get_file_url(self, obj) -> str | None:
        """Return the attached text-file URL.

        Args:
            obj: Comment being serialized.

        Returns:
            File URL, or None when no file is attached.
        """
        return obj.text_file.url if obj.text_file else None

    def get_file_name(self, obj) -> str | None:
        """Return the attached text-file filename.

        Args:
            obj: Comment being serialized.

        Returns:
            File filename, or None when no file is attached.
        """
        return os.path.basename(obj.text_file.name) if obj.text_file else None


class PreviewSerializer(serializers.Serializer):
    text = serializers.CharField()

    def validate_text(self, value: str) -> str:
        """Reject markup with unclosed tags; the preview must stay valid.

        Args:
            value: Draft text from the preview request.

        Returns:
            The unchanged value when valid.

        Raises:
            serializers.ValidationError: When tags are unbalanced.
        """
        try:
            sanitizer.sanitize(value)
        except sanitizer.UnclosedTagError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value


class RegisterSerializer(serializers.Serializer):
    user_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_user_name(self, value: str) -> str:
        """Accept latin letters and digits; require uniqueness.

        Args:
            value: Desired login name.

        Returns:
            The unchanged value when valid.

        Raises:
            serializers.ValidationError: On bad shape or taken name.
        """
        if not USERNAME_RE.fullmatch(value):
            raise serializers.ValidationError("Only latin letters and digits.")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This user name is taken.")
        return value

    def validate_email(self, value: str) -> str:
        """Require an email not yet registered.

        Args:
            value: Desired email address.

        Returns:
            The unchanged value when valid.

        Raises:
            serializers.ValidationError: When the email is taken.
        """
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is taken.")
        return value

    def validate_password(self, value: str) -> str:
        """Run Django password validators.

        Args:
            value: Raw password.

        Returns:
            The unchanged value when valid.

        Raises:
            serializers.ValidationError: When validators reject it.
        """
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        """Create the user with a hashed password.

        Args:
            validated_data: Validated registration fields.

        Returns:
            The new User instance.
        """
        return User.objects.create_user(
            username=validated_data["user_name"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class EmailTokenObtainSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Authenticate by email + password and issue a JWT pair.

        Args:
            attrs: Submitted email and password.

        Returns:
            Dict with refresh and access tokens.

        Raises:
            serializers.ValidationError: On unknown email or bad password.
        """
        try:
            account = User.objects.get(email__iexact=attrs["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")
        user = authenticate(username=account.username, password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
