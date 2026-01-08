"""統合分析サービス - 韻律分析・個人特性・介入生成を統合."""

import logging
import os
import json
from datetime import datetime
from typing import Any, Dict, List

from app.services.analysis import AnalysisService
from app.services.intervention import intervention_service
from app.services.participant_profile import profile_service
from app.services.prosody_analysis import prosody_service
from app.services.session import session_manager

logger = logging.getLogger(__name__)


class IntegratedAnalysisService:
    """
    議論の統合分析サービス.

    研究計画書で提案された以下の機能を統合:
    1. 韻律情報分析（声の揺れ、発話速度、言い淀みから認知状態推定）
    2. 個人特性モデリング（複数セッションからの学習）
    3. 介入生成（議論状況に応じた助言）
    """

    def __init__(self) -> None:
        self.base_analysis = AnalysisService()

    def analyze_segment_integrated(
        self,
        session_id: str,
        segment_id: int,
        start_sec: float,
        end_sec: float,
        utterances: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """セグメントの統合分析を実行."""
        try:
            logger.info("Starting integrated analysis for segment %s", segment_id)

            base_result = self.base_analysis.analyze_segment(
                session_id=session_id,
                segment_id=segment_id,
                start_sec=start_sec,
                end_sec=end_sec,
                utterances=utterances,
            )

            if hasattr(base_result, "model_dump"):
                base_result_dict = base_result.model_dump()
            elif hasattr(base_result, "dict"):
                base_result_dict = base_result.dict()
            else:
                base_result_dict = base_result

            participant_states: List[Dict[str, Any]] = []
            for utterance in utterances:
                speaker = utterance.get("speaker", "unknown")
                text = utterance.get("text", "")
                duration = utterance.get("end", 0) - utterance.get("start", 0)

                prosody_result = prosody_service.analyze_utterance(
                    text=text,
                    duration_sec=duration,
                    speaker=speaker,
                    audio_features=utterance.get("audio_features"),
                )

                participant_states.append(
                    {
                        "speaker": speaker,
                        "text": text,
                        "utterance_id": utterance.get("utterance_id"),
                        "prosody": prosody_result.get("prosody_features", {}),
                        "cognitive_state": prosody_result.get("cognitive_state", {}),
                    }
                )

            participant_predictions: Dict[str, Any] = {}
            for speaker in set(u.get("speaker") for u in utterances):
                topic = base_result_dict.get("dominant_topic", "general")
                prediction = profile_service.predict_difficulty(speaker, topic)
                participant_predictions[speaker] = prediction

            # プロファイル更新用のセッションデータを組み立て
            participant_profiles: Dict[str, Any] = {}
            per_speaker_session_data: Dict[str, Dict[str, Any]] = {}
            # 初期化
            for s in set(u.get("speaker") for u in utterances):
                per_speaker_session_data[s] = {
                    "name": s,
                    "utterances": [],
                    "cognitive_states": [],
                    "events": [],
                }
            # 参加者別に韻律・認知状態を格納
            for st in participant_states:
                sid = st.get("speaker")
                if sid in per_speaker_session_data:
                    per_speaker_session_data[sid]["utterances"].append(
                        {
                            "text": st.get("text", ""),
                            "speech_rate": st.get("prosody", {}).get("speech_rate", 0.0),
                        }
                    )
                    per_speaker_session_data[sid]["cognitive_states"].append(
                        st.get("cognitive_state", {})
                    )
            # ベース分析イベントを話者別に紐づけ
            for ev in base_result_dict.get("events", []) or []:
                sid = ev.get("speaker")
                if sid in per_speaker_session_data:
                    per_speaker_session_data[sid]["events"].append(ev)
            # プロファイル更新・インサイト抽出
            for sid, data in per_speaker_session_data.items():
                try:
                    profile_service.update_profile_from_session(
                        participant_id=sid,
                        session_data=data,
                    )
                    insights = profile_service.get_participant_insights(sid)
                    if insights is not None:
                        participant_profiles[sid] = insights
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Profile update failed for %s: %s", sid, exc)

            intervention_check = intervention_service.detect_intervention_need(
                segment_result=base_result_dict,
                participant_states=[s.get("cognitive_state", {}) for s in participant_states],
            )

            intervention_message = None
            if intervention_check.get("needs_intervention"):
                context = {
                    "transcript": " ".join(u.get("text", "") for u in utterances),
                    "issues": base_result_dict.get("issues", []),
                    "Q_count": base_result_dict.get("Q", 0),
                    "M": base_result_dict.get("M", 0),
                    "T": base_result_dict.get("T", 0),
                }
                intervention_message = intervention_service.generate_intervention_message(
                    intervention_type=intervention_check["intervention_type"],
                    context=context,
                )

            integrated_result = {
                "session_id": session_id,
                "segment_id": segment_id,
                "timestamp": datetime.utcnow().isoformat(),
                "base_analysis": base_result_dict,
                "utterances": utterances,
                "participant_states": participant_states,
                "participant_predictions": participant_predictions,
                "participant_profiles": participant_profiles,
                "intervention": {
                    "needed": intervention_check.get("needs_intervention"),
                    "type": intervention_check.get("intervention_type"),
                    "priority": intervention_check.get("priority"),
                    "reason": intervention_check.get("reason"),
                    "message": intervention_message,
                },
                "summary": self._generate_summary(
                    base_result_dict,
                    participant_states,
                    intervention_check,
                ),
            }

            # 補足メッセージ: 介入が必要だがテンプレが空のとき
            if (
                integrated_result["intervention"].get("needed")
                and not integrated_result["intervention"].get("message")
            ):
                integrated_result["intervention"]["message"] = (
                    "議論の停滞/混乱が検出されました。要点の再整理や役割の明確化を提案します。"
                )

            logger.info("Integrated analysis completed for segment %s", segment_id)
            self._save_participant_states_history(
                session_id=session_id,
                segment_id=segment_id,
                timestamp=integrated_result["timestamp"],
                participant_states=participant_states,
            )
            self._save_participant_profiles_snapshot(
                session_id=session_id,
                timestamp=integrated_result["timestamp"],
                participant_profiles=participant_profiles,
            )
            return integrated_result

        except Exception as e:  # pragma: no cover - defensive
            logger.error("Error in integrated analysis: %s", e, exc_info=True)
            return {
                "session_id": session_id,
                "segment_id": segment_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _save_participant_states_history(
        self,
        session_id: str,
        segment_id: int,
        timestamp: str,
        participant_states: List[Dict[str, Any]],
    ) -> None:
        """韻律/認知状態をセッションメタデータとファイルに保存."""
        # メモリ上のセッションにも格納
        session_obj = session_manager.get_session(session_id)
        if session_obj is not None:
            history = session_obj.metadata.get("participant_states_history", [])
            history.append(
                {
                    "segment_id": segment_id,
                    "timestamp": timestamp,
                    "participant_states": participant_states,
                }
            )
            session_obj.metadata["participant_states_history"] = history

        # 簡易なJSONLで永続化（後でDBに移行可）
        try:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "prosody_history")
            os.makedirs(base_dir, exist_ok=True)
            path = os.path.join(base_dir, f"{session_id}.jsonl")
            record = {
                "session_id": session_id,
                "segment_id": segment_id,
                "timestamp": timestamp,
                "participant_states": participant_states,
            }
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to persist participant_states_history: %s", exc)

    def _save_participant_profiles_snapshot(
        self,
        session_id: str,
        timestamp: str,
        participant_profiles: Dict[str, Any],
    ) -> None:
        """参加者プロファイルのスナップショットをセッションメタデータとファイルに保存."""
        # メモリ上のセッションに最新スナップショットを保持
        session_obj = session_manager.get_session(session_id)
        if session_obj is not None:
            session_obj.metadata["participant_profiles"] = participant_profiles

        # JSONファイルとしてスナップショット保存
        try:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "participant_profiles")
            os.makedirs(base_dir, exist_ok=True)
            path = os.path.join(base_dir, f"{session_id}.json")
            payload = {
                "session_id": session_id,
                "timestamp": timestamp,
                "profiles": participant_profiles,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to persist participant_profiles: %s", exc)

    def update_participant_profiles(
        self,
        session_id: str,
        session_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """セッション終了後に参加者プロファイルを更新."""
        try:
            updated_profiles: Dict[str, Any] = {}
            participant_data: Dict[str, Any] = {}

            for result in session_results:
                for state in result.get("participant_states", []):
                    speaker = state.get("speaker")
                    if speaker not in participant_data:
                        participant_data[speaker] = {
                            "name": speaker,
                            "utterances": [],
                            "cognitive_states": [],
                            "events": [],
                        }

                    participant_data[speaker]["utterances"].append(
                        {
                            "text": state.get("text", ""),
                            "speech_rate": state.get("prosody", {}).get("speech_rate", 0),
                        }
                    )
                    participant_data[speaker]["cognitive_states"].append(
                        state.get("cognitive_state", {})
                    )

                for event in result.get("base_analysis", {}).get("events", []):
                    speaker = event.get("speaker")
                    if speaker in participant_data:
                        participant_data[speaker]["events"].append(event)

            for participant_id, data in participant_data.items():
                profile_service.update_profile_from_session(
                    participant_id=participant_id,
                    session_data=data,
                )
                updated_profiles[participant_id] = profile_service.get_participant_insights(
                    participant_id
                )

            logger.info(
                "Updated %d participant profiles for session %s",
                len(updated_profiles),
                session_id,
            )

            return {
                "session_id": session_id,
                "updated_count": len(updated_profiles),
                "profiles": updated_profiles,
            }

        except Exception as e:  # pragma: no cover - defensive
            logger.error("Error updating participant profiles: %s", e, exc_info=True)
            return {
                "session_id": session_id,
                "error": str(e),
            }

    def get_realtime_recommendations(
        self,
        session_id: str,
        current_segment_result: Dict[str, Any],
        participant_states: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """リアルタイムで推奨アクションを取得."""
        recommendations: List[Dict[str, Any]] = []

        confused_participants = [
            s.get("speaker")
            for s in participant_states
            if s.get("cognitive_state", {}).get("understanding_level", 1.0) < 0.4
        ]
        if confused_participants:
            recommendations.append(
                {
                    "type": "support_needed",
                    "priority": "high",
                    "participants": confused_participants,
                    "action": "理解度が低い参加者がいます。説明を補足するか確認してください。",
                }
            )

        hesitant_participants = [
            s.get("speaker")
            for s in participant_states
            if s.get("cognitive_state", {}).get("hesitation_level", 0) > 0.6
        ]
        if hesitant_participants:
            recommendations.append(
                {
                    "type": "encouragement",
                    "priority": "medium",
                    "participants": hesitant_participants,
                    "action": "迷っている参加者がいます。意見を引き出す質問をしてみましょう。",
                }
            )

        if current_segment_result.get("T", 0) > 0.7:
            recommendations.append(
                {
                    "type": "break_stagnation",
                    "priority": "high",
                    "action": "議論が停滞しています。視点を変えるか、休憩を取りましょう。",
                }
            )

        unanswered = current_segment_result.get("Q", 0) - current_segment_result.get("A", 0)
        if unanswered > 0:
            recommendations.append(
                {
                    "type": "answer_questions",
                    "priority": "medium",
                    "action": f"{unanswered}件の質問に回答がありません。",
                }
            )

        return {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "recommendations": recommendations,
            "count": len(recommendations),
        }

    def _generate_summary(
        self,
        base_result: Dict[str, Any],
        participant_states: List[Dict[str, Any]],
        intervention_check: Dict[str, Any],
    ) -> Dict[str, Any]:
        """分析結果のサマリーを生成."""
        cognitive_stats = {
            "avg_confidence": 0.0,
            "avg_understanding": 0.0,
            "avg_hesitation": 0.0,
        }

        if participant_states:
            confidences = [
                s.get("cognitive_state", {}).get("confidence_level", 0.5) for s in participant_states
            ]
            understandings = [
                s.get("cognitive_state", {}).get("understanding_level", 0.5) for s in participant_states
            ]
            hesitations = [
                s.get("cognitive_state", {}).get("hesitation_level", 0.5) for s in participant_states
            ]
            cognitive_stats = {
                "avg_confidence": sum(confidences) / len(confidences),
                "avg_understanding": sum(understandings) / len(understandings),
                "avg_hesitation": sum(hesitations) / len(hesitations),
            }

        return {
            "discussion_health": self._calculate_health_score(base_result, cognitive_stats),
            "cognitive_stats": cognitive_stats,
            "key_metrics": {
                "confusion": base_result.get("M", 0),
                "stagnation": base_result.get("T", 0),
                "understanding": base_result.get("L", 0),
            },
            "needs_attention": intervention_check.get("needs_intervention", False),
        }

    def _calculate_health_score(
        self,
        base_result: Dict[str, Any],
        cognitive_stats: Dict[str, float],
    ) -> float:
        """議論の健全性スコアを計算（0-1）."""
        confusion_score = 1.0 - min(base_result.get("M", 0), 1.0)
        stagnation_score = 1.0 - min(base_result.get("T", 0), 1.0)
        understanding_score = cognitive_stats.get("avg_understanding", 0.5)
        confidence_score = cognitive_stats.get("avg_confidence", 0.5)

        health_score = (
            confusion_score * 0.3
            + stagnation_score * 0.3
            + understanding_score * 0.2
            + confidence_score * 0.2
        )

        return round(health_score, 3)


integrated_service = IntegratedAnalysisService()
