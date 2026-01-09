#!/usr/bin/env python3
"""
Quick test script for LLM-based issue map generation.

Usage:
    python test_issue_map_llm.py
"""

import asyncio
import json
from app.services.issue_map import IssueMapService

# Sample utterances for testing
SAMPLE_UTTERANCES = [
    {
        "speaker": "Alice",
        "text": "仕様定義が不明確だと思います。例えば、ユーザ認証の流れがまだはっきりしていない",
        "start": 0,
        "end": 5,
    },
    {
        "speaker": "Bob",
        "text": "そうですね。認証方式も決まっていない。OAuth か JWT か内製か。",
        "start": 5,
        "end": 10,
    },
    {
        "speaker": "Alice",
        "text": "期限も気になります。認証実装にはどのくらい時間がかかりますか？",
        "start": 10,
        "end": 15,
    },
    {
        "speaker": "Charlie",
        "text": "1-2週間あれば基本的な実装は完了できます。",
        "start": 15,
        "end": 20,
    },
]


def test_issue_map_generation():
    """Test both heuristic and LLM-based issue map generation."""
    
    service = IssueMapService()
    
    print("=" * 80)
    print("Testing LLM-based Issue Map Generation")
    print("=" * 80)
    
    # Test with heuristic method (fallback)
    print("\n1. Testing heuristic-based generation...")
    events = service._build_events_from_utterances(SAMPLE_UTTERANCES)
    heuristic_map = service.generate_issue_map(events, SAMPLE_UTTERANCES)
    
    print(f"   Nodes: {len(heuristic_map.get('nodes', []))}")
    print(f"   Edges: {len(heuristic_map.get('edges', []))}")
    print(f"   Clusters: {len(heuristic_map.get('clusters', []))}")
    
    # Test with LLM method
    print("\n2. Testing LLM-based generation...")
    try:
        llm_map = service.generate_issue_map_from_utterances(SAMPLE_UTTERANCES)
        print(f"   Nodes: {len(llm_map.get('nodes', []))}")
        print(f"   Edges: {len(llm_map.get('edges', []))}")
        print(f"   Clusters: {len(llm_map.get('clusters', []))}")
        
        # Show generated nodes
        print("\n   Generated Nodes:")
        for node in llm_map.get('nodes', [])[:3]:
            print(f"     - {node.get('id')}: {node.get('title')} (topic: {node.get('topic')})")
        
    except Exception as e:
        print(f"   Error: {e}")
        print("   (This is expected if LLM is not available)")
    
    print("\n" + "=" * 80)
    print("Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_issue_map_generation()
