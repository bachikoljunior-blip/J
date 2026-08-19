from babai_local_certificate_parameter_gate_v1 import (
    babai_local_certificate_parameter_gate,
)


def test_exact_theorem_window_is_certified():
    # n=1024 gives 2+log2(n)=12; t=13 is valid when m>=130.
    r = babai_local_certificate_parameter_gate(1024, 200, 13)
    assert r.status == "certified_local_certificate_parameter_window"
    assert r.certified
    assert r.strict_lower_bound == 12
    assert r.upper_bound == 20


def test_merely_logarithmic_but_too_small_is_not_theorem_evidence():
    r = babai_local_certificate_parameter_gate(1024, 200, 8)
    assert r.status == "test_set_below_theorem_window"
    assert not r.certified


def test_test_set_larger_than_one_tenth_giant_degree_is_rejected():
    r = babai_local_certificate_parameter_gate(1024, 100, 13)
    assert r.status == "giant_degree_too_small_for_test_set"
    assert not r.certified


def test_small_correctness_fixtures_cannot_be_misreported_as_theorem_scale():
    r = babai_local_certificate_parameter_gate(12, 6, 4)
    assert not r.certified
