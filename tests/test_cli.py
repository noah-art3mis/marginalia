import json

from typer.testing import CliRunner

from marginalia.cli import app

runner = CliRunner()


def test_discovery_lists_workflows_without_a_document():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    for command in ("guide", "versions", "review", "status"):
        assert command in result.stdout


def test_terminal_workflow_keeps_draft_until_explicit_acceptance(tmp_path):
    document = tmp_path / "draft.md"
    document.write_text("A rather long sentence.\n\nKeep this example.\n")
    path = str(document)
    started = runner.invoke(app, ["versions", "start", path, "--type", "tighten", "--json"])
    assert started.exit_code == 0, started.output
    payload = tmp_path / "proposal.json"
    payload.write_text(
        json.dumps(
            {
                "kind": "replace",
                "original": "A rather long sentence.",
                "replacement": "A long sentence.",
                "explanation": "Remove filler.",
            }
        )
    )
    proposed = runner.invoke(app, ["review", "submit", path, "--file", str(payload), "--json"])
    assert proposed.exit_code == 0, proposed.output
    proposal_id = json.loads(proposed.stdout)["id"]
    assert document.read_text().startswith("A rather long")
    shown = runner.invoke(app, ["review", "show", path, proposal_id])
    assert shown.exit_code == 0, shown.output
    assert "A rather long sentence." in shown.stdout
    accepted = runner.invoke(app, ["review", "accept", path, proposal_id, "--json"])
    assert accepted.exit_code == 0, accepted.output
    assert document.read_text() == "A long sentence.\n\nKeep this example.\n"
    assert runner.invoke(app, ["versions", "finish", path]).exit_code == 0


def test_bad_agent_input_is_a_concise_error_without_document_changes(tmp_path):
    document = tmp_path / "draft.md"
    document.write_text("Original.\n")
    runner.invoke(app, ["versions", "start", str(document), "--type", "cleanup"])
    payload = tmp_path / "invalid.json"
    payload.write_text("not json")
    result = runner.invoke(app, ["review", "submit", str(document), "--file", str(payload)])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Traceback" not in result.output
    assert document.read_text() == "Original.\n"


def test_status_recovers_before_reporting_pass_and_version_context(tmp_path, monkeypatch):
    import pytest

    from marginalia import versions
    from marginalia.storage import Workspace

    document = tmp_path / "draft.md"
    document.write_text("Original text.\n")
    ws = Workspace(document)
    versions.start(ws, "tighten")
    document.write_text("New author writing.\n")
    writer = ws.write_json

    def interrupt_state(relative, data):
        if relative == "state.json":
            raise OSError("interrupted state update")
        writer(relative, data)

    monkeypatch.setattr(ws, "write_json", interrupt_state)
    with pytest.raises(OSError):
        versions.restore(ws, "v0001")
    result = runner.invoke(app, ["status", str(document), "--json"])
    assert result.exit_code == 0, result.output
    state = json.loads(result.stdout)
    assert state["active_pass"] is None
    assert len(state["versions"]) == 2
    assert state["passes"][0]["status"] == "interrupted"
