import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
PYTHON = sys.executable


def run(*args, cwd=HERE):
    return subprocess.run([PYTHON, *args], cwd=cwd, text=True, capture_output=True)


def test_development_freeze_run_verify(tmp_path):
    lock = tmp_path / "lock.json"
    r = run(
        "freeze_eval.py", "--manifest", "manifest-v1.yaml", "--public", "public-example.jsonl",
        "--private", "private-example.jsonl", "--candidate-id", "example", "--candidate-digest", "dev-local",
        "--mode", "development", "--out", str(lock),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    evidence = tmp_path / "evidence.json"
    r = run(
        "run_harness.py", "--manifest", "manifest-v1.yaml", "--public", "public-example.jsonl",
        "--private", "private-example.jsonl", "--lock", str(lock), "--candidate-id", "example",
        "--candidate-digest", "dev-local", "--adapter-mode", "command", "--adapter", PYTHON,
        str((HERE / "example_adapter.py").resolve()), "--mode", "development", "--out", str(evidence),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(evidence.read_text())
    assert doc["summary"]["passed_tasks"] == 2
    assert doc["summary"]["generality_pass"] is False
    r = run(
        "verify_evidence.py", "--evidence", str(evidence), "--manifest", "manifest-v1.yaml",
        "--public", "public-example.jsonl", "--private", "private-example.jsonl", "--lock", str(lock),
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_final_run_rejects_draft_manifest(tmp_path):
    lock = tmp_path / "lock.json"
    r = run(
        "freeze_eval.py", "--manifest", "manifest-v1.yaml", "--public", "public-example.jsonl",
        "--private", "private-example.jsonl", "--candidate-id", "example", "--candidate-digest", "sha256:" + "a"*64,
        "--mode", "final", "--out", str(lock),
    )
    assert r.returncode != 0


def test_generator_separates_private_grader(tmp_path):
    pub = tmp_path / "pub.jsonl"
    priv = tmp_path / "priv.jsonl"
    prov = tmp_path / "prov.json"
    r = run(
        "generate_taskpack.py", "--spec", "generator-example.yaml", "--manifest", "manifest-v1.yaml",
        "--public-out", str(pub), "--private-out", str(priv), "--provenance-out", str(prov),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    pub_text = pub.read_text()
    assert "expected" not in pub_text
    assert "grader" not in pub_text
    assert "expected" in priv.read_text()
    assert json.loads(prov.read_text())["public_pack_sha256"]
