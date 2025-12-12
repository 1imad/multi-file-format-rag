from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager
import os
import dotenv

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, Document, StorageContext, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding

from utils.pandoc_supported import pandoc_supported
from utils.extractors.doc_extractor import doc_extractor

dotenv.load_dotenv()

# Database configuration
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = os.getenv("PGPORT", "5432")
DB_NAME = os.getenv("PGDATABASE", "embeddings")
DB_USER = os.getenv("PGUSER", "imad")
DB_PASSWORD = os.getenv("PGPASSWORD", "123456789")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Global vector store and index
vector_store = None
index = None

async def initialize_llamaindex():
    """Initialize LlamaIndex with PGVectorStore and Ollama embeddings"""
    global vector_store, index
    
    # Import Ollama LLM
    from llama_index.llms.ollama import Ollama
    
    # Configure Ollama embeddings with smaller batch size for stability
    embed_model = OllamaEmbedding(
        model_name=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
        embed_batch_size=1,  # Process one at a time to avoid Ollama crashes
    )
    
    # Configure Ollama LLM for query engine
    llm = Ollama(
        model="gemma3:1b",  # Use a small fast model for queries
        base_url=OLLAMA_BASE_URL,
        request_timeout=30.0,
    )
    
    # Set global settings
    Settings.embed_model = embed_model
    Settings.llm = llm
    Settings.chunk_size = 128  # Very small chunks to avoid Ollama crashes
    Settings.chunk_overlap = 10
    
    # Create PGVectorStore
    vector_store = PGVectorStore.from_params(
        database=DB_NAME,
        host=DB_HOST,
        password=DB_PASSWORD,
        port=int(DB_PORT),
        user=DB_USER,
        table_name="llamaindex_embeddings",
        embed_dim=768,  # nomic-embed-text dimension
    )
    
    # Create storage context
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Create or load index
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
    )
    
    print("LlamaIndex initialized with PGVectorStore and Ollama embeddings")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    await initialize_llamaindex()
    yield
    print("Application shutdown")

# Directory to store uploaded files
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(title="LlamaIndex Upload & Embeddings API", lifespan=lifespan)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file, extract content, and store in LlamaIndex vector store.
    LlamaIndex handles chunking, embedding, and storage automatically.
    """
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

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in pandoc_supported():
        raise HTTPException(status_code=400, detail="Unsupported file type for extraction.")
    
    # Extract content
    content = doc_extractor(destination)
    
    # Truncate very large documents to avoid Ollama crashes
    max_content_length = 50000  # ~50KB of text
    if len(content) > max_content_length:
        content = content[:max_content_length]
        print(f"Warning: Content truncated to {max_content_length} characters")
    
    # Create LlamaIndex Document with metadata
    document = Document(
        text=content,
        metadata={
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size": destination.stat().st_size,
            "file_path": str(destination),
        }
    )
    
    # Insert into vector store (LlamaIndex handles chunking and embedding)
    try:
        index.insert(document)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to embed document. Ollama embedding service may have crashed: {str(e)}"
        )
    
    return JSONResponse(
        status_code=201,
        content={
            "message": "Document embedded successfully",
            "filename": file.filename,
            "content_length": len(content),
            "embedding_model": EMBEDDING_MODEL,
            "note": "LlamaIndex automatically chunked and embedded the document"
        }
    )

@app.get("/query")
async def query_documents(query: str, top_k: int = 5):
    """
    Query the vector store using LlamaIndex.
    Returns the most relevant chunks with their metadata.
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Query the index
    query_engine = index.as_query_engine(similarity_top_k=top_k)
    response = query_engine.query(query)

    # Extract source nodes for detailed results
    results = []
    results.extend(
        {
            "text": node.node.text,
            "score": node.score,
            "metadata": node.node.metadata,
        }
        for node in response.source_nodes
    )
    return JSONResponse(
        content={
            "query": query,
            "response": str(response),
            "sources": results,
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "vector_store": "PGVectorStore" if vector_store else "Not initialized",
        "embedding_model": EMBEDDING_MODEL,
    }

if __name__ == "__main__":
    uvicorn.run("app_llamaindex:app", host="0.0.0.0", port=8000, reload=True)
