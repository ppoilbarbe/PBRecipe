"""Tests de AppConfig et DialogDirs (persistance YAML)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pbrecipe.config.app_config import AppConfig
from pbrecipe.config.dialog_dirs import DialogDirs


@pytest.fixture
def xdg(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


def test_load_missing_returns_defaults(xdg):
    cfg = AppConfig.load()
    assert cfg.log_level == "INFO"
    assert cfg.recent_files == []
    assert cfg.php_debug is False


def test_save_then_load_roundtrip(xdg):
    cfg = AppConfig.load()
    cfg.log_level = "DEBUG"
    cfg.php_debug = True
    cfg.window_geometry = {"x": 10}
    cfg.dialog_geometries = {"d": {"w": 5}}
    cfg.splitter_sizes = [100, 200]
    cfg.toolbar_state = "abc"
    cfg.grammalecte_enabled = False
    cfg.add_recent("/tmp/foo.yaml")
    cfg.save()

    loaded = AppConfig.load()
    assert loaded.log_level == "DEBUG"
    assert loaded.php_debug is True
    assert loaded.window_geometry == {"x": 10}
    assert loaded.dialog_geometries == {"d": {"w": 5}}
    assert loaded.splitter_sizes == [100, 200]
    assert loaded.toolbar_state == "abc"
    assert loaded.grammalecte_enabled is False
    assert loaded.recent_files


def test_load_invalid_level_falls_back(xdg):
    path = xdg / "pbrecipe" / "app.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("log_level: BOGUS\n", encoding="utf-8")
    assert AppConfig.load().log_level == "INFO"


def test_load_corrupt_file_returns_defaults(xdg):
    path = xdg / "pbrecipe" / "app.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("log_level: [unterminated\n", encoding="utf-8")
    assert AppConfig.load().log_level == "INFO"


def test_load_non_dict_types_sanitised(xdg):
    path = xdg / "pbrecipe" / "app.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "window_geometry: notadict\ndialog_geometries: 5\nsplitter_sizes: notalist\n",
        encoding="utf-8",
    )
    cfg = AppConfig.load()
    assert cfg.window_geometry == {}
    assert cfg.dialog_geometries == {}
    assert cfg.splitter_sizes == []


def test_recent_files_dedup_and_order(xdg):
    cfg = AppConfig()
    cfg.add_recent("/a/b.yaml")
    cfg.add_recent("/c/d.yaml")
    cfg.add_recent("/a/b.yaml")
    assert cfg.recent_files[0] == str(Path("/a/b.yaml").resolve())
    assert len(cfg.recent_files) == 2
    assert cfg.last_file == str(Path("/a/b.yaml").resolve())


def test_recent_files_max(xdg):
    cfg = AppConfig()
    for i in range(15):
        cfg.add_recent(f"/x/{i}.yaml")
    assert len(cfg.recent_files) == 10


def test_clear_recent(xdg):
    cfg = AppConfig()
    cfg.add_recent("/a.yaml")
    cfg.clear_recent()
    assert cfg.recent_files == []
    assert cfg.last_file is None


# --- DialogDirs ---


def test_dialog_dirs_missing(xdg):
    dd = DialogDirs.load()
    assert dd.get("missing", "fallback") == "fallback"


def test_dialog_dirs_record_file(xdg):
    dd = DialogDirs.load()
    dd.record("export", "/home/user/data/file.yaml")
    assert dd.get("export") == "/home/user/data"
    reloaded = DialogDirs.load()
    assert reloaded.get("export") == "/home/user/data"


def test_dialog_dirs_record_dir(xdg):
    dd = DialogDirs.load()
    dd.record("php", "/home/user/site", is_dir=True)
    assert dd.get("php") == "/home/user/site"


def test_dialog_dirs_record_empty_noop(xdg):
    dd = DialogDirs.load()
    dd.record("k", "")
    assert dd.get("k") == ""


def test_dialog_dirs_record_same_noop(xdg):
    dd = DialogDirs.load()
    dd.record("k", "/a/b/file", is_dir=False)
    dd.record("k", "/a/b/file2", is_dir=False)
    assert dd.get("k") == "/a/b"


def test_dialog_dirs_corrupt(xdg):
    path = xdg / "pbrecipe" / "dialog_dirs.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("[broken\n", encoding="utf-8")
    assert DialogDirs.load().get("any", "fb") == "fb"
