"""Cryptographically bind sealed-bank custodian participation declarations.

An SSH signature proves control of an accepted signing key over the declaration;
it does NOT by itself prove that two organizations are genuinely independent.
Identity/conflict evidence therefore remains an auditable external input. This
module fails closed on missing declarations, overlapping identity commitments,
or invalid signatures and never treats unsigned labels as participation.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from eval_core import REQUIRED_DOMAINS, canonical_json
from family_matrix import required_family_map, validate_family_matrix

SCHEMA = "agi-custodian-acceptance-v1"
SIGN_NAMESPACE = "agi-custodian-acceptance-v1"
HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@+-]{1,127}$")

REQUIRED_TRUE_DECLARATIONS = {
    "content_remains_nonpublic_through_final_rerun",
    "no_private_task_material_shared_with_peer_lineages",
    "no_candidate_specific_tuning_after_assignment",
    "accept_fail_closed_invalidation_on_material_leakage",
    "retain_audit_evidence_through_final_rerun",
}
REQUIRED_FALSE_DECLARATIONS = {
    "controlled_by_candidate_developer",
    "candidate_developer_has_final_bank_content_access",
}


def validate_acceptance(record: dict, family_map: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    if record.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA}"]
    for key in ("custodian_id", "signing_principal", "implementation_lineage"):
        value = record.get(key)
        if not isinstance(value, str) or not ID_RE.fullmatch(value):
            errors.append(f"{key} must be a stable identifier")
    for key in ("identity_evidence_commitment", "conflict_review_commitment"):
        value = record.get(key)
        if not isinstance(value, str) or not HEX_RE.fullmatch(value):
            errors.append(f"{key} must be a 64-hex SHA-256 commitment")
    assignments = record.get("assignments")
    if not isinstance(assignments, list) or not assignments:
        errors.append("assignments must be a non-empty list")
        assignments = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(assignments):
        if not isinstance(row, dict):
            errors.append(f"assignments[{index}] must be a mapping")
            continue
        domain, family = row.get("domain"), row.get("family")
        if domain not in family_map or family not in family_map.get(domain, []):
            errors.append(f"assignments[{index}] is not a preregistered family")
            continue
        pair = (str(domain), str(family))
        if pair in seen:
            errors.append(f"duplicate assignment {domain}/{family}")
        seen.add(pair)
    declarations = record.get("declarations")
    if not isinstance(declarations, dict):
        errors.append("declarations must be a mapping")
        declarations = {}
    for key in sorted(REQUIRED_TRUE_DECLARATIONS):
        if declarations.get(key) is not True:
            errors.append(f"declaration {key} must be true")
    for key in sorted(REQUIRED_FALSE_DECLARATIONS):
        if declarations.get(key) is not False:
            errors.append(f"declaration {key} must be false")
    return errors


def verify_ssh_signature(record: dict, *, signature_path: str | Path, allowed_signers_path: str | Path) -> tuple[bool, str]:
    principal = str(record.get("signing_principal", ""))
    proc = subprocess.run(
        [
            "ssh-keygen", "-Y", "verify",
            "-f", str(allowed_signers_path),
            "-I", principal,
            "-n", SIGN_NAMESPACE,
            "-s", str(signature_path),
        ],
        input=canonical_json(record) + "\n",
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    detail = (proc.stdout + "\n" + proc.stderr).strip()[-1000:]
    return proc.returncode == 0, detail


def validate_coverage(records: list[dict], family_map: dict[str, list[str]], *, minimum: int = 2) -> list[str]:
    """Require multiple signed-declaration identities/lineages for every family.

    This checks documentary separation, not real-world truth. The commitments must
    later be opened/audited under X2.1c before independence is accepted as fact.
    """
    errors: list[str] = []
    if minimum < 2:
        return ["minimum independent custodians must be >=2"]
    coverage: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in records:
        rec_errors = validate_acceptance(record, family_map)
        if rec_errors:
            errors.extend(f"{record.get('custodian_id','?')}: {e}" for e in rec_errors)
            continue
        for row in record["assignments"]:
            coverage[(row["domain"], row["family"])].append(record)
    for domain, families in family_map.items():
        for family in families:
            rows = coverage.get((domain, family), [])
            if len(rows) < minimum:
                errors.append(f"coverage {domain}/{family}: {len(rows)} acceptances < {minimum}")
                continue
            for field in ("custodian_id", "identity_evidence_commitment", "implementation_lineage", "signing_principal"):
                count = len({str(r[field]) for r in rows})
                if count < minimum:
                    errors.append(f"coverage {domain}/{family}: only {count} distinct {field} values")
    return errors


def load_family_map(path: str | Path) -> dict[str, list[str]]:
    matrix = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(matrix, dict):
        raise ValueError("family matrix must be a mapping")
    errors = validate_family_matrix(matrix, required_domains=set(REQUIRED_DOMAINS))
    if errors:
        raise ValueError("invalid family matrix: " + "; ".join(errors))
    return required_family_map(matrix)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--family-matrix", required=True)
    p.add_argument("--record", required=True)
    p.add_argument("--signature", required=True)
    p.add_argument("--allowed-signers", required=True)
    args = p.parse_args()
    try:
        family_map = load_family_map(args.family_matrix)
        record = json.loads(Path(args.record).read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("record must be a JSON object")
        errors = validate_acceptance(record, family_map)
        if errors:
            raise ValueError("; ".join(errors))
        ok, detail = verify_ssh_signature(record, signature_path=args.signature, allowed_signers_path=args.allowed_signers)
        if not ok:
            raise ValueError("SSH signature verification failed: " + detail)
    except Exception as e:
        print(json.dumps({"accepted": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps({"accepted": True, "custodian_id": record["custodian_id"], "assignments": len(record["assignments"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
