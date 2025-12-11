from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from utils.embed import generate_embedding
from utils.extractors.doc_extractor import doc_extractor

# Directory to store uploaded files
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(title="Upload & Embeddings API")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must include a filename.")
    
    # Save the uploaded file
    destination = UPLOAD_DIR / file.filename
    print(f"Saving uploaded file to: {destination}")
    try:
        with destination.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
    finally:
        await file.close()

    
    content = doc_extractor(destination)

    # Generate embeddings
    embeddings = generate_embedding(content)

    # Return JSON response
    return JSONResponse(
        status_code=201,
        content={
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": destination.stat().st_size,
            "content": content,
            "embeddings": embeddings
        }
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
