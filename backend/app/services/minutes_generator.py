"""議事録生成サービス - 統合分析結果をMarkdown形式で出力."""

from datetime import datetime
from typing import Any, Dict, List


class MinutesGenerator:
    """統合分析結果から議事録を生成するサービス."""

    def generate_markdown(
        self,
        session_id: str,
        session_title: str,
        integrated_result: Dict[str, Any],
    ) -> str:
        """統合分析結果からMarkdown議事録を生成."""
        lines: List[str] = []

        # タイトル
        lines.append(f"# 議事録: {session_title}")
        lines.append("")
        lines.append(f"**セッションID**: `{session_id}`  ")
        lines.append(f"**実施日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 健全度サマリ
        summary = integrated_result.get("summary", {})
        health = summary.get("discussion_health", 0)
        health_pct = int(health * 100)
        lines.append("## 📊 議論の健全度")
        lines.append("")
        lines.append(f"**総合スコア**: {health_pct}% {'🟢' if health_pct >= 70 else '🟡' if health_pct >= 50 else '🔴'}")
        lines.append("")

        key_metrics = summary.get("key_metrics", {})
        lines.append("| 指標 | 値 |")
        lines.append("|------|-----|")
        lines.append(f"| 混乱度 | {int(key_metrics.get('confusion', 0) * 100)}% |")
        lines.append(f"| 停滞度 | {int(key_metrics.get('stagnation', 0) * 100)}% |")
        lines.append(f"| 理解度 | {int(key_metrics.get('understanding', 0) * 100)}% |")
        lines.append("")

        # 介入提案
        intervention = integrated_result.get("intervention", {})
        if intervention.get("needed"):
            lines.append("## 🚨 ファシリテーション支援")
            lines.append("")
            lines.append(f"**種別**: {intervention.get('type', '-')}")
            lines.append(f"**優先度**: {intervention.get('priority', '-')}")
            lines.append(f"**理由**: {intervention.get('reason', '-')}")
            lines.append("")
            if intervention.get("message"):
                lines.append(f"> {intervention.get('message')}")
                lines.append("")

        # 発言ログ
        utterances = integrated_result.get("utterances", [])
        lines.append("## 💬 発言ログ")
        lines.append("")

        for idx, utt in enumerate(utterances, 1):
            speaker = utt.get("speaker", "不明")
            text = utt.get("text", "")
            lines.append(f"### 発言{idx}: {speaker}")
            lines.append("")
            lines.append(f"> {text}")
            lines.append("")

        # 参加者ごとの理解度推移
        participant_states = integrated_result.get("participant_states", [])
        if participant_states:
            lines.append("## 📈 参加者の理解度推移")
            lines.append("")

            # 話者ごとにグループ化
            speaker_understanding: Dict[str, List[float]] = {}
            for state in participant_states:
                speaker = state.get("speaker", "不明")
                understanding = state.get("cognitive_state", {}).get("understanding_level", 0.5)
                if speaker not in speaker_understanding:
                    speaker_understanding[speaker] = []
                speaker_understanding[speaker].append(understanding)

            for speaker, values in speaker_understanding.items():
                avg = sum(values) / len(values) if values else 0
                trend = "📈" if len(values) > 1 and values[-1] > values[0] else "📉" if len(values) > 1 and values[-1] < values[0] else "➡️"
                lines.append(f"- **{speaker}**: 平均 {int(avg * 100)}% {trend}")

            lines.append("")

        # 理解のズレ検出
        lines.append("## ⚠️ 理解のズレ検出")
        lines.append("")

        misunderstandings = []
        for idx, utt in enumerate(utterances):
            state = participant_states[idx] if idx < len(participant_states) else None
            if state:
                understanding = state.get("cognitive_state", {}).get("understanding_level", 1.0)
                hesitation = state.get("cognitive_state", {}).get("hesitation_level", 0)
                if understanding < 0.5 or hesitation > 0.6:
                    misunderstandings.append({
                        "index": idx + 1,
                        "speaker": utt.get("speaker", "不明"),
                        "text": utt.get("text", ""),
                        "understanding": understanding,
                    })

        if misunderstandings:
            for mis in misunderstandings:
                lines.append(f"### 発言{mis['index']}: {mis['speaker']}")
                lines.append("")
                lines.append(f"**理解度**: {int(mis['understanding'] * 100)}% 🔴")
                lines.append("")
                lines.append(f"> {mis['text']}")
                lines.append("")
        else:
            lines.append("理解のズレは検出されませんでした。 ✅")
            lines.append("")

        # フッター
        lines.append("---")
        lines.append("")
        lines.append("*この議事録はEchoMind Voice Discussion Systemにより自動生成されました。*")
        lines.append("")

        return "\n".join(lines)


minutes_generator = MinutesGenerator()
