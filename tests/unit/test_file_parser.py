"""Unit tests for File Parser utilities"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import os

from app.utils.file_parser import parse_pdf, parse_docx, parse_cv_file


class TestParsePDF:
    """Tests for PDF parsing"""

    def test_parse_pdf_success(self, tmp_path):
        """Test successful PDF parsing"""
        with patch('pypdf.PdfReader') as mock_pdf_reader, \
             patch('builtins.open', mock_open(read_data=b'fake pdf')):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test PDF content"
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            result = parse_pdf("/fake/path/test.pdf")

            assert result == "Test PDF content"

    def test_parse_pdf_multiple_pages(self):
        """Test PDF parsing with multiple pages"""
        with patch('pypdf.PdfReader') as mock_pdf_reader, \
             patch('builtins.open', mock_open(read_data=b'fake pdf')):
            mock_pages = []
            for i in range(3):
                mock_page = MagicMock()
                mock_page.extract_text.return_value = f"Page {i+1} content"
                mock_pages.append(mock_page)

            mock_reader = MagicMock()
            mock_reader.pages = mock_pages
            mock_pdf_reader.return_value = mock_reader

            result = parse_pdf("/fake/path/test.pdf")

            assert "Page 1 content" in result
            assert "Page 2 content" in result
            assert "Page 3 content" in result

    def test_parse_pdf_empty(self):
        """Test parsing empty PDF"""
        with patch('pypdf.PdfReader') as mock_pdf_reader, \
             patch('builtins.open', mock_open(read_data=b'fake pdf')):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = ""
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            result = parse_pdf("/fake/path/empty.pdf")

            assert result == ""

    def test_parse_pdf_error(self):
        """Test PDF parsing error handling"""
        with patch('app.utils.file_parser.pypdf') as mock_pypdf:
            mock_pypdf.PdfReader.side_effect = Exception("Corrupted PDF")

            with pytest.raises(ValueError) as exc_info:
                parse_pdf("/fake/path/corrupted.pdf")

            assert "Failed to parse PDF" in str(exc_info.value)

    def test_parse_pdf_file_not_found(self):
        """Test PDF parsing when file doesn't exist"""
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")), \
             patch('app.utils.file_parser.pypdf'):

            with pytest.raises(ValueError) as exc_info:
                parse_pdf("/nonexistent/path/test.pdf")

            assert "Failed to parse PDF" in str(exc_info.value)


class TestParseDOCX:
    """Tests for DOCX parsing"""

    def test_parse_docx_success(self):
        """Test successful DOCX parsing"""
        with patch('app.utils.file_parser.Document') as mock_document:
            mock_para1 = MagicMock()
            mock_para1.text = "First paragraph"
            mock_para2 = MagicMock()
            mock_para2.text = "Second paragraph"

            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para1, mock_para2]
            mock_document.return_value = mock_doc

            result = parse_docx("/fake/path/test.docx")

            assert "First paragraph" in result
            assert "Second paragraph" in result

    def test_parse_docx_empty(self):
        """Test parsing empty DOCX"""
        with patch('app.utils.file_parser.Document') as mock_document:
            mock_doc = MagicMock()
            mock_doc.paragraphs = []
            mock_document.return_value = mock_doc

            result = parse_docx("/fake/path/empty.docx")

            assert result == ""

    def test_parse_docx_error(self):
        """Test DOCX parsing error handling"""
        with patch('app.utils.file_parser.Document') as mock_document:
            mock_document.side_effect = Exception("Invalid DOCX")

            with pytest.raises(ValueError) as exc_info:
                parse_docx("/fake/path/invalid.docx")

            assert "Failed to parse DOCX" in str(exc_info.value)

    def test_parse_docx_whitespace_paragraphs(self):
        """Test DOCX parsing with whitespace-only paragraphs"""
        with patch('app.utils.file_parser.Document') as mock_document:
            mock_para1 = MagicMock()
            mock_para1.text = "Content"
            mock_para2 = MagicMock()
            mock_para2.text = "   "  # Whitespace only
            mock_para3 = MagicMock()
            mock_para3.text = "More content"

            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]
            mock_document.return_value = mock_doc

            result = parse_docx("/fake/path/test.docx")

            assert "Content" in result
            assert "More content" in result


class TestParseCVFile:
    """Tests for the main parse_cv_file function"""

    def test_parse_cv_file_pdf(self):
        """Test parsing PDF CV file"""
        with patch('app.utils.file_parser.parse_pdf', return_value="PDF content"):
            result = parse_cv_file("/fake/path/cv.pdf", "pdf")
            assert result == "PDF content"

    def test_parse_cv_file_docx(self):
        """Test parsing DOCX CV file"""
        with patch('app.utils.file_parser.parse_docx', return_value="DOCX content"):
            result = parse_cv_file("/fake/path/cv.docx", "docx")
            assert result == "DOCX content"

    def test_parse_cv_file_doc(self):
        """Test parsing DOC CV file (legacy format)"""
        with patch('app.utils.file_parser.parse_docx', return_value="DOC content"):
            result = parse_cv_file("/fake/path/cv.doc", "doc")
            assert result == "DOC content"

    def test_parse_cv_file_unsupported(self):
        """Test parsing unsupported file type"""
        with pytest.raises(ValueError) as exc_info:
            parse_cv_file("/fake/path/cv.txt", "txt")

        assert "Unsupported file type" in str(exc_info.value)

    def test_parse_cv_file_unsupported_image(self):
        """Test parsing image file (unsupported)"""
        with pytest.raises(ValueError) as exc_info:
            parse_cv_file("/fake/path/cv.png", "png")

        assert "Unsupported file type" in str(exc_info.value)


class TestFileParserEdgeCases:
    """Edge case tests for file parser"""

    def test_parse_pdf_special_characters(self):
        """Test parsing PDF with special characters"""
        with patch('pypdf.PdfReader') as mock_pdf_reader, \
             patch('builtins.open', mock_open(read_data=b'fake pdf')):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Content with special chars: @#$%^&*()"
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            result = parse_pdf("/fake/path/test.pdf")

            assert "@#$%^&*()" in result

    def test_parse_pdf_unicode(self):
        """Test parsing PDF with unicode characters"""
        with patch('pypdf.PdfReader') as mock_pdf_reader, \
             patch('builtins.open', mock_open(read_data=b'fake pdf')):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Content with unicode: "
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            result = parse_pdf("/fake/path/test.pdf")

            assert "" in result

    def test_parse_docx_unicode(self):
        """Test parsing DOCX with unicode characters"""
        with patch('app.utils.file_parser.Document') as mock_document:
            mock_para = MagicMock()
            mock_para.text = "Resume with emojis "
            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para]
            mock_document.return_value = mock_doc

            result = parse_docx("/fake/path/test.docx")

            assert "" in result

    def test_parse_cv_file_case_insensitive_extension(self):
        """Test that file extension is handled (assumes lowercase in the test)"""
        # The parse_cv_file function expects lowercase extension
        with patch('app.utils.file_parser.parse_pdf', return_value="PDF content"):
            # Extension should be passed as lowercase by the calling code
            result = parse_cv_file("/fake/path/CV.PDF", "pdf")
            assert result == "PDF content"

    def test_parse_pdf_strips_whitespace(self):
        """Test that result is stripped of whitespace"""
        with patch('pypdf.PdfReader') as mock_pdf_reader, \
             patch('builtins.open', mock_open(read_data=b'fake pdf')):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "  Content with whitespace  "
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            result = parse_pdf("/fake/path/test.pdf")

            assert result == "Content with whitespace"

    def test_parse_pdf_large_file(self):
        """Test parsing large PDF with many pages"""
        with patch('pypdf.PdfReader') as mock_pdf_reader, \
             patch('builtins.open', mock_open(read_data=b'fake pdf')):
            mock_pages = []
            for i in range(100):
                mock_page = MagicMock()
                mock_page.extract_text.return_value = f"Page {i} content " * 100
                mock_pages.append(mock_page)

            mock_reader = MagicMock()
            mock_reader.pages = mock_pages
            mock_pdf_reader.return_value = mock_reader

            result = parse_pdf("/fake/path/large.pdf")

            assert len(result) > 0
            assert "Page 0 content" in result
            assert "Page 99 content" in result
