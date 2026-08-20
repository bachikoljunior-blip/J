from itertools import combinations
from math import factorial

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from s1_string_isomorphism_v3 import s1_string_isomorphism_v3
from s1_string_isomorphism_v4 import s1_string_isomorphism_v4
from signed_johnson_ground_profile_partition_si_v1 import (
    signed_johnson_ground_profile_partition_si,
)
from u2_candidate_coset_string_iso_v7 import candidate_coset_string_isomorphism_u7


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_ground_group(v, k=2):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(index[tuple(sorted(sigma[x] for x in subset))] for subset in subsets)

    generators = tuple(induce(g) for g in (swap01(v), cycle(v)))
    return schreier_stabilizer_chain(generators), generators, subsets


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def cycle_edge_colors(subsets, size):
    edges = {tuple(sorted((i, (i + 1) % size))) for i in range(size)}
    return tuple(int(subset in edges) for subset in subsets)


def membership_count_colors(subsets, marked):
    marked = set(marked)
    return tuple(sum(x in marked for x in subset) for subset in subsets)


def maps_string(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def stabilizes_string(values, p):
    return all(values[i] == values[p[i]] for i in range(len(values)))


def test_s1_reuses_bounded_ground_terminal_after_profile_no_split():
    G, generators, subsets = induced_ground_group(5)
    source = cycle_edge_colors(subsets, 5)
    target = relabel_target(source, generators[1])

    before = s1_string_isomorphism_v3(
        G,
        source,
        target,
        root_n=128,
        max_explicit_degree=8,
        max_group_order=64,
    )
    assert not before.exact, before
    assert before.status == "undetermined_signed_ground_profile_no_split", before

    got = s1_string_isomorphism_v4(
        G,
        source,
        target,
        root_n=128,
        max_explicit_degree=8,
        max_group_order=64,
    )
    assert got.exact and got.coset is not None, got
    assert got.status == "exact_primitive_johnson_ground_coset"
    assert got.coset.subgroup.order == 10
    assert maps_string(source, target, got.coset.representative)
    assert validate_quasipoly_recurrence_tree_v4(got.accounting).certified


def test_nonidentity_significant_filter_closes_through_recursive_s1_v4():
    G, generators, subsets = induced_ground_group(10)
    source = cycle_edge_colors(subsets, 5)
    target = relabel_target(source, generators[1])

    profile = signed_johnson_ground_profile_partition_si(
        G,
        source,
        target,
        root_n=128,
        max_partition_states=4096,
    )
    assert profile.status == "verified_signed_ground_profile_partition_filter", profile
    assert not profile.exact and profile.coset is not None
    assert profile.significant_ground_split
    assert not profile.relation_profile_determined

    got = candidate_coset_string_isomorphism_u7(
        RightCoset(G, identity(G.degree)),
        source,
        target,
        root_n=128,
        max_explicit_degree=8,
        max_group_order=64,
        max_partition_states=4096,
    )
    assert got.exact and got.coset is not None, got
    assert got.coset.subgroup.order == 10 * factorial(5)
    assert got.coset.contains(generators[1])
    assert maps_string(source, target, got.coset.representative)
    assert all(stabilizes_string(target, g) for g in got.coset.subgroup.original_generators)
    assert validate_quasipoly_recurrence_tree_v4(got.accounting).certified


def test_nonidentity_profile_exact_coset_uses_target_stabilizer():
    G, generators, subsets = induced_ground_group(9)
    source = membership_count_colors(subsets, range(4))
    target = relabel_target(source, generators[1])
    got = signed_johnson_ground_profile_partition_si(
        G,
        source,
        target,
        root_n=128,
        max_partition_states=4096,
    )
    assert got.exact and got.coset is not None, got
    assert got.status == "exact_signed_ground_profile_partition_coset"
    assert got.coset.subgroup.order == factorial(4) * factorial(5)
    assert got.coset.contains(generators[1])
    assert maps_string(source, target, got.coset.representative)
    assert all(stabilizes_string(target, g) for g in got.coset.subgroup.original_generators)


def test_bounded_ground_gate_remains_fail_closed_below_ground_size():
    G, generators, subsets = induced_ground_group(5)
    source = cycle_edge_colors(subsets, 5)
    target = relabel_target(source, generators[1])
    got = s1_string_isomorphism_v4(
        G,
        source,
        target,
        root_n=128,
        max_explicit_degree=4,
        max_group_order=64,
    )
    assert not got.exact and got.coset is None, got
    assert got.status == "undetermined_signed_ground_profile_no_split"
