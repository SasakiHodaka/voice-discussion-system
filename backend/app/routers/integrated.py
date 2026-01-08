"""統合分析APIルーター."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel

from app.services.integrated_analysis import integrated_service
from app.services.participant_profile import profile_service
from app.services.intervention import intervention_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrated", tags=["integrated-analysis"])


class AnalyzeSegmentRequest(BaseModel):
    session_id: str
    segment_id: int
    start_sec: float
    end_sec: float
    utterances: Optional[List[Dict[str, Any]]] = None


@router.post("/analyze-segment")
async def analyze_segment_integrated(
    request: AnalyzeSegmentRequest,
) -> dict:
    """
    統合分析を実行（韻律分析 + 認知状態推定 + 介入判定）.

    研究計画書の提案手法に基づく統合分析:
    - 韻律情報から認知状態を推定
    - 個人特性を考慮した予測
    - 介入が必要かを判定し助言を生成
    """
    try:
        utterances = request.utterances or []

        result = integrated_service.analyze_segment_integrated(
            session_id=request.session_id,
            segment_id=request.segment_id,
            start_sec=request.start_sec,
            end_sec=request.end_sec,
            utterances=utterances,
        )

        return result

    except Exception as e:
        logger.error(f"Error in integrated analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/participant-profile/{participant_id}")
async def get_participant_profile(participant_id: str) -> dict:
    """
    参加者の特性プロファイルを取得.

    複数セッションから学習した個人特性:
    - 発言傾向
    - 認知傾向
    - つまずきやすいトピック
    """
    try:
        insights = profile_service.get_participant_insights(participant_id)

        if not insights:
            raise HTTPException(status_code=404, detail="Profile not found")

        return insights

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/participant-profiles")
async def get_all_participant_profiles() -> dict:
    """全参加者のプロファイルを取得."""
    try:
        profiles = profile_service.export_profiles()
        return {"profiles": profiles, "count": len(profiles)}

    except Exception as e:
        logger.error(f"Error exporting profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateProfilesRequest(BaseModel):
    session_id: str
    session_results: List[Dict[str, Any]]


@router.post("/update-profiles")
async def update_participant_profiles(
    request: UpdateProfilesRequest,
) -> dict:
    """
    セッション終了後に参加者プロファイルを更新.

    履歴データとして蓄積し、次回以降の分析に活用します。
    """
    try:
        result = integrated_service.update_participant_profiles(
            session_id=request.session_id,
            session_results=request.session_results,
        )

        return result

    except Exception as e:
        logger.error(f"Error updating profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CheckInterventionRequest(BaseModel):
    segment_result: Dict[str, Any]
    participant_states: List[Dict[str, Any]]


@router.post("/check-intervention")
async def check_intervention_need(
    request: CheckInterventionRequest,
) -> dict:
    """
    介入が必要かをチェック.

    議論の停滞や理解不足を検出し、必要な介入タイプを判定します。
    """
    try:
        result = intervention_service.detect_intervention_need(
            segment_result=request.segment_result,
            participant_states=request.participant_states,
        )

        return result

    except Exception as e:
        logger.error(f"Error checking intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GenerateInterventionRequest(BaseModel):
    intervention_type: str
    context: Dict[str, Any]


@router.post("/generate-intervention")
async def generate_intervention_message(
    request: GenerateInterventionRequest,
) -> dict:
    """
    介入メッセージを生成.

    議論の状況に応じた具体的な助言を生成します:
    - 明確化要求
    - 要点整理
    - 新しい視点の提示
    - 発言促進
    """
    try:
        message = intervention_service.generate_intervention_message(
            intervention_type=request.intervention_type,
            context=request.context,
        )

        if message is None:
            return {"intervention_type": request.intervention_type, "message": None}

        return {
            "intervention_type": request.intervention_type,
            "message": message,
        }

    except Exception as e:
        logger.error(f"Error generating intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RealtimeRecommendationsRequest(BaseModel):
    session_id: str
    current_segment_result: Dict[str, Any]
    participant_states: List[Dict[str, Any]]


@router.post("/realtime-recommendations")
async def get_realtime_recommendations(
    request: RealtimeRecommendationsRequest,
) -> dict:
    """
    リアルタイムで推奨アクションを取得.

    現在の議論状況から、ファシリテーターが取るべきアクションを提案します。
    """
    try:
        recommendations = integrated_service.get_realtime_recommendations(
            session_id=request.session_id,
            current_segment_result=request.current_segment_result,
            participant_states=request.participant_states,
        )

        return recommendations

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict-difficulty")
async def predict_difficulty(
    participant_id: str = Query(..., description="Participant ID"),
    topic: str = Query(..., description="Topic"),
) -> dict:
    """
    特定のトピックでの理解困難度を予測.

    過去の履歴から、参加者がどのトピックで理解が遅れがちかを予測します。
    """
    try:
        prediction = profile_service.predict_difficulty(
            participant_id=participant_id,
            topic=topic,
        )

        return {
            "participant_id": participant_id,
            "topic": topic,
            **prediction,
        }

    except Exception as e:
        logger.error(f"Error predicting difficulty: {e}")
        raise HTTPException(status_code=500, detail=str(e))
