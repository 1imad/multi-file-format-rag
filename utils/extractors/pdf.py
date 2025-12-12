import pymupdf
from fastapi import HTTPException
from pathlib import Path


def pdf_extractor(destination):
    """Extract text from PDF, preserving page structure"""
    try:
        # Convert to Path object if string
        pdf_path = Path(destination) if isinstance(destination, str) else destination

        # Open PDF file
        doc = pymupdf.open(pdf_path)

        # Extract text with page breaks
        pages_text = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            if text.strip():  # Only add non-empty pages
                pages_text.append(text)

        # Close the document
        doc.close()

        return "\f".join(pages_text)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"PDF file not found: {str(destination)}"
        ) from e
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"PDF extraction failed: {str(exc)}",
        ) from exc
