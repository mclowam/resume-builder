from io import BytesIO
from zipfile import BadZipFile, is_zipfile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.text.paragraph import Paragraph
from lxml.etree import XMLSyntaxError
from pypdf import PdfReader
from pypdf.errors import PyPdfError


class TextExtractor:
    def extract(self, data: bytes) -> str:
        if not data:
            raise ValueError("Resume file must not be empty")

        try:
            if data.lstrip().startswith(b"%PDF-"):
                document = PdfReader(BytesIO(data))
                if document.is_encrypted:
                    raise ValueError("Encrypted PDF is not supported")
                text = "\n".join(page.extract_text() or "" for page in document.pages)
            elif is_zipfile(BytesIO(data)):
                document = Document(BytesIO(data))
                text = "\n".join(
                    Paragraph(element, document).text
                    for element in document.element.body.xpath(".//w:p")
                )
            else:
                raise ValueError("Resume must be a PDF or DOCX file")
        except (PyPdfError, BadZipFile, PackageNotFoundError, XMLSyntaxError, KeyError) as exc:
            raise ValueError("Resume must be a valid PDF or DOCX file") from exc

        text = text.strip()
        if not text:
            raise ValueError("Resume text must not be empty")
        return text
