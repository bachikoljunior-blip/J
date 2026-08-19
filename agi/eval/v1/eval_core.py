"""Core primitives for AGI evaluation harness v1.

The module is intentionally candidate-agnostic. It validates sealed task packs,
computes cryptographic identities, scores trusted grader records, and emits
conservative family/domain summaries. Nothing here asserts that an AGI exists.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import yaml

SCHEMA = "agi-eval-v1"
FORBIDDEN_PUBLIC_KEYS = {
    "answer_key",
    "expected_answer",
    "expected",
    "grader",
    "human_reference",
    "human_reference_lower_bound",
    "reference_answer",
    "secret",
    "private",
}
REQUIRED_GATES = {
    "generality",
    "performance",
    "autonomy",
    "practical_delivery",
    "evidence_integrity",
}
REQUIRED_DOMAINS = {
    "language_knowledge",
    "mathematics",
    "software_engineering",
    "data_analysis",
    "planning_decision",
    "novel_task_induction",
}
REQUIRED_AUTONOMY = {
    "completion_rate",
    "intervention_count",
    "recovery_rate",
    "elapsed_time",
    "resource_cost",
    "policy_violations",
    "state_persistence_success",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path: str | Path) -> dict:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return doc


def load_jsonl(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{lineno}: invalid JSON") from e
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{lineno}: each row must be an object")
        rows.append(row)
    if not rows:
        raise ValueError(f"{path}: task pack is empty")
    return rows


def _find_forbidden_keys(value: Any, prefix: str = "$") -> list[str]:
    bad: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            key = str(k)
            if key.lower() in FORBIDDEN_PUBLIC_KEYS:
                bad.append(f"{prefix}.{key}")
            bad.extend(_find_forbidden_keys(v, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            bad.extend(_find_forbidden_keys(v, f"{prefix}[{i}]"))
    return bad


def validate_manifest(doc: dict, *, final: bool = False) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != SCHEMA:
        errors.append("schema must be agi-eval-v1")
    if int(doc.get("version", -1)) != 1:
        errors.append("version must be 1")
    if set(doc.get("required_gates", [])) != REQUIRED_GATES:
        errors.append("required_gates changed or incomplete")
    domains = set(doc.get("domains", []))
    if not REQUIRED_DOMAINS.issubset(domains):
        errors.append("required domains missing")
    rules = doc.get("rules") or {}
    if float(rules.get("max_domain_weight", 1.0)) > 0.25:
        errors.append("max_domain_weight weakened")
    if rules.get("failed_required_domain_can_be_averaged_away") is not False:
        errors.append("domain failure may be hidden by averaging")
    if rules.get("failed_required_family_can_be_averaged_away") is not False:
        errors.append("family failure may be hidden by averaging")
    if rules.get("report_uncertainty") is not True:
        errors.append("uncertainty reporting disabled")
    if rules.get("fail_closed") is not True:
        errors.append("fail_closed must be true")
    uncertainty = rules.get("uncertainty") or {}
    if uncertainty.get("method") != "wilson_lower_bound":
        errors.append("uncertainty method must be wilson_lower_bound")
    confidence = float(uncertainty.get("confidence", 0.0))
    if confidence < 0.95 or confidence >= 1.0:
        errors.append("uncertainty confidence must be in [0.95, 1)")
    autonomy = set(doc.get("autonomy_metrics", []))
    if not REQUIRED_AUTONOMY.issubset(autonomy):
        errors.append("autonomy metrics missing")
    integ = doc.get("evidence_integrity") or {}
    if integ.get("independent_rerun_required") is not True:
        errors.append("independent rerun requirement missing")
    if integ.get("record_failures") is not True:
        errors.append("failure recording disabled")
    freeze = doc.get("freeze_policy") or {}
    if freeze.get("final_run_requires_lock") is not True:
        errors.append("final run must require lock")
    if freeze.get("candidate_digest_required") is not True:
        errors.append("candidate digest requirement missing")
    if freeze.get("sealed_private_pack_required") is not True:
        errors.append("sealed private pack requirement missing")
    if final:
        if doc.get("status") != "frozen":
            errors.append("final evaluation requires manifest status=frozen")
        plan = doc.get("sample_size_plan") or {}
        min_trials = plan.get("minimum_trials_per_family")
        if not isinstance(min_trials, int) or min_trials <= 0:
            errors.append("final manifest needs positive minimum_trials_per_family")
        if not str(plan.get("justification", "")).strip():
            errors.append("final manifest needs sample-size justification")
    return errors


def validate_taskpacks(
    public_rows: list[dict], private_rows: list[dict], manifest: dict, *, final: bool = False
) -> list[str]:
    errors: list[str] = []
    pub_by_id: dict[str, dict] = {}
    priv_by_id: dict[str, dict] = {}
    allowed_domains = set(manifest.get("domains", []))

    for i, row in enumerate(public_rows):
        missing = {"task_id", "domain", "family", "prompt"} - row.keys()
        if missing:
            errors.append(f"public[{i}] missing {sorted(missing)}")
            continue
        tid = str(row["task_id"])
        if tid in pub_by_id:
            errors.append(f"duplicate public task_id {tid}")
        pub_by_id[tid] = row
        if row.get("domain") not in allowed_domains:
            errors.append(f"public task {tid} has unknown domain {row.get('domain')}")
        bad = _find_forbidden_keys(row)
        if bad:
            errors.append(f"public task {tid} leaks forbidden grader keys: {bad[:5]}")

    for i, row in enumerate(private_rows):
        missing = {"task_id", "grader", "human_reference_lower_bound"} - row.keys()
        if missing:
            errors.append(f"private[{i}] missing {sorted(missing)}")
            continue
        tid = str(row["task_id"])
        if tid in priv_by_id:
            errors.append(f"duplicate private task_id {tid}")
        priv_by_id[tid] = row
        try:
            thr = float(row["human_reference_lower_bound"])
            if not 0 <= thr <= 1:
                errors.append(f"private task {tid} human_reference_lower_bound outside [0,1]")
        except Exception:
            errors.append(f"private task {tid} invalid human_reference_lower_bound")
        grader = row.get("grader") or {}
        if grader.get("type") not in {"exact_match", "numeric_at_least", "boolean"}:
            errors.append(f"private task {tid} unsupported grader type")

    if set(pub_by_id) != set(priv_by_id):
        missing_private = sorted(set(pub_by_id) - set(priv_by_id))
        missing_public = sorted(set(priv_by_id) - set(pub_by_id))
        if missing_private:
            errors.append(f"tasks missing private records: {missing_private[:10]}")
        if missing_public:
            errors.append(f"tasks missing public records: {missing_public[:10]}")

    family_thresholds: dict[tuple[str, str], set[float]] = defaultdict(set)
    family_counts: dict[tuple[str, str], int] = defaultdict(int)
    for tid in sorted(set(pub_by_id) & set(priv_by_id)):
        pub = pub_by_id[tid]
        priv = priv_by_id[tid]
        key = (str(pub["domain"]), str(pub["family"]))
        family_counts[key] += 1
        try:
            family_thresholds[key].add(float(priv["human_reference_lower_bound"]))
        except Exception:
            pass
    for key, vals in family_thresholds.items():
        if len(vals) != 1:
            errors.append(f"family {key[0]}/{key[1]} has inconsistent human thresholds")

    if final:
        min_trials = int((manifest.get("sample_size_plan") or {}).get("minimum_trials_per_family", 0))
        if min_trials <= 0:
            errors.append("final task-pack validation requires positive minimum_trials_per_family")
        for key, count in family_counts.items():
            if count < min_trials:
                errors.append(f"family {key[0]}/{key[1]} has {count} tasks < required {min_trials}")
        covered_domains = {d for d, _ in family_counts}
        missing_domains = sorted(REQUIRED_DOMAINS - covered_domains)
        if missing_domains:
            errors.append(f"final suite missing required domains: {missing_domains}")
    return errors


def score_result(private_row: dict, candidate_result: dict) -> tuple[float, bool, str | None]:
    """Score one trusted private grader record. Malformed results fail closed."""
    if not isinstance(candidate_result, dict):
        return 0.0, False, "candidate result is not an object"
    grader = private_row.get("grader") or {}
    typ = grader.get("type")
    try:
        if typ == "exact_match":
            passed = candidate_result.get("answer") == grader.get("expected")
            return (1.0 if passed else 0.0), passed, None
        if typ == "boolean":
            expected = bool(grader.get("expected", True))
            passed = candidate_result.get("answer") is expected
            return (1.0 if passed else 0.0), passed, None
        if typ == "numeric_at_least":
            value = float(candidate_result.get("score"))
            threshold = float(grader["threshold"])
            passed = math.isfinite(value) and value >= threshold
            return value if math.isfinite(value) else 0.0, passed, None
    except Exception as e:
        return 0.0, False, f"grader error: {type(e).__name__}: {e}"
    return 0.0, False, f"unsupported grader type: {typ}"


def _z_for_confidence(confidence: float) -> float:
    from statistics import NormalDist
    alpha = 1.0 - confidence
    return NormalDist().inv_cdf(1.0 - alpha / 2.0)


def wilson_lower_bound(successes: int, n: int, confidence: float = 0.95) -> float:
    if n <= 0:
        return 0.0
    if successes < 0 or successes > n:
        raise ValueError("successes must be within [0,n]")
    z = _z_for_confidence(confidence)
    phat = successes / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    radius = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return max(0.0, (centre - radius) / denom)


def summarize_records(records: Iterable[dict], private_rows: list[dict], manifest: dict) -> dict:
    priv_by_id = {str(r["task_id"]): r for r in private_rows}
    confidence = float(((manifest.get("rules") or {}).get("uncertainty") or {}).get("confidence", 0.95))
    fam: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in records:
        tid = str(rec.get("task_id"))
        domain = str(rec.get("domain"))
        family = str(rec.get("family"))
        key = (domain, family)
        if key not in fam:
            threshold = float(priv_by_id[tid]["human_reference_lower_bound"]) if tid in priv_by_id else 1.0
            fam[key] = {"domain": domain, "family": family, "n": 0, "passed": 0, "threshold": threshold}
        fam[key]["n"] += 1
        fam[key]["passed"] += 1 if rec.get("passed") is True else 0

    family_rows: list[dict] = []
    for key in sorted(fam):
        row = fam[key]
        lb = wilson_lower_bound(row["passed"], row["n"], confidence)
        family_rows.append({
            **row,
            "point_rate": row["passed"] / row["n"] if row["n"] else 0.0,
            "wilson_lower_bound": lb,
            "family_pass": lb >= row["threshold"],
        })

    by_domain: dict[str, list[dict]] = defaultdict(list)
    for row in family_rows:
        by_domain[row["domain"]].append(row)
    domain_rows: list[dict] = []
    for domain in sorted(by_domain):
        rows = by_domain[domain]
        conservative = sum(r["wilson_lower_bound"] for r in rows) / len(rows)
        reference = sum(r["threshold"] for r in rows) / len(rows)
        domain_rows.append({
            "domain": domain,
            "families": len(rows),
            "conservative_lower_bound": conservative,
            "reference_threshold": reference,
            "all_families_pass": all(r["family_pass"] for r in rows),
        })
    covered = {r["domain"] for r in domain_rows}
    required_covered = REQUIRED_DOMAINS.issubset(covered)
    all_required_domain_pass = required_covered and all(
        r["all_families_pass"] for r in domain_rows if r["domain"] in REQUIRED_DOMAINS
    )
    macro_lb = (
        sum(r["conservative_lower_bound"] for r in domain_rows if r["domain"] in REQUIRED_DOMAINS)
        / len(REQUIRED_DOMAINS)
        if required_covered else 0.0
    )
    macro_ref = (
        sum(r["reference_threshold"] for r in domain_rows if r["domain"] in REQUIRED_DOMAINS)
        / len(REQUIRED_DOMAINS)
        if required_covered else 1.0
    )
    return {
        "families": family_rows,
        "domains": domain_rows,
        "coverage": {
            "required_domains_covered": required_covered,
            "missing_required_domains": sorted(REQUIRED_DOMAINS - covered),
        },
        "conservative_macro_lower_bound": macro_lb,
        "macro_reference_threshold": macro_ref,
        "generality_pass": all_required_domain_pass,
        "performance_pass": all_required_domain_pass and macro_lb >= macro_ref,
    }


def append_hash_chain(records: list[dict]) -> str:
    prev = "0" * 64
    for rec in records:
        payload = {k: v for k, v in rec.items() if k not in {"record_sha256", "previous_record_sha256"}}
        rec["previous_record_sha256"] = prev
        digest = sha256_bytes((prev + canonical_json(payload)).encode("utf-8"))
        rec["record_sha256"] = digest
        prev = digest
    return prev


def verify_hash_chain(records: list[dict], expected_tip: str | None = None) -> list[str]:
    errors: list[str] = []
    prev = "0" * 64
    for i, rec in enumerate(records):
        if rec.get("previous_record_sha256") != prev:
            errors.append(f"record[{i}] previous hash mismatch")
        payload = {k: v for k, v in rec.items() if k not in {"record_sha256", "previous_record_sha256"}}
        digest = sha256_bytes((prev + canonical_json(payload)).encode("utf-8"))
        if rec.get("record_sha256") != digest:
            errors.append(f"record[{i}] hash mismatch")
        prev = digest
    if expected_tip is not None and prev != expected_tip:
        errors.append("hash-chain tip mismatch")
    return errors
