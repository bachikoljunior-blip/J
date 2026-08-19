"""Structural validator for the AGI acceptance manifest.

This does not evaluate an AGI candidate. It prevents accidental weakening of
required gates before a real evaluation harness exists.
"""
from pathlib import Path
import sys
import yaml

REQUIRED_GATES = {
    "generality", "performance", "autonomy", "practical_delivery", "evidence_integrity"
}
REQUIRED_DOMAINS = {
    "language_knowledge", "mathematics", "software_engineering", "data_analysis",
    "planning_decision", "novel_task_induction"
}
REQUIRED_AUTONOMY = {
    "completion_rate", "intervention_count", "recovery_rate", "elapsed_time",
    "resource_cost", "policy_violations", "state_persistence_success"
}


def validate(doc: dict) -> list[str]:
    errors = []
    if set(doc.get("required_gates", [])) != REQUIRED_GATES:
        errors.append("required_gates changed or incomplete")
    if not REQUIRED_DOMAINS.issubset(set(doc.get("domains", []))):
        errors.append("required domains missing")
    rules = doc.get("rules", {})
    if rules.get("max_domain_weight", 1) > 0.25:
        errors.append("max_domain_weight weakened")
    if rules.get("failed_required_domain_can_be_averaged_away") is not False:
        errors.append("domain failure may be hidden by averaging")
    perf = doc.get("performance_reference", {})
    if not perf.get("require_each_family_pass") or not perf.get("require_macro_pass"):
        errors.append("performance gate weakened")
    if not REQUIRED_AUTONOMY.issubset(set(doc.get("autonomy_metrics", []))):
        errors.append("autonomy metrics missing")
    integrity = doc.get("evidence_integrity", {})
    if not integrity.get("independent_rerun_required"):
        errors.append("independent rerun requirement missing")
    return errors


def main(path: str) -> int:
    doc = yaml.safe_load(Path(path).read_text())
    errors = validate(doc)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALID STRUCTURE — this is not evidence that AGI exists or passes evaluation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "manifest-v0.yaml"))
