from itertools import combinations
from math import comb

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from signed_johnson_complement_safe_image_si_v1 import (
    complement_safe_t_relation_signatures,
)
from signed_johnson_ground_profile_partition_si_v1 import (
    _color_token,
    _ordered_cells,
    _point_signatures,
    _profile_table,
)
from u2_candidate_coset_string_iso_v7 import candidate_coset_string_isomorphism_u7


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_ground_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    generators = tuple(induce(g) for g in (swap01(v), cycle(v)))
    return schreier_stabilizer_chain(generators), generators, subsets


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def maps_string(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def stabilizes_string(values, p):
    return all(values[i] == values[p[i]] for i in range(len(values)))


def test_general_nonconstant_pair_image_closes_above_bounded_no_split_ground():
    v = 9
    k = 3
    group, generators, subsets = induced_ground_group(v, k)

    base = (0, 1, 3)
    cyclic_triples = {
        tuple(sorted((x + shift) % v for x in base))
        for shift in range(v)
    }
    source = tuple(int(subset in cyclic_triples) for subset in subsets)
    target = relabel_target(source, generators[0])

    # This is the selected rev214 boundary without paying for a second Johnson
    # recognition in the precondition: v=9 exceeds the explicit ground cap 8,
    # all point profiles are equal, and the one-cell profile cannot determine
    # the nonconstant 3-set relation.
    source_tokens = tuple(_color_token(x) for x in source)
    target_tokens = tuple(_color_token(x) for x in target)
    source_cells = tuple(
        cell for _, cell in _ordered_cells(
            _point_signatures(v, k, source_tokens, complement_in_image=False)
        )
    )
    target_cells = tuple(
        cell for _, cell in _ordered_cells(
            _point_signatures(v, k, target_tokens, complement_in_image=False)
        )
    )
    assert tuple(map(len, source_cells)) == tuple(map(len, target_cells)) == (v,)
    assert _profile_table(v, k, source_cells, source_tokens) is None
    assert _profile_table(v, k, target_cells, target_tokens) is None

    pair_source = complement_safe_t_relation_signatures(
        v, k, source_tokens, 2, complement_in_image=False
    )
    pair_target = complement_safe_t_relation_signatures(
        v, k, target_tokens, 2, complement_in_image=False
    )
    assert len(set(pair_source).union(pair_target)) > 1
    assert comb(v, 2) < comb(v, k) == group.degree

    got = candidate_coset_string_isomorphism_u7(
        RightCoset(group, identity(group.degree)),
        source,
        target,
        root_n=512,
        max_explicit_degree=8,
        max_group_order=256,
        max_partition_states=4096,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    assert got.exact and got.coset is not None, got
    assert got.status.startswith("exact_w1r_log_codegree_pair_candidate_")
    assert got.coset.subgroup.order == v
    assert got.coset.contains(generators[0])
    assert maps_string(source, target, got.coset.representative)
    assert all(
        stabilizes_string(target, g)
        for g in got.coset.subgroup.original_generators
    )
    assert validate_quasipoly_recurrence_tree_v4(got.accounting).certified
