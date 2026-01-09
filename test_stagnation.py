#!/usr/bin/env python3
"""Test stagnation scenario via API."""

import sys
import json
import requests
from pathlib import Path

# Backend URL
API_BASE = "http://127.0.0.1:8000"

def test_stagnation():
    """Test stagnation detection."""
    print("\n" + "="*60)
    print("  Stagnation Scenario Test")
    print("="*60)
    
    # Create session
    print("\n[1/3] Creating session...")
    session_resp = requests.post(
        f"{API_BASE}/api/sessions/",
        params={
            "title": "Stagnation Test",
            "creator_name": "TestAdmin",
            "description": "Testing stagnation detection"
        }
    )
    session_id = session_resp.json()['session_id']
    print(f"  ✅ Session ID: {session_id}")
    
    # Create stagnant utterances
    print("\n[2/3] Creating stagnation scenario...")
    stagnant_utterances = [
        {"utterance_id": "s1", "start": 0.0, "end": 2.0, "speaker": "Speaker_A", "text": "Hmm, I wonder..."},
        {"utterance_id": "s2", "start": 3.0, "end": 5.0, "speaker": "Speaker_B", "text": "Well, maybe..."},
        {"utterance_id": "s3", "start": 6.0, "end": 8.0, "speaker": "Speaker_C", "text": "That's difficult..."},
        {"utterance_id": "s4", "start": 9.0, "end": 11.0, "speaker": "Speaker_A", "text": "Perhaps..."},
        {"utterance_id": "s5", "start": 12.0, "end": 14.0, "speaker": "Speaker_B", "text": "Maybe so..."},
        {"utterance_id": "s6", "start": 15.0, "end": 17.0, "speaker": "Speaker_C", "text": "I don't know..."},
    ]
    
    # Run analysis
    print("\n[3/3] Running integrated analysis...")
    analysis_resp = requests.post(
        f"{API_BASE}/api/integrated/analyze-segment",
        json={
            "session_id": session_id,
            "segment_id": 1,
            "start_sec": 0.0,
            "end_sec": 17.0,
            "utterances": stagnant_utterances
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
        print(f"    Message: {intervention.get('message', 'N/A')}")
    
    # Cognitive stats
    cognitive = summary.get('cognitive_stats', {})
    print(f"\n  Cognitive Statistics:")
    print(f"    Avg Confidence: {cognitive.get('avg_confidence', 0):.2f}")
    print(f"    Avg Understanding: {cognitive.get('avg_understanding', 0):.2f}")
    print(f"    Avg Hesitation: {cognitive.get('avg_hesitation', 0):.2f}")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    try:
        test_stagnation()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
