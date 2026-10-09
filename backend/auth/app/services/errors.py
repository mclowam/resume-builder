class AuthError(Exception):
    pass


class InvalidRefreshTokenError(AuthError):
    pass