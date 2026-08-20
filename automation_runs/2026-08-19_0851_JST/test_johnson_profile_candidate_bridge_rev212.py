from itertools import combinations
from math import factorial

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from s1_string_isomorphism_v3 import s1_string_isomorphism_v3
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2
from u2_candidate_coset_string_iso_v6 import candidate_coset_string_isomorphism_u6
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
        return tuple(index[tuple(sorted(sigma[x] for x in subset))] for subset in subsets)

    generators = tuple(induce(g) for g in (swap01(v), cycle(v)))
    return schreier_stabilizer_chain(generators), generators, subsets


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def membership_count_colors(subsets, marked):
    marked = set(marked)
    return tuple(sum(x in marked for x in subset) for subset in subsets)


def maps_string(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def test_candidate_closes_large_j92_profile_case_that_rev211_leaves_open():
    G, generators, subsets = induced_ground_group(9, 2)
    source = membership_count_colors(subsets, range(4))
    target = relabel_target(source, generators[1])
    candidate = RightCoset(G, identity(G.degree))

    before = candidate_coset_string_isomorphism_u6(
        candidate,
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=256,
        max_johnson_test_sets=1000,
        max_partition_states=1024,
    )
    assert not before.exact, before
    assert before.status == "undetermined_johnson_ground_cap", before

    got = candidate_coset_string_isomorphism_u7(
        candidate,
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=256,
        max_johnson_test_sets=1000,
        max_partition_states=1024,
    )
    assert got.exact and got.coset is not None, got
    assert "exact_signed_ground_profile_partition_coset" in got.status
    assert got.coset.contains(generators[1])
    assert maps_string(source, target, got.coset.representative)
    assert got.coset.subgroup.order == 24 * 120
    assert validate_quasipoly_recurrence_tree_v4(got.accounting).certified


def test_s1_and_intransitive_candidate_reuse_the_same_profile_terminal():
    G, generators, subsets = induced_ground_group(9, 2)
    source = membership_count_colors(subsets, range(4))
    target = relabel_target(source, generators[1])

    direct = s1_string_isomorphism_v3(
        G,
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=1024,
        max_partition_states=1024,
    )
    assert direct.exact and direct.coset is not None, direct
    assert direct.status == "exact_signed_ground_profile_partition_coset"

    m = G.degree
    extended = tuple(tuple(g) + (m,) for g in G.original_generators)
    H = schreier_stabilizer_chain(extended)
    extended_source = source + ("fixed",)
    witness = tuple(generators[1]) + (m,)
    extended_target = relabel_target(extended_source, witness)
    got = candidate_coset_string_isomorphism_u2(
        RightCoset(H, identity(m + 1)),
        extended_source,
        extended_target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=1024,
    )
    assert got.exact and got.coset is not None, got
    assert got.coset.contains(witness)
    assert maps_string(extended_source, extended_target, got.coset.representative)


def test_profile_invariant_mismatch_is_exact_empty_at_candidate_boundary():
    G, _generators, subsets = induced_ground_group(9, 2)
    source = membership_count_colors(subsets, range(4))
    target = list(source)
    # Preserve the global color inventory so the cheap multiplicity terminal
    # cannot decide the instance; the Johnson star profiles themselves differ.
    target[0], target[3] = target[3], target[0]
    got = candidate_coset_string_isomorphism_u7(
        RightCoset(G, identity(G.degree)),
        source,
        tuple(target),
        root_n=64,
        max_explicit_degree=8,
        max_group_order=256,
        max_partition_states=1024,
    )
    assert got.exact and got.coset is None, got
    assert "exact_empty_signed_ground_profile" in got.status
    assert validate_quasipoly_recurrence_tree_v4(got.accounting).certified


def test_profile_partition_cap_remains_typed_fail_closed():
    G, generators, subsets = induced_ground_group(9, 2)
    source = membership_count_colors(subsets, range(4))
    target = relabel_target(source, generators[1])
    got = candidate_coset_string_isomorphism_u7(
        RightCoset(G, identity(G.degree)),
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=256,
        max_partition_states=8,
    )
    assert not got.exact and got.coset is None, got
    assert "partition_orbit_limit" in got.status


def test_s1_reuses_literal_giant_terminal_for_orbit_children():
    n = 9
    G = schreier_stabilizer_chain((cycle(n), swap01(n)))
    source = (0,) * n
    got = s1_string_isomorphism_v3(
        G,
        source,
        source,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=64,
    )
    assert G.order == factorial(n)
    assert got.exact and got.coset is not None, got
    assert got.status == "exact_literal_giant_string_isomorphism"
    assert got.coset.subgroup.order == G.order
    assert validate_quasipoly_recurrence_tree_v4(got.accounting).certified
