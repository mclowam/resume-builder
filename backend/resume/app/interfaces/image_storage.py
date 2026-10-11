from typing import Protocol


class IImageStorage(Protocol):
    async def upload_image(self, file_obj, key: str, *, content_type: str | None = None) -> None:
        pass

    async def get_bytes(self, key: str) -> tuple[bytes, str]:
        pass

    async def delete_file(self, object_key: str) -> None:
        pass
