"""WebSocket/SocketIO handlers."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

import socketio

from app.models.schemas import (
    SocketMessage,
    MessageType,
    ParticipantRole,
)
from app.services.session import session_manager
from app.services.analysis import AnalysisService

logger = logging.getLogger(__name__)
analysis_service = AnalysisService()

# SocketIO server instance
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["*"],
    logger=False,
    engineio_logger=False,
)


@sio.event
async def connect(sid: str, environ: Dict[str, Any]) -> None:
    """Handle client connection."""
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def join(sid: str, data: Dict[str, Any]) -> None:
    """Handle participant joining a session."""
    try:
        session_id = data.get("session_id")
        participant_name = data.get("participant_name", "Anonymous")
        role = data.get("role", ParticipantRole.PARTICIPANT.value)

        session = session_manager.get_session(session_id)
        if not session:
            await sio.emit("error", {"message": "Session not found"}, to=sid)
            return

        participant = session_manager.add_participant(
            session_id=session_id,
            participant_name=participant_name,
            role=ParticipantRole(role),
        )

        if not participant:
            await sio.emit("error", {"message": "Could not add participant"}, to=sid)
            return

        # Notify all clients in session
        await sio.emit(
            "participant_joined",
            {
                "session_id": session_id,
                "participant": {
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "role": participant.role.value,
                },
            },
            room=session_id,
        )

        # Join SocketIO room
        sio.enter_room(sid, session_id)
        logger.info(f"Participant {participant.participant_id} joined session {session_id}")

    except Exception as e:
        logger.error(f"Error in join handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)


@sio.event
async def send_text(sid: str, data: Dict[str, Any]) -> None:
    """Handle text message from participant."""
    try:
        session_id = data.get("session_id")
        participant_id = data.get("participant_id")
        text = data.get("text", "")
        speaker = data.get("speaker") or data.get("speaker_label")

        session = session_manager.get_session(session_id)
        if not session:
            await sio.emit("error", {"message": "Session not found"}, to=sid)
            return

        # Resolve participant name
        participant_name = None
        for p in session.participants:
            if p.participant_id == participant_id:
                participant_name = p.name
                break

        # Broadcast text to all participants
        await sio.emit(
            "text_received",
            {
                "session_id": session_id,
                "participant_id": participant_id,
                "participant_name": participant_name or "Unknown",
                "speaker": speaker,
                "text": text,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=session_id,
        )

        logger.info(f"Text from {participant_id} [{speaker or participant_name}]: {len(text)} chars")

    except Exception as e:
        logger.error(f"Error in send_text handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)


@sio.event
async def analyze_segment(sid: str, data: Dict[str, Any]) -> None:
    """Handle segment analysis request."""
    try:
        session_id = data.get("session_id")
        segment_id = data.get("segment_id", 0)
        start_sec = data.get("start_sec", 0.0)
        end_sec = data.get("end_sec", 20.0)
        utterances = data.get("utterances", [])

        session = session_manager.get_session(session_id)
        if not session:
            await sio.emit("error", {"message": "Session not found"}, to=sid)
            return

        # Perform analysis
        result = analysis_service.analyze_segment(
            session_id=session_id,
            segment_id=segment_id,
            start_sec=start_sec,
            end_sec=end_sec,
            utterances=utterances,
        )

        # Add to session
        session_manager.add_segment_result(session_id, result)

        # Emit result to all participants
        await sio.emit(
            "segment_analyzed",
            {
                "session_id": session_id,
                "segment_id": segment_id,
                "result": result.model_dump(),
            },
            room=session_id,
        )

        logger.info(f"Segment {segment_id} analyzed for session {session_id}")

    except Exception as e:
        logger.error(f"Error in analyze_segment handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)


@sio.event
async def leave(sid: str, data: Dict[str, Any]) -> None:
    """Handle participant leaving session."""
    try:
        session_id = data.get("session_id")
        participant_id = data.get("participant_id")

        removed = session_manager.remove_participant(session_id, participant_id)
        if removed:
            await sio.emit(
                "participant_left",
                {
                    "session_id": session_id,
                    "participant_id": participant_id,
                },
                room=session_id,
            )
            sio.leave_room(sid, session_id)
            logger.info(f"Participant {participant_id} left session {session_id}")

    except Exception as e:
        logger.error(f"Error in leave handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)
