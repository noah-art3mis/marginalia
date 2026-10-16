"""Author-managed local paths and aliases, stored beside document workspaces."""

import fcntl
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

from marginalia.storage import MarginaliaError, Workspace

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def _base(start: Path | None) -> Path:
    return (Path.cwd() if start is None else Path(start)).absolute()


def _guard(path: Path):
    for item in (path.parent, path):
        if item.is_symlink():
            raise MarginaliaError(f"Symlink config paths are not supported: {item}")


def find_config(start: Path | None = None) -> Path | None:
    """Find the nearest local configuration without creating anything."""
    base = _base(start)
    for directory in (base, *base.parents):
        path = directory / ".marginalia" / "config.json"
        _guard(path)
        if path.exists():
            return path
    return None


def _name(name: str):
    if not isinstance(name, str) or _NAME.fullmatch(name) is None:
        raise MarginaliaError(
            "Config names must begin with a letter and use letters, digits, _ or -."
        )


def _value(value: str):
    if not isinstance(value, str) or not value.strip():
        raise MarginaliaError("Config values must be a nonempty string.")


def _read(path: Path) -> dict[str, str]:
    _guard(path)
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise MarginaliaError(f"Invalid config JSON in {path}: {error}") from error
    if not isinstance(values, dict):
        raise MarginaliaError(f"Expected a config object in {path}.")
    try:
        for name, value in values.items():
            _name(name)
            _value(value)
    except MarginaliaError as error:
        raise MarginaliaError(f"Invalid config in {path}: {error}") from error
    return values


def show(start: Path | None = None) -> dict:
    path = find_config(start)
    return {"path": str(path) if path else None, "values": _read(path) if path else {}}


@contextmanager
def _locked(path: Path):
    _guard(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.parent / ".config.lock"
    _guard(lock)
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise MarginaliaError("Local config is busy (locked by another command).") from error
        yield
    finally:
        os.close(descriptor)


def _vault(value: str, path: Path) -> Path:
    supplied = Path(value)
    resolved = (supplied if supplied.is_absolute() else path.parent.parent / supplied).resolve()
    if not resolved.is_dir():
        raise MarginaliaError(f"Configured vault must be an existing directory: {resolved}")
    return resolved


def set_value(name: str, value: str, start: Path | None = None) -> dict:
    _name(name)
    _value(value)
    path = find_config(start) or _base(start) / ".marginalia" / "config.json"
    if name == "vault":
        value = str(_vault(value, path))
    with _locked(path):
        values = _read(path) if path.exists() else {}
        values[name] = value
        Workspace._atomic(path, json.dumps(values, ensure_ascii=False, indent=2) + "\n")
    return {"path": str(path), "values": values}


def unset_value(name: str, start: Path | None = None) -> dict:
    _name(name)
    path = find_config(start)
    if path is None:
        raise MarginaliaError(f"Unknown config name: {name}; no local config exists.")
    with _locked(path):
        values = _read(path)
        if name not in values:
            raise MarginaliaError(f"Unknown config name: {name}")
        del values[name]
        Workspace._atomic(path, json.dumps(values, ensure_ascii=False, indent=2) + "\n")
    return {"path": str(path), "values": values}


def resolve_document(reference: str | Path, start: Path | None = None) -> Path:
    """Resolve explicit @aliases; ordinary paths retain ordinary cwd semantics."""
    if isinstance(reference, str) and reference.startswith("@"):
        name = reference[1:]
        _name(name)
        if name == "vault":
            raise MarginaliaError("The vault setting is a directory, not a document alias.")
        path = find_config(start)
        if path is None:
            raise MarginaliaError(
                "No local config found; configure an alias or use a document path."
            )
        values = _read(path)
        if name not in values:
            raise MarginaliaError(f"Unknown document alias: @{name}")
        document = Path(values[name])
        if not document.is_absolute():
            base = _vault(values["vault"], path) if "vault" in values else path.parent.parent
            document = base / document
        return document.absolute()
    document = Path(reference)
    return document.absolute() if document.is_absolute() else (_base(start) / document).absolute()
