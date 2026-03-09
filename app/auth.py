"""Basic HTTP authentication middleware."""

import secrets
from fastapi import Request, HTTPException
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import base64

from app.config import get_settings


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Simple HTTP Basic Auth for the entire dashboard."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for static files
        if request.url.path.startswith("/static"):
            return await call_next(request)

        settings = get_settings()
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Basic "):
            return Response(
                content="Authentication required",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Domain IQ"'},
            )

        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            return Response(
                content="Invalid credentials",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Domain IQ"'},
            )

        # Constant-time comparison to prevent timing attacks
        correct_user = secrets.compare_digest(username, settings.AUTH_USERNAME)
        correct_pass = secrets.compare_digest(password, settings.AUTH_PASSWORD)

        if not (correct_user and correct_pass):
            return Response(
                content="Invalid credentials",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Domain IQ"'},
            )

        return await call_next(request)
