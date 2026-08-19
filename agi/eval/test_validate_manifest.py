from copy import deepcopy
import yaml
from validate_manifest import validate


def load_manifest():
    with open("manifest-v0.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_manifest_is_structurally_valid():
    assert validate(load_manifest()) == []


def test_removing_gate_fails():
    doc = deepcopy(load_manifest())
    doc["required_gates"].remove("autonomy")
    assert validate(doc)


def test_weakening_domain_weight_fails():
    doc = deepcopy(load_manifest())
    doc["rules"]["max_domain_weight"] = 0.5
    assert validate(doc)


def test_disabling_independent_rerun_fails():
    doc = deepcopy(load_manifest())
    doc["evidence_integrity"]["independent_rerun_required"] = False
    assert validate(doc)
