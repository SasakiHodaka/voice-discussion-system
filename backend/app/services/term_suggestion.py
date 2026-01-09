"""Term suggestion service - extract key terms from discussion and provide definitions."""

import logging
import re
from typing import Dict, List, Any, Optional
from collections import Counter

from app.services.llm import LLMService

logger = logging.getLogger(__name__)


class TermSuggestionService:
    """議論からキー用語を抽出し、定義を提供するサービス."""

    def __init__(self):
        """Initialize term suggestion service."""
        self.llm_service = LLMService()
        # 一般的なストップワード
        self.stop_words = {
            "は", "が", "を", "に", "へ", "で", "から", "まで", "など",
            "そして", "しかし", "ただし", "また", "また", "つまり", "例えば",
            "ある", "いる", "する", "なる", "いく", "くる", "できる",
            "ある", "です", "ます", "ません", "ました", "ましょう",
            "思う", "考える", "言う", "見る", "聞く", "知る",
            "a", "an", "the", "is", "are", "was", "were", "be",
            "and", "or", "but", "in", "on", "at", "to", "of", "for"
        }

    def extract_terms_from_transcript(
        self,
        transcript: str,
        top_n: int = 5,
    ) -> List[Dict[str, str]]:
        """
        議論のテキストから重要な用語を抽出.

        Args:
            transcript: 議論の全テキスト
            top_n: 抽出する用語の最大数

        Returns:
            用語と説明のリスト
        """
        if not transcript or len(transcript) < 50:
            return []

        try:
            # 名詞的な単語を抽出（簡易実装）
            # 日本語の場合、カタカナ語やサ行変可能名詞などを検出
            terms = self._extract_key_terms_from_japanese(transcript, top_n)

            # 各用語に対して説明を生成
            result = []
            for term in terms:
                definition = self._generate_definition(term, transcript)
                if definition:
                    result.append({
                        "term": term,
                        "definition": definition,
                    })

            return result

        except Exception as e:
            logger.error(f"Error extracting terms: {e}")
            return []

    def _extract_key_terms_from_japanese(
        self,
        text: str,
        top_n: int,
    ) -> List[str]:
        """日本語テキストからキー用語を抽出（簡易版）."""
        # カタカナ語を優先的に抽出（外来語は重要な概念を表すことが多い）
        katakana_pattern = r"[ァ-ヴー]+"
        katakana_terms = re.findall(katakana_pattern, text)

        # 長めの複合名詞も抽出
        complex_pattern = r"[ぁ-んァ-ヴー一-龥々〆〤]{3,}"
        complex_terms = re.findall(complex_pattern, text)

        # 出現頻度でカウント
        all_terms = katakana_terms + complex_terms
        term_counter = Counter(all_terms)

        # ストップワードを除外
        filtered = [
            term for term, _ in term_counter.most_common(top_n * 3)
            if term not in self.stop_words and len(term) > 1
        ]

        return filtered[:top_n]

    def _generate_definition(
        self,
        term: str,
        context: str,
    ) -> Optional[str]:
        """用語の定義を生成."""
        try:
            # 議論の文脈から用語の使用例を抽出
            # 簡易版：該当する文を探す
            sentences = re.split(r'[。！？\n]', context)
            relevant_sentences = [
                s for s in sentences if term in s
            ][:2]

            if not relevant_sentences:
                return None

            # LLM を使用した定義生成
            if self.llm_service.client:
                prompt = f"""
以下の用語について、この議論の文脈での定義を簡潔に説明してください（1-2文）。

用語: {term}

文脈:
{' '.join(relevant_sentences)}

定義:"""
                try:
                    response = self.llm_service.client.chat.completions.create(
                        model=self.llm_service.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.5,
                        max_tokens=150,
                    )
                    definition = response.choices[0].message.content.strip()
                    return definition if definition else None
                except Exception as e:
                    logger.error(f"LLM definition generation failed: {e}")

            # フォールバック：文脈から簡単な説明を構成
            if relevant_sentences:
                return f"この議論で「{term}」という用語が使用されています。"

            return None

        except Exception as e:
            logger.error(f"Error generating definition: {e}")
            return None

    def suggest_terms_for_session(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        セッションの会話から用語提案を生成.

        Args:
            session_id: セッション ID
            messages: メッセージリスト

        Returns:
            提案された用語と定義
        """
        if not messages or len(messages) == 0:
            return {
                "session_id": session_id,
                "terms": [],
                "count": 0,
            }

        # テキストを結合
        transcript = " ".join([msg.get("text", "") for msg in messages])

        terms = self.extract_terms_from_transcript(transcript, top_n=5)

        return {
            "session_id": session_id,
            "terms": terms,
            "count": len(terms),
        }


# Singleton instance
term_suggestion_service = TermSuggestionService()
