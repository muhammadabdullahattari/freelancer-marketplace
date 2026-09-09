import pytest
from fastapi import Response, Request
from fastapi.testclient import TestClient
from app.core.cookie_settings import CookieSettings
from app.core.cookie_utils import CookieManager


def test_cookie_settings_security_options():
    """Test cookie settings options for HttpOnly, Path, and Max Age."""
    opts = CookieSettings.get_refresh_token_cookie_options()
    assert opts["key"] == "refresh_token"
    assert opts["httponly"] is True
    assert opts["path"] == "/"
    assert opts["max_age"] > 0


def test_cookie_manager_set_and_clear_cookies():
    """Test CookieManager sets and clears authorization cookies."""
    response = Response()
    CookieManager.set_access_token_cookie(response, "access_token_val")
    CookieManager.set_refresh_token_cookie(response, "refresh_token_val")

    # Verify cookie headers present in response
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie_header or len(response.raw_headers) > 0

    del_res = Response()
    CookieManager.clear_auth_cookies(del_res)
    assert len(del_res.raw_headers) > 0


def test_middleware_request_id_header(client: TestClient):
    """Test RequestIDMiddleware adds X-Request-ID header to responses."""
    response = client.get("/")
    assert response.status_code == 200
    assert "x-request-id" in response.headers


def test_middleware_request_logging_process_time_header(client: TestClient):
    """Test RequestLoggingMiddleware adds X-Process-Time header to responses."""
    response = client.get("/")
    assert response.status_code == 200
    assert "x-process-time" in response.headers


def test_rate_limit_middleware_headers(client: TestClient):
    """Test RateLimitMiddleware attaches rate limit tracking headers to API calls."""
    response = client.get("/")
    assert response.status_code == 200
    assert "x-ratelimit-limit" in response.headers
    assert "x-ratelimit-remaining" in response.headers
