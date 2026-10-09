import hashlib
from passlib.context import CryptContext


class PasswordHashed:
    def __init__(self):
        self._ctx = CryptContext(
            schemes=["argon2", "bcrypt"],
            deprecated="auto",
        )

    @staticmethod
    def _prepare(plain: str) -> str:
        return hashlib.sha256(plain.encode("utf-8")).hexdigest()

    def hash(self, plain: str) -> str:
        return self._ctx.hash(self._prepare(plain))

    def verify(self, plain: str, hashed: str) -> bool:
        return self._ctx.verify(self._prepare(plain), hashed)