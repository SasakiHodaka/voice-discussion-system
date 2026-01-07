"""Session management service."""

import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from app.models.schemas import (
    DiscussionSessionModel,
    ParticipantModel,
    SegmentResultModel,
    ParticipantRole,
)


class SessionManager:
    """Manages active discussion sessions."""

    def __init__(self, timeout_minutes: int = 60):
        """Initialize session manager."""
        self.timeout_minutes = timeout_minutes
        self.sessions: Dict[str, DiscussionSessionModel] = {}
        self.participant_to_session: Dict[str, str] = {}

    def create_session(
        self,
        title: str,
        description: Optional[str] = None,
        creator_name: str = "Facilitator",
    ) -> DiscussionSessionModel:
        """Create a new discussion session."""
        session_id = uuid.uuid4().hex[:8]
        facilitator = ParticipantModel(
            participant_id=uuid.uuid4().hex[:8],
            name=creator_name,
            role=ParticipantRole.FACILITATOR,
            joined_at=datetime.utcnow(),
        )

        session = DiscussionSessionModel(
            session_id=session_id,
            title=title,
            description=description,
            participants=[facilitator],
            created_at=datetime.utcnow(),
        )

        self.sessions[session_id] = session
        self.participant_to_session[facilitator.participant_id] = session_id
        return session

    def get_session(self, session_id: str) -> Optional[DiscussionSessionModel]:
        """Get a session by ID."""
        session = self.sessions.get(session_id)
        if session and self._is_expired(session):
            del self.sessions[session_id]
            return None
        return session

    def add_participant(
        self,
        session_id: str,
        participant_name: str,
        role: ParticipantRole = ParticipantRole.PARTICIPANT,
    ) -> Optional[ParticipantModel]:
        """Add a participant to a session."""
        session = self.get_session(session_id)
        if not session:
            return None

        participant_id = uuid.uuid4().hex[:8]
        participant = ParticipantModel(
            participant_id=participant_id,
            name=participant_name,
            role=role,
            joined_at=datetime.utcnow(),
        )

        session.participants.append(participant)
        self.participant_to_session[participant_id] = session_id
        return participant

    def remove_participant(
        self, session_id: str, participant_id: str
    ) -> Optional[ParticipantModel]:
        """Remove a participant from a session."""
        session = self.get_session(session_id)
        if not session:
            return None

        for i, p in enumerate(session.participants):
            if p.participant_id == participant_id:
                removed = session.participants.pop(i)
                if participant_id in self.participant_to_session:
                    del self.participant_to_session[participant_id]
                return removed
        return None

    def add_segment_result(
        self,
        session_id: str,
        segment_result: SegmentResultModel,
    ) -> bool:
        """Add segment analysis result to session."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.segments.append(segment_result)
        return True

    def end_session(self, session_id: str) -> Optional[DiscussionSessionModel]:
        """End a discussion session."""
        session = self.get_session(session_id)
        if not session:
            return None

        session.ended_at = datetime.utcnow()
        if session.started_at:
            session.duration_sec = (
                session.ended_at - session.started_at
            ).total_seconds()

        return session

    def _is_expired(self, session: DiscussionSessionModel) -> bool:
        """Check if session has expired."""
        if not session.started_at:
            return False
        expiry = session.started_at + timedelta(minutes=self.timeout_minutes)
        return datetime.utcnow() > expiry


# Global session manager
session_manager = SessionManager()
