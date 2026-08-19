from itertools import combinations

from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_johnson_ground_pair_reduction_si_v1 import (
    _signed_pair_weights,
    signed_johnson_ground_pair_reduction_si,
)
from signed_johnson_ground_profile_partition_si_v1 import (
    signed_johnson_ground_profile_partition_si,
)


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_action(v, k, ground_generators, *, include_complement=False):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}
    universe = set(range(v))

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    domain = [induce(g) for g in ground_generators]
    complement = None
    if include_complement:
        if v != 2 * k:
            raise ValueError("complement requires v=2k")
        complement = tuple(
            index[tuple(sorted(universe.difference(subset)))]
            for subset in subsets
        )
        domain.append(complement)
    return schreier_stabilizer_chain(domain), tuple(domain), complement


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def c3_plus_c4_pair_colors():
    red = {
        (0, 1), (1, 2), (0, 2),
        (3, 4), (4, 5), (5, 6), (3, 6),
    }
    return tuple(
        1 if tuple(sorted(pair)) in red else 0
        for pair in combinations(range(7), 2)
    )


def c7_pair_colors():
    red = {
        tuple(sorted((i, (i + 1) % 7)))
        for i in range(7)
    }
    return tuple(
        1 if tuple(sorted(pair)) in red else 0
        for pair in combinations(range(7), 2)
    )


def test_pair_coherent_split_closes_regular_relation_that_point_profiles_cannot_split():
    G, gens, _ = induced_action(7, 2, (swap01(7), cycle(7)))
    assert G.order == 5040
    source = c3_plus_c4_pair_colors()
    witness = gens[1]
    target = relabel_target(source, witness)

    point_only = signed_johnson_ground_profile_partition_si(
        G,
        source,
        target,
        root_n=64,
        max_partition_states=1024,
    )
    assert point_only.status == "undetermined_signed_ground_profile_no_split", point_only

    got = signed_johnson_ground_pair_reduction_si(
        G,
        source,
        target,
        root_n=64,
        max_partition_states=1024,
        max_candidate_group_order=512,
    )
    assert got.status == "exact_signed_ground_pair_split_coset", got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert got.significant_ground_split
    assert tuple(sorted(map(len, got.source_ground_cells))) == (3, 4)
    assert got.partition_orbit_states == 35
    assert got.candidate_stabilizer_order == 144
    assert got.candidate_elements_checked == 288
    assert got.recurrence_validation is not None and got.recurrence_validation.progress_verified
    assert got.coset is not None and got.coset.contains(witness)
    assert got.coset.subgroup.order == 48
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_stable_homogeneous_pair_relation_stays_fail_closed_for_higher_arity():
    G, _, _ = induced_action(7, 2, (swap01(7), cycle(7)))
    source = c7_pair_colors()
    got = signed_johnson_ground_pair_reduction_si(
        G,
        source,
        source,
        root_n=64,
        max_partition_states=1024,
        max_candidate_group_order=512,
    )
    assert got.status == "undetermined_signed_ground_pair_no_split", got
    assert not got.exact
    assert not got.significant_ground_split
    assert got.source_pair_rank >= 2


def test_complement_safe_pair_signature_is_invariant_under_pure_complement():
    v, k = 6, 3
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}
    universe = set(range(v))
    complement = tuple(
        index[tuple(sorted(universe.difference(subset)))]
        for subset in subsets
    )
    source = tuple((sum(subset) + subset[0]) % 5 for subset in subsets)
    target = relabel_target(source, complement)

    source_weights = _signed_pair_weights(v, k, source, complement_in_image=True)
    target_weights = _signed_pair_weights(v, k, target, complement_in_image=True)
    assert source_weights == target_weights
