"""Pydantic models for API requests/responses."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class SegmentStatus(str, Enum):
    """Segment analysis status."""

    OK = "OK"
    NOT_VALID = "NOT_VALID"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class ParticipantRole(str, Enum):
    """Participant role in discussion."""

    FACILITATOR = "facilitator"
    PARTICIPANT = "participant"
    OBSERVER = "observer"


# --- Request/Response Models ---


class AudioStatsModel(BaseModel):
    """Audio statistics."""

    volume_dbfs: float = 0.0
    peak_dbfs: float = 0.0
    silence: bool = False


class UtteranceModel(BaseModel):
    """Single utterance in conversation."""

    utterance_id: str
    start: float
    end: float
    speaker: str
    text: str


class EventModel(BaseModel):
    """Analysis event (Question, Answer, etc)."""

    event_id: str
    t: float
    type: str  # Q, A, R, S, X
    utterance_id: str
    speaker: str
    link_q_event_id: Optional[str] = None
    delay_sec: Optional[float] = None


class SegmentResultModel(BaseModel):
    """Result for a single segment."""

    session_id: str
    segment_id: int
    start_sec: float
    end_sec: float
    status: SegmentStatus
    status_reason: str

    audio: AudioStatsModel
    utterances: List[UtteranceModel]
    events: List[EventModel]

    U: int = 0
    Q: int = 0
    A: int = 0
    UQ: int = 0
    R: int = 0
    S: int = 0
    X: int = 0
    P: int = 0
    D: float = 0.0

    M: float = 0.0  # confusion proxy
    T: float = 0.0  # stagnation proxy
    L: float = 0.0  # understanding proxy

    is_risky: bool = False
    note: str = ""


class ParticipantModel(BaseModel):
    """Discussion participant."""

    participant_id: str
    name: str
    role: ParticipantRole = ParticipantRole.PARTICIPANT
    joined_at: datetime
    color: Optional[str] = None


class DiscussionSessionModel(BaseModel):
    """Discussion session."""

    session_id: str
    title: str
    description: Optional[str] = None
    participants: List[ParticipantModel]
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_sec: Optional[float] = None
    segments: List[SegmentResultModel] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- WebSocket Messages ---


class MessageType(str, Enum):
    """WebSocket message types."""

    # Client -> Server
    JOIN = "join"
    LEAVE = "leave"
    SEND_TEXT = "send_text"
    START_ANALYSIS = "start_analysis"
    END_ANALYSIS = "end_analysis"

    # Server -> Client
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    TEXT_RECEIVED = "text_received"
    SEGMENT_ANALYZED = "segment_analyzed"
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR = "error"


class SocketMessage(BaseModel):
    """WebSocket message."""

    type: MessageType
    session_id: str
    participant_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- Analysis request model (for REST) ---

class AnalysisRequest(BaseModel):
    session_id: str
    segment_id: int = 0
    start_sec: float = 0.0
    end_sec: float = 0.0
    utterances: List[Dict[str, Any]] = Field(default_factory=list)


class FullAnalysisRequest(BaseModel):
    """Request model for full discussion analysis."""
    session_id: str
    utterances: List[Dict[str, Any]] = Field(default_factory=list)
