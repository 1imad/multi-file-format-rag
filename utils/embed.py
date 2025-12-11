from typing import List
from fastapi import HTTPException
import os
import dotenv
import requests

dotenv.load_dotenv()
EMBEDDING_URL = os.getenv("EMBEDDING_URL")
EMBEDDING_MODEL = os.getenv("EMBEDDINFG_MODEL")

def generate_embedding(text: str) -> List[float]:
    """
    Generate embeddings for the given text using Ollama.
    """
    response = requests.post(
        EMBEDDING_URL,
        json={"model": EMBEDDING_MODEL, "prompt": text}
    )
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to generate embeddings from Ollama.")
    
    data = response.json()
    if "embedding" not in data:
        raise HTTPException(status_code=500, detail="Ollama response missing 'embedding'.")
    
    return data["embedding"]
