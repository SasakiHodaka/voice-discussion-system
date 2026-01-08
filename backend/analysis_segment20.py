"""
Legacy analysis module for segment analysis.
Provides heuristic-based event detection (Q/A/R/S/X).
"""

from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class AudioStats:
    """Audio statistics for utterance."""
    volume: float = 0.0
    pitch: float = 0.0
    tempo: float = 0.0


@dataclass
class Utterance:
    """Single utterance in a discussion (compatible with AnalysisService)."""
    utterance_id: str
    start: float
    end: float
    speaker: str
    text: str
    audio_stats: Optional[AudioStats] = None


@dataclass
class Event:
    """Discussion event (Q/A/R/S/X)."""
    event_type: str  # 'Q', 'A', 'R', 'S', 'X'
    participant_id: str
    timestamp: float
    text: str
    confidence: float = 1.0


@dataclass _is_question(text: str) -> bool:
    """Check if text is a question."""
    question_markers = ['?', '?', 'ですか', 'ますか', 'ませんか', 'どう', 'なぜ', 'いつ', 'どこ', 'だれ', '誰']
    text_lower = text.lower()
    return any(marker in text_lower for marker in question_markers)


def _is_refutation(text: str) -> bool:
    """Check if text is a refutation/disagreement."""
    refutation_markers = ['でも', 'しかし', 'でもね', 'いや', 'でもさ', '違う', 'ちがう', 'そうじゃなくて']
    text_lower = text.lower()
    return any(marker in text_lower for marker in refutation_markers)


def _is_support(text: str) -> bool:
    """Check if text is support/agreement."""
    support_markers = ['そうですね', 'たしかに', '確かに', 'そうそう', 'いいね', 'わかる', '賛成']
    text_lower = text.lower()
    return any(marker in text_lower for marker in support_markers)


@dataclass
class SegmentAnalysisResult:
    """Full analysis result compatible with AnalysisService."""
    session_id: str
    segment_id: int
    start_sec: float
    end_sec: float
    status: str  # 'EVALUABLE', 'NOT_EVALUABLE'
    status_reason: str
    audio: AudioStats
    utterances: List[Utterance]
    events: List[Event]
    U: int  # Total utterances
    Q: int  # Questions
    A: int  # Assertions
    UQ: int  # Unanswered questions
    R: int  # Refutations
    S: int  # Supports
    X: int  # Other
    P: int  # Participant switches
    D: int  # Dialog depth
    M: float  # Mutuality
    T: float  # Transactivity
    L: float  # Liveliness
    is_risky: bool = False
    note: str = ""


def analyze_segment(
    session_id: str,
    segment_id: int,
    start_sec: float,
    end_sec: float,
    audio_stats: Optional[AudioStats] = None,
    utterances: Optional[List[Utterance]] = None,
    min_total_chars_for_evaluable: int = 40
) -> SegmentAnalysisResult:
    """
    Analyze a discussion segment (compatible with AnalysisService).
    
    Args:
        session_id: Session identifier
        segment_id: Segment identifier
        start_sec: Segment start time
        end_sec: Segment end time
        audio_stats: Optional audio statistics
        utterances: List of utterances in the segment
        min_total_chars_for_evaluable: Minimum character count
    
    Returns:
        SegmentAnalysisResult with full analysis
    """
    if audio_stats is None:
        audio_stats = AudioStats()
    if utterances is None:
        utterances = []
    
    # Check if evaluable
    total_chars = sum(len(u.text) for u in utterances)
    if total_chars < min_total_chars_for_evaluable:
        return SegmentAnalysisResult(
            session_id=session_id,
            segment_id=segment_id,
            start_sec=start_sec,
            end_sec=end_sec,
            status='NOT_EVALUABLE',
            status_reason=f'Insufficient text: {total_chars} < {min_total_chars_for_evaluable} chars',
            audio=audio_stats,
            utterances=utterances,
            events=[],
            U=len(utterances),
            Q=0, A=0, UQ=0, R=0, S=0, X=0, P=0, D=0,
            M=0.0, T=0.0, L=0.0,
            note='Not enough content for analysis'
        )
    
    # Classify utterances into events
    events: List[Event] = []
    q_count = 0
    a_count = 0
    r_count = 0
    s_count = 0
    x_count = 0
    
    for utt in utterances:
        text = utt.text.strip()
        if not text:
            continue
        
        # Classify utterance
        if _is_question(text):
            events.append(Event('Q', utt.speaker, utt.start, text))
            q_count += 1
        elif _is_refutation(text):
            events.append(Event('R', utt.speaker, utt.start, text))
            r_count += 1
        elif _is_support(text):
            events.append(Event('S', utt.speaker, utt.start, text))
            s_count += 1
        else:
            # Default to assertion
            events.append(Event('A', utt.speaker, utt.start, text))
            a_count += 1
    
    # Calculate metrics
    total_events = len(events)
    unique_speakers = len(set(e.participant_id for e in events))
    
    # Participant switches
    p_switches = 0
    prev_speaker = None
    for utt in utterances:
        if prev_speaker and prev_speaker != utt.speaker:
            p_switches += 1
        prev_speaker = utt.speaker
    
    # Scores
    M = unique_speakers / max(len(utterances), 1) if utterances else 0.0
    T = (q_count + r_count + s_count) / max(total_events, 1) if total_events > 0 else 0.0
    L = total_events / max((end_sec - start_sec), 1.0)
    
    return SegmentAnalysisResult(
        session_id=session_id,
        segment_id=segment_id,
        start_sec=start_sec,
        end_sec=end_sec,
        status='EVALUABLE',
        status_reason='Analysis completed successfully',
        audio=audio_stats,
        utterances=utterances,
        events=events,
        U=len(utterances),
        Q=q_count,
        A=a_count,
        UQ=0,  # Simple heuristic: not tracking answered questions
        R=r_count,
        S=s_count,
        X=x_count,
        P=p_switches,
        D=0,  # Dialog depth: simplified
        M=M,
        T=T,
        L=L,
        is_risky=(M < 0.3 or T < 0.2),  # Simple risk detection
        note=f'{total_events} events detected'
    )
