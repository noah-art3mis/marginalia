"""Reviewable operations on exact document passages, independent of any agent."""

import difflib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from marginalia.storage import MarginaliaError


class ProposalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    kind: Literal["replace", "insert", "move", "query"]
    original: str = Field(
        description="Exact nonempty source passage, unique in the current document."
    )
    replacement: str | None = Field(
        default=None,
        description="Exact replacement or inserted text; empty replacement means deletion.",
    )
    explanation: str = Field(description="Reason for the proposal; never inserted into the draft.")
    information_cuts: list[str] = Field(
        default_factory=list, description="Substantive removals requiring separate approval."
    )
    destination: str | None = Field(
        default=None, description="Unique exact anchor before which unchanged source is moved."
    )
    question: str | None = Field(
        default=None, description="Author query; answering never applies a text change."
    )

    @model_validator(mode="after")
    def operation_fields(self):
        if not self.original:
            raise ValueError("original must be a nonempty exact passage")
        if self.kind == "replace":
            if self.replacement is None or self.replacement == self.original:
                raise ValueError("replacement must differ from original")
            if self.destination is not None or self.question is not None:
                raise ValueError("replacement cannot contain move or query fields")
        elif self.kind == "insert":
            if not self.replacement:
                raise ValueError("insert requires nonempty replacement text")
            if self.destination is not None or self.question is not None or self.information_cuts:
                raise ValueError("insert cannot contain destination, question, or information cuts")
        elif self.kind == "move":
            if not self.destination or self.replacement is not None or self.question is not None:
                raise ValueError("move requires destination and unchanged original content")
            if self.information_cuts:
                raise ValueError("a move cannot cut information")
        elif not self.question or self.replacement is not None or self.destination is not None:
            raise ValueError("query requires question without a replacement or destination")
        return self


def _parse(payload):
    try:
        return ProposalInput.model_validate(payload).model_dump()
    except ValidationError as exc:
        raise MarginaliaError(f"Invalid proposal: {exc}") from exc


def _path(identifier):
    import re

    if not re.fullmatch(r"p[0-9]{4,}", identifier):
        raise MarginaliaError("Invalid proposal ID; expected p0001.")
    return f"proposals/{identifier}.json"


def _read(ws, identifier):
    value = ws.read_json(_path(identifier))
    if not isinstance(value, dict) or value.get("id") != identifier:
        raise MarginaliaError("Invalid proposal state.")
    # Validate editable payload on every read; metadata cannot replace proposal meaning.
    _parse({key: value[key] for key in ProposalInput.model_fields if key in value})
    return value


def _unique(text, passage):
    if text.count(passage) != 1:
        raise MarginaliaError("The passage must have one unique exact match in the document.")
    return text.index(passage)


def _move_spans(text, payload):
    start = _unique(text, payload["original"])
    dest = _unique(text, payload["destination"])
    end = start + len(payload["original"])
    if dest == end:
        raise MarginaliaError("Passage is already immediately before this destination.")
    if start <= dest < end or dest <= start < dest + len(payload["destination"]):
        raise MarginaliaError("Move source and destination must not overlap.")
    return start, end, dest


def _evidence(text, payload):
    if payload["kind"] == "move":
        _move_spans(text, payload)
    else:
        _unique(text, payload["original"])
    return {"source_text": text}


def _target_current(before, current, passage):
    if before.count(passage) != 1 or current.count(passage) != 1:
        return False
    if before == current:
        return True
    start = before.index(passage)
    end = start + len(passage)
    new_start = current.index(passage)
    # Anchor the unique exact passage to an unchanged neighboring context or
    # document boundary. Whole-document character matching is both expensive
    # and unable to establish identity when an author copies text elsewhere.
    prefix, suffix = before[max(0, start - 48) : start], before[end : end + 48]
    return (
        (bool(prefix.strip()) and current[max(0, new_start - len(prefix)) : new_start] == prefix)
        or (
            bool(suffix.strip())
            and current[new_start + len(passage) : new_start + len(passage) + len(suffix)] == suffix
        )
        or (start == 0 and new_start == 0)
        or (end == len(before) and new_start + len(passage) == len(current))
    )


def _current(proposal, current):
    before = proposal["source_text"]
    if not _target_current(before, current, proposal["original"]):
        return False
    return proposal["kind"] != "move" or _target_current(before, current, proposal["destination"])


def _status(proposal, current):
    result = dict(proposal)
    if result["status"] == "pending" and not _current(result, current):
        result["status"] = "outdated"
    return result


def _all(ws):
    return [_read(ws, path.stem) for path in sorted((ws.root / "proposals").glob("p*.json"))]


def submit(ws, payload: dict) -> dict:
    parsed = _parse(payload)
    with ws.locked():
        state = ws.load_state()
        pass_id = state.get("active_pass")
        if not pass_id:
            raise MarginaliaError("Start a pass with versions start before submitting proposals.")
        text = ws.read_text()
        evidence = _evidence(text, parsed)
        existing = _all(ws)
        for previous in existing:
            if (
                previous["status"] == "rejected"
                and previous["pass_id"] == pass_id
                and all(
                    previous.get(k) == parsed.get(k)
                    for k in ("kind", "original", "replacement", "destination", "question")
                )
            ):
                raise MarginaliaError(
                    "This proposal was rejected in this pass; inspect the decision."
                )
        number = max((int(p["id"][1:]) for p in existing), default=0) + 1
        proposal = dict(
            parsed,
            **evidence,
            id=f"p{number:04d}",
            pass_id=pass_id,
            status="pending",
            cuts_approved=False,
        )
        ws.write_json(_path(proposal["id"]), proposal)
        return proposal


def revise(ws, identifier, payload: dict) -> dict:
    parsed = _parse(payload)
    with ws.locked():
        proposal = _read(ws, identifier)
        if proposal["status"] != "pending":
            raise MarginaliaError("Only pending proposals can be revised.")
        evidence = _evidence(ws.read_text(), parsed)
        proposal.update(parsed, **evidence, cuts_approved=False)
        ws.write_json(_path(identifier), proposal)
        return proposal


def get(ws, identifier) -> dict:
    with ws.locked():
        return _status(_read(ws, identifier), ws.read_text())


def list_proposals(ws) -> list:
    with ws.locked():
        return list_current(ws)


def list_current(ws) -> list:
    """Read current proposals while the caller holds the workspace lock."""
    text = ws.read_text()
    return [_status(p, text) for p in _all(ws)]


def approve_cuts(ws, identifier) -> dict:
    with ws.locked():
        proposal = _status(_read(ws, identifier), ws.read_text())
        if proposal["status"] != "pending":
            raise MarginaliaError("Only current pending proposals can have cuts approved.")
        proposal["cuts_approved"] = True
        ws.write_json(_path(identifier), proposal)
        return proposal


def accept(ws, identifier) -> dict:
    with ws.locked():
        text = ws.read_text()
        proposal = _status(_read(ws, identifier), text)
        if proposal["status"] != "pending":
            raise MarginaliaError(f"Cannot accept {proposal['status']} proposal.")
        if proposal["kind"] == "query":
            raise MarginaliaError("An author query cannot apply document changes.")
        if proposal["information_cuts"] and not proposal["cuts_approved"]:
            raise MarginaliaError("Information cuts require separate explicit approval.")
        if proposal["kind"] == "move":
            original = proposal["original"]
            start, end, dest = _move_spans(text, proposal)
            if dest < start:
                changed = text[:dest] + original + text[dest:start] + text[end:]
            else:
                changed = text[:start] + text[end:dest] + original + text[dest:]
        elif proposal["kind"] == "insert":
            changed = text.replace(
                proposal["original"], proposal["replacement"] + proposal["original"], 1
            )
        else:
            changed = text.replace(proposal["original"], proposal["replacement"], 1)
        proposal["status"] = "accepted"
        ws.apply_text(text, changed, _path(identifier), proposal)
        return proposal


def reject(ws, identifier, reason="") -> dict:
    with ws.locked():
        proposal = _read(ws, identifier)
        if proposal["status"] != "pending":
            raise MarginaliaError("Only pending proposals can be rejected.")
        proposal.update(status="rejected", reason=reason)
        ws.write_json(_path(identifier), proposal)
        return proposal


def answer(ws, identifier, answer) -> dict:
    with ws.locked():
        proposal = _read(ws, identifier)
        if proposal["kind"] != "query" or proposal["status"] != "pending":
            raise MarginaliaError("Only pending author queries can be answered.")
        proposal.update(status="answered", answer=answer)
        ws.write_json(_path(identifier), proposal)
        return proposal


def render(ws, identifier, mode="diff") -> str:
    proposal = get(ws, identifier)
    lines = [f"Proposal {identifier} ({proposal['status']})", proposal["explanation"]]
    if proposal["information_cuts"]:
        lines += [
            "Information cuts (separate approval required):",
            *[f"- {cut}" for cut in proposal["information_cuts"]],
        ]
    if proposal["kind"] == "move":
        lines += [
            "Move unchanged passage:",
            proposal["original"],
            "Destination (insert before):",
            proposal["destination"],
        ]
    elif proposal["kind"] == "query":
        lines += ["Original:", proposal["original"], "Question:", proposal["question"]]
        if "answer" in proposal:
            lines += ["Answer:", proposal["answer"]]
    elif mode == "markdown":
        lines += [
            "Insert before (anchor retained):" if proposal["kind"] == "insert" else "Original:",
            proposal["original"],
            "Proposed insertion:" if proposal["kind"] == "insert" else "Proposed replacement:",
            "\n".join("> " + line for line in proposal["replacement"].split("\n")),
        ]
    elif mode == "diff":
        replacement = proposal["replacement"]
        if proposal["kind"] == "insert":
            replacement += proposal["original"]
        for line in difflib.unified_diff(
            proposal["original"].splitlines(keepends=True),
            replacement.splitlines(keepends=True),
            fromfile="original",
            tofile="proposed",
            lineterm="\n",
        ):
            lines.append(line.rstrip("\n"))
            if not line.endswith("\n"):
                lines.append("\\ No newline at end of file")
    else:
        raise MarginaliaError("Review mode must be diff or markdown.")
    return "\n".join(lines)
