"""
Development settings override.
Removes AsyncRequestTimingMiddleware which causes startup hangs.
"""
from backend.settings import *  # noqa: F401,F403

MIDDLEWARE = [m for m in MIDDLEWARE if m != 'backend.middleware.async_middleware.AsyncRequestTimingMiddleware']  # noqa: F405
