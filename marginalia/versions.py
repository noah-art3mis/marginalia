"""Author-controlled passes and text-only saved versions."""

import difflib
from datetime import UTC, datetime

from marginalia.storage import MarginaliaError, Workspace


def _now():
    return datetime.now(UTC).isoformat()


def _snapshot(ws, state, text, label, pass_id=None):
    number = max((int(v["id"][1:]) for v in state["versions"]), default=0) + 1
    # A crash can leave an unreferenced snapshot. Never overwrite it.
    while ws._path(f"versions/v{number:04d}.md").exists():
        number += 1
    entry = {"id": f"v{number:04d}", "label": label, "pass_id": pass_id, "created_at": _now()}
    ws.write_text_file(f"versions/{entry['id']}.md", text)
    state["versions"].append(entry)
    return entry


def start(ws: Workspace, pass_type: str, brief: str = "") -> dict:
    if not pass_type.strip():
        raise MarginaliaError("A pass type is required.")
    with ws.locked():
        state = ws.load_state()
        if state["active_pass"] is not None:
            raise MarginaliaError("An active pass already exists; resume or finish it first.")
        number = max((int(p["id"][4:]) for p in state["passes"]), default=0) + 1
        entry = {
            "id": f"pass{number:04d}",
            "type": pass_type,
            "brief": brief,
            "status": "active",
            "started_at": _now(),
        }
        snapshot = _snapshot(ws, state, ws.read_text(), "Pass start", entry["id"])
        entry["start_version"] = snapshot["id"]
        state["passes"].append(entry)
        state["active_pass"] = entry["id"]
        ws.save_state(state)
        return entry


def _active(state):
    if state["active_pass"] is None:
        raise MarginaliaError("There is no active pass.")
    return next(p for p in state["passes"] if p["id"] == state["active_pass"])


def finish(ws: Workspace) -> dict:
    with ws.locked():
        state = ws.load_state()
        entry = _active(state)
        snapshot = _snapshot(ws, state, ws.read_text(), "Pass finish", entry["id"])
        entry.update(status="finished", finished_at=_now(), end_version=snapshot["id"])
        state["active_pass"] = None
        ws.save_state(state)
        return entry


def resume(ws: Workspace) -> dict:
    with ws.locked():
        return _active(ws.load_state())


def save(ws: Workspace, label: str = "") -> dict:
    with ws.locked():
        state = ws.load_state()
        entry = _snapshot(ws, state, ws.read_text(), label, state["active_pass"])
        ws.save_state(state)
        return entry


def list_versions(ws: Workspace) -> list:
    with ws.locked():
        return ws.load_state()["versions"]


def _version_text(ws, state, version_id):
    if version_id not in {v["id"] for v in state["versions"]}:
        raise MarginaliaError(f"Unknown version: {version_id}")
    return ws.read_text_file(f"versions/{version_id}.md")


def compare(ws: Workspace, version_id: str, other_id: str | None = None) -> str:
    with ws.locked():
        state = ws.load_state()
        old = _version_text(ws, state, version_id)
        new = _version_text(ws, state, other_id) if other_id else ws.read_text()
        return "".join(
            difflib.unified_diff(
                old.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile=version_id,
                tofile=other_id or "current",
            )
        )


def restore(ws: Workspace, version_id: str) -> dict:
    with ws.locked():
        state = ws.load_state()
        restored = _version_text(ws, state, version_id)
        current = ws.read_text()
        updates = {}
        proposals = ws._path("proposals")
        if proposals.exists():
            for path in sorted(proposals.glob("*.json")):
                relative = f"proposals/{path.name}"
                proposal = ws.read_json(relative)
                if proposal.get("status") == "pending":
                    proposal.update(
                        status="outdated", outdated_reason="Document restored from a saved version."
                    )
                    updates[relative] = proposal
        if state["active_pass"]:
            _active(state).update(status="interrupted", finished_at=_now())
        state["active_pass"] = None
        backup = _snapshot(ws, state, current, "Before restore")
        updates["state.json"] = state
        ws.apply_text(current, restored, updates=updates)
        return {"restored": version_id, "backup": backup["id"]}
