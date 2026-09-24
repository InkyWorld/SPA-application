"""Minimal CORS middleware — avoids adding django-cors-headers dependency."""

from __future__ import annotations


class AllowAllCorsMiddleware:
    def __init__(self, get_response):
        """Store the next handler in the chain.

        Args:
            get_response: Next middleware or view callable.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Add permissive CORS headers to every response.

        Args:
            request: Incoming Django request.

        Returns:
            Response from the chain with CORS headers attached.
        """
        response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response
