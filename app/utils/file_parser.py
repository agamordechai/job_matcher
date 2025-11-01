"""File parsing utilities for CV processing"""
import pypdf
from docx import Document
from typing import Optional


def parse_pdf(file_path: str) -> str:
    """Parse PDF file and extract text"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")


def parse_docx(file_path: str) -> str:
    """Parse DOCX file and extract text"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX: {str(e)}")


def parse_cv_file(file_path: str, file_ext: str) -> str:
    """Parse CV file based on extension"""
    if file_ext in ['pdf']:
        return parse_pdf(file_path)
    elif file_ext in ['docx', 'doc']:
        return parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")

