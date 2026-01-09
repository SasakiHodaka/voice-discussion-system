"""
SessionMessageBuffer - Text accumulation and auto-trigger for LLM analysis.

Tracks accumulated message text per session and triggers issue_map generation
when threshold is reached.
"""

from datetime import datetime
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class SessionMessageBuffer:
    """
    Buffers messages per session and triggers LLM when character threshold is reached.

    Responsibilities:
    - Accumulate message text per session
    - Track character count
    - Trigger issue_map generation on threshold
    - Reset buffer after trigger
    """

    def __init__(self, char_threshold: int = 500, word_threshold: Optional[int] = None):
        """
        Initialize buffer.

        Args:
            char_threshold: Character count threshold for auto-trigger
            word_threshold: Word count threshold (optional, uses char if not set)
        """
        self.char_threshold = char_threshold
        self.word_threshold = word_threshold
        # Per-session buffers: session_id -> { text, char_count, word_count, utterances }
        self.buffers: Dict[str, Dict] = {}

    def add_message(
        self, session_id: str, speaker: str, text: str
    ) -> tuple[bool, Optional[Dict]]:
        """
        Add message to buffer and check if threshold is reached.

        Args:
            session_id: Session identifier
            speaker: Speaker name
            text: Message text

        Returns:
            (threshold_reached, buffer_content)
        """
        if session_id not in self.buffers:
            self.buffers[session_id] = {
                "text": "",
                "char_count": 0,
                "word_count": 0,
                "utterances": [],
                "last_update": datetime.utcnow(),
            }

        buf = self.buffers[session_id]
        
        # Append message
        if buf["text"]:
            buf["text"] += " "  # Add space between messages
        buf["text"] += text
        
        # Recalculate counts
        buf["char_count"] = len(buf["text"])
        buf["word_count"] = len(buf["text"].split())
        
        # Record utterance
        buf["utterances"].append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        buf["last_update"] = datetime.utcnow()

        # Check thresholds
        char_exceeded = buf["char_count"] >= self.char_threshold
        word_exceeded = (
            self.word_threshold and buf["word_count"] >= self.word_threshold
        ) or False

        threshold_reached = char_exceeded or word_exceeded

        logger.debug(
            f"[SessionMessageBuffer] Added message to session={session_id} "
            f"chars={buf['char_count']} words={buf['word_count']} "
            f"threshold_reached={threshold_reached}"
        )

        if threshold_reached:
            return True, self._get_buffer_snapshot(session_id)
        else:
            return False, None

    def get_buffer(self, session_id: str) -> Optional[Dict]:
        """Get current buffer content without triggering."""
        if session_id not in self.buffers:
            return None
        return self._get_buffer_snapshot(session_id)

    def _get_buffer_snapshot(self, session_id: str) -> Dict:
        """Create a snapshot of the buffer for processing."""
        buf = self.buffers[session_id]
        return {
            "session_id": session_id,
            "text": buf["text"],
            "char_count": buf["char_count"],
            "word_count": buf["word_count"],
            "utterances": buf["utterances"],
            "last_update": buf["last_update"].isoformat(),
        }

    def reset_buffer(self, session_id: str) -> None:
        """Reset buffer after processing."""
        if session_id in self.buffers:
            logger.info(
                f"[SessionMessageBuffer] Resetting buffer for session={session_id} "
                f"(had {self.buffers[session_id]['char_count']} chars)"
            )
            self.buffers[session_id] = {
                "text": "",
                "char_count": 0,
                "word_count": 0,
                "utterances": [],
                "last_update": datetime.utcnow(),
            }

    def cleanup_idle_buffers(self, idle_minutes: int = 60) -> None:
        """Remove buffers for sessions that haven't been updated."""
        import datetime as dt
        
        cutoff = datetime.utcnow() - dt.timedelta(minutes=idle_minutes)
        to_remove = []
        
        for session_id, buf in self.buffers.items():
            if datetime.fromisoformat(buf["last_update"].isoformat()) < cutoff:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            logger.debug(
                f"[SessionMessageBuffer] Removing idle buffer for session={session_id}"
            )
            del self.buffers[session_id]


# Global instance
message_buffer = SessionMessageBuffer(char_threshold=500)
