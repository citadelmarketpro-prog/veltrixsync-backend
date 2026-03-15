"""
Cookie-based JWT authentication.

Reads the access token from the `access_token` HTTP-only cookie instead of
the Authorization header. This keeps tokens out of JavaScript entirely.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import exceptions


class CookieJWTAuthentication(JWTAuthentication):
    """
    Extend simplejwt's default authentication to pull the token from
    the `access_token` cookie rather than the Authorization header.
    Falls back to the header if the cookie is absent (useful for API
    testing tools like Postman / DRF browsable API).
    """

    def authenticate(self, request):
        # 1. Try cookie first
        raw_token = request.COOKIES.get("access_token")

        # 2. Fall back to Authorization header
        if raw_token is None:
            header = self.get_header(request)
            if header is None:
                return None
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return self.get_user(validated_token), validated_token
