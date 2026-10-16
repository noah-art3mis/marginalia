"""Plaintext workspace storage and guarded document transactions."""

import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


class MarginaliaError(Exception):
    """An operation needs the author's attention before it can proceed."""


class Workspace:
    def __init__(self, document: str | Path):
        supplied = Path(document).absolute()
        if supplied.is_symlink():
            raise MarginaliaError("Symlink documents are not supported.")
        self.document = supplied.resolve()
        if not self.document.is_file():
            raise MarginaliaError(f"Document does not exist: {self.document}")
        self.root = self.document.parent / ".marginalia" / self.document.name

    def _path(self, relative: str) -> Path:
        part = Path(relative)
        if part.is_absolute() or ".." in part.parts or not part.parts:
            raise MarginaliaError("Workspace paths must stay inside the document workspace.")
        result = self.root / part
        current = self.document.parent
        for component in result.relative_to(current).parts:
            current = current / component
            if current.is_symlink():
                raise MarginaliaError(f"Symlink workspace paths are not supported: {current}")
        return result

    def read_text(self) -> str:
        if self.document.is_symlink():
            raise MarginaliaError("Symlink documents are not supported.")
        return self.document.read_bytes().decode("utf-8")

    def read_text_file(self, relative: str) -> str:
        return self._path(relative).read_bytes().decode("utf-8")

    def write_text_file(self, relative: str, text: str):
        self._atomic(self._path(relative), text)

    @staticmethod
    def _atomic(path: Path, text: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(text.encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                os.chmod(name, path.stat().st_mode & 0o777)
            os.replace(name, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def read_json(self, relative: str) -> dict:
        try:
            result = json.loads(self.read_text_file(relative))
        except (ValueError, UnicodeError) as error:
            raise MarginaliaError(f"Invalid JSON in {relative}: {error}") from error
        if not isinstance(result, dict):
            raise MarginaliaError(f"Expected a JSON object in {relative}.")
        return result

    def write_json(self, relative: str, data: dict):
        self.write_text_file(relative, json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def load_state(self) -> dict:
        if not self._path("state.json").exists():
            if self._path("versions").exists() and any(self._path("versions").iterdir()):
                raise MarginaliaError(
                    "Missing state file with existing saved versions; inspect workspace."
                )
            return {"schema_version": 1, "passes": [], "active_pass": None, "versions": []}
        state = self.read_json("state.json")
        self._validate_state(state)
        return state

    @staticmethod
    def _validate_state(state):
        if state.get("schema_version") != 1:
            raise MarginaliaError("Unsupported or corrupt state schema.")
        for key in ("passes", "versions"):
            values = state.get(key)
            if not isinstance(values, list) or any(
                not isinstance(v, dict) or not isinstance(v.get("id"), str) for v in values
            ):
                raise MarginaliaError(f"Invalid state {key}.")
            pattern = r"pass[0-9]{4,}" if key == "passes" else r"v[0-9]{4,}"
            if any(re.fullmatch(pattern, v["id"]) is None for v in values):
                raise MarginaliaError(f"Invalid state {key} identifier.")
            if len({v["id"] for v in values}) != len(values):
                raise MarginaliaError(f"Duplicate state {key} identifiers.")
        active = state.get("active_pass")
        if active is not None and (
            not isinstance(active, str) or active not in {p["id"] for p in state["passes"]}
        ):
            raise MarginaliaError("Invalid active pass in state.")

    def save_state(self, state: dict):
        self._validate_state(state)
        self.write_json("state.json", state)

    @contextmanager
    def locked(self):
        path = self._path(".lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise MarginaliaError("Workspace is busy (locked by another command).") from error
            self._recover()
            yield
        finally:
            os.close(descriptor)

    def _recover(self):
        path = self._path("pending-transaction.json")
        if not path.exists():
            return
        transaction = self.read_json("pending-transaction.json")
        current = self.read_text()
        if current == transaction["new"]:
            for relative, value in transaction["updates"].items():
                self.write_json(relative, value)
        elif current != transaction["expected"]:
            raise MarginaliaError(
                "Interrupted transaction conflicts with current writing. "
                "Inspect pending-transaction.json and recovery copies."
            )
        path.unlink()

    def apply_text(
        self,
        expected_text: str,
        new_text: str,
        relative_json: str | None = None,
        updated_proposal: dict | None = None,
        *,
        updates: dict | None = None,
    ):
        """Caller holds locked(). External editors must save before applying."""
        changes = dict(updates or {})
        if relative_json is not None:
            changes[relative_json] = updated_proposal
        for relative in changes:
            self._path(relative)
        if self.read_text() != expected_text:
            raise MarginaliaError("Document changed; inspect the current text before applying.")
        self.write_text_file(f"recovery/{uuid4().hex}.md", expected_text)
        self.write_json(
            "pending-transaction.json",
            {"expected": expected_text, "new": new_text, "updates": changes},
        )
        # Check again after durable recovery preparation. Non-cooperating external
        # writers can still race this final check and replace; no filesystem CAS exists.
        if self.read_text() != expected_text:
            self._path("pending-transaction.json").unlink()
            raise MarginaliaError("Document changed while preparing the edit; retry after saving.")
        self._atomic(self.document, new_text)
        for relative, value in changes.items():
            self.write_json(relative, value)
        self._path("pending-transaction.json").unlink()

    def replace_document(self, expected_text: str, new_text: str):
        self.apply_text(expected_text, new_text)
