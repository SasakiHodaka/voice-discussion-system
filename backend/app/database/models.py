"""SQLAlchemy ORM models for EchoMind Voice Discussion System."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


class SessionModel(Base):
    """Database model for discussion sessions."""

    __tablename__ = "sessions"

    session_id = Column(String(255), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    creator_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    metadata = Column(JSON, default=dict, nullable=False)

    # Relationships
    participants = relationship("ParticipantModel", back_populates="session", cascade="all, delete-orphan")
    utterances = relationship("UtteranceModel", back_populates="session", cascade="all, delete-orphan")
    participant_states = relationship("ParticipantStateModel", back_populates="session", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResultModel", back_populates="session", cascade="all, delete-orphan")
    participant_profiles = relationship("ParticipantProfileModel", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SessionModel(session_id={self.session_id}, title={self.title})>"


class ParticipantModel(Base):
    """Database model for discussion participants."""

    __tablename__ = "participants"

    participant_id = Column(String(255), primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=True)  # facilitator, participant
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("SessionModel", back_populates="participants")
    utterances = relationship("UtteranceModel", back_populates="participant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ParticipantModel(participant_id={self.participant_id}, name={self.name})>"


class UtteranceModel(Base):
    """Database model for individual utterances."""

    __tablename__ = "utterances"

    utterance_id = Column(String(255), primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False)
    participant_id = Column(String(255), ForeignKey("participants.participant_id"), nullable=True)
    segment_id = Column(Integer, nullable=False)
    speaker = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    start_sec = Column(Float, nullable=False)
    end_sec = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("SessionModel", back_populates="utterances")
    participant = relationship("ParticipantModel", back_populates="utterances")

    def __repr__(self):
        return f"<UtteranceModel(utterance_id={self.utterance_id}, speaker={self.speaker})>"


class ParticipantStateModel(Base):
    """Database model for participant cognitive states at each segment."""

    __tablename__ = "participant_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False)
    segment_id = Column(Integer, nullable=False)
    speaker = Column(String(255), nullable=False)
    text = Column(Text, nullable=True)
    prosody_features = Column(JSON, default=dict, nullable=False)
    cognitive_state = Column(JSON, default=dict, nullable=False)  # confidence, understanding, hesitation, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("SessionModel", back_populates="participant_states")

    def __repr__(self):
        return f"<ParticipantStateModel(session_id={self.session_id}, segment_id={self.segment_id}, speaker={self.speaker})>"


class AnalysisResultModel(Base):
    """Database model for segment analysis results."""

    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False)
    segment_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    base_analysis = Column(JSON, default=dict, nullable=False)
    events = Column(JSON, default=list, nullable=False)
    summary = Column(JSON, default=dict, nullable=False)
    intervention_needed = Column(Integer, default=0, nullable=False)  # 0=false, 1=true
    intervention_type = Column(String(50), nullable=True)  # stagnation, confusion, imbalance
    intervention_message = Column(Text, nullable=True)

    # Relationships
    session = relationship("SessionModel", back_populates="analysis_results")

    def __repr__(self):
        return f"<AnalysisResultModel(session_id={self.session_id}, segment_id={self.segment_id})>"


class ParticipantProfileModel(Base):
    """Database model for participant profiles (aggregated across sessions)."""

    __tablename__ = "participant_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False)
    participant_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    speech_style = Column(String(50), nullable=True)  # 詳細型, 簡潔型, バランス型
    contribution_style = Column(String(50), nullable=True)  # 質問型, 回答型, 提案型
    cognitive_tendency = Column(JSON, default=list, nullable=False)
    confused_topics = Column(JSON, default=list, nullable=False)
    confident_topics = Column(JSON, default=list, nullable=False)
    avg_confidence = Column(Float, default=0.5, nullable=False)
    avg_understanding = Column(Float, default=0.5, nullable=False)
    avg_hesitation = Column(Float, default=0.5, nullable=False)
    total_sessions = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("SessionModel", back_populates="participant_profiles")

    def __repr__(self):
        return f"<ParticipantProfileModel(session_id={self.session_id}, participant_id={self.participant_id})>"
