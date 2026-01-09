"""Migration script to load JSONL data from artifacts into SQLite database."""

import os
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.db import SessionLocal, init_db
from app.database.models import (
    SessionModel,
    ParticipantStateModel,
)

logger = logging.getLogger(__name__)


def migrate_prosody_history_to_db():
    """Load prosody_history JSONL files and insert into database."""
    init_db()  # Ensure tables exist
    db = SessionLocal()

    try:
        prosody_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "artifacts",
            "prosody_history",
        )

        if not os.path.exists(prosody_dir):
            logger.info("No prosody_history directory found. Skipping migration.")
            return

        jsonl_files = [f for f in os.listdir(prosody_dir) if f.endswith(".jsonl")]
        logger.info(f"Found {len(jsonl_files)} JSONL files to migrate.")

        for filename in jsonl_files:
            session_id = filename.replace(".jsonl", "")
            filepath = os.path.join(prosody_dir, filename)

            # Create or get session
            session_obj = db.query(SessionModel).filter(
                SessionModel.session_id == session_id
            ).first()
            if session_obj is None:
                session_obj = SessionModel(
                    session_id=session_id,
                    title=f"Migrated Session ({session_id})",
                    description="Migrated from JSONL artifacts",
                    creator_name="migration",
                )
                db.add(session_obj)
                db.flush()

            # Read and insert participant states
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        for state in record.get("participant_states", []):
                            ps = ParticipantStateModel(
                                session_id=session_id,
                                segment_id=record.get("segment_id", 0),
                                speaker=state.get("speaker", "unknown"),
                                text=state.get("text"),
                                prosody_features=state.get("prosody", {}),
                                cognitive_state=state.get("cognitive_state", {}),
                                created_at=datetime.fromisoformat(
                                    record.get("timestamp", datetime.utcnow().isoformat())
                                ),
                            )
                            db.add(ps)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing line in {filename}: {e}")
                        continue

        db.commit()
        logger.info(
            f"Successfully migrated {len(jsonl_files)} prosody history files to database."
        )

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_prosody_history_to_db()
