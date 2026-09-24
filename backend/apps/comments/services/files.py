"""File rules from the task: images fit 320x240, txt <= 100 kB."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image

IMAGE_EXTS = set(settings.IMAGE_EXTENSIONS)


def is_image(upload: UploadedFile) -> bool:
    """Tell whether an upload is an image by extension.

    Args:
        upload: Uploaded file.

    Returns:
        True for JPG/GIF/PNG extensions, False for TXT.
    """
    return Path(upload.name).suffix.lower() in IMAGE_EXTS


def validate_upload(upload: UploadedFile | None) -> None:
    """Route an upload to the matching validator by file extension.

    Args:
        upload: Uploaded file or None (no file is valid).

    Raises:
        ValidationError: Dict-shaped error keyed by field name when the
            extension is unknown or the content check fails.
    """
    if upload is None:
        return
    ext = Path(upload.name).suffix.lower()
    if ext in IMAGE_EXTS:
        _validate_image(upload)
    elif ext == ".txt":
        _validate_text(upload)
    else:
        raise ValidationError({"file": "Only JPG/GIF/PNG images or TXT files are allowed."})


def _validate_image(upload: UploadedFile) -> None:
    """Reject files Pillow cannot parse as an image.

    Args:
        upload: Uploaded file with an image extension.

    Raises:
        ValidationError: With the "image" key when parsing fails.
    """
    try:
        upload.seek(0)
        with Image.open(upload) as img:
            img.verify()
    except Exception as exc:
        raise ValidationError({"image": "Invalid image file."}) from exc
    finally:
        upload.seek(0)


def _validate_text(upload: UploadedFile) -> None:
    """Reject text files larger than the task's 100 kB limit.

    Args:
        upload: Uploaded file with the .txt extension.

    Raises:
        ValidationError: With the "text_file" key when the file is too big.
    """
    if upload.size > settings.TEXT_FILE_MAX_BYTES:
        raise ValidationError({"text_file": "Text file must not exceed 100 kB."})


def resize_image(path: str) -> None:
    """Proportionally downscale a stored image to fit IMAGE_MAX_SIZE in place.

    Args:
        path: Filesystem path of the stored image.
    """
    max_size: tuple[int, int] = settings.IMAGE_MAX_SIZE
    with Image.open(path) as img:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(path)
