from itertools import combinations

from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_subset_incidence_partition_v1 import (
    _incidence_point_signatures,
    signed_subset_incidence_string_isomorphism,
)


def ground_cycle(v):
    return tuple((i + 1) % v for i in range(v))


def ground_swap(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_symmetric_action(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    gens = tuple(induce(g) for g in (ground_swap(v), ground_cycle(v)))
    return schreier_stabilizer_chain(gens), subsets, gens


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def test_s9_j93_large_group_closes_by_higher_arity_incidence_split():
    G, subsets, gens = induced_symmetric_action(9, 3)
    assert G.degree == 84
    assert G.order == 362880

    # Intrinsic unique colors make each ground point's incident-subset histogram
    # unique.  This is not a small-ground or small-group terminal: v=9 and |S9|
    # are both above the earlier explicit caps, so progress comes from the actual
    # colored 3-subset relation before the residual exact scan.
    source = tuple(10000 * a + 100 * b + c for a, b, c in subsets)
    witness = gens[1]
    target = relabel_target(source, witness)

    got = signed_subset_incidence_string_isomorphism(
        G,
        source,
        target,
        root_n=128,
        max_residual_group_order=64,
    )
    assert got.status == "exact_signed_subset_relation_coset", got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert (got.ground_size, got.subset_size, got.domain_size) == (9, 3, 84)
    assert got.incidence_split_verified
    assert got.largest_ground_class == 1
    assert got.candidate_signed_subgroup_order == 1
    assert got.coset is not None and got.coset.contains(witness)
    assert got.coset.subgroup.order == 1
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_s9_j93_homogeneous_incidence_remains_typed_unresolved():
    G, _, _ = induced_symmetric_action(9, 3)
    source = (0,) * G.degree
    got = signed_subset_incidence_string_isomorphism(
        G,
        source,
        source,
        root_n=128,
        max_residual_group_order=64,
    )
    assert got.status == "undetermined_homogeneous_subset_incidence", got
    assert not got.exact
    assert not got.incidence_split_verified
    assert (got.ground_size, got.subset_size) == (9, 3)


def test_complement_normalized_signatures_are_invariant_under_j63_complement():
    v, k = 6, 3
    subsets = tuple(combinations(range(v), k))
    values = tuple(100 * a + 10 * b + c for a, b, c in subsets)
    color_ids = {value: i for i, value in enumerate(sorted(values))}
    index = {subset: i for i, subset in enumerate(subsets)}
    universe = set(range(v))
    complement = tuple(
        index[tuple(sorted(universe.difference(subset)))]
        for subset in subsets
    )
    target = relabel_target(values, complement)

    src = _incidence_point_signatures(
        v, k, values, color_ids, allow_complement=True
    )
    dst = _incidence_point_signatures(
        v, k, target, color_ids, allow_complement=True
    )
    assert src == dst
