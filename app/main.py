import asyncio
import json
import uuid
from datetime import datetime
from typing import List

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    AllChatsResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ChatSummary,
    CreateChatResponse,
    FilesResponse,
    ResetRequest,
    ResetResponse,
    StatusResponse,
    UploadResponse,
)
from app.utils import ConnectionManager, MemoryStore, mock_pdf_qa

memory = MemoryStore()
manager = ConnectionManager()

app = FastAPI(title="Backend API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Backend API", "version": "1.0.0"}


@app.get("/api/status")
async def get_status():
    """Get current session status"""
    return StatusResponse(
        has_memory=memory.has_memory,
        session_id=memory.session_id,
        uploaded_files_count=len(memory.uploaded_files),
        chat_history_count=memory.get_total_chat_count(),
        chat_sessions_count=memory.get_chat_sessions_count(),
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload PDF files"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    uploaded_files_info = []

    for file in files:
        # Validate file type (basic check)
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail=f"File {file.filename} is not a PDF"
            )

        # Read file content (in real implementation, you'd process/store this)
        content = await file.read()

        file_info = {
            "filename": file.filename,
            "size": len(content),
            "upload_time": datetime.now().isoformat(),
            "id": str(uuid.uuid4()),
        }

        uploaded_files_info.append(file_info)
        memory.uploaded_files.append(file_info)

    return UploadResponse(
        message=f"Successfully uploaded {len(files)} file(s)", files=uploaded_files_info
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Ask a question about uploaded documents"""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Generate mock answer
    answer, source = mock_pdf_qa(request.question, memory.uploaded_files)

    # Store in memory
    chat_entry = memory.add_chat(request.question, answer, source, request.chat_id)

    return ChatResponse(
        answer=answer,
        source=source,
        id=chat_entry["id"],
        timestamp=chat_entry["timestamp"],
        chat_id=chat_entry["chat_id"],
    )


@app.post("/api/chat/create", response_model=CreateChatResponse)
async def create_chat():
    """Create a new chat session"""
    chat_id = memory.create_chat()
    return CreateChatResponse(
        chat_id=chat_id, message="New chat session created successfully"
    )


@app.post("/api/reset", response_model=ResetResponse)
async def reset_session(request: ResetRequest = ResetRequest()):
    """Reset the chat session and clear memory"""
    chat_id = request.chat_id if request else None
    memory.reset(chat_id)

    if chat_id:
        message = f"Chat {chat_id} reset successfully"
    else:
        message = "All chats reset successfully"

    return ResetResponse(message=message, session_id=memory.session_id, chat_id=chat_id)


@app.get("/api/chat/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_history(chat_id: str):
    """Get chat history for a specific chat ID"""
    messages = memory.get_chat_history(chat_id)

    if not messages and chat_id not in memory.chat_history:
        raise HTTPException(status_code=404, detail=f"Chat ID {chat_id} not found")

    return ChatHistoryResponse(
        chat_id=chat_id, messages=messages, message_count=len(messages)
    )


@app.get("/api/chat", response_model=AllChatsResponse)
async def get_all_chats():
    """Get summary of all chat sessions"""
    all_chats = memory.get_all_chats()
    chat_summaries = []

    for chat_id, messages in all_chats.items():
        first_question = messages[0]["question"] if messages else None
        last_message_time = messages[-1]["timestamp"] if messages else None

        chat_summaries.append(
            ChatSummary(
                chat_id=chat_id,
                message_count=len(messages),
                first_question=first_question,
                last_message_time=last_message_time,
            )
        )

    return AllChatsResponse(
        chats=chat_summaries,
        total_sessions=memory.get_chat_sessions_count(),
        total_messages=memory.get_total_chat_count(),
    )


@app.get("/api/files", response_model=FilesResponse)
async def get_files():
    """Get all uploaded files information"""
    total_size = sum(file_info.get("size", 0) for file_info in memory.uploaded_files)

    return FilesResponse(
        files=memory.uploaded_files,
        total_files=len(memory.uploaded_files),
        total_size_bytes=total_size,
    )


@app.websocket("/api/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses"""
    await manager.connect(websocket)

    try:
        while True:
            # Receive question from client
            data = await websocket.receive_text()

            try:
                request_data = json.loads(data)
                question = request_data.get("question", "").strip()

                if not question:
                    await websocket.send_json(
                        {"type": "error", "message": "Question cannot be empty"}
                    )
                    continue

                # Send typing indicator
                await websocket.send_json(
                    {"type": "typing", "message": "Analyzing documents..."}
                )

                # Simulate streaming response by sending chunks
                answer, source = mock_pdf_qa(question, memory.uploaded_files)

                # Split answer into chunks for streaming effect
                words = answer.split()
                chunks = []
                chunk_size = 3  # Words per chunk

                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i : i + chunk_size])
                    chunks.append(chunk)

                # Send each chunk with a small delay
                full_response = ""
                for i, chunk in enumerate(chunks):
                    full_response += chunk + " "

                    await websocket.send_json(
                        {
                            "type": "chunk",
                            "content": chunk + " ",
                            "is_final": i == len(chunks) - 1,
                        }
                    )

                    # Small delay for streaming effect
                    await asyncio.sleep(0.1)

                # Get chat_id from request or create new one
                chat_id = request_data.get("chat_id")

                # Store in memory and send final response
                chat_entry = memory.add_chat(
                    question, full_response.strip(), source, chat_id
                )

                await websocket.send_json(
                    {
                        "type": "complete",
                        "id": chat_entry["id"],
                        "question": question,
                        "answer": full_response.strip(),
                        "source": source,
                        "timestamp": chat_entry["timestamp"],
                        "chat_id": chat_entry["chat_id"],
                    }
                )

            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON format"}
                )
            except Exception as e:
                await websocket.send_json(
                    {"type": "error", "message": f"An error occurred: {str(e)}"}
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "session_id": memory.session_id,
        "has_memory": memory.has_memory,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
