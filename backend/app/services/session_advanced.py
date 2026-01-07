"""Advanced session management with metrics and persistence."""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from app.models.schemas import (
    DiscussionSessionModel,
    ParticipantModel,
    SegmentResultModel,
    ParticipantRole,
)


class SessionMetrics:
    """Metrics for a discussion session."""

    def __init__(self, session_id: str):
        """Initialize metrics."""
        self.session_id = session_id
        self.total_segments_analyzed = 0
        self.total_issues_identified = 0
        self.avg_segment_quality = 0.0
        self.participation_stats: Dict[str, int] = {}  # participant_id -> message count
        self.issue_evolution: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "total_segments_analyzed": self.total_segments_analyzed,
            "total_issues_identified": self.total_issues_identified,
            "avg_segment_quality": self.avg_segment_quality,
            "participation_stats": self.participation_stats,
            "issue_evolution": self.issue_evolution,
        }


class SessionManager:
    """Enhanced session management with persistence."""

    def __init__(
        self,
        timeout_minutes: int = 60,
        storage_dir: str = "artifacts/sessions",
    ):
        """Initialize session manager."""
        self.timeout_minutes = timeout_minutes
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.sessions: Dict[str, DiscussionSessionModel] = {}
        self.metrics: Dict[str, SessionMetrics] = {}
        self.participant_to_session: Dict[str, str] = {}

    def create_session(
        self,
        title: str,
        description: Optional[str] = None,
        creator_name: str = "Facilitator",
        metadata: Optional[Dict[str, Any]] = None,
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
            metadata=metadata or {},
        )

        self.sessions[session_id] = session
        self.metrics[session_id] = SessionMetrics(session_id)
        self.participant_to_session[facilitator.participant_id] = session_id

        # Save to storage
        self._save_session(session)

        return session

    def get_session(self, session_id: str) -> Optional[DiscussionSessionModel]:
        """Get a session by ID."""
        session = self.sessions.get(session_id)
        if session and self._is_expired(session):
            self._delete_session(session_id)
            return None
        return session

    def get_all_sessions(self) -> List[DiscussionSessionModel]:
        """Get all active sessions."""
        return [s for s in self.sessions.values() if not self._is_expired(s)]

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

        # Initialize participation stats
        metrics = self.metrics.get(session_id)
        if metrics:
            metrics.participation_stats[participant_id] = 0

        return participant

    def remove_participant(
        self,
        session_id: str,
        participant_id: str,
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

        # Update metrics
        metrics = self.metrics.get(session_id)
        if metrics:
            metrics.total_segments_analyzed += 1

        self._save_session(session)
        return True

    def start_session(self, session_id: str) -> Optional[DiscussionSessionModel]:
        """Mark session as started."""
        session = self.get_session(session_id)
        if not session:
            return None

        session.started_at = datetime.utcnow()
        self._save_session(session)
        return session

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

        self._save_session(session)
        return session

    def get_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metrics."""
        metrics = self.metrics.get(session_id)
        return metrics.to_dict() if metrics else None

    def update_participation(
        self,
        session_id: str,
        participant_id: str,
    ) -> bool:
        """Update participation count for a participant."""
        metrics = self.metrics.get(session_id)
        if not metrics:
            return False

        if participant_id in metrics.participation_stats:
            metrics.participation_stats[participant_id] += 1
            return True
        return False

    def _save_session(self, session: DiscussionSessionModel) -> None:
        """Save session to storage."""
        try:
            session_file = self.storage_dir / f"{session.session_id}.json"
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session.model_dump(), f, default=str, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving session {session.session_id}: {e}")

    def _delete_session(self, session_id: str) -> None:
        """Delete session and its storage."""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.metrics:
            del self.metrics[session_id]

        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

    def _is_expired(self, session: DiscussionSessionModel) -> bool:
        """Check if session has expired."""
        if not session.started_at:
            return False
        expiry = session.started_at + timedelta(minutes=self.timeout_minutes)
        return datetime.utcnow() > expiry

    def load_session_history(self, session_id: str) -> Optional[DiscussionSessionModel]:
        """Load a session from storage."""
        session_file = self.storage_dir / f"{session_id}.json"
        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return DiscussionSessionModel(**data)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None


# Global session manager
session_manager = SessionManager()
