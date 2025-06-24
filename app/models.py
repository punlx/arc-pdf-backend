from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""

    question: str
    chat_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""

    answer: str
    source: str
    id: str
    timestamp: str
    chat_id: str


class ResetResponse(BaseModel):
    """Response model for reset endpoint"""

    message: str
    session_id: str
    chat_id: Optional[str] = None


class UploadResponse(BaseModel):
    """Response model for upload endpoint"""

    message: str
    files: List[Dict[str, Any]]


class StatusResponse(BaseModel):
    """Response model for status endpoint"""

    has_memory: bool
    session_id: str
    uploaded_files_count: int
    chat_history_count: int
    chat_sessions_count: int


class CreateChatResponse(BaseModel):
    """Response model for create chat endpoint"""

    chat_id: str
    message: str


class ResetRequest(BaseModel):
    """Request model for reset endpoint"""

    chat_id: str = None  # Optional chat_id to reset specific chat


class ChatHistoryResponse(BaseModel):
    """Response model for chat history endpoint"""

    chat_id: str
    messages: List[Dict[str, Any]]
    message_count: int


class ChatSummary(BaseModel):
    """Summary model for a single chat session"""

    chat_id: str
    message_count: int
    first_question: str = None
    last_message_time: str = None
    last_active_time: str | None = None


class AllChatsResponse(BaseModel):
    """Response model for all chats endpoint"""

    chats: List[ChatSummary]
    total_sessions: int
    total_messages: int


class FilesResponse(BaseModel):
    """Response model for files endpoint"""

    files: List[Dict[str, Any]]
    total_files: int
    total_size_bytes: int
