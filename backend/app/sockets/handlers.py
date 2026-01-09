"""WebSocket/SocketIO handlers."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

import socketio

from app.models.schemas import (
    SocketMessage,
    MessageType,
    ParticipantRole,
)
from app.services.session import session_manager
from app.services.analysis import AnalysisService
from app.services.integrated_analysis import integrated_service
from app.services.meeting_agent import meeting_agent
from app.services.message_buffer import message_buffer

logger = logging.getLogger(__name__)
analysis_service = AnalysisService()

# Track socket-to-participant mapping to recover speaker info when omitted
sid_to_participant: Dict[str, str] = {}
sid_to_session: Dict[str, str] = {}

# SocketIO server instance
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["*"],
    logger=False,
    engineio_logger=False,
)


@sio.event
async def connect(sid: str, environ: Dict[str, Any]) -> None:
    """Handle client connection."""
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {sid}")
    # Cleanup mappings if present
    participant_id = sid_to_participant.pop(sid, None)
    session_id = sid_to_session.pop(sid, None)
    if participant_id and session_id:
        logger.info("Cleaned mapping for sid=%s participant=%s", sid, participant_id)


@sio.event
async def join(sid: str, data: Dict[str, Any]) -> None:
    """Handle participant joining a session."""
    try:
        session_id = data.get("session_id")
        participant_name = data.get("participant_name", "Anonymous")
        role = data.get("role", ParticipantRole.PARTICIPANT.value)

        session = session_manager.get_session(session_id)
        if not session:
            await sio.emit("error", {"message": "Session not found"}, to=sid)
            return

        participant = session_manager.add_participant(
            session_id=session_id,
            participant_name=participant_name,
            role=ParticipantRole(role),
        )

        if not participant:
            await sio.emit("error", {"message": "Could not add participant"}, to=sid)
            return

        # Notify all clients in session
        await sio.emit(
            "participant_joined",
            {
                "session_id": session_id,
                "participant": {
                    "participant_id": participant.participant_id,
                    "name": participant.name,
                    "role": participant.role.value,
                },
            },
            room=session_id,
        )

        # Join SocketIO room
        await sio.enter_room(sid, session_id)
        sid_to_participant[sid] = participant.participant_id
        sid_to_session[sid] = session_id
        logger.info(f"Participant {participant.participant_id} joined session {session_id}")

    except Exception as e:
        logger.error(f"Error in join handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)


@sio.event
async def send_text(sid: str, data: Dict[str, Any]) -> None:
    """Handle text message from participant."""
    try:
        session_id = data.get("session_id")
        participant_id = data.get("participant_id")
        text = data.get("text", "")
        speaker = data.get("speaker") or data.get("speaker_label")

        # Fallback: recover participant/session from socket id when omitted
        if not participant_id:
            participant_id = sid_to_participant.get(sid)
        if not session_id:
            session_id = sid_to_session.get(sid)

        session = session_manager.get_session(session_id) if session_id else None
        if not session:
            await sio.emit("error", {"message": "Session not found"}, to=sid)
            return

        if not participant_id:
            await sio.emit("error", {"message": "Participant not found"}, to=sid)
            return

        # Resolve participant name and fallback speaker label
        participant_name = None
        for p in session.participants:
            if p.participant_id == participant_id:
                participant_name = p.name
                break

        # Fallback: if speaker label is missing, use participant name
        speaker_value = speaker or participant_name or "Unknown"

        # Broadcast text to all participants
        await sio.emit(
            "text_received",
            {
                "session_id": session_id,
                "participant_id": participant_id,
                "participant_name": participant_name or "Unknown",
                "speaker": speaker_value,
                "text": text,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=session_id,
        )

        logger.info(
            "Text from %s [%s]: %d chars", participant_id, speaker_value, len(text)
        )

        # Task 6: Check message buffer for auto-trigger threshold
        threshold_reached, buffer_content = message_buffer.add_message(
            session_id=session_id,
            speaker=speaker_value,
            text=text,
        )

        if threshold_reached and buffer_content:
            logger.info(
                f"[Task 6] Auto-LLM trigger: buffer threshold reached "
                f"({buffer_content['char_count']} chars) for session={session_id}"
            )

            # Convert buffer utterances to analysis format
            utterances_for_analysis = [
                {
                    "utterance_id": f"u{idx}",
                    "speaker": utt["speaker"],
                    "text": utt["text"],
                    "start": idx * 2,
                    "end": idx * 2 + 2,
                    "audio_stats": None,
                }
                for idx, utt in enumerate(buffer_content["utterances"])
            ]

            # Trigger integrated analysis with auto-generated issue_map
            result = integrated_service.analyze_segment_integrated(
                session_id=session_id,
                segment_id=0,  # Auto-trigger segment
                start_sec=0.0,
                end_sec=len(buffer_content["utterances"]) * 2,
                utterances=utterances_for_analysis,
            )

            # Emit updateIssue delta event for real-time map update
            delta = result.get("delta")
            if delta and (
                delta.get("changed_nodes")
                or delta.get("changed_edges")
                or delta.get("deleted_node_ids")
                or delta.get("deleted_edge_ids")
            ):
                await sio.emit(
                    "updateIssue",
                    {
                        "session_id": session_id,
                        "segment_id": 0,
                        "auto_triggered": True,  # Mark as auto-triggered
                        "timestamp": result.get("timestamp"),
                        "changed_nodes": delta.get("changed_nodes", []),
                        "changed_edges": delta.get("changed_edges", []),
                        "deleted_node_ids": delta.get("deleted_node_ids", []),
                        "deleted_edge_ids": delta.get("deleted_edge_ids", []),
                        "full_map": result.get("issue_map"),
                    },
                    room=session_id,
                )
                logger.info(
                    f"[Task 6] Auto-LLM updateIssue sent: "
                    f"changed_nodes={len(delta.get('changed_nodes', []))} "
                    f"changed_edges={len(delta.get('changed_edges', []))}"
                )

            # Reset buffer for next cycle
            message_buffer.reset_buffer(session_id)

    except Exception as e:
        logger.error(f"Error in send_text handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)


@sio.event
async def analyze_segment(sid: str, data: Dict[str, Any]) -> None:
    """Handle segment analysis request."""
    try:
        session_id = data.get("session_id")
        segment_id = data.get("segment_id", 0)
        start_sec = data.get("start_sec", 0.0)
        end_sec = data.get("end_sec", 20.0)
        utterances = data.get("utterances", [])

        session = session_manager.get_session(session_id)
        if not session:
            await sio.emit("error", {"message": "Session not found"}, to=sid)
            return

        # Perform analysis
        result = analysis_service.analyze_segment(
            session_id=session_id,
            segment_id=segment_id,
            start_sec=start_sec,
            end_sec=end_sec,
            utterances=utterances,
        )

        # Add to session
        session_manager.add_segment_result(session_id, result)

        # Emit result to all participants
        await sio.emit(
            "segment_analyzed",
            {
                "session_id": session_id,
                "segment_id": segment_id,
                "result": result.model_dump(),
            },
            room=session_id,
        )

        logger.info(f"Segment {segment_id} analyzed for session {session_id}")

    except Exception as e:
        logger.error(f"Error in analyze_segment handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)


@sio.event
async def leave(sid: str, data: Dict[str, Any]) -> None:
    """Handle participant leaving session."""
    try:
        session_id = data.get("session_id")
        participant_id = data.get("participant_id")

        removed = session_manager.remove_participant(session_id, participant_id)
        if removed:
            await sio.emit(
                "participant_left",
                {
                    "session_id": session_id,
                    "participant_id": participant_id,
                },
                room=session_id,
            )
            await sio.leave_room(sid, session_id)
            sid_to_participant.pop(sid, None)
            sid_to_session.pop(sid, None)
            logger.info(f"Participant {participant_id} left session {session_id}")

    except Exception as e:
        logger.error(f"Error in leave handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)


@sio.event
async def analyze_segment_integrated(sid: str, data: Dict[str, Any]) -> None:
    """
    統合分析を実行（韻律分析 + 認知状態推定 + 介入判定）.
    
    研究計画書の提案手法に基づく高度な分析:
    - 声の調子や話し方から認知状態を推定
    - 個人特性を考慮した予測
    - 必要に応じて介入メッセージを生成
    """
    try:
        session_id = data.get("session_id")
        segment_id = data.get("segment_id", 0)
        start_sec = data.get("start_sec", 0.0)
        end_sec = data.get("end_sec", 20.0)
        utterances = data.get("utterances", [])

        session = session_manager.get_session(session_id)
        if not session:
            await sio.emit("error", {"message": "Session not found"}, to=sid)
            return

        # 統合分析を実行
        result = integrated_service.analyze_segment_integrated(
            session_id=session_id,
            segment_id=segment_id,
            start_sec=start_sec,
            end_sec=end_sec,
            utterances=utterances,
        )

        # セッションに結果を追加
        if "base_analysis" in result:
            session_manager.add_segment_result(session_id, result["base_analysis"])

        # 全参加者に結果を配信
        await sio.emit(
            "segment_analyzed_integrated",
            {
                "session_id": session_id,
                "segment_id": segment_id,
                "result": result,
            },
            room=session_id,
        )

        # Task 5: Emit updateIssue event with delta for efficient map updates
        # This allows frontend to apply only changed nodes/edges instead of full replacement
        delta = result.get("delta")
        if delta and (delta.get("changed_nodes") or delta.get("changed_edges") or 
                     delta.get("deleted_node_ids") or delta.get("deleted_edge_ids")):
            await sio.emit(
                "updateIssue",
                {
                    "session_id": session_id,
                    "segment_id": segment_id,
                    "timestamp": result.get("timestamp"),
                    "changed_nodes": delta.get("changed_nodes", []),
                    "changed_edges": delta.get("changed_edges", []),
                    "deleted_node_ids": delta.get("deleted_node_ids", []),
                    "deleted_edge_ids": delta.get("deleted_edge_ids", []),
                    "full_map": result.get("issue_map"),  # Also send full map for safety
                },
                room=session_id,
            )
            logger.info(
                f"[updateIssue] Delta sent: "
                f"changed_nodes={len(delta.get('changed_nodes', []))} "
                f"changed_edges={len(delta.get('changed_edges', []))} "
                f"deleted_nodes={len(delta.get('deleted_node_ids', []))} "
                f"deleted_edges={len(delta.get('deleted_edge_ids', []))}"
            )

        # 介入が必要な場合は別途通知
        if result.get("intervention", {}).get("needed"):
            await sio.emit(
                "intervention_needed",
                {
                    "session_id": session_id,
                    "segment_id": segment_id,
                    "intervention": result["intervention"],
                },
                room=session_id,
            )

        logger.info(f"Integrated analysis completed for segment {segment_id}")

    except Exception as e:
        logger.error(f"Error in analyze_segment_integrated handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)


@sio.event
async def get_participant_insights(sid: str, data: Dict[str, Any]) -> None:
    """参加者の特性インサイトを取得."""
    try:
        from app.services.participant_profile import profile_service

        participant_id = data.get("participant_id")
        if not participant_id:
            await sio.emit("error", {"message": "participant_id required"}, to=sid)
            return

        insights = profile_service.get_participant_insights(participant_id)

        await sio.emit(
            "participant_insights",
            {
                "participant_id": participant_id,
                "insights": insights,
            },
            to=sid,
        )

    except Exception as e:
        logger.error(f"Error in get_participant_insights handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)


@sio.event
async def hand_edit(sid: str, data: Dict[str, Any]) -> None:
    """
    Task 4: Handle hand-edit snapshots from collaborative map editing.

    Records edit snapshots in MeetingAgentGamma for protection against
    LLM overwrites within the TTL window.

    Args:
        sid: Socket ID
        data: {
            session_id: str,
            edit_type: 'position' | 'node_data' | 'edge_add' | 'edge_delete',
            node_id?: str,
            edge_id?: str,
            old_value?: Dict,
            new_value?: Dict
        }
    """
    try:
        session_id = data.get("session_id")
        edit_type = data.get("edit_type")
        node_id = data.get("node_id")
        edge_id = data.get("edge_id")
        old_value = data.get("old_value")
        new_value = data.get("new_value")

        if not session_id:
            logger.warning("[hand_edit] Missing session_id")
            return

        # Record the hand-edit snapshot for protection
        meeting_agent.record_hand_edit(
            session_id=session_id,
            edit_type=edit_type,
            node_id=node_id,
            edge_id=edge_id,
            old_value=old_value,
            new_value=new_value,
        )

        logger.info(
            f"[hand_edit] Recorded: session={session_id} "
            f"type={edit_type} node={node_id} edge={edge_id}"
        )

        # Broadcast hand_edit event to all participants in session for real-time sync
        await sio.emit(
            "hand_edit_broadcast",
            {
                "session_id": session_id,
                "participant_id": sid_to_participant.get(sid),
                "edit_type": edit_type,
                "node_id": node_id,
                "edge_id": edge_id,
                "new_value": new_value,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=session_id,
        )

    except Exception as e:
        logger.error(f"Error in hand_edit handler: {e}")
        await sio.emit("error", {"message": str(e)}, to=sid)
