from itertools import permutations

from bounded_group_transport import act_string
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_state_orbit_candidate_v1 import (
    exact_state_orbit_candidate_string_isomorphism,
    state_orbit_candidate_envelope,
)
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


def _symmetric_group(n):
    return schreier_stabilizer_chain(tuple(permutations(range(n))))


def test_envelope_uses_multiset_orbit_not_large_group_order():
    group = _symmetric_group(6)
    candidate = RightCoset(group, identity(6))
    proof = state_orbit_candidate_envelope(
        candidate, (0, 0, 0, 0, 0, 1), max_work=10**20,
    )
    assert group.order == 720
    assert proof.multiset_image_upper_bound == 6
    assert proof.state_image_upper_bound == 6
    assert proof.admitted


def test_exact_nonidentity_candidate_is_translated_back():
    group = _symmetric_group(5)
    shift = (1, 2, 3, 4, 0)
    candidate = RightCoset(group, shift)
    source = (0, 0, 0, 1, 1)
    target = act_string(source, (2, 0, 1, 4, 3))
    got = exact_state_orbit_candidate_string_isomorphism(
        candidate, source, target, root_n=5, max_work=10**20,
    )
    assert got.exact and got.coset is not None
    assert act_string(source, got.coset.representative) == target
    assert got.coset.subgroup.order == 12
    assert got.permutation_candidates_checked <= 10


def test_exact_empty_state_orbit_is_proved_without_structural_dispatch():
    cycle = schreier_stabilizer_chain(((1, 2, 3, 4, 0),))
    candidate = RightCoset(cycle, identity(5))
    got = exact_state_orbit_candidate_string_isomorphism(
        candidate, (1, 1, 0, 0, 0), (1, 0, 1, 0, 0),
        root_n=5, max_work=10**20,
    )
    assert got.exact and got.coset is None
    assert got.status == "exact_empty_state_orbit_candidate"


def test_u2_optional_terminal_bypasses_large_transitive_structure():
    group = _symmetric_group(6)
    candidate = RightCoset(group, identity(6))
    values = (0, 0, 0, 0, 0, 1)
    got = candidate_coset_string_isomorphism_u2(
        candidate, values, values, root_n=6,
        max_group_order=2, max_state_orbit_work=10**20,
    )
    assert got.status == "exact_state_orbit_candidate_coset"
    assert got.coset is not None and got.coset.subgroup.order == 120


def test_cap_rejects_before_state_orbit_execution():
    group = _symmetric_group(6)
    candidate = RightCoset(group, identity(6))
    got = exact_state_orbit_candidate_string_isomorphism(
        candidate, (0, 1, 2, 3, 4, 5), (0, 1, 2, 3, 4, 5),
        root_n=6, max_work=7,
    )
    assert got.status == "undetermined_state_orbit_work_cap"
    assert not got.exact
