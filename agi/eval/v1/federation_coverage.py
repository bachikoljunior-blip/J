"""Validate documentary coverage for the independent evidence federation.

This module validates structure only. It does not establish real-world independence.
"""
from __future__ import annotations

from collections import defaultdict

REQUIRED_ROLES = {"human_calibration", "independent_rerun", "security_autonomy_observer"}


def validate_federation_coverage(records: list[dict], required_families: set[tuple[str, str]]) -> list[str]:
    errors: list[str] = []
    family_rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
    role_rows: dict[str, list[dict]] = defaultdict(list)

    for i, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record[{i}] must be a mapping")
            continue
        for key in ("participant_id", "control_lineage", "signing_principal"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                errors.append(f"record[{i}] missing {key}")
        roles = record.get("roles", [])
        if not isinstance(roles, list):
            errors.append(f"record[{i}] roles must be a list")
            roles = []
        for role in roles:
            if role in REQUIRED_ROLES:
                role_rows[role].append(record)
        assignments = record.get("sealed_generator_assignments", [])
        if not isinstance(assignments, list):
            errors.append(f"record[{i}] sealed_generator_assignments must be a list")
            assignments = []
        for row in assignments:
            if not isinstance(row, dict):
                errors.append(f"record[{i}] assignment must be a mapping")
                continue
            pair = (row.get("domain"), row.get("family"))
            if pair not in required_families:
                errors.append(f"record[{i}] assignment {pair!r} is not preregistered")
                continue
            if not isinstance(row.get("implementation_lineage"), str) or not row["implementation_lineage"].strip():
                errors.append(f"record[{i}] assignment {pair!r} missing implementation_lineage")
                continue
            family_rows[pair].append({**record, "implementation_lineage": row["implementation_lineage"]})

    for pair in sorted(required_families):
        rows = family_rows.get(pair, [])
        if len(rows) < 2:
            errors.append(f"sealed family {pair[0]}/{pair[1]} has {len(rows)} participants < 2")
            continue
        for field in ("participant_id", "control_lineage", "signing_principal", "implementation_lineage"):
            if len({r.get(field) for r in rows}) < 2:
                errors.append(f"sealed family {pair[0]}/{pair[1]} lacks two distinct {field} values")

    for role in sorted(REQUIRED_ROLES):
        rows = role_rows.get(role, [])
        if not rows:
            errors.append(f"role {role} has no assigned participant")
            continue
        if not any(r.get("externally_audited") is True for r in rows):
            errors.append(f"role {role} has no externally audited participant")

    return errors
