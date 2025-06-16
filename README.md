# ArcFusion Take-Home Assignment: Frontend/Fullstack

## Objective

Build a production-ready frontend application that enables users to upload PDFs and ask questions about their content via an API. The focus is on component architecture, state management, styling, and frontend code quality — not on the LLM or AI logic itself.

## Requirements

Frontend Stack

- React (with TypeScript)
- Tailwind CSS (Shadcn, Radix UI, or custom components)
- State Management: Your choice (Zustand, Redux, React Context)
- Component Design: Reusable, documented, scalable

## Core Features

- PDF Upload UI
- Allow users to upload one or more PDF files
- Display uploaded filenames in a list
- Chat-like Q&A Interface
- Input field for user to ask questions
- Display of question/answer pairs
- Simulate real-time feedback (loading indicators)
- Session Management
- "Reset" button to clear current chat session
- Memory Indicator
- Show whether the current session has memory (e.g., simple badge or toggle)

## API Integration

- Assume the following API structure:
  - POST /api/upload // Uploads PDFs
  - POST /api/chat // { question: string } => { answer: string, source: string }
  - POST /api/reset // Clears chat memory

## Bonus Points

- Component-driven development (with Storybook)
- Theme toggle (dark/light mode)
- Responsive design across mobile/tablet/desktop
- Accessibility (WAI-ARIA)
- Visual regression testing setup (Chromatic or similar)
- Docker + docker-compose setup for easy run
- Websocket integration for chat api

## Deliverables

Git Repository

- Source code
- Component folder structure clearly organized

README.md containing:

- How to run it locally
- Project structure and component breakdown
- Any tradeoffs or assumptions made
- What you would do to improve in a real-world scenario
  Optional: Short Loom/video walkthrough explaining the project

# What We're Evaluating

Category What We Look For

- Architecture Well-structured, maintainable codebase
- Component Design Reusability, isolation, and clarity
- State Management Clean, scalable handling of UI and app state
- API Integration Clean, decoupled service layer or hooks
- Styling & Theming Tailwind conventions, consistent visual system
- Code Quality TypeScript use, folder structure, code readability
- UX Attention Thoughtful interactions, loading/error handling
- Ownership Mindset README clarity, polish, and

## Backend Setup (For Candidates)

A FastAPI backend has been provided for this take-home test. Follow these steps to set it up:

### Option 1: Using Docker (Recommended)

```bash
# Start the backend service
docker-compose up backend

# The API will be available at http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Make the run script executable (first time only)
chmod +x run_backend.sh

# Run the backend
./run_backend.sh

# Or manually:
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Available Endpoints

#### Core Functionality

- **POST** `/api/upload` - Upload PDF files
- **POST** `/api/chat` - Ask questions about uploaded documents
- **POST** `/api/reset` - Reset chat session and clear memory
- **WebSocket** `/api/ws/chat` - Streaming chat interface

#### Chat Management

- **POST** `/api/chat/create` - Create new chat session
- **GET** `/api/chat/{chat_id}` - Get chat history for specific chat ID
- **GET** `/api/chat` - Get summary of all chat sessions

#### Dashboard & Info

- **GET** `/api/files` - Get all uploaded files information
- **GET** `/api/status` - Get session status
- **GET** `/health` - Health check

### API Documentation

Once the backend is running, visit:

- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

### Frontend Integration

The backend supports CORS and is configured to work with frontend applications running on ports 3000-3001. Example API calls:

```javascript
// Upload files
const formData = new FormData();
formData.append("files", pdfFile);
const response = await fetch("http://localhost:8000/api/upload", {
  method: "POST",
  body: formData,
});

// Chat
const response = await fetch("http://localhost:8000/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question: "What is this document about?" }),
});

// WebSocket streaming
const ws = new WebSocket("ws://localhost:8000/api/ws/chat");
ws.send(
  JSON.stringify({
    question: "Your question here",
    chat_id: "optional-chat-id",
  })
);

// Create new chat session
const newChat = await fetch("http://localhost:8000/api/chat/create", {
  method: "POST",
});
const { chat_id } = await newChat.json();

// Get chat history
const chatHistory = await fetch(`http://localhost:8000/chat/${chat_id}`);
const history = await chatHistory.json();

// Get all chats summary
const allChats = await fetch("http://localhost:8000/api/chat");
const chatsData = await allChats.json();

// Get uploaded files info
const files = await fetch("http://localhost:8000/api/files");
const filesData = await files.json();
```

## Questions?

Please feel free to reach out any time if you need clarification or run into blockers.
