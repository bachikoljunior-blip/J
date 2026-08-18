from pathlib import Path
import importlib.util

MODULE_PATH = Path(__file__).parents[1] / "tools" / "freeze_candidate.py"
spec = importlib.util.spec_from_file_location("freeze_candidate", MODULE_PATH)
freeze_candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freeze_candidate)


def test_manifest_is_deterministic_and_ignores_bytecode(tmp_path):
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "a.py").write_text("a=1\n", encoding="utf-8")
    cache = root / "__pycache__"
    cache.mkdir()
    (cache / "a.pyc").write_bytes(b"irrelevant")
    first = freeze_candidate.build_manifest(root, "2026-08-18T12:00:00Z")
    second = freeze_candidate.build_manifest(root, "2026-08-18T12:00:00Z")
    assert first == second
    assert [f["path"] for f in first["files"]] == ["a.py"]
    assert len(first["bundle_sha256"]) == 64


def test_bundle_changes_when_source_changes(tmp_path):
    root = tmp_path / "candidate"
    root.mkdir()
    source = root / "core.py"
    source.write_text("x=1\n", encoding="utf-8")
    before = freeze_candidate.build_manifest(root, "2026-08-18T12:00:00Z")
    source.write_text("x=2\n", encoding="utf-8")
    after = freeze_candidate.build_manifest(root, "2026-08-18T12:00:00Z")
    assert before["bundle_sha256"] != after["bundle_sha256"]
