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


def test_saved_local_reference_works_across_pass_and_review_commands(tmp_path, monkeypatch):
    vault = tmp_path / "My vault"
    vault.mkdir()
    document = vault / "draft.md"
    document.write_text("It could possibly help.\n")
    monkeypatch.chdir(vault)
    result = runner.invoke(app, ["config", "set", "vault", str(vault)])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["config", "set", "draft", "draft.md"])
    assert result.exit_code == 0, result.output
    config = json.loads((vault / ".marginalia" / "config.json").read_text())
    assert config == {"vault": str(vault), "draft": "draft.md"}
    status = runner.invoke(app, ["status", "@draft", "--json"])
    assert status.exit_code == 0, status.output
    assert json.loads(status.stdout)["document"] == str(document)
    started = runner.invoke(app, ["versions", "start", "@draft", "--type", "tighten"])
    assert started.exit_code == 0, started.output
    payload = tmp_path / "proposal.json"
    payload.write_text(
        json.dumps(
            {
                "kind": "replace",
                "original": "It could possibly help.",
                "replacement": "It could help.",
                "explanation": "Remove filler.",
            }
        )
    )
    submitted = runner.invoke(app, ["review", "submit", "@draft", "--file", str(payload), "--json"])
    assert submitted.exit_code == 0, submitted.output
    identifier = json.loads(submitted.stdout)["id"]
    accepted = runner.invoke(app, ["review", "accept", "@draft", identifier])
    assert accepted.exit_code == 0, accepted.output
    assert document.read_text() == "It could help.\n"
    assert runner.invoke(app, ["versions", "finish", "@draft"]).exit_code == 0
    assert (vault / ".marginalia" / "draft.md" / "versions" / "v0001.md").read_text() == (
        "It could possibly help.\n"
    )


def test_local_config_can_be_inspected_and_removed_without_editing_the_draft(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["config", "set", "draft", "draft.md"]).exit_code == 0
    result = runner.invoke(app, ["config", "show", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["values"]["draft"] == "draft.md"
    assert runner.invoke(app, ["config", "unset", "draft"]).exit_code == 0
    result = runner.invoke(app, ["status", "@draft"])
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_literal_at_filename_can_be_referred_to_with_an_explicit_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    document = tmp_path / "@draft.md"
    document.write_text("Literal filename.\n")
    result = runner.invoke(app, ["status", "./@draft.md", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["document"] == str(document)
