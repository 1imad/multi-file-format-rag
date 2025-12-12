from typing import List
from fastapi import HTTPException
import os
import dotenv
import requests

dotenv.load_dotenv()
EMBEDDING_URL = os.getenv("EMBEDDING_URL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

def generate_embedding(text: str) -> List[float]:
    """
    Generate embeddings for the given text using Ollama.
    """
    try:
        response = requests.post(
            EMBEDDING_URL,
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=10,
        )
        print(response.json())
    except requests.RequestException as exc:
        raise HTTPException(status_code=500, detail=f"Ollama request failed: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to generate embeddings from Ollama.")

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON from Ollama: {exc}") from exc

    if "embedding" not in data:
        raise HTTPException(status_code=500, detail="Ollama response missing 'embedding'.")

    return data["embedding"]
