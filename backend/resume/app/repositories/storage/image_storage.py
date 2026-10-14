from urllib.parse import quote, unquote

from aioboto3 import Session
from botocore.exceptions import ClientError

from app.core.config import Config

session_minio = Session()


class ImageStorage:
    def __init__(self, settings: Config):
        self._settings = settings

    def get_file_url(self, key: str) -> str:
        endpoint = self._settings.MINIO_ENDPOINT_URL.rstrip("/")
        return f"{endpoint}/{self._settings.MINIO_BUCKET}/{quote(key, safe='/')}"

    def get_key(self, file_url: str) -> str:
        prefix = self.get_file_url("")
        if not file_url.startswith(prefix) or file_url == prefix:
            raise ValueError("Invalid resume file URL")
        return unquote(file_url[len(prefix):])

    async def upload_file(
            self,
            file_obj,
            key: str,
            *,
            content_type: str | None = None,
    ) -> None:
        extra: dict[str, str] = {}
        if content_type:
            extra["ContentType"] = content_type
        async with session_minio.client(
                "s3",
                endpoint_url=self._settings.MINIO_ENDPOINT_URL,
                aws_access_key_id=self._settings.MINIO_ROOT_USER,
                aws_secret_access_key=self._settings.MINIO_ROOT_PASSWORD,
        ) as s3:
            bucket = self._settings.MINIO_BUCKET
            if extra:
                await s3.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra)
            else:
                await s3.upload_fileobj(file_obj, bucket, key)

    async def get_bytes(self, key: str) -> tuple[bytes, str]:
        async with session_minio.client(
                "s3",
                endpoint_url=self._settings.MINIO_ENDPOINT_URL,
                aws_access_key_id=self._settings.MINIO_ROOT_USER,
                aws_secret_access_key=self._settings.MINIO_ROOT_PASSWORD,
        ) as s3:
            try:
                response = await s3.get_object(
                    Bucket=self._settings.MINIO_BUCKET,
                    Key=key,
                )
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
                    raise FileNotFoundError(key) from exc
                raise
            async with response["Body"] as body:
                data = await body.read()
            content_type = response.get("ContentType") or "application/octet-stream"

            return data, content_type

    async def delete_file(self, object_key: str) -> None:
        async with session_minio.client(
                "s3",
                endpoint_url=self._settings.MINIO_ENDPOINT_URL,
                aws_access_key_id=self._settings.MINIO_ROOT_USER,
                aws_secret_access_key=self._settings.MINIO_ROOT_PASSWORD,
        ) as s3:
            await s3.delete_object(
                Bucket=self._settings.MINIO_BUCKET,
                Key=object_key,
            )
