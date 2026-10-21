from __future__ import annotations

import json
from pathlib import Path

from app_models import SessionState


class CheckpointStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (Path(__file__).parent / "runtime" / "checkpoints")
        self.root.mkdir(parents=True, exist_ok=True)

    def checkpoint_path(self, session_id: str) -> Path:
        return self.root / f"{session_id}.json"

    def save(self, state: SessionState, checkpoint_name: str) -> str:
        state.current_checkpoint = checkpoint_name
        payload = state.to_dict()
        path = self.checkpoint_path(state.session_id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    def load(self, session_id: str) -> SessionState | None:
        path = self.checkpoint_path(session_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return SessionState.from_dict(payload)