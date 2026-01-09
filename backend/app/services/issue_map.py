"""Issue Map generation service - visualizes discussion structure."""

import logging
import json
from typing import List, Dict, Any
from collections import defaultdict

from app.core.prompts import get_prompt_manager
from app.services.llm import LLMService

logger = logging.getLogger(__name__)


class IssueMapService:
    """
    Generate issue map from discussion events.
    
    Based on EchoMind paper (CSCW 2025):
    - Groups related utterances into issue nodes
    - Links Q-A-R chains to show discussion flow
    - Identifies central topics and peripheral discussions
    """

    def __init__(self):
        self.topic_keywords = {
            "requirement": ["要件", "仕様", "機能", "必要", "ニーズ"],
            "design": ["設計", "デザイン", "UI", "構造", "アーキテクチャ"],
            "implementation": ["実装", "コード", "開発", "プログラム"],
            "testing": ["テスト", "検証", "確認", "バグ", "品質"],
            "schedule": ["スケジュール", "期限", "納期", "時間", "いつ"],
            "resource": ["リソース", "人員", "予算", "コスト"],
        }
        self.prompt_manager = get_prompt_manager()
        try:
            self.llm_service = LLMService()
            self.llm_available = self.llm_service.client is not None
        except Exception as e:
            logger.warning("LLMService initialization failed: %s", e)
            self.llm_service = None
            self.llm_available = False

    def generate_issue_map(
        self,
        events: List[Dict[str, Any]],
        utterances: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate issue map from events.
        
        Returns:
        {
            "nodes": [
                {
                    "id": "node_0",
                    "topic": "requirement",
                    "label": "機能要件について",
                    "events": ["event_0", "event_3"],
                    "centrality": 0.8,
                }
            ],
            "edges": [
                {
                    "source": "node_0",
                    "target": "node_1", 
                    "type": "qa_link",
                    "weight": 1.0,
                }
            ],
            "clusters": [
                {
                    "id": "cluster_0",
                    "node_ids": ["node_0", "node_1"],
                    "topic": "requirement",
                }
            ]
        }
        """
        # ベース分析でイベントが生成されなかった場合でも、最低限の構造を描画できるよう
        # 発話から簡易イベントを組み立てる
        if not events and utterances:
            events = self._build_events_from_utterances(utterances)
        elif not events:
            return self._empty_map()

        # Step 1: Create nodes from events
        nodes = self._create_nodes(events, utterances)

        # 強制的に描画用の最低限ノードを用意
        if not nodes and utterances:
            return self._minimal_map_from_utterances(utterances)

        # Step 2: Create edges based on Q-A relationships
        edges = self._create_edges(events, nodes)

        # Step 3: Identify clusters
        clusters = self._identify_clusters(nodes, edges)

        # Step 4: Calculate centrality
        for node in nodes:
            node["centrality"] = self._calculate_centrality(node, edges)

        return {
            "nodes": nodes,
            "edges": edges,
            "clusters": clusters,
            "metadata": {
                "total_events": len(events),
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "main_topics": self._get_main_topics(clusters),
            },
        }

    def generate_issue_map_from_utterances(
        self,
        utterances: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate issue map using LLM from utterances directly.
        
        This is the primary real-time method that uses HandyLLM prompts
        to extract nodes, edges, and clusters from raw discussion text.
        
        Args:
            utterances: List of {"speaker", "text", "start", "end"} dicts
            
        Returns:
            issue_map with nodes/edges/clusters structure
        """
        if not utterances or not self.llm_available:
            # Fallback to heuristic-based generation
            events = self._build_events_from_utterances(utterances or [])
            return self.generate_issue_map(events, utterances or [])
        
        try:
            # Prepare utterance text for prompt
            utterance_text = self._format_utterances_for_prompt(utterances)
            
            # Use HandyLLM prompt to generate issue map
            rendered_prompt = self.prompt_manager.render_prompt(
                "realtime_issue_map",
                {
                    "utterances": utterance_text,
                    "recent_count": min(5, len(utterances)),
                }
            )
            
            # Call LLM via service
            response = self._call_llm_for_issue_map(rendered_prompt)
            
            if not response:
                logger.warning("LLM returned empty response, using fallback")
                events = self._build_events_from_utterances(utterances)
                return self.generate_issue_map(events, utterances)
            
            # Parse JSON from response
            issue_map = self._parse_llm_response(response)
            
            # Log node details for debugging
            node_summaries = [
                {
                    "id": n.get("id"),
                    "topic": n.get("topic"),
                    "title": n.get("title", "")[:30],
                    "summary": n.get("summary", "")[:40],
                }
                for n in issue_map.get("nodes", [])
            ]
            
            logger.info(
                "LLM-generated issue_map: nodes=%d edges=%d clusters=%d, node_details=%s",
                len(issue_map.get("nodes", [])),
                len(issue_map.get("edges", [])),
                len(issue_map.get("clusters", [])),
                node_summaries[:3],  # Log first 3 nodes
            )
            
            return issue_map
            
        except Exception as e:
            logger.warning("LLM issue_map generation failed: %s, falling back to heuristic", e)
            events = self._build_events_from_utterances(utterances)
            return self.generate_issue_map(events, utterances)

    def _format_utterances_for_prompt(self, utterances: List[Dict[str, Any]]) -> str:
        """Format utterances as readable text for LLM prompt."""
        lines = []
        for utt in utterances[-5:]:  # Focus on last 5 utterances
            speaker = utt.get("speaker", "Unknown")
            text = utt.get("text", "")
            if text:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)

    def _call_llm_for_issue_map(self, prompt: str) -> str:
        """
        Call LLM with issue map prompt.
        
        Uses the LLMService to invoke OpenAI API directly.
        """
        if not self.llm_service or not self.llm_service.client:
            return ""
        
        try:
            response = self.llm_service.client.chat.completions.create(
                model=self.llm_service.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.llm_service.temperature,
                max_tokens=self.llm_service.max_tokens,
            )
            
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM API call failed: %s", e)
            return ""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response.
        
        Expected format: triple-backtick wrapped JSON
        ```json
        {...}
        ```
        """
        try:
            # Extract JSON between triple backticks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()
            
            issue_map = json.loads(json_str)
            
            # Validate structure
            if "nodes" not in issue_map:
                issue_map["nodes"] = []
            if "edges" not in issue_map:
                issue_map["edges"] = []
            if "clusters" not in issue_map:
                issue_map["clusters"] = []
            
            # Ensure nodes list is non-empty; fallback to minimal
            if not issue_map.get("nodes"):
                return self._minimal_map()
            
            return issue_map
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse LLM JSON response: %s", e)
            return self._minimal_map()

    def _create_nodes(
        self, events: List[Dict[str, Any]], utterances: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create nodes from events grouped by topic similarity."""
        nodes = []
        event_to_node = {}
        node_id_counter = 0

        for i, event in enumerate(events):
            event_id = f"event_{i}"
            event_type = event.get("event_type", "X")
            text = event.get("text", "")
            speaker = event.get("speaker", "Unknown")

            # Detect topic
            topic = self._detect_topic(text)

            # Try to merge with existing node
            merged = False
            for node in nodes:
                if node["topic"] == topic and self._is_related(node["events"], event):
                    node["events"].append(event_id)
                    node["event_objects"].append(event)
                    event_to_node[event_id] = node["id"]
                    merged = True
                    break

            if not merged:
                # Create new node
                node_id = f"node_{node_id_counter}"
                node_id_counter += 1
                node = {
                    "id": node_id,
                    "topic": topic,
                    "label": self._generate_label(text, topic),
                    "events": [event_id],
                    "event_objects": [event],
                    "centrality": 0.0,
                    "event_types": [event_type],
                }
                nodes.append(node)
                event_to_node[event_id] = node_id

        return nodes

    def _create_edges(
        self, events: List[Dict[str, Any]], nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create edges based on Q-A relationships and temporal proximity."""
        edges = []
        edge_set = set()

        # Build event_id to node_id mapping
        event_to_node = {}
        for node in nodes:
            for event_id in node["events"]:
                event_to_node[event_id] = node["id"]

        # Find Q-A pairs
        for i, event in enumerate(events):
            if event.get("event_type") == "Q":
                question_node = event_to_node.get(f"event_{i}")
                if not question_node:
                    continue

                # Look for answers within next 5 events
                for j in range(i + 1, min(i + 6, len(events))):
                    next_event = events[j]
                    if next_event.get("event_type") == "A":
                        answer_node = event_to_node.get(f"event_{j}")
                        if answer_node and answer_node != question_node:
                            edge_key = (question_node, answer_node)
                            if edge_key not in edge_set:
                                edges.append({
                                    "source": question_node,
                                    "target": answer_node,
                                    "type": "qa_link",
                                    "weight": 1.0,
                                })
                                edge_set.add(edge_key)
                        break

        # Add temporal edges for consecutive nodes
        for i in range(len(events) - 1):
            curr_node = event_to_node.get(f"event_{i}")
            next_node = event_to_node.get(f"event_{i + 1}")
            if curr_node and next_node and curr_node != next_node:
                edge_key = (curr_node, next_node)
                if edge_key not in edge_set:
                    edges.append({
                        "source": curr_node,
                        "target": next_node,
                        "type": "temporal",
                        "weight": 0.3,
                    })
                    edge_set.add(edge_key)

        return edges

    def _identify_clusters(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify clusters based on topic similarity."""
        topic_groups = defaultdict(list)
        for node in nodes:
            topic_groups[node["topic"]].append(node["id"])

        clusters = []
        for i, (topic, node_ids) in enumerate(topic_groups.items()):
            if len(node_ids) > 0:
                clusters.append({
                    "id": f"cluster_{i}",
                    "node_ids": node_ids,
                    "topic": topic,
                    "size": len(node_ids),
                })

        return clusters

    def _build_events_from_utterances(
        self, utterances: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fallback: utterances を簡易イベントに変換する.

        分類器が動かない場合でもトピックマップを描画できるよう、発話テキストから
        ざっくりとイベント種別を推定する。
        """

        def guess_event_type(text: str) -> str:
            lowered = (text or "").lower()
            if "?" in lowered or "？" in lowered:
                return "Q"
            if lowered.startswith("はい") or lowered.startswith("了解"):
                return "A"
            return "S"  # Statement

        events: List[Dict[str, Any]] = []
        for i, utt in enumerate(utterances):
            events.append({
                "event_id": f"event_{i}",
                "event_type": guess_event_type(utt.get("text", "")),
                "text": utt.get("text", ""),
                "speaker": utt.get("speaker", "Unknown"),
            })

        return events

    def _minimal_map_from_utterances(self, utterances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Utterances から強制的に 1 ノード構築する簡易マップ."""

        if not utterances:
            return self._empty_map()

        text_joined = " ".join(u.get("text", "") for u in utterances if u.get("text"))
        node = {
            "id": "node_0",
            "topic": "general",
            "label": text_joined[:40] or "Discussion",
            "events": [],
            "event_objects": [],
            "centrality": 0.0,
            "event_types": [],
        }

        return {
            "nodes": [node],
            "edges": [],
            "clusters": [
                {
                    "id": "cluster_0",
                    "node_ids": ["node_0"],
                    "topic": "general",
                    "size": 1,
                }
            ],
            "metadata": {
                "total_events": 0,
                "total_nodes": 1,
                "total_edges": 0,
                "main_topics": ["general"],
            },
        }

    def _detect_topic(self, text: str) -> str:
        """Detect topic from text using keyword matching."""
        text_lower = text.lower()
        topic_scores = {}

        for topic, keywords in self.topic_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                topic_scores[topic] = score

        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        return "general"

    def _is_related(self, existing_events: List[str], new_event: Dict[str, Any]) -> bool:
        """Check if new event is related to existing events in node."""
        # Simple heuristic: same speaker or within 10 seconds
        return len(existing_events) < 3

    def _generate_label(self, text: str, topic: str) -> str:
        """Generate human-readable label for node."""
        # Use first 30 chars of text
        if len(text) > 30:
            return text[:27] + "..."
        return text

    def _calculate_centrality(
        self, node: Dict[str, Any], edges: List[Dict[str, Any]]
    ) -> float:
        """Calculate centrality score based on connections."""
        node_id = node["id"]
        in_degree = sum(1 for e in edges if e.get("target") == node_id)
        out_degree = sum(1 for e in edges if e.get("source") == node_id)
        total_edges = len(edges) if edges else 1
        
        # Normalize by total edges
        return (in_degree + out_degree) / (2 * total_edges)

    def _get_main_topics(self, clusters: List[Dict[str, Any]]) -> List[str]:
        """Get main topics sorted by cluster size."""
        sorted_clusters = sorted(clusters, key=lambda c: c["size"], reverse=True)
        return [c["topic"] for c in sorted_clusters[:3]]

    def _empty_map(self) -> Dict[str, Any]:
        """Return empty issue map structure."""
        return {
            "nodes": [],
            "edges": [],
            "clusters": [],
            "metadata": {
                "total_events": 0,
                "total_nodes": 0,
                "total_edges": 0,
                "main_topics": [],
            },
        }
