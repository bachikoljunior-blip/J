from pathlib import Path

import yaml

from eval_core import REQUIRED_DOMAINS
from family_matrix import activated_family_map, required_family_map, validate_family_matrix

HERE = Path(__file__).resolve().parent


def matrix():
    return yaml.safe_load((HERE / "family-matrix-v1.yaml").read_text(encoding="utf-8"))


def test_checked_in_family_matrix_is_nontrivial_and_complete():
    doc = matrix()
    assert validate_family_matrix(doc) == []
    family_map = required_family_map(doc)
    assert set(family_map) == REQUIRED_DOMAINS
    assert all(len(families) >= 3 for families in family_map.values())
    assert len({family for families in family_map.values() for family in families}) == sum(len(v) for v in family_map.values())


def test_family_matrix_rejects_silent_family_shrinkage():
    doc = matrix()
    domain = sorted(REQUIRED_DOMAINS)[0]
    doc["required_domains"][domain] = doc["required_domains"][domain][:2]
    assert any("families < required" in error for error in validate_family_matrix(doc))


def test_multimodal_families_activate_when_x1_exposes_nontext_input():
    doc = matrix()
    text_only = activated_family_map(doc, x1_modalities={"text"})
    multimodal = activated_family_map(doc, x1_modalities={"text", "image"})
    assert "multimodal_interpretation" not in text_only
    assert len(multimodal["multimodal_interpretation"]) >= 3
