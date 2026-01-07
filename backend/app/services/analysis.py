"""Analysis service - bridges existing analysis logic with FastAPI."""

import os
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import asdict

from app.models.schemas import (
    SegmentResultModel,
    AudioStatsModel,
    UtteranceModel,
    EventModel,
    SegmentStatus,
)


class AnalysisService:
    """Service for conversation analysis."""

    def __init__(self, work_dir: str = "artifacts"):
        """Initialize analysis service."""
        self.work_dir = work_dir
        os.makedirs(work_dir, exist_ok=True)

    def _import_legacy_modules(self) -> tuple:
        """Dynamically import existing analysis modules.

        Search both the backend folder and the repository root for
        analysis_segment20.py. Try sys.path import first, then direct file load.
        """
        import sys
        import importlib.util

        service_dir = os.path.dirname(__file__)                 # .../backend/app/services
        app_dir = os.path.dirname(service_dir)                   # .../backend/app
        backend_dir = os.path.dirname(app_dir)                   # .../backend
        repo_root = os.path.dirname(backend_dir)                 # .../<repo root>

        candidates = [backend_dir, repo_root, os.getcwd()]

        # 1) Try normal import after extending sys.path with candidates
        original_sys_path = list(sys.path)
        try:
            for d in candidates:
                if d and d not in sys.path:
                    sys.path.insert(0, d)
            from analysis_segment20 import (
                AudioStats,
                Utterance,
                Event,
                analyze_segment,
            )
            return AudioStats, Utterance, Event, analyze_segment
        except Exception as e1:
            # 2) Fallback: direct file load from any candidate directory
            last_error = e1
            for d in candidates:
                try:
                    module_name = "analysis_segment20"
                    module_path = os.path.join(d, f"{module_name}.py")
                    if not os.path.exists(module_path):
                        continue
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec is None or spec.loader is None:
                        continue
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                    AudioStats = getattr(mod, "AudioStats")
                    Utterance = getattr(mod, "Utterance")
                    Event = getattr(mod, "Event")
                    analyze_segment = getattr(mod, "analyze_segment")
                    return AudioStats, Utterance, Event, analyze_segment
                except Exception as e_each:
                    last_error = e_each
            # If we reach here, all attempts failed
            raise RuntimeError(
                "Could not import analysis modules. Checked paths: "
                + ", ".join(candidates)
                + f". Last error: {last_error}"
            )
        finally:
            sys.path = original_sys_path

    def analyze_segment(
        self,
        session_id: str,
        segment_id: int,
        start_sec: float,
        end_sec: float,
        audio_stats: Optional[Dict[str, float]] = None,
        utterances: Optional[List[Dict[str, Any]]] = None,
    ) -> SegmentResultModel:
        """Analyze a single segment."""

        try:
            AudioStats, Utterance, Event, analyze_segment = self._import_legacy_modules()

            # Convert input to legacy format
            audio = AudioStats(
                volume_dbfs=audio_stats.get("volume_dbfs", 0.0)
                if audio_stats
                else 0.0,
                peak_dbfs=audio_stats.get("peak_dbfs", 0.0) if audio_stats else 0.0,
                silence=audio_stats.get("silence", False) if audio_stats else False,
            )

            utterances_list: List[Utterance] = []
            if utterances:
                for u in utterances:
                    utterances_list.append(
                        Utterance(
                            utterance_id=u.get("utterance_id", f"u{len(utterances_list)}"),
                            start=u.get("start", start_sec),
                            end=u.get("end", end_sec),
                            speaker=u.get("speaker", "Unknown"),
                            text=u.get("text", ""),
                        )
                    )

            # Call legacy analyze_segment
            result = analyze_segment(
                session_id=session_id,
                segment_id=segment_id,
                start_sec=start_sec,
                end_sec=end_sec,
                audio_stats=audio,
                utterances=utterances_list,
                min_total_chars_for_evaluable=40,
            )

            # Convert result to Pydantic model
            return SegmentResultModel(
                session_id=result.session_id,
                segment_id=result.segment_id,
                start_sec=result.start_sec,
                end_sec=result.end_sec,
                status=SegmentStatus(result.status),
                status_reason=result.status_reason,
                audio=AudioStatsModel(**asdict(result.audio)),
                utterances=[
                    UtteranceModel(**asdict(u)) for u in result.utterances
                ],
                events=[EventModel(**asdict(e)) for e in result.events],
                U=result.U,
                Q=result.Q,
                A=result.A,
                UQ=result.UQ,
                R=result.R,
                S=result.S,
                X=result.X,
                P=result.P,
                D=result.D,
                M=result.M,
                T=result.T,
                L=result.L,
                is_risky=result.is_risky,
                note=result.note,
            )

        except Exception as e:
            # Fallback for when analysis fails
            return SegmentResultModel(
                session_id=session_id,
                segment_id=segment_id,
                start_sec=start_sec,
                end_sec=end_sec,
                status=SegmentStatus.NOT_EVALUABLE,
                status_reason=f"Analysis error: {str(e)}",
                audio=AudioStatsModel(),
                utterances=[],
                events=[],
                note=f"Error during segment analysis",
            )
