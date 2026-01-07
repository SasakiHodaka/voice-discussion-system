"""API routes for analysis."""

from typing import Dict, Any
from fastapi import APIRouter

from app.models.schemas import SegmentResultModel, AnalysisRequest, FullAnalysisRequest
from app.services.analysis import AnalysisService
from app.services.full_analysis import FullAnalysisService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])
analysis_service = AnalysisService()
full_analysis_service = FullAnalysisService()


@router.post("/segment", response_model=SegmentResultModel)
async def analyze_segment(req: AnalysisRequest) -> SegmentResultModel:
    """Analyze a single segment (JSON body)."""
    result = analysis_service.analyze_segment(
        session_id=req.session_id,
        segment_id=req.segment_id,
        start_sec=req.start_sec,
        end_sec=req.end_sec,
        utterances=req.utterances or [],
    )
    return result


@router.post("/full")
async def analyze_full(req: FullAnalysisRequest) -> Dict[str, Any]:
    """Analyze full discussion for understanding gaps and patterns."""
    result = full_analysis_service.analyze_full_discussion(
        session_id=req.session_id,
        utterances=req.utterances or [],
    )
    return result
