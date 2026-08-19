"""Mechanical final-mode test for candidate-none + AF_UNIX broker + isolated provider.

The tasks, credential, and service are toy CI fixtures. Passing this script is
execution evidence for the evaluation transport only and is not AGI evidence.
"""
from __future__ import annotations

import json
import os
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


def call(*args, env=None):
    p = subprocess.run(
        [PYTHON, *args],
        cwd=HERE,
        text=True,
        capture_output=True,
        env=env,
    )
    if p.returncode != 0:
        raise RuntimeError(f"command failed {args}:\nSTDOUT={p.stdout}\nSTDERR={p.stderr}")
    return p


def image_digest(image: str) -> str:
    p = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        text=True,
        capture_output=True,
        check=True,
    )
    digest = p.stdout.strip()
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"unexpected image ID for {image}: {digest!r}")
    return digest


def main() -> int:
    candidate_image = "agi-eval-v1-ci-broker-candidate"
    provider_image = "agi-eval-v1-ci-provider"
    service_image = "agi-eval-v1-ci-service"
    candidate_digest = image_digest(candidate_image)
    provider_digest = image_digest(provider_image)
    network = f"agi-eval-provider-ci-{os.getpid()}"
    service_name = f"agi-eval-service-ci-{os.getpid()}"
    fixture_secret = "ci-evaluator-credential-not-agi-evidence"

    subprocess.run(["docker", "network", "create", network], check=True, text=True, capture_output=True)
    try:
        subprocess.run(
            [
                "docker", "run", "-d", "--rm",
                "--name", service_name,
                "--network", network,
                "--network-alias", "fixture-service",
                "--read-only",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "--pids-limit", "64",
                "--memory", "128m",
                "--cpus", "0.5",
                "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m",
                "--env", f"EXPECTED_TOKEN={fixture_secret}",
                service_image,
            ],
            check=True,
            text=True,
            capture_output=True,
        )

        with tempfile.TemporaryDirectory(prefix="agi-eval-broker-ci-") as td_raw:
            td = Path(td_raw)
            manifest = yaml.safe_load((HERE / "manifest-v1.yaml").read_text())
            manifest["status"] = "frozen"
            manifest["claim"] = "CI BROKER/PROVIDER MECHANICS FIXTURE — NOT AN AGI CLAIM"
            manifest["sample_size_plan"] = {
                "minimum_trials_per_family": 1,
                "justification": "CI fixture only: exercises final broker/provider isolation, not statistical adequacy for AGI.",
            }
            mp = td / "manifest.yaml"
            mp.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

            pubs, privs = [], []
            for i, domain in enumerate(DOMAINS):
                tid = f"ci-broker-{domain}"
                pubs.append({
                    "task_id": tid,
                    "domain": domain,
                    "family": "ci_broker_provider_mechanics",
                    "prompt": "Use only the evaluator broker to validate calculator, provider, and denied-tool behavior.",
                    "budget": {"wall_s": 30, "memory_mb": 256, "cpus": 1.0},
                    "arena": {
                        "network": "none",
                        "broker": {
                            "tools": ["calculator", "secret.check"],
                            "max_requests": 4,
                            "max_wall_s": 30,
                            "max_result_bytes": 262144,
                            "cost_per_call": {"secret.check": 0.25},
                        },
                    },
                })
                privs.append({
                    "task_id": tid,
                    "grader": {"type": "boolean", "expected": True},
                    "human_reference_lower_bound": 0.15,
                    "seed": f"ci-broker-{i}",
                    "tool_providers": {
                        "secret.check": {
                            "type": "container",
                            "image": provider_image,
                            "digest": provider_digest,
                            "network": network,
                            "credential_env": ["AGI_EVAL_FIXTURE_TOKEN"],
                            "timeout_s": 10,
                            "memory_mb": 128,
                            "cpus": 0.5,
                            "max_output_bytes": 262144,
                        },
                    },
                })

            pubp, privp = td / "public.jsonl", td / "private.jsonl"
            pubp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in pubs), encoding="utf-8")
            privp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in privs), encoding="utf-8")
            provenance = td / "provenance.json"
            provenance.write_text(
                json.dumps({"schema": "ci-broker-provider-fixture", "not_agi_evidence": True}, sort_keys=True),
                encoding="utf-8",
            )
            lock = td / "lock.json"
            call(
                "freeze_eval.py",
                "--manifest", str(mp),
                "--public", str(pubp),
                "--private", str(privp),
                "--candidate-id", "ci-broker-fixture",
                "--candidate-digest", candidate_digest,
                "--generator-provenance", str(provenance),
                "--mode", "final",
                "--out", str(lock),
            )
            evidence = td / "evidence.json"
            env = dict(os.environ)
            env["AGI_EVAL_FIXTURE_TOKEN"] = fixture_secret
            call(
                "run_broker_arena_harness.py",
                "--manifest", str(mp),
                "--public", str(pubp),
                "--private", str(privp),
                "--lock", str(lock),
                "--candidate-id", "ci-broker-fixture",
                "--candidate-digest", candidate_digest,
                "--adapter-mode", "container",
                "--adapter", candidate_image,
                "--mode", "final",
                "--timeout-s", "60",
                "--out", str(evidence),
                env=env,
            )
            call(
                "verify_evidence.py",
                "--evidence", str(evidence),
                "--manifest", str(mp),
                "--public", str(pubp),
                "--private", str(privp),
                "--lock", str(lock),
            )

            raw_evidence = evidence.read_text(encoding="utf-8")
            if fixture_secret in raw_evidence:
                raise AssertionError("evaluator credential leaked into evidence")
            doc = json.loads(raw_evidence)
            assert doc["run"]["transport"] == "broker-provider-v1"
            assert doc["summary"]["passed_tasks"] == len(DOMAINS)
            assert doc["summary"]["generality_pass"] is True
            assert doc["summary"]["performance_pass"] is True
            for rec in doc["records"]:
                assert rec["isolation"]["network"] == "none"
                assert rec["isolation"]["broker_transport"] == "AF_UNIX"
                assert rec["broker"]["provider_isolation"] == "separate_evaluator_owned_containers"
                assert rec["broker"]["provider_count"] == 1
                assert rec["broker"]["requests"] == 3
                assert rec["broker"]["policy_violations"] == 1
                assert rec["broker"]["resource_cost"] == 0.25
                assert rec["autonomy_metrics"]["policy_violations"] == 1
                assert rec["autonomy_metrics"]["resource_cost"] == 0.25
                diag = rec["result"]["diagnostics"]
                assert diag["provider"]["result"]["credential_present"] is True
                assert diag["provider"]["result"]["external_service"] == {"authorized": True, "probe": "present"}
                assert diag["denied"]["error"] == "PolicyViolation"
    finally:
        subprocess.run(["docker", "rm", "-f", service_name], text=True, capture_output=True, check=False)
        subprocess.run(["docker", "network", "rm", network], text=True, capture_output=True, check=False)

    print("broker/provider final-mode mechanics: PASS (toy CI fixture; not AGI evidence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
