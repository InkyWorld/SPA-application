from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.comments.views import (
    CommentViewSet,
    EmailTokenObtainView,
    MeView,
    RegisterView,
)

router = DefaultRouter()
router.register("comments", CommentViewSet, basename="comments")

urlpatterns = [
    # django-simple-captcha: refresh/ (AJAX JSON) + image/<key>/ (PNG).
    path("captcha/", include("captcha.urls")),
    # Auth: registration, JWT by email + password, current profile.
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", EmailTokenObtainView.as_view(), name="token_obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    # Generated backend docs: raw schema, Swagger UI, ReDoc.
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    *router.urls,
]
