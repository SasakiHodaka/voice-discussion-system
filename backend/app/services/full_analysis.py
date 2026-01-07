"""Full discussion analysis service."""

import logging
from typing import List, Dict, Any
from collections import Counter, defaultdict

from app.services.analysis import AnalysisService

logger = logging.getLogger(__name__)


class FullAnalysisService:
    """Analyze entire discussion session for comprehension gaps and patterns."""

    def __init__(self):
        self.segment_analyzer = AnalysisService()

    def analyze_full_discussion(
        self,
        session_id: str,
        utterances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze full discussion for understanding gaps.
        
        Returns:
        - speaker_stats: contribution per speaker (Q/A/R counts)
        - qa_matching: Q-A matching ratio
        - topic_dispersion: spread of topics across speakers
        - understanding_gaps: identified gaps in comprehension
        """
        if not utterances:
            return self._empty_result()

        # Run segment analysis on full conversation
        segment_result = self.segment_analyzer.analyze_segment(
            session_id=session_id,
            segment_id=0,
            start_sec=0.0,
            end_sec=max((u.get('end', 0) for u in utterances), default=0),
            utterances=utterances
        )

        # Extract speaker-level stats
        speaker_stats = self._compute_speaker_stats(utterances, segment_result)
        
        # Compute Q-A matching
        qa_matching = self._compute_qa_matching(segment_result)
        
        # Compute topic dispersion (how spread topics are across speakers)
        topic_dispersion = self._compute_topic_dispersion(utterances)
        
        # Identify understanding gaps
        understanding_gaps = self._identify_gaps(segment_result, speaker_stats)

        return {
            'session_id': session_id,
            'total_utterances': len(utterances),
            'speakers': list(speaker_stats.keys()),
            'speaker_stats': speaker_stats,
            'qa_matching': qa_matching,
            'topic_dispersion': topic_dispersion,
            'understanding_gaps': understanding_gaps,
            'overall_quality': segment_result.L,
            'metrics': {
                'Q': segment_result.Q,
                'A': segment_result.A,
                'R': segment_result.R,
                'S': segment_result.S,
                'X': segment_result.X,
            }
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            'session_id': '',
            'total_utterances': 0,
            'speakers': [],
            'speaker_stats': {},
            'qa_matching': {'ratio': 0.0, 'matched': 0, 'unmatched': 0},
            'topic_dispersion': 0.0,
            'understanding_gaps': [],
            'overall_quality': 0.0,
            'metrics': {'Q': 0, 'A': 0, 'R': 0, 'S': 0, 'X': 0}
        }

    def _compute_speaker_stats(
        self,
        utterances: List[Dict[str, Any]],
        segment_result: Any
    ) -> Dict[str, Dict[str, Any]]:
        """Compute per-speaker contribution statistics."""
        stats = defaultdict(lambda: {
            'utterance_count': 0,
            'total_chars': 0,
            'questions': 0,
            'answers': 0,
            'responses': 0
        })

        # Count utterances and chars per speaker
        for u in utterances:
            speaker = u.get('speaker', 'Unknown')
            stats[speaker]['utterance_count'] += 1
            stats[speaker]['total_chars'] += len(u.get('text', ''))

        # Assign Q/A/R to speakers based on event types
        for event in segment_result.events:
            speaker = event.get('speaker', 'Unknown')
            event_type = event.get('type', '')
            if event_type == 'Q':
                stats[speaker]['questions'] += 1
            elif event_type == 'A':
                stats[speaker]['answers'] += 1
            elif event_type == 'R':
                stats[speaker]['responses'] += 1

        return dict(stats)

    def _compute_qa_matching(self, segment_result: Any) -> Dict[str, Any]:
        """Compute how many questions have answers."""
        q_count = segment_result.Q
        a_count = segment_result.A
        
        if q_count == 0:
            return {'ratio': 1.0 if a_count == 0 else 0.0, 'matched': 0, 'unmatched': 0}
        
        matched = min(q_count, a_count)
        unmatched = max(0, q_count - a_count)
        ratio = matched / q_count if q_count > 0 else 0.0
        
        return {
            'ratio': ratio,
            'matched': matched,
            'unmatched': unmatched
        }

    def _compute_topic_dispersion(self, utterances: List[Dict[str, Any]]) -> float:
        """
        Compute topic dispersion across speakers.
        Higher value = more speakers contributing to diverse topics.
        Simple heuristic: unique speaker count / total utterances.
        """
        if not utterances:
            return 0.0
        
        speakers = set(u.get('speaker', 'Unknown') for u in utterances)
        return len(speakers) / len(utterances)

    def _identify_gaps(
        self,
        segment_result: Any,
        speaker_stats: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Identify potential understanding gaps."""
        gaps = []
        
        # Gap 1: Unanswered questions
        if segment_result.Q > segment_result.A:
            gaps.append({
                'type': 'unanswered_questions',
                'severity': 'high',
                'description': f'{segment_result.Q - segment_result.A}件の未回答の質問があります'
            })
        
        # Gap 2: One-sided discussion (single speaker dominance)
        if speaker_stats:
            max_contribution = max(s['utterance_count'] for s in speaker_stats.values())
            total_utterances = sum(s['utterance_count'] for s in speaker_stats.values())
            if total_utterances > 0 and max_contribution / total_utterances > 0.7:
                gaps.append({
                    'type': 'one_sided_discussion',
                    'severity': 'medium',
                    'description': '特定の話者が議論の70%以上を占めています'
                })
        
        # Gap 3: Low response engagement
        if segment_result.R < segment_result.Q * 0.5:
            gaps.append({
                'type': 'low_engagement',
                'severity': 'medium',
                'description': '質問に対する応答が少ないです'
            })
        
        # Gap 4: High interruption/crosstalk
        if segment_result.X > segment_result.U * 0.3:
            gaps.append({
                'type': 'high_crosstalk',
                'severity': 'low',
                'description': 'クロストークや中断が多く見られます'
            })
        
        return gaps
