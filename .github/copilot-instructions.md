# EchoMind Voice Discussion System - AI Agent Instructions

## 🎯 Architecture Overview

This is a **dual-stack real-time discussion facilitation system** inspired by EchoMind (CSCW 2025):
- **Backend**: FastAPI + python-socketio for REST APIs and WebSocket communication
- **Frontend**: React 18 + TypeScript + Vite with Zustand state management
- **Communication**: REST for session management, WebSocket (Socket.IO) for real-time events, LLM integration via OpenAI

### Critical Pattern: ASGI Wrapping for Socket.IO
The backend combines FastAPI and Socket.IO by wrapping FastAPI with `ASGIApp`:
```python
# app/main.py
app = ASGIApp(socketio_server=sio, other_asgi_app=fastapi_app)
```
This single `app` instance serves both REST (`/api/*`) and WebSocket (`/socket.io/*`) traffic.

## 🏗️ Service Layer Architecture

### Three-Layer Backend Design
1. **Routers** ([routers/](backend/app/routers/)) - FastAPI endpoints, thin HTTP handlers
2. **Services** ([services/](backend/app/services/)) - Business logic, session/analysis orchestration
3. **Sockets** ([sockets/handlers.py](backend/app/sockets/handlers.py)) - WebSocket event handlers

**Key Pattern**: Services are shared between REST and WebSocket layers:
```python
# In both routers/analysis.py and sockets/handlers.py
from app.services.analysis import AnalysisService
analysis_service = AnalysisService()
```

### Session Management Pattern
- `SessionManager` (singleton via `session_manager` instance) tracks in-memory sessions
- Socket IDs (`sid`) are mapped to `participant_id` and `session_id` for tracking participants
- Sessions auto-expire after `settings.session.timeout_minutes` (default: 60min)

## 🔧 Development Workflow

### Starting Services (Critical Order)
1. **Backend first**: `cd backend && python run.py` (or `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`)
2. **Frontend second**: `cd frontend && npm run dev` (port 5173)
3. **Vite proxy** forwards `/api` and `/socket.io` to backend (see [vite.config.ts](frontend/vite.config.ts))

### Configuration Management
- Backend uses `config.yaml` (copy from [config.template.yaml](backend/config.template.yaml))
- Settings loaded via Pydantic `BaseSettings` in [app/config.py](backend/app/config.py)
- **Must set**: `llm.api_key` (OpenAI API key) for analysis features
- Frontend env: `VITE_API_BASE_URL` for API base (default: `http://localhost:8000`)

### Python Environment
- Uses `pyproject.toml` with setuptools: `pip install -e .[dev]` for editable install
- Dev dependencies include: `pytest`, `ruff`, `black`, `mypy`
- Code style: **100 char line length** (both ruff and black)

## 📝 Code Conventions

### Backend Patterns

#### HandyLLM Prompt Management
Prompts are stored as `.hprompt` files in [backend/app/core/prompts/](backend/app/core/prompts/):
- Format: Markdown-like with `---` YAML frontmatter and `{{variable}}` placeholders
- Loaded by `PromptManager` ([prompts.py](backend/app/core/prompts.py))
- Rendered with Jinja2-like variable substitution

Example usage:
```python
from app.core.prompts import get_prompt_manager
pm = get_prompt_manager()
prompt = pm.render_prompt("issue_classification", {"transcript": text, "segment_duration": 20})
```

#### Pydantic Models
All data models use Pydantic v2 ([models/schemas.py](backend/app/models/schemas.py)):
- `BaseModel` for request/response schemas
- `Enum` classes for status types (`SegmentStatus`, `ParticipantRole`, `MessageType`)
- Models shared between REST and WebSocket handlers

#### WebSocket Message Protocol
Messages use typed structure:
```python
class SocketMessage(BaseModel):
    type: MessageType  # Enum: join, send_text, analyze_segment, etc.
    session_id: str
    data: Dict[str, Any]
```

### Frontend Patterns

#### State Management with Zustand
Single store in [lib/store.ts](frontend/src/lib/store.ts):
- Session state (ID, participants, segments)
- No complex middleware - direct state updates
- Pattern: `useSessionStore.getState().addSegment(data)`

#### API Client Pattern
- REST client: [lib/api.ts](frontend/src/lib/api.ts) exports `sessionAPI` and `analysisAPI`
- Query params via `params` option (not URL strings): `apiClient.post('/sessions/', null, { params: data })`
- Socket.IO client: [lib/speech.ts](frontend/src/lib/speech.ts) (also handles Web Speech API)

#### Path Alias
Vite configured with `@/` alias for `src/`:
```typescript
import { sessionAPI } from '@/lib/api'
```

## 🚨 Common Pitfalls

### Backend
1. **Multiple Python processes**: Run `Get-Process python | Stop-Process -Force` if stuck
2. **Socket.IO 404**: Ensure `ASGIApp` wrapping is correct in [main.py](backend/app/main.py)
3. **CORS issues**: Check `settings.cors_origins` in [config.py](backend/app/config.py) matches frontend origin

### Frontend  
1. **Proxy not working**: Verify backend is running first on port 8000
2. **Type errors**: Run `npm run type-check` (uses `tsc --noEmit`)
3. **Socket connection fails**: Check browser console for `socket.io-client` connection errors

### Analysis Features
- **Segment analysis requires LLM**: Set valid `OPENAI_API_KEY` in `config.yaml`
- **Status codes**: Check `SegmentStatus` enum - `NOT_EVALUABLE` means insufficient text (<40 chars)
- **Events**: Q/A/R/S/X types based on EchoMind classification (see [ARCHITECTURE.md](ARCHITECTURE.md))

## 📚 Key Files for Context

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed design decisions and EchoMind reference
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Windows-specific debugging (PowerShell commands)
- [backend/API.md](backend/API.md) - REST/WebSocket API documentation
- [backend/app/services/full_analysis.py](backend/app/services/full_analysis.py) - Core analysis pipeline integration

## 🔗 External Dependencies

- **EchoMind reference**: [atomiechen/EchoMind](https://github.com/atomiechen/EchoMind) (CSCW 2025 paper)
- **OpenAI**: Required for LLM-based issue classification and summarization
- **Web Speech API**: Used for browser-based ASR (alternative to external ASR service)
