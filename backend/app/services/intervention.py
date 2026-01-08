"""介入・助言生成サービス - 議論の状態に応じた支援メッセージを生成."""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

from app.services.llm import LLMService

logger = logging.getLogger(__name__)


class InterventionType(str, Enum):
    """介入タイプ."""

    CLARIFICATION = "clarification"  # 明確化要求
    SUMMARY = "summary"  # 要点整理
    PERSPECTIVE = "perspective"  # 新しい視点の提示
    ENCOURAGEMENT = "encouragement"  # 発言促進
    CAUTION = "caution"  # 注意喚起
    NONE = "none"  # 介入不要


class InterventionService:
    """議論状況に応じた介入・助言を生成するサービス."""

    def __init__(self):
        """Initialize intervention service."""
        self.llm_service = LLMService()

        # 介入閾値の設定
        self.confusion_threshold = 0.6  # 混乱度がこれを超えたら介入
        self.stagnation_threshold = 0.7  # 停滞度がこれを超えたら介入
        self.low_understanding_threshold = 0.4  # 理解度がこれを下回ったら介入

    def detect_intervention_need(
        self,
        segment_result: Dict[str, Any],
        participant_states: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        介入が必要かを判定.

        Args:
            segment_result: セグメント分析結果
            participant_states: 参加者の認知状態リスト

        Returns:
            介入必要性の判定結果
        """
        needs_intervention = False
        intervention_type = InterventionType.NONE
        priority = 0.0
        reason = ""

        # 1. 混乱度チェック（Mメトリクス）
        confusion = segment_result.get("M", 0.0)
        if confusion > self.confusion_threshold:
            needs_intervention = True
            intervention_type = InterventionType.CLARIFICATION
            priority = max(priority, confusion)
            reason = f"高い混乱度が検出されました (M={confusion:.2f})"

        # 2. 停滞度チェック（Tメトリクス）
        stagnation = segment_result.get("T", 0.0)
        if stagnation > self.stagnation_threshold:
            needs_intervention = True
            intervention_type = InterventionType.PERSPECTIVE
            priority = max(priority, stagnation)
            reason = f"議論が停滞しています (T={stagnation:.2f})"

        # 3. 参加者の理解不足チェック
        low_understanding_count = 0
        for state in participant_states:
            if state.get("understanding_level", 1.0) < self.low_understanding_threshold:
                low_understanding_count += 1

        if low_understanding_count > 0:
            needs_intervention = True
            if intervention_type == InterventionType.NONE:
                intervention_type = InterventionType.SUMMARY
            priority = max(priority, 0.7)
            reason = f"{low_understanding_count}名の参加者が理解に困難を示しています"

        # 4. 質問への回答不足チェック
        Q_count = segment_result.get("Q", 0)
        A_count = segment_result.get("A", 0)
        if Q_count > 0 and A_count == 0:
            needs_intervention = True
            intervention_type = InterventionType.ENCOURAGEMENT
            priority = max(priority, 0.6)
            reason = f"{Q_count}件の質問に回答がありません"

        # 5. 発言の極端な偏りチェック
        utterances = segment_result.get("utterances", [])
        if len(utterances) > 0:
            speakers = [u.get("speaker") for u in utterances]
            dominant_speaker_ratio = speakers.count(max(set(speakers), key=speakers.count)) / len(
                speakers
            )
            if dominant_speaker_ratio > 0.7 and len(set(speakers)) > 1:
                needs_intervention = True
                intervention_type = InterventionType.ENCOURAGEMENT
                priority = max(priority, 0.5)
                reason = "発言が一部の参加者に偏っています"

        return {
            "needs_intervention": needs_intervention,
            "intervention_type": intervention_type.value,
            "priority": priority,
            "reason": reason,
        }

    def generate_intervention_message(
        self,
        intervention_type: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        介入メッセージを生成.

        Args:
            intervention_type: 介入タイプ
            context: コンテキスト情報

        Returns:
            生成された介入メッセージ
        """
        try:
            itype = InterventionType(intervention_type)

            if itype == InterventionType.CLARIFICATION:
                return self._generate_clarification_message(context)
            elif itype == InterventionType.SUMMARY:
                return self._generate_summary_message(context)
            elif itype == InterventionType.PERSPECTIVE:
                return self._generate_perspective_message(context)
            elif itype == InterventionType.ENCOURAGEMENT:
                return self._generate_encouragement_message(context)
            elif itype == InterventionType.CAUTION:
                return self._generate_caution_message(context)
            else:
                return None

        except Exception as e:
            logger.error(f"Error generating intervention message: {e}")
            return None

    def _generate_clarification_message(self, context: Dict[str, Any]) -> str:
        """明確化を促すメッセージ."""
        transcript = context.get("transcript", "")
        issues = context.get("issues", [])

        if self.llm_service.client and len(transcript) > 50:
            # LLMを使用して詳細な分析
            prompt = f"""
以下の議論で混乱が生じています。何が不明確なのか、どの点を整理すべきかを提案してください。

議論内容:
{transcript[:500]}

提案形式:
- 「〜の定義が曖昧です。具体的に説明してください」
- 「〜と〜の関係が不明確です。整理しましょう」
"""
            try:
                response = self.llm_service.client.chat.completions.create(
                    model=self.llm_service.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=200,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"LLM call failed: {e}")

        # フォールバック: 定型メッセージ
        return "💡 議論が複雑になっています。現在の論点を整理し、共通理解を確認しましょう。"

    def _generate_summary_message(self, context: Dict[str, Any]) -> str:
        """要点整理メッセージ."""
        transcript = context.get("transcript", "")

        if self.llm_service.client and len(transcript) > 50:
            prompt = f"""
以下の議論を簡潔に要約し、重要なポイントを3点以内で箇条書きしてください。

議論内容:
{transcript[:500]}

形式:
📝 現在の議論のポイント:
• [ポイント1]
• [ポイント2]
• [ポイント3]
"""
            try:
                response = self.llm_service.client.chat.completions.create(
                    model=self.llm_service.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=300,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"LLM call failed: {e}")

        return "📝 ここまでの議論を整理しましょう。主要なポイントを確認してください。"

    def _generate_perspective_message(self, context: Dict[str, Any]) -> str:
        """新しい視点提示メッセージ."""
        transcript = context.get("transcript", "")

        if self.llm_service.client and len(transcript) > 50:
            prompt = f"""
以下の議論が停滞しています。新しい視点や問いかけを提案してください。

議論内容:
{transcript[:500]}

形式:
🤔 こんな視点はどうでしょうか？
[具体的な問いかけや視点]
"""
            try:
                response = self.llm_service.client.chat.completions.create(
                    model=self.llm_service.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=200,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"LLM call failed: {e}")

        return "🤔 視点を変えてみましょう。別の角度から考えてみませんか？"

    def _generate_encouragement_message(self, context: Dict[str, Any]) -> str:
        """発言促進メッセージ."""
        Q_count = context.get("Q_count", 0)
        silent_participants = context.get("silent_participants", [])

        if Q_count > 0:
            return f"❓ {Q_count}件の質問に回答がありません。誰か答えられる方はいませんか？"

        if silent_participants:
            names = ", ".join(silent_participants[:2])
            return f"💬 {names}さんの意見も聞いてみたいです。いかがでしょうか？"

        return "💬 他の方の意見も聞いてみましょう。"

    def _generate_caution_message(self, context: Dict[str, Any]) -> str:
        """注意喚起メッセージ."""
        issue = context.get("issue", "不明な問題")
        return f"⚠️ 注意: {issue}。議論の進め方を見直しましょう。"


# Singleton instance
intervention_service = InterventionService()
