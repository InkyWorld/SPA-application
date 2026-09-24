from django.contrib import admin

from apps.comments.models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "user_name", "email", "parent_id", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user_name", "email", "text")
    readonly_fields = ("created_at",)
