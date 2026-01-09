"""REST API endpoints for database queries and history retrieval."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import (
    AnalysisResultModel,
    ParticipantStateModel,
    ParticipantProfileModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/analysis/{session_id}")
async def get_analysis_history(
    session_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    セッションの分析履歴を取得.

    Args:
        session_id: セッションID
        db: DB セッション

    Returns:
        分析結果リスト
    """
    try:
        results = (
            db.query(AnalysisResultModel)
            .filter(AnalysisResultModel.session_id == session_id)
            .order_by(AnalysisResultModel.segment_id)
            .all()
        )

        return {
            "session_id": session_id,
            "count": len(results),
            "results": [
                {
                    "segment_id": r.segment_id,
                    "timestamp": r.timestamp.isoformat(),
                    "base_analysis": r.base_analysis,
                    "summary": r.summary,
                    "intervention": {
                        "needed": bool(r.intervention_needed),
                        "type": r.intervention_type,
                        "message": r.intervention_message,
                    },
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching analysis history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/participant-states/{session_id}")
async def get_participant_states_history(
    session_id: str,
    segment_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    参加者の状態履歴を取得.

    Args:
        session_id: セッションID
        segment_id: セグメントID（オプション）
        db: DB セッション

    Returns:
        参加者状態リスト
    """
    try:
        query = db.query(ParticipantStateModel).filter(
            ParticipantStateModel.session_id == session_id
        )

        if segment_id is not None:
            query = query.filter(ParticipantStateModel.segment_id == segment_id)

        states = query.order_by(
            ParticipantStateModel.segment_id, ParticipantStateModel.created_at
        ).all()

        return {
            "session_id": session_id,
            "segment_id": segment_id,
            "count": len(states),
            "states": [
                {
                    "segment_id": s.segment_id,
                    "speaker": s.speaker,
                    "text": s.text,
                    "prosody_features": s.prosody_features,
                    "cognitive_state": s.cognitive_state,
                    "created_at": s.created_at.isoformat(),
                }
                for s in states
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching participant states: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/participant-profiles/{session_id}")
async def get_participant_profiles(
    session_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    セッションの参加者プロファイルを取得.

    Args:
        session_id: セッションID
        db: DB セッション

    Returns:
        参加者プロファイルリスト
    """
    try:
        profiles = (
            db.query(ParticipantProfileModel)
            .filter(ParticipantProfileModel.session_id == session_id)
            .all()
        )

        return {
            "session_id": session_id,
            "count": len(profiles),
            "profiles": [
                {
                    "participant_id": p.participant_id,
                    "name": p.name,
                    "speech_style": p.speech_style,
                    "contribution_style": p.contribution_style,
                    "cognitive_tendency": p.cognitive_tendency,
                    "confused_topics": p.confused_topics,
                    "confident_topics": p.confident_topics,
                    "avg_confidence": p.avg_confidence,
                    "avg_understanding": p.avg_understanding,
                    "avg_hesitation": p.avg_hesitation,
                    "total_sessions": p.total_sessions,
                }
                for p in profiles
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching participant profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{session_id}")
async def get_session_summary(
    session_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    セッションの総合サマリーを取得.

    Args:
        session_id: セッションID
        db: DB セッション

    Returns:
        セッション総合情報
    """
    try:
        analysis_count = (
            db.query(AnalysisResultModel)
            .filter(AnalysisResultModel.session_id == session_id)
            .count()
        )

        intervention_count = (
            db.query(AnalysisResultModel)
            .filter(
                AnalysisResultModel.session_id == session_id,
                AnalysisResultModel.intervention_needed == 1,
            )
            .count()
        )

        avg_health = 0.0
        results = (
            db.query(AnalysisResultModel)
            .filter(AnalysisResultModel.session_id == session_id)
            .all()
        )
        if results:
            health_scores = [
                r.summary.get("discussion_health", 0.5) for r in results
            ]
            avg_health = sum(health_scores) / len(health_scores)

        profiles = (
            db.query(ParticipantProfileModel)
            .filter(ParticipantProfileModel.session_id == session_id)
            .count()
        )

        return {
            "session_id": session_id,
            "total_segments": analysis_count,
            "interventions_needed": intervention_count,
            "average_discussion_health": avg_health,
            "total_participants": profiles,
        }
    except Exception as e:
        logger.error(f"Error fetching session summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
