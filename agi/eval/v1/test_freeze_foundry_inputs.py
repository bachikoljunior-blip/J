import hashlib
from pathlib import Path

import pytest
import yaml

from eval_core import REQUIRED_DOMAINS
from family_matrix import required_family_map
from freeze_foundry_inputs import freeze_foundry_inputs

HERE = Path(__file__).resolve().parent


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def matrix():
    doc = yaml.safe_load((HERE / "family-matrix-v1.yaml").read_text(encoding="utf-8"))
    doc["status"] = "frozen"
    return doc


def registry_for(doc):
    family_map = required_family_map(doc)
    banks = []
    for domain in sorted(REQUIRED_DOMAINS):
        for lineage in ("alpha", "beta"):
            prefix = f"{domain}-{lineage}"
            banks.append(
                {
                    "bank_id": prefix,
                    "domain": domain,
                    "families": list(family_map[domain]),
                    "custody_group": f"custody-{prefix}",
                    "implementation_lineage": f"impl-{prefix}",
                    "visibility": "sealed_nonpublic",
                    "protocol": "agi-taskgen-request-v1",
                    "sealed_content_commitment": h(prefix + "-content"),
                    "seed_schedule_commitment": h(prefix + "-seeds"),
                    "provider": {
                        "type": "container",
                        "image": f"private.invalid/{prefix}",
                        "digest": "sha256:" + h(prefix + "-image"),
                        "network": "none",
                    },
                }
            )
    return {
        "schema": "agi-sealed-bank-registry-v1",
        "minimum_independent_custodies_per_family": 2,
        "required_families": family_map,
        "banks": banks,
    }


def manifest():
    return {"schema": "test", "domains": sorted(REQUIRED_DOMAINS)}


def test_foundry_freeze_binds_all_preregistered_families():
    fm = matrix()
    reg = registry_for(fm)
    lock = freeze_foundry_inputs(fm, reg, manifest())
    assert lock["family_matrix_status"] == "frozen"
    assert sum(len(v) for v in lock["required_families"].values()) == 18
    assert lock["sealed_bank_lock"]["minimum_independent_custodies_per_family"] == 2


def test_foundry_freeze_rejects_registry_that_shrinks_family_surface():
    fm = matrix()
    reg = registry_for(fm)
    domain = sorted(REQUIRED_DOMAINS)[0]
    reg["required_families"][domain] = reg["required_families"][domain][:-1]
    for bank in reg["banks"]:
        if bank["domain"] == domain:
            bank["families"] = list(reg["required_families"][domain])
    with pytest.raises(ValueError, match="exactly match"):
        freeze_foundry_inputs(fm, reg, manifest())


def test_foundry_freeze_fails_closed_if_x1_has_unmodeled_nontext_input():
    fm = matrix()
    reg = registry_for(fm)
    with pytest.raises(ValueError, match="non-text"):
        freeze_foundry_inputs(fm, reg, manifest(), x1_modalities={"text", "image"})
