"""Use-case: create a comment. View stays thin, logic lives here."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.files.uploadedfile import UploadedFile

from apps.comments.models import Comment
from apps.comments.services import files as file_rules
from apps.comments.services import sanitizer


@dataclass(frozen=True)
class CreateCommentInput:
    user_name: str
    email: str
    text: str
    home_page: str = ""
    parent_id: int | None = None
    file: UploadedFile | None = None


class CommentCreator:
    """Single public method `execute` — easy to test, no fat view.

    CAPTCHA is verified earlier in the serializer (package store, one-time),
    so by the time input reaches here it is already human-checked.
    """

    def execute(self, data: CreateCommentInput) -> Comment:
        """Validate files, sanitize text and persist a new comment.

        The attached image is stored as-is; downscaling happens in
        the background resize task (see signals). Callers get 201 fast.

        Args:
            data: Validated use-case input (CAPTCHA already checked
                in the serializer).

        Returns:
            The saved Comment instance.

        Raises:
            DjangoValidationError: When uploads are invalid or model
                validation fails.
            UnclosedTagError: When the text has unbalanced markup.
        """
        file_rules.validate_upload(data.file)
        image, text_file = None, None
        if data.file is not None:
            if file_rules.is_image(data.file):
                image = data.file
            else:
                text_file = data.file
        comment = Comment(
            parent_id=data.parent_id,
            user_name=data.user_name,
            email=data.email,
            home_page=data.home_page or "",
            text=sanitizer.sanitize(data.text),
            image=image,
            text_file=text_file,
        )
        comment.full_clean(exclude=["text"])
        comment.save()
        return comment
