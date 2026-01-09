#!/usr/bin/env python3
"""Test productive discussion scenario."""

import sys
import json
import requests

# Backend URL
API_BASE = "http://127.0.0.1:8000"

def test_productive():
    """Test productive discussion with Q/A pattern."""
    print("\n" + "="*60)
    print("  Productive Discussion Scenario Test")
    print("="*60)
    
    # Create session
    print("\n[1/3] Creating session...")
    session_resp = requests.post(
        f"{API_BASE}/api/sessions/",
        params={
            "title": "Productive Discussion",
            "creator_name": "TestAdmin",
            "description": "Testing productive discussion pattern"
        }
    )
    session_id = session_resp.json()['session_id']
    print(f"  ✅ Session ID: {session_id}")
    
    # Create productive utterances (Q/A/Support pattern)
    print("\n[2/3] Creating productive scenario...")
    productive_utterances = [
        {"utterance_id": "p1", "start": 0.0, "end": 2.0, "speaker": "Alice", 
         "text": "What are our main challenges with the current system?"},
        
        {"utterance_id": "p2", "start": 3.0, "end": 5.0, "speaker": "Bob", 
         "text": "The main issue is scalability. We can't handle more than 10,000 concurrent users."},
        
        {"utterance_id": "p3", "start": 6.0, "end": 8.0, "speaker": "Alice", 
         "text": "That's a critical limitation. Have you identified the bottleneck?"},
        
        {"utterance_id": "p4", "start": 9.0, "end": 12.0, "speaker": "Bob", 
         "text": "Yes, it's the database layer. We need to implement sharding and caching strategies."},
        
        {"utterance_id": "p5", "start": 13.0, "end": 15.0, "speaker": "Carol", 
         "text": "I agree with Bob. We should also consider using a message queue."},
        
        {"utterance_id": "p6", "start": 16.0, "end": 18.0, "speaker": "Alice", 
         "text": "Good point. How long would implementation take?"},
        
        {"utterance_id": "p7", "start": 19.0, "end": 22.0, "speaker": "Bob", 
         "text": "With a dedicated team of 3-4 engineers, we could have a proof of concept in 6-8 weeks."},
        
        {"utterance_id": "p8", "start": 23.0, "end": 25.0, "speaker": "Carol", 
         "text": "That timeline is reasonable. We should start preparing the architecture design."},
    ]
    
    # Run analysis
    print("\n[3/3] Running integrated analysis...")
    analysis_resp = requests.post(
        f"{API_BASE}/api/integrated/analyze-segment",
        json={
            "session_id": session_id,
            "segment_id": 1,
            "start_sec": 0.0,
            "end_sec": 25.0,
            "utterances": productive_utterances
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
    if health >= 80:
        print("  ✅ Discussion is healthy and productive")
    elif health >= 50:
        print("  ⚠️  Discussion is moderately healthy")
    else:
        print("  ⛔ Discussion needs improvement")
    
    metrics = summary.get('key_metrics', {})
    print(f"\n  Key Metrics:")
    print(f"    Confusion (M): {metrics.get('confusion', 0):.2f}")
    print(f"    Stagnation (T): {metrics.get('stagnation', 0):.2f}")
    print(f"    Understanding (L): {metrics.get('understanding', 0):.2f}")
    
    # Base analysis
    base = result.get('base_analysis', {})
    if base:
        print(f"\n  Event Detection (Q/A/R/S/X):")
        print(f"    Questions (Q): {base.get('Q', 0)}")
        print(f"    Answers (A): {base.get('A', 0)}")
        print(f"    Refutations (R): {base.get('R', 0)}")
        print(f"    Support (S): {base.get('S', 0)}")
        print(f"    Other (X): {base.get('X', 0)}")
    
    # Intervention assessment
    intervention = result.get('intervention', {})
    print(f"\n  Intervention Assessment:")
    print(f"    Needed: {intervention.get('needed', False)}")
    if intervention.get('needed'):
        print(f"    Type: {intervention.get('type', 'unknown')}")
        print(f"    Priority: {intervention.get('priority', 0):.2f}")
    
    # Cognitive stats
    cognitive = summary.get('cognitive_stats', {})
    print(f"\n  Cognitive Statistics:")
    print(f"    Avg Confidence: {cognitive.get('avg_confidence', 0):.2f}")
    print(f"    Avg Understanding: {cognitive.get('avg_understanding', 0):.2f}")
    print(f"    Avg Hesitation: {cognitive.get('avg_hesitation', 0):.2f}")
    
    # Participant profiles
    profiles = result.get('participant_profiles', {})
    if profiles:
        print(f"\n  Participant Profiles:")
        for speaker, profile in profiles.items():
            if isinstance(profile, dict):
                print(f"    {speaker}:")
                print(f"      - Speech Style: {profile.get('speech_style', 'N/A')}")
                print(f"      - Contribution Style: {profile.get('contribution_style', 'N/A')}")
                if 'avg_metrics' in profile:
                    metrics = profile.get('avg_metrics', {})
                    print(f"      - Avg Confidence: {metrics.get('confidence', 0):.2f}")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    try:
        test_productive()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
