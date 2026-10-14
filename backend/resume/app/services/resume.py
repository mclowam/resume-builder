import logging
import uuid
from pathlib import PurePosixPath
from typing import BinaryIO
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from fastapi import HTTPException, UploadFile
from lxml.etree import XMLSyntaxError
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from starlette.concurrency import run_in_threadpool

from app.interfaces.image_storage import IImageStorage
from app.interfaces.resume import IResume
from app.schemas.resume import ResumeCreateSchema, ResumeResponseSchema


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
        filename = PurePosixPath((file.filename or "").replace("\\", "/")).name
        content_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        content_type = content_types.get(PurePosixPath(filename).suffix.lower())
        if content_type is None or any(ord(char) < 32 or ord(char) == 127 for char in filename):
            raise HTTPException(detail="Resume must be a PDF or DOCX file", status_code=422)
        if not await file.read(1):
            raise HTTPException(detail="Resume file must not be empty", status_code=422)
        await file.seek(0)
        await run_in_threadpool(self._validate_file, file.file, content_type)

        key = f"{user_id}/{uuid.uuid4()}/{filename}"
        data = ResumeCreateSchema(file_url=self._file_storage.get_file_url(key))
        await self._file_storage.upload_file(file.file, key, content_type=content_type)
        try:
            resume = await self._resume_repo.add(data, user_id)
        except Exception:
            try:
                await self._file_storage.delete_file(key)
            except Exception:
                logger.exception("Failed to delete resume file after database failure")
            raise

        return ResumeResponseSchema(
            id=resume.id,
            user_id=resume.user_id,
            file_url=resume.file_url,
            embedding=resume.embedding,
            created_at=resume.created_at
        )

    def _validate_file(self, file: BinaryIO, content_type: str) -> None:
        try:
            if content_type == "application/pdf":
                document = PdfReader(file, strict=True)
                if document.is_encrypted or not len(document.pages):
                    raise ValueError("PDF must contain readable pages")
            else:
                document = Document(file)
                if document.element.tag != qn("w:document") or document.element.body is None:
                    raise ValueError("DOCX must contain a document body")
        except (PyPdfError, BadZipFile, PackageNotFoundError, XMLSyntaxError, ValueError, KeyError) as exc:
            raise HTTPException(detail="Resume must be a valid PDF or DOCX file", status_code=422) from exc
        finally:
            file.seek(0)

    async def get_by_id(self, resume_id: uuid.UUID) -> ResumeResponseSchema:
        resume = await self._resume_repo.get_by_id(resume_id)

        if resume is None:
            raise HTTPException(detail="Resume not found", status_code=404)

        return resume

    async def get_file(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> tuple[bytes, str, str]:
        resume = await self._resume_repo.get_by_id(resume_id)
        if resume is None or resume.user_id != user_id:
            raise HTTPException(detail="Resume not found", status_code=404)

        try:
            key = self._file_storage.get_key(resume.file_url)
            data, content_type = await self._file_storage.get_bytes(key)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(detail="Resume file not found", status_code=404) from exc

        return data, content_type, PurePosixPath(key).name

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[ResumeResponseSchema]:
        resumes = await self._resume_repo.get_by_user_id(user_id)

        return resumes
