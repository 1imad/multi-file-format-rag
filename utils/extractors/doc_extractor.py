import subprocess
from fastapi import HTTPException

def doc_extractor(destination):
    try:
        result = subprocess.run(
            ["pandoc", str(destination), "-t", "markdown"],
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
            detail=f"Pandoc conversion failed: {exc.stderr.strip()}"
        )

    return result.stdout