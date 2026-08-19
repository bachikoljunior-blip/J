"""Mechanical final-mode integration test for the container isolation path.

This deliberately uses toy tasks and MUST NOT be interpreted as AGI evidence.
It only verifies freeze -> isolated run -> scoring -> evidence verification.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PYTHON = sys.executable
DOMAINS = [
    "language_knowledge",
    "mathematics",
    "software_engineering",
    "data_analysis",
    "planning_decision",
    "novel_task_induction",
]


def call(*args):
    p = subprocess.run([PYTHON, *args], cwd=HERE, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"command failed {args}:\nSTDOUT={p.stdout}\nSTDERR={p.stderr}")
    return p


def main() -> int:
    image = "agi-eval-v1-ci-fixture"
    inspect = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        text=True, capture_output=True, check=True,
    )
    digest = inspect.stdout.strip()
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"unexpected image ID {digest!r}")

    with tempfile.TemporaryDirectory(prefix="agi-eval-ci-") as td:
        td = Path(td)
        manifest = yaml.safe_load((HERE / "manifest-v1.yaml").read_text())
        manifest["status"] = "frozen"
        manifest["claim"] = "CI MECHANICS FIXTURE — NOT AN AGI CLAIM"
        manifest["sample_size_plan"] = {
            "minimum_trials_per_family": 1,
            "justification": "CI fixture only: exercises final-mode mechanics, not statistical adequacy for AGI.",
        }
        mp = td / "manifest.yaml"
        mp.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

        pubs, privs = [], []
        for i, domain in enumerate(DOMAINS):
            token = f"T{i}"
            tid = f"ci-{domain}"
            pubs.append({"task_id": tid, "domain": domain, "family": "ci_mechanics", "prompt": f"Return token: {token}", "budget": {"wall_s": 30}})
            privs.append({"task_id": tid, "grader": {"type": "exact_match", "expected": token}, "human_reference_lower_bound": 0.15, "seed": f"ci-{i}"})
        pubp, privp = td / "public.jsonl", td / "private.jsonl"
        pubp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in pubs), encoding="utf-8")
        privp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in privs), encoding="utf-8")
        prov = td / "provenance.json"
        prov.write_text(json.dumps({"schema": "ci-fixture", "not_agi_evidence": True}, sort_keys=True), encoding="utf-8")
        lock = td / "lock.json"
        call(
            "freeze_eval.py", "--manifest", str(mp), "--public", str(pubp), "--private", str(privp),
            "--candidate-id", "ci-fixture", "--candidate-digest", digest,
            "--generator-provenance", str(prov), "--mode", "final", "--out", str(lock),
        )
        evidence = td / "evidence.json"
        call(
            "run_harness.py", "--manifest", str(mp), "--public", str(pubp), "--private", str(privp),
            "--lock", str(lock), "--candidate-id", "ci-fixture", "--candidate-digest", digest,
            "--adapter-mode", "container", "--adapter", image, "--mode", "final", "--timeout-s", "60",
            "--out", str(evidence),
        )
        call(
            "verify_evidence.py", "--evidence", str(evidence), "--manifest", str(mp), "--public", str(pubp),
            "--private", str(privp), "--lock", str(lock),
        )
        doc = json.loads(evidence.read_text())
        assert doc["summary"]["passed_tasks"] == len(DOMAINS)
        assert doc["summary"]["generality_pass"] is True
        assert doc["summary"]["performance_pass"] is True
        assert all(r["adapter_mode"] == "container" for r in doc["records"])
        assert all(r["isolation"]["network"] == "none" for r in doc["records"])
    print("container final-mode mechanics: PASS (toy CI fixture; not AGI evidence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
