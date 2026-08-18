from jagi_eval.statistics import (
    Observation,
    disposition_for_run,
    geometric_mean_lcb,
    hierarchical_family_lcbs,
    validate_template_concentration,
)


def sample_observations():
    rows = []
    for family in ("reasoning", "computer"):
        for template in range(20):
            for instance in range(5):
                rows.append(Observation(family, f"t{template}", 1.02 + instance * 0.001))
    return rows


def test_hierarchical_bounds_are_deterministic_and_positive():
    rows = sample_observations()
    a = hierarchical_family_lcbs(rows, repetitions=300, seed=7)
    b = hierarchical_family_lcbs(rows, repetitions=300, seed=7)
    assert a == b
    assert set(a) == {"reasoning", "computer"}
    assert min(a.values()) > 1.0


def test_geometric_mean_lcb_is_above_one_for_strong_sample():
    assert geometric_mean_lcb(sample_observations(), repetitions=300, seed=9) > 1.0


def test_candidate_caused_failure_is_not_rerunnable():
    d = disposition_for_run(infrastructure_failure=True, candidate_caused=True)
    assert d.score_as_failure
    assert not d.eligible_for_rerun


def test_external_infrastructure_failure_can_be_rerun():
    d = disposition_for_run(infrastructure_failure=True, candidate_caused=False)
    assert not d.score_as_failure
    assert d.eligible_for_rerun


def test_template_concentration_rejects_dominant_template():
    counts = {"reasoning": {f"t{i}": 5 for i in range(20)}}
    ok, _ = validate_template_concentration(counts)
    assert ok
    counts["reasoning"]["t0"] = 30
    ok, reasons = validate_template_concentration(counts)
    assert not ok
    assert reasons
