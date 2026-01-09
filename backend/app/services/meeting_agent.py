"""
MeetingAgentGamma - Session-level issue map state management.

This service manages the current_map state per session, merging:
1. LLM-generated issue map updates
2. Hand-edits from participants
3. Protection logic to prevent LLM overwriting recent hand-edits
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class EditSnapshot:
    """Record of a hand-edit to protect from LLM overwrites."""

    timestamp: datetime
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    edit_type: str = "unknown"  # "node_position", "node_data", "edge_add", "edge_delete"
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None

    def is_expired(self, ttl_seconds: int = 30) -> bool:
        """Check if edit protection has expired."""
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > ttl_seconds


class MeetingAgentGamma:
    """
    Session-level agent for managing issue map state and merging edits.

    Responsibilities:
    - Track current_map per session (stored in session.current_map)
    - Apply LLM-generated updates with protection against hand-edits
    - Record hand-edit snapshots and prevent overwrites for TTL seconds
    - Merge function for LLM results + hand-edits
    """

    def __init__(self, edit_protection_ttl_seconds: int = 30):
        """
        Initialize the agent.

        Args:
            edit_protection_ttl_seconds: How long to protect hand-edits from LLM overwrites
        """
        self.edit_protection_ttl = edit_protection_ttl_seconds
        # Per-session edit history (session_id -> [EditSnapshot])
        self.edit_snapshots: Dict[str, List[EditSnapshot]] = {}

    def record_hand_edit(
        self,
        session_id: str,
        edit_type: str,
        node_id: Optional[str] = None,
        edge_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a hand-edit snapshot for protection."""
        if session_id not in self.edit_snapshots:
            self.edit_snapshots[session_id] = []

        snapshot = EditSnapshot(
            timestamp=datetime.utcnow(),
            node_id=node_id,
            edge_id=edge_id,
            edit_type=edit_type,
            old_value=old_value,
            new_value=new_value,
        )
        self.edit_snapshots[session_id].append(snapshot)
        logger.info(
            f"[MeetingAgentGamma] Recorded hand-edit: {edit_type} "
            f"node_id={node_id} edge_id={edge_id} session={session_id}"
        )

    def is_node_protected(self, session_id: str, node_id: str) -> bool:
        """
        Check if a node is protected from LLM overwrites due to recent hand-edits.

        Args:
            session_id: Session identifier
            node_id: Node identifier

        Returns:
            True if node has a recent hand-edit and should be protected
        """
        if session_id not in self.edit_snapshots:
            return False

        # Check for recent edits touching this node
        for snapshot in self.edit_snapshots[session_id]:
            if snapshot.node_id == node_id and not snapshot.is_expired(
                self.edit_protection_ttl
            ):
                return True

        return False

    def merge_llm_with_hand_edits(
        self, session_id: str, llm_map: Dict[str, Any], current_map: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Merge LLM-generated issue map with protected hand-edits.

        Strategy:
        1. If no current_map exists, use LLM map as-is
        2. For nodes: Keep LLM nodes, but preserve hand-edited node data (position, label edits)
        3. For edges: Merge LLM edges with manually-added edges
        4. Skip LLM updates to protected nodes (within edit TTL)

        Args:
            session_id: Session identifier
            llm_map: LLM-generated issue map
            current_map: Current map state (if None, uses llm_map directly)

        Returns:
            Merged issue map
        """
        if current_map is None:
            logger.info(
                f"[MeetingAgentGamma] No current_map for session={session_id}, "
                "using LLM map as-is"
            )
            return llm_map

        logger.info(
            f"[MeetingAgentGamma] Merging LLM map with current_map "
            f"session={session_id}"
        )

        merged = {
            "nodes": [],
            "edges": [],
            "clusters": llm_map.get("clusters", []),
            "metadata": llm_map.get("metadata", current_map.get("metadata", {})),
        }

        # Track node IDs for edge validation
        llm_node_ids = {n.get("id") for n in llm_map.get("nodes", [])}
        current_node_ids = {n.get("id") for n in current_map.get("nodes", [])}

        # Merge nodes: LLM wins, but preserve hand-edits
        for llm_node in llm_map.get("nodes", []):
            node_id = llm_node.get("id")
            if self.is_node_protected(session_id, node_id):
                # Find corresponding current node and preserve its data
                current_node = next(
                    (n for n in current_map.get("nodes", []) if n.get("id") == node_id),
                    None,
                )
                if current_node:
                    logger.debug(
                        f"[MeetingAgentGamma] Preserving hand-edited node {node_id}"
                    )
                    merged["nodes"].append(current_node)
                else:
                    merged["nodes"].append(llm_node)
            else:
                merged["nodes"].append(llm_node)

        # Add any current nodes that don't exist in LLM (hand-created nodes)
        for current_node in current_map.get("nodes", []):
            node_id = current_node.get("id")
            if node_id not in llm_node_ids:
                logger.debug(
                    f"[MeetingAgentGamma] Preserving hand-created node {node_id}"
                )
                merged["nodes"].append(current_node)

        # Merge edges: LLM edges + hand-created edges
        llm_edge_keys = {(e.get("source"), e.get("target")) for e in llm_map.get("edges", [])}
        current_edge_keys = {
            (e.get("source"), e.get("target")) for e in current_map.get("edges", [])
        }

        # Add all LLM edges
        for llm_edge in llm_map.get("edges", []):
            if llm_edge.get("source") in llm_node_ids and llm_edge.get("target") in llm_node_ids:
                merged["edges"].append(llm_edge)

        # Add hand-created edges (not in LLM)
        for current_edge in current_map.get("edges", []):
            edge_key = (current_edge.get("source"), current_edge.get("target"))
            if edge_key not in llm_edge_keys:
                # Validate that both nodes exist in merged
                if (
                    current_edge.get("source") in llm_node_ids
                    and current_edge.get("target") in llm_node_ids
                ):
                    logger.debug(
                        f"[MeetingAgentGamma] Preserving hand-created edge "
                        f"{current_edge.get('source')}->{current_edge.get('target')}"
                    )
                    merged["edges"].append(current_edge)

        logger.info(
            f"[MeetingAgentGamma] Merge complete: "
            f"nodes={len(merged['nodes'])} edges={len(merged['edges'])} "
            f"session={session_id}"
        )
        return merged

    def get_delta(
        self, old_map: Optional[Dict[str, Any]], new_map: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate delta (changed nodes/edges) between old and new maps.

        Used for efficient Socket.IO updates via updateIssue events.

        Args:
            old_map: Previous map state
            new_map: New map state

        Returns:
            Delta with changed_nodes, changed_edges, deleted_node_ids, deleted_edge_ids
        """
        if old_map is None:
            return {
                "changed_nodes": new_map.get("nodes", []),
                "changed_edges": new_map.get("edges", []),
                "deleted_node_ids": [],
                "deleted_edge_ids": [],
            }

        old_nodes = {n.get("id"): n for n in old_map.get("nodes", [])}
        new_nodes = {n.get("id"): n for n in new_map.get("nodes", [])}
        old_edges = {
            (e.get("source"), e.get("target")): e
            for e in old_map.get("edges", [])
        }
        new_edges = {
            (e.get("source"), e.get("target")): e
            for e in new_map.get("edges", [])
        }

        changed_nodes = []
        for node_id, new_node in new_nodes.items():
            old_node = old_nodes.get(node_id)
            if old_node is None or old_node != new_node:
                changed_nodes.append(new_node)

        deleted_node_ids = [nid for nid in old_nodes.keys() if nid not in new_nodes]

        changed_edges = []
        for edge_key, new_edge in new_edges.items():
            old_edge = old_edges.get(edge_key)
            if old_edge is None or old_edge != new_edge:
                changed_edges.append(new_edge)

        deleted_edge_ids = [
            (eid[0], eid[1])
            for eid in old_edges.keys()
            if eid not in new_edges
        ]

        return {
            "changed_nodes": changed_nodes,
            "changed_edges": changed_edges,
            "deleted_node_ids": deleted_node_ids,
            "deleted_edge_ids": deleted_edge_ids,
        }

    def cleanup_expired_edits(self, session_id: str) -> None:
        """Remove expired edit snapshots to prevent memory leak."""
        if session_id not in self.edit_snapshots:
            return

        before_len = len(self.edit_snapshots[session_id])
        self.edit_snapshots[session_id] = [
            snap
            for snap in self.edit_snapshots[session_id]
            if not snap.is_expired(self.edit_protection_ttl)
        ]
        removed = before_len - len(self.edit_snapshots[session_id])
        if removed > 0:
            logger.debug(
                f"[MeetingAgentGamma] Cleaned up {removed} expired edits "
                f"for session={session_id}"
            )


# Global instance
meeting_agent = MeetingAgentGamma()
