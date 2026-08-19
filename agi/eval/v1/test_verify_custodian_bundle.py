import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from eval_core import canonical_json
from family_matrix import required_family_map
from verify_custodian_bundle import verify_bundle

HERE = Path(__file__).resolve().parent


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def make_record(label: str) -> dict:
    matrix = yaml.safe_load((HERE / "family-matrix-v1.yaml").read_text(encoding="utf-8"))
    fmap = required_family_map(matrix)
    return {
        "schema": "agi-custodian-acceptance-v1",
        "custodian_id": f"custodian-{label}",
        "signing_principal": f"custodian-{label}@agi-eval",
        "implementation_lineage": f"lineage-{label}",
        "identity_evidence_commitment": h(label + "-identity"),
        "conflict_review_commitment": h(label + "-conflict"),
        "assignments": [{"domain": d, "family": f} for d, families in fmap.items() for f in families],
        "declarations": {
            "content_remains_nonpublic_through_final_rerun": True,
            "no_private_task_material_shared_with_peer_lineages": True,
            "no_candidate_specific_tuning_after_assignment": True,
            "accept_fail_closed_invalidation_on_material_leakage": True,
            "retain_audit_evidence_through_final_rerun": True,
            "controlled_by_candidate_developer": False,
            "candidate_developer_has_final_bank_content_access": False,
        },
    }


def sign_record(tmp_path: Path, label: str, record: dict) -> tuple[Path, Path, str]:
    key = tmp_path / f"key-{label}"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    path = tmp_path / f"{label}.json"
    path.write_text(canonical_json(record) + "\n", encoding="utf-8")
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "agi-custodian-acceptance-v1", str(path)], check=True, capture_output=True, text=True)
    pub = Path(str(key) + ".pub").read_text(encoding="utf-8").strip()
    return path, Path(str(path) + ".sig"), pub


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen unavailable")
def test_bundle_verification_requires_valid_signatures_before_documentary_coverage(tmp_path: Path):
    alpha, beta = make_record("alpha"), make_record("beta")
    ap, asp, apk = sign_record(tmp_path, "alpha", alpha)
    bp, bsp, bpk = sign_record(tmp_path, "beta", beta)
    allowed = tmp_path / "allowed_signers"
    allowed.write_text(
        f"{alpha['signing_principal']} {apk}\n{beta['signing_principal']} {bpk}\n",
        encoding="utf-8",
    )
    bundle = {
        "schema": "agi-custodian-bundle-v1",
        "minimum_independent_custodians_per_family": 2,
        "entries": [
            {"record": ap.name, "signature": asp.name},
            {"record": bp.name, "signature": bsp.name},
        ],
    }
    report = verify_bundle(
        bundle,
        family_matrix_path=HERE / "family-matrix-v1.yaml",
        allowed_signers_path=allowed,
        base_dir=tmp_path,
    )
    assert report["coverage"] == "documentary_complete"
    assert report["independence_truth_status"] == "requires_external_identity_and_conflict_audit"
    assert len(report["verified_acceptances"]) == 2

    beta["declarations"]["controlled_by_candidate_developer"] = True
    bp.write_text(canonical_json(beta) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        verify_bundle(
            bundle,
            family_matrix_path=HERE / "family-matrix-v1.yaml",
            allowed_signers_path=allowed,
            base_dir=tmp_path,
        )
