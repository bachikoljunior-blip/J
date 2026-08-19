import json
from copy import deepcopy
from pathlib import Path

import yaml

from eval_core import (
    append_hash_chain,
    score_result,
    summarize_records,
    validate_manifest,
    validate_taskpacks,
    verify_hash_chain,
    wilson_lower_bound,
)

HERE = Path(__file__).parent


def load_manifest():
    return yaml.safe_load((HERE / "manifest-v1.yaml").read_text())


def load_jsonl(name):
    return [json.loads(x) for x in (HERE / name).read_text().splitlines() if x.strip()]


def test_manifest_draft_valid_but_not_final():
    doc = load_manifest()
    assert validate_manifest(doc) == []
    assert validate_manifest(doc, final=True)


def test_manifest_anti_weakening():
    doc = load_manifest()
    weak = deepcopy(doc)
    weak["rules"]["max_domain_weight"] = 0.5
    assert validate_manifest(weak)
    weak = deepcopy(doc)
    weak["required_gates"].remove("autonomy")
    assert validate_manifest(weak)
    weak = deepcopy(doc)
    weak["evidence_integrity"]["independent_rerun_required"] = False
    assert validate_manifest(weak)


def test_public_pack_cannot_leak_expected_answer():
    pub = load_jsonl("public-example.jsonl")
    priv = load_jsonl("private-example.jsonl")
    assert validate_taskpacks(pub, priv, load_manifest()) == []
    pub[0]["expected_answer"] = "437"
    assert any("leaks forbidden" in e for e in validate_taskpacks(pub, priv, load_manifest()))


def test_exact_match_scoring_fails_closed():
    priv = load_jsonl("private-example.jsonl")[0]
    assert score_result(priv, {"answer": "437"})[:2] == (1.0, True)
    assert score_result(priv, {"answer": "438"})[:2] == (0.0, False)
    assert score_result(priv, "not-an-object")[1] is False


def test_wilson_lower_bound_is_conservative():
    assert 0 < wilson_lower_bound(100, 100, 0.95) < 1
    assert wilson_lower_bound(0, 100, 0.95) == 0
    assert wilson_lower_bound(90, 100, 0.95) < 0.90


def test_summary_requires_all_required_domains():
    priv = load_jsonl("private-example.jsonl")
    records = [
        {"task_id": "dev-math-001", "domain": "mathematics", "family": "closed_arithmetic", "passed": True},
        {"task_id": "dev-induction-001", "domain": "novel_task_induction", "family": "local_rule_induction", "passed": True},
    ]
    summary = summarize_records(records, priv, load_manifest())
    assert not summary["generality_pass"]
    assert "software_engineering" in summary["coverage"]["missing_required_domains"]


def test_hash_chain_detects_tampering():
    records = [{"task_id": "a", "passed": True}, {"task_id": "b", "passed": False}]
    tip = append_hash_chain(records)
    assert verify_hash_chain(records, tip) == []
    records[0]["passed"] = False
    assert verify_hash_chain(records, tip)
