"""韻律情報分析サービス - 声の揺れや発話速度から認知状態を推定."""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


@dataclass
class ProsodyFeatures:
    """韻律特徴量."""

    speech_rate: float  # 発話速度 (mora/sec)
    pause_ratio: float  # ポーズ比率
    hesitation_count: int  # 言い淀み回数
    pitch_variance: float  # ピッチ分散（声の揺れ）
    volume_variance: float  # 音量分散
    ambiguous_ending_count: int  # 語尾の曖昧化回数


@dataclass
class CognitiveState:
    """認知状態推定結果."""

    confidence_level: float  # 確信度 (0-1)
    understanding_level: float  # 理解度 (0-1)
    hesitation_level: float  # 迷いレベル (0-1)
    engagement_level: float  # 議論への参加度 (0-1)
    state_label: str  # "confident", "hesitant", "confused", "engaged"
    evidence: Dict[str, Any]  # 推定根拠


class ProsodyAnalysisService:
    """韻律情報から参加者の認知状態を推定するサービス."""

    def __init__(self):
        """Initialize prosody analysis service."""
        # 閾値の設定（実験的に調整が必要）
        self.slow_speech_threshold = 3.0  # mora/sec
        self.high_pause_threshold = 0.3  # 30%以上のポーズ
        self.high_hesitation_threshold = 3  # 発言あたり3回以上の言い淀み

    def extract_prosody_features(
        self,
        text: str,
        duration_sec: float,
        audio_features: Optional[Dict[str, Any]] = None,
    ) -> ProsodyFeatures:
        """
        発言から韻律特徴量を抽出.

        Args:
            text: 発言テキスト
            duration_sec: 発言時間（秒）
            audio_features: 音声特徴（pitch, volume等）

        Returns:
            ProsodyFeatures: 抽出された韻律特徴
        """
        # 発話速度の推定（文字数から簡易的に算出）
        # 実際はモーラ数を正確に計算すべき
        char_count = len(text.replace(" ", ""))
        speech_rate = char_count / duration_sec if duration_sec > 0 else 0

        # 言い淀み検出（「えー」「あの」「その」等）
        hesitation_markers = ["えー", "あー", "あの", "その", "まあ", "なんか"]
        hesitation_count = sum(text.count(marker) for marker in hesitation_markers)

        # 語尾の曖昧化検出（「〜かな」「〜みたいな」「〜って感じ」等）
        ambiguous_endings = ["かな", "みたいな", "って感じ", "かも", "だろうか"]
        ambiguous_ending_count = sum(text.count(ending) for ending in ambiguous_endings)

        # ポーズ比率の推定（句読点や「…」から）
        pause_indicators = text.count("、") + text.count("。") + text.count("…")
        pause_ratio = min(pause_indicators / max(char_count / 10, 1), 1.0)

        # 音声特徴が提供されている場合は使用
        pitch_variance = 0.0
        volume_variance = 0.0
        if audio_features:
            pitch_variance = audio_features.get("pitch_variance", 0.0)
            volume_variance = audio_features.get("volume_variance", 0.0)

        return ProsodyFeatures(
            speech_rate=speech_rate,
            pause_ratio=pause_ratio,
            hesitation_count=hesitation_count,
            pitch_variance=pitch_variance,
            volume_variance=volume_variance,
            ambiguous_ending_count=ambiguous_ending_count,
        )

    def estimate_cognitive_state(
        self,
        prosody: ProsodyFeatures,
        text: str,
    ) -> CognitiveState:
        """
        韻律特徴から認知状態を推定.

        Args:
            prosody: 韻律特徴量
            text: 発言テキスト

        Returns:
            CognitiveState: 推定された認知状態
        """
        evidence = {}

        # 1. 迷いレベルの推定
        hesitation_score = 0.0

        # 発話速度が遅い → 迷っている
        if prosody.speech_rate < self.slow_speech_threshold:
            hesitation_score += 0.3
            evidence["slow_speech"] = True

        # ポーズが多い → 考えながら話している
        if prosody.pause_ratio > self.high_pause_threshold:
            hesitation_score += 0.2
            evidence["high_pause"] = True

        # 言い淀みが多い → 迷っている
        if prosody.hesitation_count > self.high_hesitation_threshold:
            hesitation_score += 0.3
            evidence["high_hesitation"] = prosody.hesitation_count

        # 語尾が曖昧 → 確信がない
        if prosody.ambiguous_ending_count > 1:
            hesitation_score += 0.2
            evidence["ambiguous_endings"] = prosody.ambiguous_ending_count

        hesitation_level = min(hesitation_score, 1.0)

        # 2. 確信度の推定（迷いレベルの逆）
        confidence_level = 1.0 - hesitation_level

        # 3. 理解度の推定
        understanding_score = 0.5  # 基準値

        # 具体的な説明や例示がある → 理解している
        explanation_markers = ["なぜなら", "例えば", "つまり", "具体的には"]
        if any(marker in text for marker in explanation_markers):
            understanding_score += 0.3
            evidence["has_explanation"] = True

        # 質問が多い → 理解が不足
        question_markers = ["？", "ですか", "でしょうか", "わからない"]
        if any(marker in text for marker in question_markers):
            understanding_score -= 0.3
            evidence["has_questions"] = True

        understanding_level = max(0.0, min(understanding_score, 1.0))

        # 4. 参加度の推定
        engagement_score = 0.5
        text_length = len(text.replace(" ", ""))

        # 発言が長い → 積極的
        if text_length > 100:
            engagement_score += 0.3
            evidence["long_utterance"] = True

        # 発言が短すぎる → 消極的
        if text_length < 20:
            engagement_score -= 0.3
            evidence["short_utterance"] = True

        engagement_level = max(0.0, min(engagement_score, 1.0))

        # 状態ラベルの決定
        if confidence_level > 0.7 and understanding_level > 0.7:
            state_label = "confident"
        elif hesitation_level > 0.6:
            state_label = "hesitant"
        elif understanding_level < 0.4:
            state_label = "confused"
        elif engagement_level > 0.7:
            state_label = "engaged"
        else:
            state_label = "neutral"

        return CognitiveState(
            confidence_level=confidence_level,
            understanding_level=understanding_level,
            hesitation_level=hesitation_level,
            engagement_level=engagement_level,
            state_label=state_label,
            evidence=evidence,
        )

    def analyze_utterance(
        self,
        text: str,
        duration_sec: float,
        speaker: str,
        audio_features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        発言を分析して認知状態を推定.

        Args:
            text: 発言テキスト
            duration_sec: 発言時間
            speaker: 話者ID
            audio_features: 音声特徴（オプション）

        Returns:
            分析結果
        """
        try:
            # 韻律特徴抽出
            prosody = self.extract_prosody_features(text, duration_sec, audio_features)

            # 認知状態推定
            cognitive_state = self.estimate_cognitive_state(prosody, text)

            return {
                "speaker": speaker,
                "prosody_features": {
                    "speech_rate": prosody.speech_rate,
                    "pause_ratio": prosody.pause_ratio,
                    "hesitation_count": prosody.hesitation_count,
                    "pitch_variance": prosody.pitch_variance,
                    "volume_variance": prosody.volume_variance,
                    "ambiguous_ending_count": prosody.ambiguous_ending_count,
                },
                "cognitive_state": {
                    "confidence_level": cognitive_state.confidence_level,
                    "understanding_level": cognitive_state.understanding_level,
                    "hesitation_level": cognitive_state.hesitation_level,
                    "engagement_level": cognitive_state.engagement_level,
                    "state_label": cognitive_state.state_label,
                    "evidence": cognitive_state.evidence,
                },
            }

        except Exception as e:
            logger.error(f"Error in analyze_utterance: {e}")
            return {
                "speaker": speaker,
                "error": str(e),
            }


# Singleton instance
prosody_service = ProsodyAnalysisService()
