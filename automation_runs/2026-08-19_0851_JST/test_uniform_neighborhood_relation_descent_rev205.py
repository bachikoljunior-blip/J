from itertools import combinations

import pytest

from uniform_neighborhood_relation_descent_v1 import (
    descend_uniform_neighborhood_test_relation,
)


def test_higher_arity_point_codegrees_give_exact_right_split():
    v, t = 6, 3
    coords = tuple(combinations(range(v), t))
    colors = tuple(int(0 in T) for T in coords)
    got = descend_uniform_neighborhood_test_relation(v, t, coords, colors)
    assert got.status == "certified_right_design_codegree_split"
    assert got.significant_split
    assert got.exact
    assert sorted(map(len, got.right_cells)) == [1, 5]
    assert got.decisive_subset_size == 1


def test_noninteger_pair_colors_are_canonically_encoded_before_coherent_split():
    v, t = 6, 2
    coords = tuple(combinations(range(v), t))
    colors = tuple("inside" if set(T) <= {0, 1} else "outside" for T in coords)
    got = descend_uniform_neighborhood_test_relation(v, t, coords, colors)
    assert got.status == "certified_right_pair_coherent_split"
    assert got.significant_split
    assert got.exact
    assert sorted(map(len, got.right_cells)) == [2, 4]
    assert got.pair_reduction_status == "certified_coherent_point_split"


def test_constant_relation_stays_fail_closed():
    v, t = 7, 3
    coords = tuple(combinations(range(v), t))
    got = descend_uniform_neighborhood_test_relation(v, t, coords, (0,) * len(coords))
    assert got.status == "constant_right_relation_unresolved"
    assert not got.significant_split
    assert got.exact


def test_incomplete_coordinate_system_is_rejected():
    v, t = 6, 3
    coords = tuple(combinations(range(v), t))
    with pytest.raises(ValueError, match="every t-subset exactly once"):
        descend_uniform_neighborhood_test_relation(v, t, coords[:-1], (0,) * (len(coords) - 1))
