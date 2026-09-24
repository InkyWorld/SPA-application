"""Data layer only. No business logic here — see services/ and selectors.py."""

from __future__ import annotations

from django.db import models
from mptt.models import MPTTModel, TreeForeignKey


class Comment(MPTTModel):
    """One comment. `parent=None` => top-level record from the task."""

    parent = TreeForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="replies",
        on_delete=models.CASCADE,
    )
    user_name = models.CharField(max_length=50, db_index=True)
    email = models.EmailField(max_length=254, db_index=True)
    home_page = models.URLField(max_length=500, blank=True, default="")
    text = models.TextField(help_text="Sanitized XHTML with allowed tags only")
    image = models.ImageField(upload_to="images/%Y/%m/", blank=True, null=True)
    text_file = models.FileField(upload_to="files/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class MPTTMeta:
        order_insertion_by = ["-created_at"]

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["parent", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_name} #{self.pk}"
