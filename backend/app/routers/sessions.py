"""API routes for discussion sessions."""

from typing import List
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    DiscussionSessionModel,
    SegmentResultModel,
    ParticipantModel,
    ParticipantRole,
)
from app.services.session import session_manager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/", response_model=DiscussionSessionModel, status_code=status.HTTP_201_CREATED)
async def create_session(
    title: str,
    description: str = "",
    creator_name: str = "Facilitator",
) -> DiscussionSessionModel:
    """Create a new discussion session."""
    session = session_manager.create_session(
        title=title,
        description=description if description else None,
        creator_name=creator_name,
    )
    return session


@router.get("/{session_id}", response_model=DiscussionSessionModel)
async def get_session(session_id: str) -> DiscussionSessionModel:
    """Get a session by ID."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return session


@router.get("/", response_model=List[DiscussionSessionModel])
async def list_sessions() -> List[DiscussionSessionModel]:
    """List all active sessions."""
    return list(session_manager.sessions.values())


@router.post("/{session_id}/participants", response_model=ParticipantModel)
async def add_participant(
    session_id: str,
    name: str,
    role: ParticipantRole = ParticipantRole.PARTICIPANT,
) -> ParticipantModel:
    """Add a participant to a session."""
    participant = session_manager.add_participant(
        session_id=session_id,
        participant_name=name,
        role=role,
    )
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return participant


@router.delete("/{session_id}/participants/{participant_id}")
async def remove_participant(session_id: str, participant_id: str) -> dict:
    """Remove a participant from a session."""
    removed = session_manager.remove_participant(
        session_id=session_id,
        participant_id=participant_id,
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant or session not found",
        )
    return {"status": "ok", "removed_participant_id": participant_id}


@router.get("/{session_id}/segments", response_model=List[SegmentResultModel])
async def get_segments(session_id: str) -> List[SegmentResultModel]:
    """Get all segment results for a session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return session.segments


@router.post("/{session_id}/end")
async def end_session(session_id: str) -> DiscussionSessionModel:
    """End a discussion session."""
    session = session_manager.end_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return session
