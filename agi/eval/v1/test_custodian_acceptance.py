import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from custodian_acceptance import validate_acceptance, validate_coverage, verify_ssh_signature
from family_matrix import required_family_map
from eval_core import canonical_json

HERE = Path(__file__).resolve().parent


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def family_map():
    matrix = yaml.safe_load((HERE / "family-matrix-v1.yaml").read_text(encoding="utf-8"))
    return required_family_map(matrix)


def record(label: str):
    fmap = family_map()
    return {
        "schema": "agi-custodian-acceptance-v1",
        "custodian_id": f"custodian-{label}",
        "signing_principal": f"custodian-{label}@agi-eval",
        "implementation_lineage": f"lineage-{label}",
        "identity_evidence_commitment": h(label + "-identity"),
        "conflict_review_commitment": h(label + "-conflict"),
        "assignments": [
            {"domain": domain, "family": family}
            for domain, families in fmap.items()
            for family in families
        ],
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


def test_acceptance_and_coverage_require_two_distinct_documentary_lineages():
    fmap = family_map()
    alpha, beta = record("alpha"), record("beta")
    assert validate_acceptance(alpha, fmap) == []
    assert validate_coverage([alpha, beta], fmap, minimum=2) == []
    beta["identity_evidence_commitment"] = alpha["identity_evidence_commitment"]
    errors = "\n".join(validate_coverage([alpha, beta], fmap, minimum=2))
    assert "distinct identity_evidence_commitment" in errors


def test_acceptance_rejects_candidate_control_and_missing_nonsharing_declaration():
    fmap = family_map()
    row = record("alpha")
    row["declarations"]["controlled_by_candidate_developer"] = True
    row["declarations"]["no_private_task_material_shared_with_peer_lineages"] = False
    errors = "\n".join(validate_acceptance(row, fmap))
    assert "controlled_by_candidate_developer must be false" in errors
    assert "no_private_task_material_shared_with_peer_lineages must be true" in errors


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen unavailable")
def test_ssh_signature_binds_exact_canonical_acceptance(tmp_path: Path):
    row = record("alpha")
    key = tmp_path / "custodian_key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    canonical = tmp_path / "acceptance.canonical.json"
    canonical.write_text(canonical_json(row) + "\n", encoding="utf-8")
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "agi-custodian-acceptance-v1", str(canonical)], check=True, capture_output=True, text=True)
    signature = Path(str(canonical) + ".sig")
    allowed = tmp_path / "allowed_signers"
    public_key = Path(str(key) + ".pub").read_text(encoding="utf-8").strip()
    allowed.write_text(f"{row['signing_principal']} {public_key}\n", encoding="utf-8")
    ok, detail = verify_ssh_signature(row, signature_path=signature, allowed_signers_path=allowed)
    assert ok, detail
    row["declarations"]["controlled_by_candidate_developer"] = True
    ok, _ = verify_ssh_signature(row, signature_path=signature, allowed_signers_path=allowed)
    assert ok is False
