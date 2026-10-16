import json

import pytest

from marginalia import config
from marginalia.storage import MarginaliaError


def test_config_is_optional_and_does_not_rebase_direct_documents(tmp_path):
    assert config.show(tmp_path) == {"path": None, "values": {}}
    assert config.resolve_document("draft.md", tmp_path) == tmp_path / "draft.md"
    assert not (tmp_path / ".marginalia").exists()


def test_set_show_and_unset_share_nearest_parent_config(tmp_path):
    child = tmp_path / "notes" / "subfolder"
    child.mkdir(parents=True)
    configured = config.set_value("obras", "Folder/draft.md", tmp_path)
    path = tmp_path / ".marginalia" / "config.json"
    assert configured == {"path": str(path), "values": {"obras": "Folder/draft.md"}}
    assert json.loads(path.read_text()) == {"obras": "Folder/draft.md"}
    assert config.find_config(child) == path
    config.set_value("second", "second.md", child)
    assert config.resolve_document("@obras", child) == tmp_path / "Folder" / "draft.md"
    assert config.resolve_document("draft.md", child) == child / "draft.md"
    assert config.unset_value("second", child)["values"] == {"obras": "Folder/draft.md"}
    with pytest.raises(MarginaliaError, match="Unknown"):
        config.unset_value("second", child)
    assert not (child / ".marginalia").exists()


def test_vault_resolves_relative_to_config_and_aliases_follow_it(tmp_path):
    vault = tmp_path / "My Vault"
    vault.mkdir()
    child = tmp_path / "work"
    child.mkdir()
    config.set_value("vault", "My Vault", tmp_path)
    assert config.show(child)["values"]["vault"] == str(vault)
    config.set_value("obras", "Folder/draft.md", child)
    assert config.resolve_document("@obras", child) == vault / "Folder" / "draft.md"
    absolute = tmp_path / "elsewhere.md"
    config.set_value("other", str(absolute), child)
    assert config.resolve_document("@other", child) == absolute
    with pytest.raises(MarginaliaError, match="vault.*directory"):
        config.resolve_document("@vault", child)


def test_cwd_discovery_and_nearest_config_take_precedence(tmp_path, monkeypatch):
    child = tmp_path / "nested"
    child.mkdir()
    config.set_value("outer", "outer.md", tmp_path)
    local = child / ".marginalia"
    local.mkdir()
    (local / "config.json").write_text('{"inner": "inner.md"}')
    monkeypatch.chdir(child)
    assert config.show()["values"] == {"inner": "inner.md"}
    assert config.resolve_document("@inner") == child / "inner.md"
    with pytest.raises(MarginaliaError, match="Unknown"):
        config.resolve_document("@outer")


def test_manual_plaintext_values_are_not_evaluated(tmp_path):
    folder = tmp_path / ".marginalia"
    folder.mkdir()
    (folder / "config.json").write_text('{"draft": "$HOME/$(echo nope).md"}')
    assert config.resolve_document("@draft", tmp_path) == tmp_path / "$HOME/$(echo nope).md"
    assert config.resolve_document("./@draft.md", tmp_path) == tmp_path / "@draft.md"
    assert config.resolve_document(tmp_path / "@draft.md", tmp_path) == tmp_path / "@draft.md"


@pytest.mark.parametrize("name", ["", "../x", "has space", "@draft", "1draft"])
def test_invalid_names_never_create_files(tmp_path, name):
    with pytest.raises(MarginaliaError, match="name"):
        config.set_value(name, "draft.md", tmp_path)
    assert not (tmp_path / ".marginalia").exists()


def test_empty_values_nonexistent_vault_and_missing_alias_are_clear_errors(tmp_path):
    for value in ("", "   ", 3):
        with pytest.raises(MarginaliaError, match="nonempty string"):
            config.set_value("draft", value, tmp_path)
    with pytest.raises(MarginaliaError, match="directory"):
        config.set_value("vault", "missing", tmp_path)
    with pytest.raises(MarginaliaError, match="No local config"):
        config.resolve_document("@draft", tmp_path)
    config.set_value("draft", "draft.md", tmp_path)
    with pytest.raises(MarginaliaError, match="Unknown"):
        config.resolve_document("@missing", tmp_path)


@pytest.mark.parametrize("contents", ["bad json", "[]", '{"bad": 2}', '{"../bad": "x"}'])
def test_invalid_config_is_not_silently_reset(tmp_path, contents):
    folder = tmp_path / ".marginalia"
    folder.mkdir()
    path = folder / "config.json"
    path.write_text(contents)
    with pytest.raises(MarginaliaError, match="config"):
        config.set_value("new", "draft.md", tmp_path)
    assert path.read_text() == contents


@pytest.mark.parametrize("target", ["directory", "file", "lock"])
def test_symlinks_cannot_redirect_config_reads_or_writes(tmp_path, target):
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "keep.json"
    marker.write_text('{"keep": "original"}')
    folder = tmp_path / ".marginalia"
    if target == "directory":
        folder.symlink_to(outside, target_is_directory=True)
    else:
        folder.mkdir()
        name = "config.json" if target == "file" else ".config.lock"
        (folder / name).symlink_to(marker)
    with pytest.raises(MarginaliaError, match="[Ss]ymlink"):
        config.set_value("draft", "draft.md", tmp_path)
    assert marker.read_text() == '{"keep": "original"}'


def test_locked_config_rejects_concurrent_updates_without_losing_values(tmp_path):
    import fcntl

    config.set_value("first", "first.md", tmp_path)
    lock_path = tmp_path / ".marginalia" / ".config.lock"
    with lock_path.open("r+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(MarginaliaError, match="busy"):
            config.set_value("second", "second.md", tmp_path)
    assert config.show(tmp_path)["values"] == {"first": "first.md"}
    config.set_value("second", "second.md", tmp_path)
    assert config.show(tmp_path)["values"] == {"first": "first.md", "second": "second.md"}


def test_manual_relative_vault_is_relative_to_config_not_invoking_directory(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    child = tmp_path / "other"
    child.mkdir()
    folder = tmp_path / ".marginalia"
    folder.mkdir()
    (folder / "config.json").write_text('{"vault": "Vault", "draft": "draft.md"}')
    assert config.resolve_document("@draft", child) == vault / "draft.md"
