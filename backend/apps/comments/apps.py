from django.apps import AppConfig


class CommentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.comments"

    def ready(self) -> None:
        """Connect domain event handlers."""
        from apps.comments import signals  # noqa: F401
