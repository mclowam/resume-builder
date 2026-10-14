from typing import Protocol


class IImageStorage(Protocol):
    async def upload_file(self, file_obj, key: str, *, content_type: str | None = None) -> None:
        pass

    def get_file_url(self, key: str) -> str:
        pass

    def get_key(self, file_url: str) -> str:
        pass

    async def get_bytes(self, key: str) -> tuple[bytes, str]:
        pass

    async def delete_file(self, object_key: str) -> None:
        pass
