from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from contextlib import asynccontextmanager
import os
import dotenv

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, Document, StorageContext, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding

from utils.pandoc_supported import pandoc_supported
from utils.extractors.pandoc import pandoc_extractor
from utils.extractors.pdf import pdf_extractor
from utils.prompts import get_system_prompt, list_available_prompts, get_prompts_info

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

# Pydantic models for request/response
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    chat_history: Optional[List[ChatMessage]] = None
    system_prompt: Optional[str] = "default"  # Can be a prompt type or custom text

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
    if file_extension in pandoc_supported():
        content = pandoc_extractor(destination)
    elif file_extension == "pdf":
        content = pdf_extractor(destination)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type for extraction.")
    # Extract content with page breaks preserved

    # Truncate very large documents to avoid Ollama crashes
    max_content_length = 50000  # ~50KB of text
    if len(content) > max_content_length:
        content = content[:max_content_length]
        print(f"Warning: Content truncated to {max_content_length} characters")

    # Split by form feeds if present, otherwise split by estimated page size
    if '\f' in content:
        pages = content.split('\f')
    else:
        # Split content into chunks and estimate page numbers
        # Average page is ~3000 characters (roughly 500 words)
        chars_per_page = 3000

        pages = [
            content[i : i + chars_per_page]
            for i in range(0, len(content), chars_per_page)
        ]
    documents = []
    for page_num, page_content in enumerate(pages, start=1):
        if page_content.strip():  # Skip empty pages
            doc = Document(
                text=page_content.strip(),
                metadata={
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "file_size": destination.stat().st_size,
                    "file_path": str(destination),
                    "page_number": page_num,
                    "total_pages": len(pages),
                }
            )
            documents.append(doc)

    # Insert into vector store (LlamaIndex handles chunking and embedding)
    try:
        for doc in documents:
            index.insert(doc)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to embed document. Ollama embedding service may have crashed: {str(e)}",
        ) from e

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
    # Extract source nodes for detailed results with page numbers
    results = []
    for node in response.source_nodes:
        result = {
            "text": node.node.text,
            "score": node.score,
            "filename": node.node.metadata.get("filename", "unknown"),
            "page_number": node.node.metadata.get("page_number"),
            "content_type": node.node.metadata.get("content_type"),
            "metadata": node.node.metadata,
        }
        results.append(result)
    
    return JSONResponse(
        content={
            "query": query,
            "response": str(response),
            "sources": results,
        }
    )

@app.post("/chat")
async def chat_with_documents(request: ChatRequest):
    """
    Chat with documents using LlamaIndex chat engine with streaming.
    Maintains conversation context and provides conversational responses.
    
    Args:
        request: ChatRequest containing message, optional chat_history, and system_prompt
        
    System Prompt Options:
        - Use a predefined prompt type (e.g., "default", "technical", "summarizer")
        - Provide custom system prompt text
        - Leave as "default" for general assistance
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    # Get system prompt (either predefined type or custom text)
    if request.system_prompt in list_available_prompts():
        system_prompt = get_system_prompt(request.system_prompt)
    else:
        # Use custom system prompt if provided
        system_prompt = request.system_prompt or get_system_prompt("default")
    
    # Create chat engine from index with streaming enabled and system prompt
    chat_engine = index.as_chat_engine(
        chat_mode="context",  # Uses retrieval context for each message
        similarity_top_k=5,
        streaming=True,  # Enable streaming
        system_prompt=system_prompt,
    )
    
    # If chat history is provided, restore context
    if request.chat_history:
        # LlamaIndex chat engine can handle chat history
        # Build up the conversation context
        for msg in request.chat_history:
            if msg.role == "user":
                # Send previous user messages to build context
                chat_engine.chat(msg.content)
    
    # Stream response for current message
    streaming_response = chat_engine.stream_chat(request.message)
    
    async def generate():
        # Stream the response tokens as plain text
        for token in streaming_response.response_gen:
            yield token
        
        # After streaming is complete, add source references
        if hasattr(streaming_response, 'source_nodes') and streaming_response.source_nodes:
            yield "\n\n---\n**References:**\n"
            
            # Group sources by filename
            sources_by_file = {}
            for node in streaming_response.source_nodes:
                filename = node.node.metadata.get("filename", "unknown")
                page_num = node.node.metadata.get("page_number")
                
                if filename not in sources_by_file:
                    sources_by_file[filename] = set()
                if page_num:
                    sources_by_file[filename].add(page_num)
            
            # Output references
            for filename, pages in sources_by_file.items():
                if pages:
                    page_list = sorted(list(pages))
                    pages_str = ", ".join([f"Page[{p}]" for p in page_list])
                    yield f"- {filename} ({pages_str})\n"
                else:
                    yield f"- {filename}\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/prompts")
async def get_prompts():
    """
    Get information about all available system prompts.
    Returns prompt types with descriptions.
    """
    return JSONResponse(
        content={
            "available_prompts": list_available_prompts(),
            "prompts_info": get_prompts_info(),
            "note": "Use these prompt types in the 'system_prompt' field of /chat requests, or provide your own custom prompt text"
        }
    )

@app.get("/prompts/{prompt_type}")
async def get_specific_prompt(prompt_type: str):
    """
    Get the full text of a specific system prompt.
    
    Args:
        prompt_type: The type of prompt to retrieve
    """
    if prompt_type not in list_available_prompts():
        raise HTTPException(
            status_code=404, 
            detail=f"Prompt type '{prompt_type}' not found. Available types: {', '.join(list_available_prompts())}"
        )
    
    return JSONResponse(
        content={
            "prompt_type": prompt_type,
            "prompt_text": get_system_prompt(prompt_type)
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
