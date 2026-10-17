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


async def validate_resume_file(file: UploadFile) -> tuple[str, str]:
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
    await run_in_threadpool(_validate_file, file.file, content_type)
    return filename, content_type


def _validate_file(file: BinaryIO, content_type: str) -> None:
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
