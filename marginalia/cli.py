"""Terminal operations over the shared document workflow."""

from __future__ import annotations

import json
from functools import wraps
from importlib.resources import files
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console

from marginalia import proposals, versions
from marginalia.storage import MarginaliaError, Workspace

app = typer.Typer(
    help="Review agent proposals and keep recoverable Markdown versions.",
    invoke_without_command=True,
    pretty_exceptions_enable=False,
)
version_app = typer.Typer(
    help="Start, resume, and finish passes; compare and recover saved text.", no_args_is_help=True
)
review_app = typer.Typer(
    help="Submit, inspect, discuss, and decide on proposals.", no_args_is_help=True
)
app.add_typer(version_app, name="versions")
app.add_typer(review_app, name="review")
console = Console(markup=False, highlight=False)
Json = Annotated[bool, typer.Option("--json", help="Output structured data for agents.")]


def operation(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (MarginaliaError, OSError, ValueError, ValidationError) as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(1) from None

    return guarded


def emit(value, structured=False):
    if structured:
        typer.echo(json.dumps(value, ensure_ascii=False))
    else:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        # Agent content is literal text, never Rich markup or terminal control sequences.
        text = "".join(c for c in text if c in "\n\t" or (ord(c) >= 32 and ord(c) != 127))
        console.print(text, soft_wrap=True)


@app.callback()
def discover(ctx: typer.Context):
    """Run without arguments to discover available workflows."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
@operation
def guide(topic: Annotated[str, typer.Argument()] = "workflow"):
    """Read bundled editorial instructions. Example: marginalia guide tighten."""
    available = {
        p.stem: p
        for p in files("marginalia").joinpath("guides").iterdir()
        if p.name.endswith(".md")
    }
    if topic not in available:
        raise MarginaliaError(f"Unknown guide {topic!r}. Available: {', '.join(sorted(available))}")
    emit(available[topic].read_text(encoding="utf-8"))


@app.command()
@operation
def status(document: Path, as_json: Json = False):
    """Inspect a document, active pass, proposals, versions, and editorial context."""
    ws = Workspace(document)
    with ws.locked():
        state = ws.load_state()
        result = {
            "document": str(ws.document),
            "storage": str(ws.root),
            "active_pass": state["active_pass"],
            "passes": state["passes"],
            "versions": state["versions"],
            "proposals": proposals.list_current(ws),
            "context": {},
        }
        for name in ("brief.md", "style.md", "notes.md"):
            path = ws.root / name
            if path.exists():
                result["context"][name] = ws.read_text_file(name)
    result["next"] = [
        "marginalia guide",
        "marginalia review list DOCUMENT",
        "marginalia versions --help",
    ]
    emit(result, as_json)


@version_app.command("start")
@operation
def start(
    document: Path,
    pass_type: Annotated[str, typer.Option("--type")],
    brief: str = "",
    as_json: Json = False,
):
    """Save starting text and begin a pass. Example: versions start draft.md --type tighten."""
    emit(versions.start(Workspace(document), pass_type, brief), as_json)


@version_app.command("finish")
@operation
def finish(document: Path, as_json: Json = False):
    """Save the result and finish the active pass."""
    emit(versions.finish(Workspace(document)), as_json)


@version_app.command("resume")
@operation
def resume(document: Path, as_json: Json = False):
    """Inspect the active pass and continue it through the agent conversation."""
    emit(versions.resume(Workspace(document)), as_json)


@version_app.command("save")
@operation
def save(document: Path, label: str = "", as_json: Json = False):
    """Save a text-only recovery version without finishing a pass."""
    emit(versions.save(Workspace(document), label), as_json)


@version_app.command("list")
@operation
def list_versions(document: Path, as_json: Json = False):
    """List recoverable text versions."""
    emit(versions.list_versions(Workspace(document)), as_json)


@version_app.command("compare")
@operation
def compare(
    document: Path, version_id: str, other_id: Annotated[str | None, typer.Argument()] = None
):
    """Compare a saved version with current text or another saved version."""
    emit(versions.compare(Workspace(document), version_id, other_id))


@version_app.command("restore")
@operation
def restore(document: Path, version_id: str, as_json: Json = False):
    """Restore saved text, preserving current text first. Requires author approval."""
    emit(versions.restore(Workspace(document), version_id), as_json)


def read_payload(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MarginaliaError("Proposal input must be a JSON object. See review schema.")
    return payload


@review_app.command("submit")
@operation
def submit(document: Path, file: Annotated[Path, typer.Option("--file")], as_json: Json = False):
    """Store a proposal without changing the document.

    Example: review submit draft.md --file p.json.
    """
    emit(proposals.submit(Workspace(document), read_payload(file)), as_json)


@review_app.command("revise")
@operation
def revise(
    document: Path,
    proposal_id: str,
    file: Annotated[Path, typer.Option("--file")],
    as_json: Json = False,
):
    """Replace a pending proposal after discussion; previous cut approval is cleared."""
    emit(proposals.revise(Workspace(document), proposal_id, read_payload(file)), as_json)


@review_app.command("list")
@operation
def list_proposals(document: Path, as_json: Json = False):
    """List proposals and decisions, including outdated targets."""
    emit(proposals.list_proposals(Workspace(document)), as_json)


@review_app.command("show")
@operation
def show(document: Path, proposal_id: str, mode: str = "diff", as_json: Json = False):
    """Read one proposal as diff, Markdown comparison, or JSON."""
    if mode not in ("diff", "markdown"):
        raise MarginaliaError("Review mode must be diff or markdown.")
    ws = Workspace(document)
    emit(
        proposals.get(ws, proposal_id) if as_json else proposals.render(ws, proposal_id, mode),
        as_json,
    )


@review_app.command("approve-cuts")
@operation
def approve_cuts(document: Path, proposal_id: str, as_json: Json = False):
    """Record explicit author approval of declared information cuts without applying text."""
    emit(proposals.approve_cuts(Workspace(document), proposal_id), as_json)


@review_app.command("accept")
@operation
def accept(document: Path, proposal_id: str, as_json: Json = False):
    """Apply the reviewed proposal after explicit author approval and target validation."""
    emit(proposals.accept(Workspace(document), proposal_id), as_json)


@review_app.command("reject")
@operation
def reject(document: Path, proposal_id: str, reason: str = "", as_json: Json = False):
    """Reject a proposal; a reason is optional and never becomes a global style rule."""
    emit(proposals.reject(Workspace(document), proposal_id, reason), as_json)


@review_app.command("answer")
@operation
def answer(document: Path, proposal_id: str, answer_text: str, as_json: Json = False):
    """Answer an author query without approving a document change."""
    emit(proposals.answer(Workspace(document), proposal_id, answer_text), as_json)


@review_app.command("schema")
@operation
def schema():
    """Print the authoritative proposal JSON schema for external agents."""
    emit(proposals.ProposalInput.model_json_schema(), True)
