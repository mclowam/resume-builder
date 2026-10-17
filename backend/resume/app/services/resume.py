import logging
import uuid
from pathlib import PurePosixPath

from fastapi import HTTPException, UploadFile

from app.interfaces.image_storage import IImageStorage
from app.interfaces.resume import IResume
from app.schemas.resume import ResumeCreateSchema, ResumeResponseSchema, ResumeSetEmbeddingSchema
from app.services.resume_file import validate_resume_file


logger = logging.getLogger(__name__)


class ResumeService:
    def __init__(
            self,
            resume_repository: IResume,
            file_storage: IImageStorage,
    ):
        self._resume_repo = resume_repository
        self._file_storage = file_storage

    async def create_resume(self, file: UploadFile, user_id: uuid.UUID) -> ResumeResponseSchema:
        filename, content_type = await validate_resume_file(file)

        key = f"{user_id}/{uuid.uuid4()}/{filename}"
        data = ResumeCreateSchema(file_url=self._file_storage.get_file_url(key))
        await self._file_storage.upload_file(file.file, key, content_type=content_type)
        try:
            resume = await self._resume_repo.add(data, user_id)
        except Exception:
            await self._delete_file_after_failure(key)
            raise

        return ResumeResponseSchema(
            id=resume.id,
            user_id=resume.user_id,
            file_url=resume.file_url,
            embedding=resume.embedding,
            created_at=resume.created_at
        )

    async def _delete_file_after_failure(self, key: str) -> None:
        try:
            await self._file_storage.delete_file(key)
        except Exception:
            logger.exception("Failed to delete resume file after database failure")

    async def get_by_id(self, resume_id: uuid.UUID) -> ResumeResponseSchema:
        resume = await self._resume_repo.get_by_id(resume_id)

        if resume is None:
            raise HTTPException(detail="Resume not found", status_code=404)

        return resume

    async def get_file(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> tuple[bytes, str, str]:
        resume = await self.get_by_id(resume_id)
        if resume.user_id != user_id:
            raise HTTPException(detail="Resume not found", status_code=404)

        try:
            key = self._file_storage.get_key(resume.file_url)
            data, content_type = await self._file_storage.get_bytes(key)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(detail="Resume file not found", status_code=404) from exc

        return data, content_type, PurePosixPath(key).name

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[ResumeResponseSchema]:
        return await self._resume_repo.get_by_user_id(user_id)

    async def set_embedding(self, resume_id: uuid.UUID, data: ResumeSetEmbeddingSchema):
        resume = await self._resume_repo.set_embedding(resume_id, data)

        if resume is None:
            raise HTTPException(detail="Resume not found", status_code=404)

        return resume
