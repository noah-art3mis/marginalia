import json

import pytest

from marginalia import versions
from marginalia.storage import MarginaliaError, Workspace


@pytest.fixture
def workspace(tmp_path):
    document = tmp_path / "draft.md"
    document.write_bytes(b"# Draft\r\n\r\nKeep this example.\r\n")
    return Workspace(document)


def test_pass_boundaries_preserve_exact_document_text(workspace):
    original = workspace.read_text()
    started = versions.start(workspace, "tighten", brief="Keep examples.")
    assert started["id"] == "pass0001"
    assert started["brief"] == "Keep examples."
    assert versions.resume(workspace) == started
    workspace.document.write_text("# Draft\n\nKeep example.\n", encoding="utf-8")
    finished = versions.finish(workspace)
    assert finished["status"] == "finished"
    saved = versions.list_versions(workspace)
    assert [entry["id"] for entry in saved] == ["v0001", "v0002"]
    assert workspace.read_text_file("versions/v0001.md") == original
    assert workspace.read_text_file("versions/v0002.md") == workspace.read_text()
    with pytest.raises(MarginaliaError, match="active pass"):
        versions.resume(workspace)


def test_start_does_not_silently_replace_an_active_pass(workspace):
    versions.start(workspace, "tighten")
    with pytest.raises(MarginaliaError, match="active pass"):
        versions.start(workspace, "translate")
    assert len(versions.list_versions(workspace)) == 1


def test_restore_keeps_current_writing_and_invalidates_pending_proposals(workspace):
    original = workspace.read_text()
    versions.start(workspace, "tighten")
    workspace.write_json("proposals/p0001.json", {"id": "p0001", "status": "pending"})
    workspace.write_json("proposals/p0002.json", {"id": "p0002", "status": "rejected"})
    newer = "New writing with an example.\n"
    workspace.document.write_text(newer, encoding="utf-8")
    result = versions.restore(workspace, "v0001")
    assert result["restored"] == "v0001"
    assert workspace.read_text() == original
    assert workspace.read_text_file(f"versions/{result['backup']}.md") == newer
    assert workspace.read_json("proposals/p0001.json")["status"] == "outdated"
    assert workspace.read_json("proposals/p0002.json")["status"] == "rejected"
    assert workspace.load_state()["active_pass"] is None


def test_compare_versions_and_current_text(workspace):
    versions.save(workspace, "before")
    workspace.document.write_text("Changed text.\n", encoding="utf-8")
    assert "-Keep this example." in versions.compare(workspace, "v0001")
    assert "+Changed text." in versions.compare(workspace, "v0001")
    versions.save(workspace, "after")
    assert "+Changed text." in versions.compare(workspace, "v0001", "v0002")


def test_corrupt_state_is_not_reset_and_unknown_restore_leaves_text_alone(workspace):
    original = workspace.read_text()
    with pytest.raises(MarginaliaError, match="Unknown version"):
        versions.restore(workspace, "v9999")
    assert workspace.read_text() == original
    workspace.root.mkdir(parents=True, exist_ok=True)
    (workspace.root / "state.json").write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(MarginaliaError, match="state"):
        versions.save(workspace)
    assert workspace.read_text() == original


def test_storage_rejects_traversal_and_symlinks(workspace, tmp_path):
    with pytest.raises(MarginaliaError):
        workspace.write_text_file("../escape.md", "bad")
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace.root.mkdir(parents=True, exist_ok=True)
    (workspace.root / "versions").symlink_to(outside, target_is_directory=True)
    with pytest.raises(MarginaliaError, match="[Ss]ymlink"):
        versions.save(workspace)
    assert list(outside.iterdir()) == []


def test_lock_contention_fails_and_lock_releases_after_error(workspace):
    with workspace.locked():
        with pytest.raises(MarginaliaError, match="[Bb]usy|locked"):
            with Workspace(workspace.document).locked():
                pass
    with pytest.raises(RuntimeError):
        with workspace.locked():
            raise RuntimeError("interrupted")
    with workspace.locked():
        pass


def test_corrupt_version_ids_fail_with_clear_error(workspace):
    workspace.write_json(
        "state.json",
        {"schema_version": 1, "passes": [], "active_pass": None, "versions": [{"id": "bogus"}]},
    )
    with pytest.raises(MarginaliaError, match="state"):
        versions.save(workspace)


def test_interrupted_apply_recovers_decision_without_losing_new_text(workspace, monkeypatch):
    original = workspace.read_text()
    proposal = {"id": "p0001", "status": "pending"}
    workspace.write_json("proposals/p0001.json", proposal)
    writer = workspace.write_json

    def interrupt_metadata(relative, data):
        if relative == "proposals/p0001.json":
            raise OSError("simulated interruption")
        writer(relative, data)

    with workspace.locked():
        monkeypatch.setattr(workspace, "write_json", interrupt_metadata)
        with pytest.raises(OSError):
            workspace.apply_text(
                original,
                "Accepted text.\n",
                "proposals/p0001.json",
                {"id": "p0001", "status": "accepted"},
            )
    assert workspace.read_text() == "Accepted text.\n"
    with Workspace(workspace.document).locked():
        assert workspace.read_json("proposals/p0001.json")["status"] == "accepted"
    assert original in [
        p.read_bytes().decode("utf-8") for p in (workspace.root / "recovery").glob("*.md")
    ]


def test_apply_refuses_changed_document(workspace):
    original = workspace.read_text()
    workspace.document.write_text("Author changed this.\n", encoding="utf-8")
    with workspace.locked():
        with pytest.raises(MarginaliaError, match="changed"):
            workspace.apply_text(original, "Agent text.\n")
    assert workspace.read_text() == "Author changed this.\n"
