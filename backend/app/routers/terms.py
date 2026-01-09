"""REST API endpoints for term suggestion."""

import logging
from typing import List
from fastapi import APIRouter, HTTPException

from app.services.term_suggestion import term_suggestion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terms", tags=["terms"])


@router.post("/suggest")
async def suggest_terms(payload: dict) -> dict:
    """
    議論のテキストから用語提案を生成.

    Request body:
        {
            "session_id": "session-123",
            "messages": [
                {"speaker": "Alice", "text": "..."},
                {"speaker": "Bob", "text": "..."}
            ]
        }

    Returns:
        提案された用語と定義
    """
    try:
        session_id = payload.get("session_id", "unknown")
        messages = payload.get("messages", [])

        result = term_suggestion_service.suggest_terms_for_session(
            session_id=session_id,
            messages=messages,
        )

        return result

    except Exception as e:
        logger.error(f"Error suggesting terms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest/{session_id}")
async def get_suggested_terms(session_id: str) -> dict:
    """
    セッション ID から用語提案を取得.

    Args:
        session_id: セッション ID

    Returns:
        提案された用語リスト
    """
    try:
        # Note: In production, fetch messages from DB based on session_id
        # For now, return empty list
        return {
            "session_id": session_id,
            "terms": [],
            "count": 0,
            "message": "Messages should be retrieved from database for full implementation.",
        }

    except Exception as e:
        logger.error(f"Error fetching terms: {e}")
        raise HTTPException(status_code=500, detail=str(e))
