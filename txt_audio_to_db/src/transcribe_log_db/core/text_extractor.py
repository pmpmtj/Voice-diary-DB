"""
Text extraction utilities for various document formats.

Extract text content from .txt, .docx, and .pdf files with proper error handling.
Includes special handling for PDF extraction failures with clear logging.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# Add the project root to the path to import the config
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logging_utils.logging_config import get_logger

logger = get_logger("text_extractor")


def extract_text_content(file_path: Path) -> Dict[str, Any]:
    """
    Extract text content from various document formats.
    
    Args:
        file_path (Path): Path to the document file
        
    Returns:
        Dict[str, Any]: Structured data containing:
            - text: Extracted text content
            - title: First line of text (truncated to 255 chars)
            - source_file: File path as string
            - file_type: File extension
            
    Raises:
        ValueError: If file type is not supported
        FileNotFoundError: If file does not exist
    """
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_type = file_path.suffix.lower()
    logger.debug(f"Extracting text from {file_type} file: {file_path.name}")
    
    if file_type == ".txt":
        return _extract_txt_content(file_path)
    elif file_type == ".docx":
        return _extract_docx_content(file_path)
    elif file_type == ".pdf":
        return _extract_pdf_content(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _extract_txt_content(file_path: Path) -> Dict[str, Any]:
    """Extract text from .txt file with UTF-8 encoding and BOM handling."""
    try:
        # Try UTF-8 first, then fallback to other encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        text = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                logger.debug(f"Successfully read .txt file with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        
        if text is None:
            raise ValueError("Could not decode text file with any supported encoding")
            
        return _create_extraction_result(file_path, text, ".txt")
        
    except Exception as e:
        logger.error(f"Failed to extract text from .txt file {file_path}: {e}")
        raise


def _extract_docx_content(file_path: Path) -> Dict[str, Any]:
    """Extract text from .docx file using python-docx."""
    try:
        from docx import Document
        
        doc = Document(file_path)
        paragraphs = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():  # Skip empty paragraphs
                paragraphs.append(paragraph.text.strip())
        
        text = "\n".join(paragraphs)
        logger.debug(f"Successfully extracted {len(paragraphs)} paragraphs from .docx file")
        
        return _create_extraction_result(file_path, text, ".docx")
        
    except ImportError:
        logger.error("python-docx library not available. Install with: pip install python-docx")
        raise
    except Exception as e:
        logger.error(f"Failed to extract text from .docx file {file_path}: {e}")
        raise


def _extract_pdf_content(file_path: Path) -> Dict[str, Any]:
    """Extract text from .pdf file using PyPDF2 with special error handling."""
    try:
        import PyPDF2
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_parts = []
            
            for page_num in range(len(pdf_reader.pages)):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(page_text.strip())
                except Exception as page_error:
                    logger.warning(f"Failed to extract text from page {page_num + 1} of PDF {file_path.name}: {page_error}")
                    continue
            
            if not text_parts:
                raise ValueError("No text could be extracted from any page of the PDF")
            
            text = "\n".join(text_parts)
            logger.debug(f"Successfully extracted text from {len(text_parts)} pages of PDF")
            
            return _create_extraction_result(file_path, text, ".pdf")
            
    except ImportError:
        error_msg = "PyPDF2 library not available. Install with: pip install PyPDF2"
        logger.error(f"FAILED TO EXTRACT PDF: {file_path} - ERROR: {error_msg}")
        print(f"ERROR: {error_msg}")
        # Return empty result instead of raising to continue processing
        return _create_extraction_result(file_path, "", ".pdf")
        
    except Exception as e:
        error_msg = f"PDF extraction failed: {e}"
        logger.error(f"FAILED TO EXTRACT PDF: {file_path} - ERROR: {error_msg}")
        print(f"ERROR: FAILED TO EXTRACT PDF: {file_path} - {error_msg}")
        # Return empty result instead of raising to continue processing
        return _create_extraction_result(file_path, "", ".pdf")


def _create_extraction_result(file_path: Path, text: str, file_type: str) -> Dict[str, Any]:
    """Create standardized extraction result dictionary."""
    # Extract title from first line (up to 255 characters)
    lines = text.strip().split('\n')
    first_line = lines[0].strip() if lines else ""
    title = first_line[:255] if first_line else file_path.stem
    
    return {
        "text": text,
        "title": title,
        "source_file": str(file_path),
        "file_type": file_type
    }
