import io
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zipfile import ZipFile

from docx import Document
from fastapi import HTTPException, UploadFile
from pypdf import PdfWriter

from app.services.resume import ResumeService


class ResumeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()
        self.resume = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_url="http://minio/resumes/resume.pdf",
            embedding=None,
            created_at=datetime.now(timezone.utc),
        )
        self.repository = SimpleNamespace(add=AsyncMock(return_value=self.resume))
        self.storage = SimpleNamespace(
            get_file_url=Mock(return_value=self.resume.file_url),
            upload_file=AsyncMock(),
            delete_file=AsyncMock(),
        )
        self.service = ResumeService(self.repository, self.storage)

    def pdf_bytes(self, encrypted=False):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        if encrypted:
            writer.encrypt("password")
        stream = io.BytesIO()
        writer.write(stream)
        return stream.getvalue()

    def docx_bytes(self):
        document = Document()
        document.add_paragraph("Python developer")
        stream = io.BytesIO()
        document.save(stream)
        return stream.getvalue()

    def replace_document_xml(self, xml):
        stream = io.BytesIO()
        with ZipFile(io.BytesIO(self.docx_bytes())) as source, ZipFile(stream, "w") as target:
            for name in source.namelist():
                target.writestr(name, xml if name == "word/document.xml" else source.read(name))
        return stream.getvalue()

    async def test_valid_documents_upload_complete_original_bytes(self):
        for filename, data, content_type in (
            ("resume.PDF", self.pdf_bytes(), "application/pdf"),
            ("resume.docx", self.docx_bytes(),
             "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ):
            with self.subTest(filename=filename):
                async def upload(stream, key, *, content_type):
                    self.assertEqual(stream.tell(), 0)
                    self.assertEqual(stream.read(), data)

                self.storage.upload_file.side_effect = upload
                file = UploadFile(io.BytesIO(data), filename=filename)
                result = await self.service.create_resume(file, self.user_id)
                self.assertEqual(result.id, self.resume.id)
                self.assertEqual(self.storage.upload_file.call_args.kwargs["content_type"], content_type)
                self.repository.add.assert_awaited()
                self.storage.delete_file.assert_not_awaited()

    async def test_invalid_documents_rejected_before_storage_and_database(self):
        archive = io.BytesIO()
        with ZipFile(archive, "w") as zip_file:
            zip_file.writestr("resume.txt", "Python developer")
        for filename, data in (
            ("resume.pdf", b""),
            ("resume.docx", b""),
            ("resume.txt", b"Python developer"),
            ("resume.pdf", b"Python developer"),
            ("resume.pdf", b"%PDF-1.7\nnot a PDF\n%%EOF"),
            ("resume.docx", b"Python developer"),
            ("resume.pdf", self.docx_bytes()),
            ("resume.docx", self.pdf_bytes()),
            ("resume.pdf", self.pdf_bytes()[:100]),
            ("resume.docx", self.docx_bytes()[:100]),
            ("resume.docx", archive.getvalue()),
            ("resume.pdf", self.pdf_bytes(encrypted=True)),
            ("resume.docx", self.replace_document_xml(b"<broken>")),
            ("resume.docx", self.replace_document_xml(b"<wrong/>")),
        ):
            with self.subTest(filename=filename, data=data[:30]):
                file = UploadFile(io.BytesIO(data), filename=filename)
                with self.assertRaises(HTTPException) as error:
                    await self.service.create_resume(file, self.user_id)
                self.assertEqual(error.exception.status_code, 422)
                self.assertEqual(file.file.tell(), 0)
                self.storage.upload_file.assert_not_awaited()
                self.storage.get_file_url.assert_not_called()
                self.repository.add.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
