"""参加者特性モデリングサービス - 複数回の議論から個人特性を抽出."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import statistics

logger = logging.getLogger(__name__)


@dataclass
class ParticipantProfile:
    """参加者の特性プロファイル."""

    participant_id: str
    name: str

    # 発言傾向
    avg_utterance_length: float = 0.0  # 平均発言文字数
    avg_speech_rate: float = 0.0  # 平均発話速度
    utterance_count: int = 0  # 総発言回数

    # 認知傾向
    avg_confidence: float = 0.5  # 平均確信度
    avg_understanding: float = 0.5  # 平均理解度
    avg_hesitation: float = 0.5  # 平均迷いレベル

    # つまずきやすいトピック
    confused_topics: List[str] = field(default_factory=list)
    confident_topics: List[str] = field(default_factory=list)

    # 議論への貢献スタイル
    question_ratio: float = 0.0  # 質問の比率
    answer_ratio: float = 0.0  # 回答の比率
    suggestion_ratio: float = 0.0  # 提案の比率

    # 履歴メタデータ
    total_sessions: int = 0  # 参加セッション数
    last_updated: datetime = field(default_factory=datetime.utcnow)


class ParticipantProfileService:
    """参加者の特性を複数セッションから学習・管理するサービス."""

    def __init__(self):
        """Initialize participant profile service."""
        self.profiles: Dict[str, ParticipantProfile] = {}

    def get_or_create_profile(
        self,
        participant_id: str,
        name: str,
    ) -> ParticipantProfile:
        """
        参加者プロファイルを取得または新規作成.

        Args:
            participant_id: 参加者ID
            name: 参加者名

        Returns:
            ParticipantProfile
        """
        if participant_id not in self.profiles:
            self.profiles[participant_id] = ParticipantProfile(
                participant_id=participant_id,
                name=name,
            )
        return self.profiles[participant_id]

    def update_profile_from_session(
        self,
        participant_id: str,
        session_data: Dict[str, Any],
    ) -> ParticipantProfile:
        """
        セッションデータからプロファイルを更新.

        Args:
            participant_id: 参加者ID
            session_data: セッション分析結果

        Returns:
            更新されたParticipantProfile
        """
        profile = self.get_or_create_profile(
            participant_id,
            session_data.get("name", "Unknown"),
        )

        utterances = session_data.get("utterances", [])
        cognitive_states = session_data.get("cognitive_states", [])

        if not utterances:
            return profile

        # 発言傾向の更新
        utterance_lengths = [len(u.get("text", "")) for u in utterances]
        speech_rates = [u.get("speech_rate", 0) for u in utterances if "speech_rate" in u]

        # 移動平均的に更新
        alpha = 0.3  # 新しいデータの重み
        profile.avg_utterance_length = (
            alpha * statistics.mean(utterance_lengths)
            + (1 - alpha) * profile.avg_utterance_length
        )

        if speech_rates:
            profile.avg_speech_rate = (
                alpha * statistics.mean(speech_rates) + (1 - alpha) * profile.avg_speech_rate
            )

        profile.utterance_count += len(utterances)

        # 認知傾向の更新
        if cognitive_states:
            confidences = [cs.get("confidence_level", 0.5) for cs in cognitive_states]
            understandings = [cs.get("understanding_level", 0.5) for cs in cognitive_states]
            hesitations = [cs.get("hesitation_level", 0.5) for cs in cognitive_states]

            profile.avg_confidence = (
                alpha * statistics.mean(confidences) + (1 - alpha) * profile.avg_confidence
            )
            profile.avg_understanding = (
                alpha * statistics.mean(understandings) + (1 - alpha) * profile.avg_understanding
            )
            profile.avg_hesitation = (
                alpha * statistics.mean(hesitations) + (1 - alpha) * profile.avg_hesitation
            )

        # つまずきやすいトピックの抽出
        for state in cognitive_states:
            if state.get("understanding_level", 1.0) < 0.4:
                topic = state.get("topic", "unknown")
                if topic not in profile.confused_topics:
                    profile.confused_topics.append(topic)

            if state.get("confidence_level", 0.0) > 0.7:
                topic = state.get("topic", "unknown")
                if topic not in profile.confident_topics:
                    profile.confident_topics.append(topic)

        # 貢献スタイルの更新
        events = session_data.get("events", [])
        if events:
            q_count = sum(1 for e in events if e.get("type") == "Q")
            a_count = sum(1 for e in events if e.get("type") == "A")
            s_count = sum(1 for e in events if e.get("type") == "S")
            total = len(events)

            if total > 0:
                profile.question_ratio = q_count / total
                profile.answer_ratio = a_count / total
                profile.suggestion_ratio = s_count / total

        # メタデータ更新
        profile.total_sessions += 1
        profile.last_updated = datetime.utcnow()

        logger.info(f"Updated profile for participant {participant_id}")
        return profile

    def predict_difficulty(
        self,
        participant_id: str,
        topic: str,
    ) -> Dict[str, Any]:
        """
        特定のトピックでの理解困難度を予測.

        Args:
            participant_id: 参加者ID
            topic: トピック

        Returns:
            予測結果
        """
        if participant_id not in self.profiles:
            return {
                "difficulty_score": 0.5,
                "confidence": 0.0,
                "reason": "No profile data available",
            }

        profile = self.profiles[participant_id]

        # トピックが過去に混乱したものか確認
        if topic in profile.confused_topics:
            return {
                "difficulty_score": 0.8,
                "confidence": 0.9,
                "reason": f"Previously struggled with topic: {topic}",
            }

        # 参加者の平均理解度から予測
        difficulty_score = 1.0 - profile.avg_understanding

        return {
            "difficulty_score": difficulty_score,
            "confidence": min(profile.total_sessions / 5.0, 1.0),  # セッション数に応じた信頼度
            "reason": f"Based on average understanding level: {profile.avg_understanding:.2f}",
        }

    def get_participant_insights(
        self,
        participant_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        参加者の特性インサイトを取得.

        Args:
            participant_id: 参加者ID

        Returns:
            インサイト情報
        """
        if participant_id not in self.profiles:
            return None

        profile = self.profiles[participant_id]

        # 発言スタイルの判定
        if profile.avg_utterance_length > 150:
            speech_style = "詳細な説明型"
        elif profile.avg_utterance_length < 50:
            speech_style = "簡潔型"
        else:
            speech_style = "バランス型"

        # 貢献スタイルの判定
        if profile.question_ratio > 0.4:
            contribution_style = "質問主導型"
        elif profile.answer_ratio > 0.4:
            contribution_style = "回答提供型"
        elif profile.suggestion_ratio > 0.3:
            contribution_style = "提案型"
        else:
            contribution_style = "バランス型"

        # 認知的特徴
        cognitive_tendency = []
        if profile.avg_confidence > 0.7:
            cognitive_tendency.append("自信を持って発言")
        if profile.avg_hesitation > 0.6:
            cognitive_tendency.append("慎重に考えながら発言")
        if profile.avg_understanding < 0.5:
            cognitive_tendency.append("理解に時間がかかる傾向")

        return {
            "participant_id": participant_id,
            "name": profile.name,
            "speech_style": speech_style,
            "contribution_style": contribution_style,
            "cognitive_tendency": cognitive_tendency,
            "confused_topics": profile.confused_topics,
            "confident_topics": profile.confident_topics,
            "total_sessions": profile.total_sessions,
            "avg_metrics": {
                "confidence": profile.avg_confidence,
                "understanding": profile.avg_understanding,
                "hesitation": profile.avg_hesitation,
            },
        }

    def export_profiles(self) -> Dict[str, Dict[str, Any]]:
        """全プロファイルをエクスポート."""
        return {
            pid: {
                "name": p.name,
                "avg_utterance_length": p.avg_utterance_length,
                "avg_speech_rate": p.avg_speech_rate,
                "utterance_count": p.utterance_count,
                "avg_confidence": p.avg_confidence,
                "avg_understanding": p.avg_understanding,
                "avg_hesitation": p.avg_hesitation,
                "confused_topics": p.confused_topics,
                "confident_topics": p.confident_topics,
                "question_ratio": p.question_ratio,
                "answer_ratio": p.answer_ratio,
                "suggestion_ratio": p.suggestion_ratio,
                "total_sessions": p.total_sessions,
            }
            for pid, p in self.profiles.items()
        }


# Singleton instance
profile_service = ParticipantProfileService()
