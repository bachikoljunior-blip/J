from collections import deque

from bipartite_twin_ambient_coset_intersection_v1 import (
    intersect_unique_twin_mapping_with_ambient_coset,
)
from bipartite_twin_cell_transport_coset_v1 import build_bipartite_twin_cell_transport_coset
from bipartite_twin_quotient_refinement_v1 import refine_bipartite_twin_quotient_pair
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain


def _source_matching_blocks():
    return {(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)}


def _target_permuted_matching_blocks():
    return {(4, 1), (5, 1), (0, 2), (1, 2), (2, 0), (3, 0)}


def _unique_refinement():
    return refine_bipartite_twin_quotient_pair(
        6,
        3,
        _source_matching_blocks(),
        _target_permuted_matching_blocks(),
        source_right_colors=("a", "b", "c"),
        target_right_colors=("c", "a", "b"),
    )


def _group_elements(chain, cap=10000):
    e = identity(chain.degree)
    gens = chain.original_generators or (e,)
    seen = {e}
    queue = deque((e,))
    while queue:
        x = queue.popleft()
        for g in gens:
            y = compose(x, g)
            if y not in seen:
                if len(seen) >= cap:
                    raise AssertionError("test-only group enumeration exceeded cap")
                seen.add(y)
                queue.append(y)
    assert len(seen) == chain.order
    return seen


def _coset_members(coset, cap=10000):
    return {
        compose(coset.representative, h)
        for h in _group_elements(coset.subgroup, cap=cap)
    }


def test_intersection_with_rev202_full_cell_transport_recovers_exact_same_family():
    refinement = _unique_refinement()
    unconstrained = build_bipartite_twin_cell_transport_coset(refinement)
    got = intersect_unique_twin_mapping_with_ambient_coset(refinement, unconstrained.coset)
    assert got.status == "exact_complete_ambient_twin_cell_intersection"
    assert got.exact and got.complete and got.candidate_coset is not None
    expected = _coset_members(unconstrained.coset)
    actual = _coset_members(got.candidate_coset)
    assert len(expected) == len(actual) == 8
    assert actual == expected


def test_identity_ambient_group_gives_exact_empty_when_required_cell_map_is_nontrivial():
    refinement = _unique_refinement()
    n = refinement.left_size + refinement.right_size
    trivial = schreier_stabilizer_chain((identity(n),))
    ambient = RightCoset(trivial, identity(n))
    got = intersect_unique_twin_mapping_with_ambient_coset(refinement, ambient)
    assert got.status == "exact_empty_ambient_twin_cell_intersection"
    assert got.exact and got.complete
    assert got.candidate_coset is None


def test_strict_subcoset_of_internal_transports_is_preserved_exactly():
    refinement = _unique_refinement()
    unconstrained = build_bipartite_twin_cell_transport_coset(refinement)
    # Pick one nonidentity internal target-cell generator, retaining only two
    # transports from the eight-element complete twin-cell family.
    nonidentity = next(
        g for g in unconstrained.coset.subgroup.original_generators
        if g != identity(unconstrained.degree)
    )
    small = schreier_stabilizer_chain((nonidentity,))
    ambient = RightCoset(small, unconstrained.representative)
    got = intersect_unique_twin_mapping_with_ambient_coset(refinement, ambient)
    assert got.status == "exact_complete_ambient_twin_cell_intersection"
    assert got.candidate_coset is not None
    assert _coset_members(got.candidate_coset) == _coset_members(ambient)
    assert len(_coset_members(ambient)) == 2


def test_partition_orbit_cap_fails_closed_instead_of_reporting_empty():
    refinement = _unique_refinement()
    unconstrained = build_bipartite_twin_cell_transport_coset(refinement)
    n = unconstrained.degree
    moving_group = schreier_stabilizer_chain((unconstrained.representative,))
    ambient = RightCoset(moving_group, identity(n))
    got = intersect_unique_twin_mapping_with_ambient_coset(
        refinement,
        ambient,
        max_states=1,
    )
    assert got.status == "undetermined_partition_orbit_limit"
    assert not got.exact and not got.complete
    assert got.candidate_coset is None


def test_ambiguous_rev201_mapping_is_not_intersected_by_guessing_cells():
    refinement = refine_bipartite_twin_quotient_pair(
        6,
        3,
        _source_matching_blocks(),
        _target_permuted_matching_blocks(),
    )
    n = refinement.left_size + refinement.right_size
    trivial = schreier_stabilizer_chain((identity(n),))
    got = intersect_unique_twin_mapping_with_ambient_coset(
        refinement,
        RightCoset(trivial, identity(n)),
    )
    assert got.status == "ambient_twin_intersection_refinement_not_unique"
    assert not got.complete
    assert got.candidate_coset is None
