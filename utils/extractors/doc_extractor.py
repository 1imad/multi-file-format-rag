import subprocess
from fastapi import HTTPException

def doc_extractor(destination):
    """Extract text from document, preserving page structure when possible"""
    try:
        # Try to extract with page breaks preserved
        result = subprocess.run(
            ["pandoc", str(destination), "-t", "markdown", "--reference-links"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500, detail="Pandoc is not installed on the server."
        ) from e
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Pandoc conversion failed: {exc.stderr.strip()}",
        ) from exc

    return result.stdout