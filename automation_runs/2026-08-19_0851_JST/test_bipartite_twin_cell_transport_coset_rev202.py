from itertools import permutations, product

from bipartite_twin_cell_transport_coset_v1 import build_bipartite_twin_cell_transport_coset
from bipartite_twin_quotient_refinement_v1 import refine_bipartite_twin_quotient_pair
from permutation_group_schreier import compose, identity


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


def _all_target_cell_permutations(degree, cells):
    cells = tuple(tuple(sorted(cell)) for cell in cells)
    choices = tuple(tuple(permutations(cell)) for cell in cells)
    for selected in product(*choices):
        h = list(range(degree))
        for cell, image in zip(cells, selected):
            for a, b in zip(cell, image):
                h[a] = b
        yield tuple(h)


def _mapped_edges(p, left_size, source_edges):
    out = set()
    for a, b in source_edges:
        ta = p[a]
        tb = p[left_size + b] - left_size
        assert 0 <= ta < left_size
        assert 0 <= tb
        out.add((ta, tb))
    return out


def test_complete_transport_coset_has_exact_product_factorial_order():
    refinement = _unique_refinement()
    got = build_bipartite_twin_cell_transport_coset(refinement)
    assert got.status == "exact_complete_twin_cell_transport_coset"
    assert got.exact and got.complete_for_cell_transport
    assert got.target_cell_sizes == (1, 1, 1, 2, 2, 2)
    assert got.expected_order == got.subgroup_order == 8
    assert got.coset is not None and got.representative is not None


def test_right_coset_contains_every_cellwise_bijection_and_all_map_the_graph():
    refinement = _unique_refinement()
    got = build_bipartite_twin_cell_transport_coset(refinement)
    n1 = refinement.left_size
    target_cells = tuple(refinement.target_left_cells) + tuple(
        tuple(n1 + x for x in cell) for cell in refinement.target_right_cells
    )
    candidates = {
        compose(got.representative, h)
        for h in _all_target_cell_permutations(got.degree, target_cells)
    }
    assert len(candidates) == got.expected_order == 8
    assert all(got.coset.contains(p) for p in candidates)
    assert all(
        _mapped_edges(p, n1, _source_matching_blocks()) == _target_permuted_matching_blocks()
        for p in candidates
    )


def test_coset_contains_no_extra_small_degree_permutations():
    refinement = _unique_refinement()
    got = build_bipartite_twin_cell_transport_coset(refinement)
    # Exhaust the 9! ambient permutations for this tiny regression and count exact
    # coset membership. This is test-only and proves the returned family has no
    # extra transports beyond the expected internal twin permutations.
    members = [p for p in permutations(range(got.degree)) if got.coset.contains(p)]
    assert len(members) == got.expected_order == 8


def test_ambiguous_quotient_refinement_is_rejected_without_cell_choice():
    refinement = refine_bipartite_twin_quotient_pair(
        6,
        3,
        _source_matching_blocks(),
        _target_permuted_matching_blocks(),
    )
    got = build_bipartite_twin_cell_transport_coset(refinement)
    assert got.status == "twin_cell_transport_refinement_not_unique"
    assert got.coset is None and got.representative is None
    assert not got.complete_for_cell_transport


def test_singleton_cells_produce_a_trivial_internal_subgroup():
    source = {(0, 0), (1, 1), (2, 2)}
    target = {(0, 2), (1, 0), (2, 1)}
    refinement = refine_bipartite_twin_quotient_pair(
        3,
        3,
        source,
        target,
        source_left_colors=("x", "y", "z"),
        target_left_colors=("y", "z", "x"),
        source_right_colors=("a", "b", "c"),
        target_right_colors=("b", "c", "a"),
    )
    assert refinement.status == "exact_unique_twin_quotient_mapping"
    # All quotient cells already have distinct base colors. WL stabilization is
    # therefore one refinement round even if the canonical integer IDs themselves
    # would be re-assigned on another round; rev202 explicitly tests partition
    # stabilization rather than literal numeric-ID equality.
    assert refinement.refinement_rounds == 1
    got = build_bipartite_twin_cell_transport_coset(refinement)
    assert got.expected_order == got.subgroup_order == 1
    assert got.coset.contains(got.representative)
    assert not got.coset.contains(identity(got.degree)) or got.representative == identity(got.degree)
