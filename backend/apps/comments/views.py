"""Thin views: parse request -> call service/selector -> return response.

Side effects (WS broadcast, cache invalidation, image jobs) live in
signals, fired by model save; verification happens in the serializer.
"""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.comments import selectors
from apps.comments.models import Comment
from apps.comments.pagination import TopLevelPagination
from apps.comments.serializers import (
    CommentCreateSerializer,
    CommentNodeSerializer,
    EmailTokenObtainSerializer,
    MeSerializer,
    PreviewSerializer,
    RegisterSerializer,
)
from apps.comments.services import sanitizer
from apps.comments.services.comments import CommentCreator, CreateCommentInput
from apps.comments.services.tree import build_tree

creator = CommentCreator()


class CommentViewSet(viewsets.GenericViewSet):
    queryset = Comment.objects.all()
    pagination_class = TopLevelPagination

    def get_permissions(self):
        """Posting and preview require login; reading stays public."""
        if self.action in ("create", "preview"):
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_class(self):
        """Return the serializer per action (used by schema generation).

        Returns:
            Preview serializer for preview, tree serializer for listing,
            create serializer otherwise.
        """
        if self.action == "preview":
            return PreviewSerializer
        if self.action == "list":
            return CommentNodeSerializer
        return CommentCreateSerializer

    def list(self, request: Request) -> Response:
        """Return one page of top-level comments with nested replies.

        Args:
            request: DRF request; honors the `?sort=` and `?page=` params.

        Returns:
            Paginated response with nested comment trees (cached 5 min).
        """
        sort = request.query_params.get("sort")
        qs = selectors.top_level_qs(sort)
        page_number = self.paginator.get_page_number(request, qs)
        cached = cache.get(selectors.list_cache_key(sort, page_number))
        if cached is not None:
            return Response(cached)
        page = self.paginate_queryset(qs)
        # page already arrives in the requested sort order — keep it.
        nodes = self._nodes_for_page(list(page) if page else [])
        serializer = CommentNodeSerializer(
            [n["comment"] for n in nodes],
            many=True, context={"children_map": self._children_map(nodes)},
        )
        response = self.get_paginated_response(serializer.data)
        cache.set(
            selectors.list_cache_key(sort, page_number),
            response.data, timeout=settings.COMMENTS_LIST_CACHE_TTL,
        )
        return response

    def create(self, request: Request) -> Response:
        """Validate input, create a comment and notify WS subscribers.

        Args:
            request: DRF request with multipart form data.

        Returns:
            201 response with the new comment id, or 400 with field errors.
        """
        form = CommentCreateSerializer(
            data=request.data, context={"request": request}
        )
        form.is_valid(raise_exception=True)
        try:
            comment = creator.execute(self._to_input(form.validated_data, request))
        except DjangoValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": comment.pk}, status=status.HTTP_201_CREATED)


    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request: Request) -> Response:
        """Sanitize markup and return it without saving anything.

        Args:
            request: DRF request with a JSON body holding "text".

        Returns:
            Response with the sanitized "html", or 400 on bad markup.
        """
        form = PreviewSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        return Response({"html": sanitizer.sanitize(form.validated_data["text"])})

    # --- helpers (each does one thing) ---
    def _to_input(self, data: dict, request: Request) -> CreateCommentInput:
        """Map validated data and request metadata to the use-case input.

        Args:
            data: Validated serializer data (CAPTCHA already consumed).
            request: DRF request carrying the uploaded files.

        Returns:
            Populated CreateCommentInput for CommentCreator.
        """
        return CreateCommentInput(
            user_name=data["user_name"], email=data["email"],
            text=data["text"], home_page=data.get("home_page") or "",
            parent_id=data.get("parent_id"),
            file=request.FILES.get("file"),
        )

    @staticmethod
    def _nodes_for_page(page: list[Comment]) -> list[dict]:
        """Attach every descendant to its page item and keep page order.

        Args:
            page: Top-level comments of the current page, already sorted.

        Returns:
            Tree nodes in the same order as the input page.
        """
        ids = [c.pk for c in page]
        all_comments = list(page)
        all_comments += list(selectors.subtree_for_parents(ids))
        tree = build_tree(all_comments)
        order = {c.pk: i for i, c in enumerate(page)}
        return sorted(tree, key=lambda n: order.get(n["comment"].pk, 0))

    @staticmethod
    def _children_map(nodes: list[dict]) -> dict:
        """Flatten the tree into a children map for the serializer.

        Args:
            nodes: Tree nodes built by _nodes_for_page.

        Returns:
            Mapping of parent pk to child comment lists.
        """
        flat: dict[int, list] = {}

        def walk(items: list[dict]) -> None:
            """Recursively collect children for every tree node.

            Args:
                items: Tree nodes at the current level.
            """
            for item in items:
                flat[item["comment"].pk] = [r["comment"] for r in item["replies"]]
                walk(item["replies"])

        walk(nodes)
        return flat


class RegisterView(generics.CreateAPIView):
    """Public registration with user name, email and password."""

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Register the user and return its public profile.

        Args:
            request: DRF request with registration fields.

        Returns:
            201 response with id, user_name and email.
        """
        form = self.get_serializer(data=request.data)
        form.is_valid(raise_exception=True)
        user = form.save()
        return Response(
            {"id": user.pk, "user_name": user.username, "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class EmailTokenObtainView(TokenObtainPairView):
    """JWT pair issuance by email + password (instead of username)."""

    serializer_class = EmailTokenObtainSerializer


class MeView(generics.RetrieveAPIView):
    """Current JWT profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        """Return the profile dict for the requesting user.

        Returns:
            Dict with id, user_name and email.
        """
        user = self.request.user
        return {"id": user.pk, "user_name": user.username, "email": user.email}
