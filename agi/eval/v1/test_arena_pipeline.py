import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
PYTHON = sys.executable


def run(*args):
    return subprocess.run([PYTHON, *args], cwd=HERE, text=True, capture_output=True)


def test_workspace_arena_development_pipeline(tmp_path):
    lock = tmp_path / "lock.json"
    r = run(
        "freeze_eval.py", "--manifest", "manifest-v1.yaml", "--public", "workspace-example-public.jsonl",
        "--private", "workspace-example-private.jsonl", "--candidate-id", "workspace-example",
        "--candidate-digest", "dev-workspace", "--mode", "development", "--out", str(lock),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    evidence = tmp_path / "evidence.json"
    r = run(
        "run_arena_harness.py", "--manifest", "manifest-v1.yaml", "--public", "workspace-example-public.jsonl",
        "--private", "workspace-example-private.jsonl", "--lock", str(lock), "--candidate-id", "workspace-example",
        "--candidate-digest", "dev-workspace", "--adapter-mode", "command", "--adapter", PYTHON,
        str((HERE / "example_workspace_adapter.py").resolve()), "--mode", "development", "--out", str(evidence),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(evidence.read_text())
    assert doc["summary"]["passed_tasks"] == 1
    assert doc["records"][0]["arena_grader"]["passed"] is True
    assert doc["records"][0]["autonomy_metrics"]["intervention_count"] == 0
    assert doc["summary"]["autonomy_metrics"]["autonomy_gate_assessed"] is False
    assert doc["summary"]["generality_pass"] is False
    r = run(
        "verify_evidence.py", "--evidence", str(evidence), "--manifest", "manifest-v1.yaml",
        "--public", "workspace-example-public.jsonl", "--private", "workspace-example-private.jsonl",
        "--lock", str(lock),
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_final_arena_rejects_non_none_network(tmp_path):
    # Final manifest is deliberately draft, so this also checks fail-closed final startup.
    lock = tmp_path / "lock.json"
    r = run(
        "freeze_eval.py", "--manifest", "manifest-v1.yaml", "--public", "workspace-example-public.jsonl",
        "--private", "workspace-example-private.jsonl", "--candidate-id", "workspace-example",
        "--candidate-digest", "sha256:" + "a" * 64, "--mode", "final", "--out", str(lock),
    )
    assert r.returncode != 0
