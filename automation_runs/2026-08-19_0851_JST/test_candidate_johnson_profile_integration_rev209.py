from itertools import combinations
from math import factorial

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from primitive_johnson_ground_terminal_v1 import primitive_johnson_ground_string_isomorphism_terminal
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


def _cycle(v):
    return tuple((i + 1) % v for i in range(v))


def _swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def _induced_johnson_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    generators = tuple(induce(g) for g in (_swap01(v), _cycle(v)))
    return schreier_stabilizer_chain(generators), generators


def _relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def _membership_count_colors(v, k, marked):
    marked = set(marked)
    return tuple(
        sum(x in marked for x in subset)
        for subset in combinations(range(v), k)
    )


def _maps(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def test_candidate_closes_large_j92_profile_case_that_small_ground_terminal_rejects():
    v, k = 9, 2
    G, gens = _induced_johnson_group(v, k)
    assert G.order == factorial(v)
    source = _membership_count_colors(v, k, range(4))
    witness = gens[1]
    target = _relabel_target(source, witness)

    old_leaf = primitive_johnson_ground_string_isomorphism_terminal(
        G,
        source,
        target,
        root_n=64,
        max_ground_degree=8,
    )
    assert old_leaf.status == "undetermined_johnson_ground_cap"
    assert not old_leaf.exact

    got = candidate_coset_string_isomorphism_u2(
        RightCoset(G, identity(G.degree)),
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=1024,
        max_partition_states=1024,
    )
    assert got.exact and got.coset is not None, got
    assert "exact_signed_ground_profile_partition_coset" in got.status
    assert got.coset.contains(witness)
    assert _maps(source, target, got.coset.representative)
    assert got.local_cost_certified
    assert got.terminal_certified


def test_candidate_large_j92_profile_mismatch_becomes_exact_empty():
    v, k = 9, 2
    G, _ = _induced_johnson_group(v, k)
    source = _membership_count_colors(v, k, range(4))
    target = list(source)
    target[0] = 999

    got = candidate_coset_string_isomorphism_u2(
        RightCoset(G, identity(G.degree)),
        source,
        tuple(target),
        root_n=64,
        max_explicit_degree=8,
        max_group_order=1024,
        max_partition_states=1024,
    )
    assert got.exact and got.coset is None, got


def test_profile_integration_remains_fail_closed_when_partition_orbit_cap_is_too_small():
    v, k = 9, 2
    G, gens = _induced_johnson_group(v, k)
    source = _membership_count_colors(v, k, range(4))
    target = _relabel_target(source, gens[1])

    got = candidate_coset_string_isomorphism_u2(
        RightCoset(G, identity(G.degree)),
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=1024,
        max_partition_states=8,
    )
    assert not got.exact
    assert "partition_orbit_limit" in got.status
    assert got.coset is None
