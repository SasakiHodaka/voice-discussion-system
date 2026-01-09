#!/usr/bin/env python3
"""Test imbalance scenario via API."""

import sys
import json
import requests
from pathlib import Path

# Backend URL
API_BASE = "http://127.0.0.1:8000"

def test_imbalance():
    """Test discussion imbalance detection."""
    print("\n" + "="*60)
    print("  Discussion Imbalance Scenario Test")
    print("="*60)
    
    # Create session
    print("\n[1/3] Creating session...")
    session_resp = requests.post(
        f"{API_BASE}/api/sessions/",
        params={
            "title": "Imbalance Test",
            "creator_name": "TestAdmin",
            "description": "Testing discussion imbalance detection"
        }
    )
    session_id = session_resp.json()['session_id']
    print(f"  ✅ Session ID: {session_id}")
    
    # Create imbalanced utterances (one person dominates)
    print("\n[2/3] Creating imbalance scenario...")
    imbalanced_utterances = [
        {"utterance_id": "i1", "start": 0.0, "end": 3.0, "speaker": "Dominant", 
         "text": "I think we should prioritize customer acquisition over retention. This is crucial for our business strategy."},
        {"utterance_id": "i2", "start": 4.0, "end": 6.0, "speaker": "Quiet", 
         "text": "Yes, I agree."},
        {"utterance_id": "i3", "start": 7.0, "end": 10.0, "speaker": "Dominant", 
         "text": "Furthermore, we need to expand to new markets immediately. The window is closing and we cannot afford to wait."},
        {"utterance_id": "i4", "start": 11.0, "end": 13.0, "speaker": "Quiet", 
         "text": "OK, that sounds good."},
        {"utterance_id": "i5", "start": 14.0, "end": 18.0, "speaker": "Dominant", 
         "text": "Our competitors are already moving in this direction. If we don't act now, we'll lose market share. Every day counts."},
        {"utterance_id": "i6", "start": 19.0, "end": 20.0, "speaker": "Quiet", 
         "text": "Right."},
    ]
    
    # Run analysis
    print("\n[3/3] Running integrated analysis...")
    analysis_resp = requests.post(
        f"{API_BASE}/api/integrated/analyze-segment",
        json={
            "session_id": session_id,
            "segment_id": 1,
            "start_sec": 0.0,
            "end_sec": 20.0,
            "utterances": imbalanced_utterances
        }
    )
    
    result = analysis_resp.json()
    
    # Display results
    print("\n" + "-"*60)
    print("Analysis Results:")
    print("-"*60)
    
    summary = result.get('summary', {})
    health = int(summary.get('discussion_health', 0) * 100)
    
    print(f"\n  Discussion Health Score: {health}%")
    
    metrics = summary.get('key_metrics', {})
    print(f"\n  Key Metrics:")
    print(f"    Confusion (M): {metrics.get('confusion', 0):.2f}")
    print(f"    Stagnation (T): {metrics.get('stagnation', 0):.2f}")
    print(f"    Understanding (L): {metrics.get('understanding', 0):.2f}")
    
    # Intervention assessment
    intervention = result.get('intervention', {})
    print(f"\n  Intervention Assessment:")
    print(f"    Needed: {intervention.get('needed', False)}")
    if intervention.get('needed'):
        print(f"    Type: {intervention.get('type', 'unknown')}")
        print(f"    Priority: {intervention.get('priority', 0):.2f}")
        print(f"    Message: {intervention.get('message', 'N/A')[:100]}...")
    
    # Cognitive stats
    cognitive = summary.get('cognitive_stats', {})
    print(f"\n  Cognitive Statistics:")
    print(f"    Avg Confidence: {cognitive.get('avg_confidence', 0):.2f}")
    print(f"    Avg Understanding: {cognitive.get('avg_understanding', 0):.2f}")
    print(f"    Avg Hesitation: {cognitive.get('avg_hesitation', 0):.2f}")
    
    # Participant states analysis
    states = result.get('participant_states', [])
    if states:
        print(f"\n  Participant Analysis:")
        speaker_words = {}
        for state in states:
            speaker = state.get('speaker', 'Unknown')
            text = state.get('text', '')
            word_count = len(text.split())
            speaker_words[speaker] = speaker_words.get(speaker, 0) + word_count
            
            cognitive_state = state.get('cognitive_state', {})
            print(f"    {speaker}:")
            print(f"      - Engagement: {cognitive_state.get('engagement_level', 0):.2f}")
            print(f"      - Confidence: {cognitive_state.get('confidence_level', 0):.2f}")
            print(f"      - Understanding: {cognitive_state.get('understanding_level', 0):.2f}")
        
        # Calculate imbalance
        if speaker_words:
            total_words = sum(speaker_words.values())
            print(f"\n  Speech Balance:")
            for speaker, words in sorted(speaker_words.items(), key=lambda x: -x[1]):
                percentage = (words / total_words * 100) if total_words > 0 else 0
                print(f"    {speaker}: {percentage:.1f}% ({words} words)")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    try:
        test_imbalance()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
