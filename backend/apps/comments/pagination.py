from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class TopLevelPagination(PageNumberPagination):
    """Paginate top-level comments, fixed at 25 per page."""
    page_size = settings.COMMENTS_PAGE_SIZE
    page_size_query_param = None
    max_page_size = settings.COMMENTS_PAGE_SIZE
