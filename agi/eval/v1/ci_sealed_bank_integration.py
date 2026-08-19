"""Docker integration test for sealed-bank freeze/staging/qualification mechanics.

All banks are toy CI fixtures owned by this repository. Passing this test is not
X2.1b real-custodian evidence and is not AGI evidence.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from eval_core import REQUIRED_DOMAINS
from family_matrix import required_family_map

HERE = Path(__file__).resolve().parent
PYTHON = sys.executable


def call(*args: str) -> subprocess.CompletedProcess:
    proc = subprocess.run([PYTHON, *args], cwd=HERE, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed {args}:\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")
    return proc


def image_digest(image: str) -> str:
    proc = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        text=True,
        capture_output=True,
        check=True,
    )
    digest = proc.stdout.strip().lower()
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"unexpected image ID for {image}: {digest!r}")
    return digest


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def main() -> int:
    images = {
        "alpha": "agi-eval-v1-ci-sealed-alpha",
        "beta": "agi-eval-v1-ci-sealed-beta",
    }
    digests = {lineage: image_digest(image) for lineage, image in images.items()}
    if digests["alpha"] == digests["beta"]:
        raise AssertionError("toy lineages unexpectedly have identical image digests")

    with tempfile.TemporaryDirectory(prefix="agi-sealed-bank-ci-") as td_raw:
        td = Path(td_raw)
        matrix = yaml.safe_load((HERE / "family-matrix-v1.yaml").read_text(encoding="utf-8"))
        matrix["status"] = "frozen"
        family_map = required_family_map(matrix)
        banks = []
        for domain in sorted(REQUIRED_DOMAINS):
            for lineage in ("alpha", "beta"):
                bank_id = f"ci-{domain}-{lineage}"
                banks.append(
                    {
                        "bank_id": bank_id,
                        "domain": domain,
                        "families": list(family_map[domain]),
                        "custody_group": f"ci-custody-{lineage}",
                        "implementation_lineage": f"ci-implementation-{lineage}",
                        "visibility": "sealed_nonpublic",
                        "protocol": "agi-taskgen-request-v1",
                        "sealed_content_commitment": h(bank_id + "-content"),
                        "seed_schedule_commitment": h(bank_id + "-seeds"),
                        "provider": {
                            "type": "container",
                            "image": images[lineage],
                            "digest": digests[lineage],
                            "network": "none",
                            "timeout_s": 15,
                            "memory_mb": 128,
                            "cpus": 0.5,
                            "max_output_bytes": 262144,
                        },
                    }
                )
        registry = {
            "schema": "agi-sealed-bank-registry-v1",
            "minimum_independent_custodies_per_family": 2,
            "required_families": family_map,
            "banks": banks,
        }

        matrix_path = td / "family-matrix.yaml"
        registry_path = td / "registry.yaml"
        bank_lock_path = td / "bank-lock.json"
        foundry_lock_path = td / "foundry-lock.json"
        report_path = td / "qualification.json"
        matrix_path.write_text(yaml.safe_dump(matrix, sort_keys=False), encoding="utf-8")
        registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

        call(
            "freeze_sealed_banks.py",
            "--registry", str(registry_path),
            "--manifest", str(HERE / "manifest-v1.yaml"),
            "--out", str(bank_lock_path),
        )
        call(
            "freeze_foundry_inputs.py",
            "--family-matrix", str(matrix_path),
            "--registry", str(registry_path),
            "--manifest", str(HERE / "manifest-v1.yaml"),
            "--out", str(foundry_lock_path),
        )
        call(
            "qualify_sealed_banks.py",
            "--registry", str(registry_path),
            "--manifest", str(HERE / "manifest-v1.yaml"),
            "--lock", str(bank_lock_path),
            "--nonce", "ci-qualification-nonce-0123456789",
            "--out", str(report_path),
        )

        foundry_lock = json.loads(foundry_lock_path.read_text(encoding="utf-8"))
        assert sum(len(v) for v in foundry_lock["required_families"].values()) == 18
        assert foundry_lock["family_matrix_status"] == "frozen"
        report_raw = report_path.read_text(encoding="utf-8")
        assert "CI_SEALED_RAW" not in report_raw
        report = json.loads(report_raw)
        assert report["passed"] is True
        assert report["failures"] == []
        assert report["expected_family_assignments"] == 36
        assert len(report["qualified"]) == 36
        assert all(len(row["public_sha256"]) == 64 and len(row["private_sha256"]) == 64 for row in report["qualified"])

    print("sealed-bank freeze/staging/qualification mechanics: PASS (toy CI only; not X2.1b/AGI evidence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
