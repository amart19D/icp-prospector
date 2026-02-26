from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def load_seen_domains(path: str) -> dict[str, str]:
    state_path = Path(path)
    if not state_path.exists():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def save_seen_domains(path: str, seen_domains: dict[str, str]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(seen_domains, indent=2, sort_keys=True), encoding="utf-8")


def mark_seen(path: str, domain: str) -> None:
    seen = load_seen_domains(path)
    if domain not in seen:
        seen[domain] = datetime.now(timezone.utc).date().isoformat()
        save_seen_domains(path, seen)


def reset_seen_domains(path: str) -> None:
    save_seen_domains(path, {})
