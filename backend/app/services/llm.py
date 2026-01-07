"""LLM service for calling OpenAI and other models."""

import json
import logging
from typing import Dict, Any, Optional

from app.config import settings
from app.core.prompts import get_prompt_manager

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM interactions."""

    def __init__(self):
        """Initialize LLM service."""
        self.provider = settings.llm.provider
        self.api_key = settings.llm.api_key
        self.model = settings.llm.model
        self.temperature = settings.llm.temperature
        self.max_tokens = settings.llm.max_tokens
        self.prompt_manager = get_prompt_manager()
        self.client = self._init_client()

    def _init_client(self):
        """Initialize LLM client."""
        if self.provider == "openai":
            try:
                from openai import OpenAI

                return OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("OpenAI client not available")
                return None
        return None

    def classify_issues(
        self,
        transcript: str,
        segment_id: int,
        segment_duration: float,
        participant_count: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Classify and map issues from transcript."""
        if not self.client:
            logger.warning("LLM client not initialized")
            return None

        try:
            # Render prompt with context
            prompt_text = self.prompt_manager.render_prompt(
                "issue_classification",
                {
                    "transcript": transcript,
                    "segment_duration": int(segment_duration),
                    "participant_count": participant_count,
                    "text_length": len(transcript),
                },
            )

            if not prompt_text:
                logger.warning("Could not render issue_classification prompt")
                return None

            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse JSON response
            content = response.choices[0].message.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            else:
                logger.warning("Could not find JSON in LLM response")
                return None

        except Exception as e:
            logger.error(f"Error in classify_issues: {e}")
            return None

    def generate_summary(
        self,
        transcript: str,
        issues: Optional[Dict[str, Any]] = None,
        segment_id: int = 0,
        start_sec: float = 0.0,
        end_sec: float = 20.0,
        participant_count: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Generate summary and action items."""
        if not self.client:
            logger.warning("LLM client not initialized")
            return None

        try:
            prompt_text = self.prompt_manager.render_prompt(
                "summary_generation",
                {
                    "transcript": transcript,
                    "segment_id": segment_id,
                    "start_sec": int(start_sec),
                    "end_sec": int(end_sec),
                    "participant_count": participant_count,
                    "issue_count": len(issues.get("issues", [])) if issues else 0,
                    "issues_json": json.dumps(issues, ensure_ascii=False, indent=2)
                    if issues
                    else "[]",
                },
            )

            if not prompt_text:
                return None

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)

        except Exception as e:
            logger.error(f"Error in generate_summary: {e}")
            return None

    def assess_quality(
        self,
        transcript: str,
        segment_id: int,
        q_count: int = 0,
        a_count: int = 0,
        uq_count: int = 0,
        r_count: int = 0,
        m_score: float = 0.0,
        t_score: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Assess discussion quality."""
        if not self.client:
            logger.warning("LLM client not initialized")
            return None

        try:
            prompt_text = self.prompt_manager.render_prompt(
                "quality_assessment",
                {
                    "segment_id": segment_id,
                    "segment_duration": 20,
                    "speaker_count": len(set(line.split(":")[0] for line in transcript.split("\n") if ":" in line)),
                    "utterance_count": len(transcript.split("。")) + len(transcript.split(".")),
                    "text_length": len(transcript),
                    "transcript": transcript,
                    "q_count": q_count,
                    "a_count": a_count,
                    "uq_count": uq_count,
                    "r_count": r_count,
                    "m_score": f"{m_score:.2f}",
                    "t_score": f"{t_score:.2f}",
                },
            )

            if not prompt_text:
                return None

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)

        except Exception as e:
            logger.error(f"Error in assess_quality: {e}")
            return None
