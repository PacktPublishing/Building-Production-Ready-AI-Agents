import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional


class TraceRecorder:
    def __init__(self) -> None:
        self.events: list[Dict[str, Any]] = []

    def record(self, actor: str, event: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.events.append(
            {
                "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "actor": actor,
                "event": event,
                "details": details or {},
            }
        )

    def save(self, output_dir: str) -> str:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"run-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
        target_path = target_dir / filename
        target_path.write_text(json.dumps(self.events, indent=2), encoding="utf-8")
        return str(target_path)
