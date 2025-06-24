import time
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import WebSocket


class MemoryStore:
    """
    Global in-memory storage
    - uploaded_files  -> Dict[chat_id, List[fileMeta]]
    - chat_history    -> Dict[chat_id, List[message]]
    """

    def __init__(self):
        self.uploaded_files: Dict[str, List[Dict[str, Any]]] = {}
        self.chat_history: Dict[str, List[Dict[str, Any]]] = {}
        self.chat_last_active: Dict[str, str] = {}
        self.has_memory = False
        self.session_id = str(uuid.uuid4())

    def reset(self, chat_id: str | None = None, *, clear_files: bool = False):
        """
        Reset chat(s)
        - chat_id=None  -> reset ALL
        - clear_files   -> delete uploaded files, used on full reset
        """
        if chat_id:
            self.chat_history.pop(chat_id, None)
            self.uploaded_files.pop(chat_id, None)
        else:
            self.chat_history = {}
            if clear_files:
                self.uploaded_files = {}
            self.session_id = str(uuid.uuid4())

        self.has_memory = len(self.chat_history) > 0

    def create_chat(self) -> str:
        """Create a new chat session and return the chat_id"""
        chat_id = str(uuid.uuid4())
        self.chat_history[chat_id] = []
        self.uploaded_files[chat_id] = []  # แยกไฟล์ตาม session
        self.chat_last_active[chat_id] = datetime.now().isoformat()  # 🆕
        return chat_id

    # ───────────────────────── Chat / File ops ─────────────────────── #
    def add_chat(
        self,
        question: str,
        answer: str,
        source: str = "",
        chat_id: str | None = None,
    ):
        """บันทึก Q/A เข้า session และอัปเดตเวลาใช้งานล่าสุด"""

        # 1) กำหนด chat_id ถ้าไม่ส่งมา
        if chat_id is None:
            chat_id = self.create_chat()  # สร้าง session ใหม่ (จะตั้ง dict ให้ครบ)

        # 2) ตรวจให้แน่ใจว่ามีโครงสร้าง dict แล้ว
        if chat_id not in self.chat_history:
            self.chat_history[chat_id] = []
        if chat_id not in self.uploaded_files:
            self.uploaded_files[chat_id] = []
        if chat_id not in self.chat_last_active:  # 🆕
            self.chat_last_active[chat_id] = datetime.now().isoformat()

        # 3) สร้าง entry
        entry = {
            "id": str(uuid.uuid4()),
            "question": question,
            "answer": answer,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "chat_id": chat_id,
        }

        # 4) เก็บในประวัติ แล้วอัปเดต last_active
        self.chat_history[chat_id].append(entry)
        self.chat_last_active[chat_id] = entry["timestamp"]  # 🆕

        # 5) ตั้ง flag memory
        self.has_memory = True
        return entry

    def get_chat_history(self, chat_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a specific chat_id"""
        return self.chat_history.get(chat_id, [])

    def get_all_chats(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all chat histories"""
        return self.chat_history

    def get_total_chat_count(self) -> int:
        """Get total number of chat messages across all chats"""
        return sum(len(messages) for messages in self.chat_history.values())

    def get_chat_sessions_count(self) -> int:
        """Get number of chat sessions"""
        return len(self.chat_history)

        # -------------------------- file ops ---------------------------- #

    def add_files(self, chat_id: str, files: List[Dict[str, Any]]):
        if chat_id not in self.uploaded_files:
            self.uploaded_files[chat_id] = []
        self.uploaded_files[chat_id].extend(files)

    def get_files(self, chat_id: str):
        return self.uploaded_files.get(chat_id, [])

    def delete_file(self, chat_id: str, file_id: str):
        self.uploaded_files[chat_id] = [
            f for f in self.uploaded_files.get(chat_id, []) if f["id"] != file_id
        ]

    def clear_files(self, chat_id: str):
        self.uploaded_files[chat_id] = []

        # 🆕 utility

    def touch_chat(self, chat_id: str):
        """Update last_active_time when user opens the chat (even without new message)"""
        self.chat_last_active[chat_id] = datetime.now().isoformat()


class ConnectionManager:
    """WebSocket connection manager for streaming chat"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)


def mock_pdf_qa(question: str, uploaded_files: List[Dict]) -> tuple[str, str]:
    """
    Mock function to simulate PDF content analysis and question answering.
    In a real implementation, this would use LLM/AI to process PDFs and answer questions.
    """
    if not uploaded_files:
        return (
            "I don't have any documents to reference. Please upload some PDFs first.",
            "",
        )

    time.sleep(0.5)

    question_lower = question.lower()

    # ------ 1) summary / summarize ------
    if "summary" in question_lower or "summarize" in question_lower:
        answer = (
            f"Based on the uploaded document(s), here's a summary: "
            "The documents contain information relevant to your query. "
            "This is a mock response simulating content analysis from "
            f"{len(uploaded_files)} uploaded file(s)."
        )
        source = (
            f"Multiple sources ({len(uploaded_files)} files)"
            if len(uploaded_files) > 1
            else uploaded_files[0]["filename"]
        )

    # ------ 2) what / how / why ---------
    elif any(k in question_lower for k in ("what", "how", "why")):
        answer = (
            f"According to the uploaded documents, here's what I found: {question} - "
            "This is a simulated response that would typically be generated by analyzing "
            "the PDF content using AI/LLM."
        )
        source = (
            f"Multiple sources ({len(uploaded_files)} files)"
            if len(uploaded_files) > 1
            else uploaded_files[-1]["filename"]
        )

    # ------ 3) อื่น ๆ  -------------------
    else:
        answer = (
            f"I found relevant information in your documents regarding: '{question}'. "
            "This response is generated from the uploaded PDF content analysis simulation."
        )
        source = (
            f"Multiple sources ({len(uploaded_files)} files)"
            if len(uploaded_files) > 1
            else uploaded_files[0]["filename"]
        )

    return answer, source
