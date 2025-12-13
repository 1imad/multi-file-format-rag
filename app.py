from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from contextlib import asynccontextmanager
import os
import dotenv
from datetime import timedelta

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, Document, StorageContext, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding  # Correct class name is OllamaEmbedding (singular)

from utils.pandoc_supported import pandoc_supported
from utils.extractors.pandoc import pandoc_extractor
from utils.extractors.pdf import pdf_extractor
from utils.prompts import get_system_prompt, list_available_prompts, get_prompts_info
from utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user,
    UserCreate,
    UserLogin,
    Token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

dotenv.load_dotenv()

# Database configuration
DB_HOST = os.getenv("PGHOST")
DB_PORT = os.getenv("PGPORT")
DB_NAME = os.getenv("PGDATABASE")
DB_USER = os.getenv("PGUSER")
DB_PASSWORD = os.getenv("PGPASSWORD")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
LLM_URL = os.getenv("LLM_URL")
CHAT_MODEL= os.getenv("CHAT_MODEL")

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
        base_url=LLM_URL,
        embed_batch_size=1,  # Process one at a time to avoid Ollama crashes
    )
    
    # Configure Ollama LLM for query engine
    llm = Ollama(
        model=CHAT_MODEL,  # Use a small fast model for queries
        base_url=LLM_URL,
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],  # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    chat_history: Optional[List[ChatMessage]] = None
    system_prompt: Optional[str] = "default"  # Can be a prompt type or custom text

@app.post("/register", response_model=Token)
async def register(user: UserCreate):
    """
    Register a new user.
    Creates a user account and returns a JWT access token.
    """
    import asyncpg
    
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    try:
        # Check if user already exists
        existing_user = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            user.email
        )
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        # Hash password and create user
        hashed_password = get_password_hash(user.password)
        await conn.execute(
            """INSERT INTO users (email, hashed_password, full_name) 
               VALUES ($1, $2, $3)""",
            user.email,
            hashed_password,
            user.full_name
        )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    finally:
        await conn.close()

@app.post("/login", response_model=Token)
async def login(user: UserLogin):
    """
    Login with email and password.
    Returns a JWT access token on successful authentication.
    """
    import asyncpg
    
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    try:
        # Get user from database
        db_user = await conn.fetchrow(
            "SELECT email, hashed_password, is_active FROM users WHERE email = $1",
            user.email
        )
        
        if not db_user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(user.password, db_user['hashed_password']):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        # Check if user is active
        if not db_user['is_active']:
            raise HTTPException(
                status_code=400,
                detail="Inactive user account"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    finally:
        await conn.close()

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_active_user)
):
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

    # Insert into vector store and update user_id column
    try:
        import asyncpg
        
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        for doc in documents:
            # Insert document into index
            index.insert(doc)
            
        # Update user_id for all documents with this filename
        # (LlamaIndex inserts happen synchronously, so we can update after)
        await conn.execute(
            """
            UPDATE data_llamaindex_embeddings 
            SET user_id = $1 
            WHERE metadata_->>'filename' = $2 
            AND user_id IS NULL
            """,
            current_user,
            file.filename
        )
        
        await conn.close()
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
async def query_documents(
    query: str,
    top_k: int = 5,
    current_user: str = Depends(get_current_active_user)
):
    """
    Query the vector store using LlamaIndex for the current user's documents.
    Returns the most relevant chunks with their metadata.
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Query using direct database filter on user_id column
    import asyncpg
    
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    # Get node IDs for user's documents
    node_ids_query = """
        SELECT node_id 
        FROM data_llamaindex_embeddings 
        WHERE user_id = $1
    """
    node_rows = await conn.fetch(node_ids_query, current_user)
    await conn.close()
    
    if not node_rows:
        return JSONResponse(
            content={
                "query": query,
                "response": "No documents found for your account.",
                "sources": [],
            }
        )
    
    # Get all nodes and filter by user's node IDs
    query_engine = index.as_query_engine(similarity_top_k=top_k * 10)  # Get more to filter
    response = query_engine.query(query)
    
    # Filter results by user's node IDs
    user_node_ids = {row['node_id'] for row in node_rows}
    results = []
    for node in response.source_nodes:
        if node.node.node_id in user_node_ids:
            result = {
                "text": node.node.text,
                "score": node.score,
                "filename": node.node.metadata.get("filename", "unknown"),
                "page_number": node.node.metadata.get("page_number"),
                "content_type": node.node.metadata.get("content_type"),
                "metadata": node.node.metadata,
            }
            results.append(result)
            if len(results) >= top_k:
                break
    
    return JSONResponse(
        content={
            "query": query,
            "response": str(response),
            "sources": results,
        }
    )

@app.post("/chat")
async def chat_with_documents(
    request: ChatRequest,
    current_user: str = Depends(get_current_active_user)
):
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
    
    # Get user's document node IDs from database
    import asyncpg
    
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    node_ids_query = """
        SELECT node_id 
        FROM data_llamaindex_embeddings 
        WHERE user_id = $1
    """
    node_rows = await conn.fetch(node_ids_query, current_user)
    await conn.close()
    
    if not node_rows:
        # Return empty response if user has no documents
        async def empty_response():
            yield "You don't have any documents uploaded yet. Please upload documents first."
        
        return StreamingResponse(
            empty_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    # Store user's node IDs for filtering
    user_node_ids = {row['node_id'] for row in node_rows}
    
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
        
        # After streaming is complete, add source references (filtered by user)
        if hasattr(streaming_response, 'source_nodes') and streaming_response.source_nodes:
            yield "\n\n---\n**References:**\n"
            
            # Group sources by filename (only user's documents)
            sources_by_file = {}
            for node in streaming_response.source_nodes:
                # Only include nodes that belong to the user
                if node.node.node_id in user_node_ids:
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

@app.get("/files")
async def list_files(current_user: str = Depends(get_current_active_user)):
    """
    List all unique files that have embeddings stored in the vector store for the current user.
    Returns a list of filenames with their metadata.
    """
    try:
        # Query the database directly to get unique files for this user
        import asyncpg
        
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        # Get unique filenames with their metadata filtered by user_id column
        query = """
            SELECT 
                metadata_->>'filename' as filename,
                metadata_->>'content_type' as content_type,
                metadata_->>'file_size' as file_size,
                metadata_->>'file_path' as file_path,
                COUNT(*) as chunk_count
            FROM data_llamaindex_embeddings
            WHERE user_id = $1
              AND metadata_->>'filename' IS NOT NULL
            GROUP BY 
                metadata_->>'filename',
                metadata_->>'content_type',
                metadata_->>'file_size',
                metadata_->>'file_path'
            ORDER BY metadata_->>'filename'
        """
        
        rows = await conn.fetch(query, current_user)
        await conn.close()
        
        files = []
        for row in rows:
            files.append({
                "filename": row['filename'],
                "content_type": row['content_type'],
                "file_size": int(row['file_size']) if row['file_size'] else None,
                "file_path": row['file_path'],
                "chunk_count": row['chunk_count']
            })
        
        return JSONResponse(
            content={
                "files": files,
                "total_files": len(files)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )

@app.delete("/files/{filename}")
async def delete_file(
    filename: str,
    current_user: str = Depends(get_current_active_user)
):
    """
    Delete all embeddings associated with a specific file for the current user.
    
    Args:
        filename: The name of the file to delete
    """
    try:
        # Query the database directly to delete embeddings for this file and user
        import asyncpg
        
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        # Check if file exists for this user using user_id column
        check_query = """
            SELECT COUNT(*) as count
            FROM data_llamaindex_embeddings
            WHERE user_id = $1
              AND metadata_->>'filename' = $2
        """
        result = await conn.fetchrow(check_query, current_user, filename)
        
        if result['count'] == 0:
            await conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"File '{filename}' not found in your embeddings"
            )
        
        # Delete all embeddings for this file and user using user_id column
        delete_query = """
            DELETE FROM data_llamaindex_embeddings
            WHERE user_id = $1
              AND metadata_->>'filename' = $2
        """
        deleted = await conn.execute(delete_query, current_user, filename)
        await conn.close()
        
        # Also try to delete the physical file if it exists
        file_path = UPLOAD_DIR / filename
        if file_path.exists():
            file_path.unlink()
            physical_deleted = True
        else:
            physical_deleted = False
        
        return JSONResponse(
            content={
                "message": f"Successfully deleted embeddings for '{filename}'",
                "filename": filename,
                "embeddings_deleted": result['count'],
                "physical_file_deleted": physical_deleted
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
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
