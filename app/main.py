import asyncio
import json
import uuid
from datetime import datetime
from typing import List

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Query,
    Path,
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
    allow_origins=[
        "http://localhost:5173",  # สำหรับพัฒนาในเครื่อง
        "https://arc-pdf.onrender.com",  # Frontend production
    ],
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


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@app.post("/api/upload", response_model=UploadResponse)
async def upload_files(
    chat_id: str = Query(..., description="Target chat_id (session)"),
    files: List[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(400, "No files provided")

    # Create session on-the-fly if not exist
    if chat_id not in memory.chat_history:
        (
            memory.create_chat()
            if chat_id is None
            else memory.chat_history.setdefault(chat_id, [])
        )
        memory.uploaded_files.setdefault(chat_id, [])

    uploaded_infos = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, f"{file.filename} is not a PDF")
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(413, f"{file.filename} exceeds 10 MB")

        info = {
            "filename": file.filename,
            "size": len(content),
            "upload_time": datetime.now().isoformat(),
            "id": str(uuid.uuid4()),
        }
        uploaded_infos.append(info)

    memory.add_files(chat_id, uploaded_infos)

    return UploadResponse(
        message=f"Uploaded {len(uploaded_infos)} file(s)",
        files=uploaded_infos,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    # 1) เตรียม chat_id (สร้างใหม่ถ้าไม่ส่งมา)
    chat_id = request.chat_id or memory.create_chat()

    # 2) ไฟล์เฉพาะ session
    files_in_session = memory.get_files(chat_id)

    # 3) mock QA
    answer, source = mock_pdf_qa(request.question, files_in_session)

    # 4) บันทึก & ตอบกลับ
    chat_entry = memory.add_chat(request.question, answer, source, chat_id)
    return ChatResponse(
        answer=answer,
        source=source,
        id=chat_entry["id"],
        timestamp=chat_entry["timestamp"],
        chat_id=chat_id,
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
    """
    Reset the chat session.
    - ถ้าส่ง chat_id → ลบเฉพาะแชตนั้น
    - ถ้าไม่ส่ง → ลบทุกแชต + ลบไฟล์
    """
    chat_id = request.chat_id if request else None
    clear_files = chat_id is None  # ลบไฟล์เฉพาะกรณี full reset

    memory.reset(chat_id, clear_files=clear_files)  # 🆕 ส่ง flag เข้าไป

    message = (
        f"Chat {chat_id} reset successfully"
        if chat_id
        else "All chats and files reset successfully"
    )

    return ResetResponse(message=message, session_id=memory.session_id, chat_id=chat_id)


@app.get("/api/chat/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_history(chat_id: str):
    """Get chat history for a specific chat ID"""
    memory.touch_chat(chat_id)
    messages = memory.get_chat_history(chat_id)

    if not messages and chat_id not in memory.chat_history:
        raise HTTPException(status_code=404, detail=f"Chat ID {chat_id} not found")

    return ChatHistoryResponse(
        chat_id=chat_id, messages=messages, message_count=len(messages)
    )


@app.get("/api/chat", response_model=AllChatsResponse)
async def get_all_chats():
    all_chats = memory.get_all_chats()
    chat_summaries = []

    for chat_id, messages in all_chats.items():
        first_question = messages[0]["question"] if messages else None
        last_message_time = messages[-1]["timestamp"] if messages else None
        last_active_time = memory.chat_last_active.get(chat_id, last_message_time)

        chat_summaries.append(
            ChatSummary(
                chat_id=chat_id,
                message_count=len(messages),
                first_question=first_question,
                last_message_time=last_message_time,
                last_active_time=last_active_time,  # 🆕
            )
        )

    # ----- เรียงตาม last_active_time DESC -----
    chat_summaries.sort(key=lambda c: c.last_active_time or "", reverse=True)

    return AllChatsResponse(
        chats=chat_summaries,
        total_sessions=memory.get_chat_sessions_count(),
        total_messages=memory.get_total_chat_count(),
    )


@app.get("/api/files", response_model=FilesResponse)
async def get_files(chat_id: str = Query(..., description="chat_id of session")):
    files = memory.get_files(chat_id)
    total = len(files)
    size = sum(f.get("size", 0) for f in files)
    return FilesResponse(files=files, total_files=total, total_size_bytes=size)


@app.websocket("/api/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses (session-aware)"""
    await manager.connect(websocket)

    try:
        while True:
            # ─── 1. รับข้อความจาก client ───
            raw = await websocket.receive_text()

            try:
                payload = json.loads(raw)
                question = payload.get("question", "").strip()

                if not question:
                    await websocket.send_json(
                        {"type": "error", "message": "Question cannot be empty"}
                    )
                    continue

                # ─── 2. ระบุ / สร้าง chat_id ───
                chat_id: str | None = payload.get("chat_id")
                if not chat_id:
                    chat_id = memory.create_chat()  # สร้าง session ใหม่

                # ─── 3. ไฟล์เฉพาะ session ───
                files_in_session = memory.get_files(chat_id)

                # ─── 4. ส่ง typing indicator ───
                await websocket.send_json(
                    {"type": "typing", "message": "Analyzing documents..."}
                )

                # ─── 5. สร้างคำตอบ & ตัดเป็น chunk ───
                answer, source = mock_pdf_qa(question, files_in_session)
                words = answer.split()
                chunk_size = 3
                full_resp = ""

                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i : i + chunk_size]) + " "
                    full_resp += chunk

                    await websocket.send_json(
                        {
                            "type": "chunk",
                            "content": chunk,
                            "is_final": i + chunk_size >= len(words),
                        }
                    )
                    await asyncio.sleep(0.1)  # streaming effect

                # ─── 6. บันทึกประวัติ ───
                chat_entry = memory.add_chat(
                    question, full_resp.strip(), source, chat_id
                )

                # ─── 7. ส่ง complete ───
                await websocket.send_json(
                    {
                        "type": "complete",
                        "id": chat_entry["id"],
                        "question": question,
                        "answer": full_resp.strip(),
                        "source": source,
                        "timestamp": chat_entry["timestamp"],
                        "chat_id": chat_id,
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


@app.delete("/api/files/{file_id}")
async def delete_file(chat_id: str = Query(...), file_id: str = Path(...)):
    if chat_id not in memory.uploaded_files:
        raise HTTPException(404, "chat_id not found")
    memory.delete_file(chat_id, file_id)
    return {"message": "File deleted"}


@app.delete("/api/files")
async def delete_all_files(chat_id: str = Query(...)):
    """
    Delete **all** PDF files in the given chat session
    """
    if chat_id not in memory.uploaded_files:
        raise HTTPException(404, f"chat_id {chat_id} not found")

    memory.clear_files(chat_id)
    return {"message": "All files deleted"}


@app.post("/api/reset", response_model=ResetResponse)
async def reset_session(req: ResetRequest = ResetRequest()):
    memory.reset(req.chat_id, clear_files=True if req.chat_id is None else False)
    msg = f"Chat {req.chat_id} reset" if req.chat_id else "All chats reset"
    return ResetResponse(message=msg, session_id=memory.session_id, chat_id=req.chat_id)
