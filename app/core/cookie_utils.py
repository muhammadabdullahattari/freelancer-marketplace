from fastapi import Response, Request, HTTPException, status
from app.core.cookie_settings import CookieSettings
import logging

logger = logging.getLogger(__name__)

class CookieManager:
    
    @staticmethod
    def set_access_token_cookie(response: Response, token: str) -> None:
        options = CookieSettings.get_access_token_cookie_options()
        response.set_cookie(value=token, **options)
        logger.debug("Access token cookie set")
    
    @staticmethod
    def set_refresh_token_cookie(response: Response, token: str) -> None:
        options = CookieSettings.get_refresh_token_cookie_options()
        response.set_cookie(value=token, **options)
        logger.debug("Refresh token cookie set")
    
    @staticmethod
    def set_session_id_cookie(response: Response, session_id: str) -> None:
        options = CookieSettings.get_session_id_cookie_options()
        response.set_cookie(value=session_id, **options)
        logger.debug("Session ID cookie set")
    
    @staticmethod
    def clear_auth_cookies(response: Response) -> None:
        response.delete_cookie(
            key=CookieSettings.ACCESS_TOKEN_COOKIE_NAME,
            path=CookieSettings.COOKIE_PATH,
            domain=CookieSettings.COOKIE_DOMAIN
        )
        response.delete_cookie(
            key=CookieSettings.REFRESH_TOKEN_COOKIE_NAME,
            path=CookieSettings.COOKIE_PATH,
            domain=CookieSettings.COOKIE_DOMAIN
        )
        response.delete_cookie(
            key=CookieSettings.SESSION_ID_COOKIE_NAME,
            path=CookieSettings.COOKIE_PATH,
            domain=CookieSettings.COOKIE_DOMAIN
        )
        logger.debug("All auth cookies cleared")
    
    @staticmethod
    def get_access_token_from_cookies(request: Request) -> str | None:
        return request.cookies.get(CookieSettings.ACCESS_TOKEN_COOKIE_NAME)
    
    @staticmethod
    def get_refresh_token_from_cookies(request: Request) -> str | None:
        return request.cookies.get(CookieSettings.REFRESH_TOKEN_COOKIE_NAME)
    
    @staticmethod
    def get_session_id_from_cookies(request: Request) -> str | None:
        return request.cookies.get(CookieSettings.SESSION_ID_COOKIE_NAME)