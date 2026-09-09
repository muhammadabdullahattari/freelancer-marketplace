from datetime import timedelta
from app.core.config import settings

class CookieSettings:
    
    ACCESS_TOKEN_COOKIE_NAME = "access_token"
    ACCESS_TOKEN_COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 
    
    REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
    REFRESH_TOKEN_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 
    
    SESSION_ID_COOKIE_NAME = "session_id"
    SESSION_ID_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    
    COOKIE_DOMAIN = None  
    COOKIE_PATH = "/"
    COOKIE_SECURE = True 
    COOKIE_HTTPONLY = True  
    COOKIE_SAMESITE = "strict"  
    
    if settings.DEBUG:
        COOKIE_SECURE = False 
        COOKIE_SAMESITE = "lax"
    
    @staticmethod
    def get_access_token_cookie_options() -> dict:
        return {
            "key": CookieSettings.ACCESS_TOKEN_COOKIE_NAME,
            "max_age": CookieSettings.ACCESS_TOKEN_COOKIE_MAX_AGE,
            "path": CookieSettings.COOKIE_PATH,
            "domain": CookieSettings.COOKIE_DOMAIN,
            "secure": CookieSettings.COOKIE_SECURE,
            "httponly": CookieSettings.COOKIE_HTTPONLY,
            "samesite": CookieSettings.COOKIE_SAMESITE
        }
    
    @staticmethod
    def get_refresh_token_cookie_options() -> dict:
        return {
            "key": CookieSettings.REFRESH_TOKEN_COOKIE_NAME,
            "max_age": CookieSettings.REFRESH_TOKEN_COOKIE_MAX_AGE,
            "path": CookieSettings.COOKIE_PATH,
            "domain": CookieSettings.COOKIE_DOMAIN,
            "secure": CookieSettings.COOKIE_SECURE,
            "httponly": CookieSettings.COOKIE_HTTPONLY,
            "samesite": CookieSettings.COOKIE_SAMESITE
        }
    
    @staticmethod
    def get_session_id_cookie_options() -> dict:
        return {
            "key": CookieSettings.SESSION_ID_COOKIE_NAME,
            "max_age": CookieSettings.SESSION_ID_COOKIE_MAX_AGE,
            "path": CookieSettings.COOKIE_PATH,
            "domain": CookieSettings.COOKIE_DOMAIN,
            "secure": CookieSettings.COOKIE_SECURE,
            "httponly": CookieSettings.COOKIE_HTTPONLY,
            "samesite": CookieSettings.COOKIE_SAMESITE
        }