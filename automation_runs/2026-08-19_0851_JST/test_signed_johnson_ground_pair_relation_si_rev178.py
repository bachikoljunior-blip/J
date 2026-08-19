from itertools import combinations

from permutation_group_schreier import inverse, schreier_stabilizer_chain
from signed_johnson_ground_pair_relation_si_v1 import (
    signed_johnson_ground_pair_relation_si,
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


def induced_ground_group(v, k, *, include_complement=False):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}
    universe = set(range(v))

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    ground_gens = (swap01(v), cycle(v))
    domain_gens = [induce(g) for g in ground_gens]
    complement = None
    if include_complement:
        if v != 2 * k:
            raise ValueError("complement requires v=2k")
        complement = tuple(
            index[tuple(sorted(universe.difference(subset)))]
            for subset in subsets
        )
        domain_gens.append(complement)
    return schreier_stabilizer_chain(domain_gens), tuple(domain_gens), complement


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def graph_edge_colors(v, edges):
    edge_set = {tuple(sorted(edge)) for edge in edges}
    return tuple(
        int(pair in edge_set)
        for pair in combinations(range(v), 2)
    )


def test_pair_coherent_refinement_splits_when_point_profiles_are_uniform():
    v, k = 8, 2
    G, gens, _ = induced_ground_group(v, k)
    triangle = {(0, 1), (1, 2), (0, 2)}
    pentagon = {(3, 4), (4, 5), (5, 6), (6, 7), (3, 7)}
    source = graph_edge_colors(v, triangle | pentagon)
    witness = gens[1]
    target = relabel_target(source, witness)

    first_order = signed_johnson_ground_profile_partition_si(
        G, source, target, root_n=64, max_partition_states=2048
    )
    assert first_order.status == "undetermined_signed_ground_profile_no_split", first_order
    assert not first_order.relation_profile_determined
    assert not first_order.significant_ground_split

    got = signed_johnson_ground_pair_relation_si(
        G, source, target, root_n=64, max_partition_states=2048
    )
    assert got.status == "verified_signed_ground_pair_partition_filter", got
    assert not got.exact and not got.terminal_certified
    assert got.local_cost_certified
    assert got.pair_relation_nontrivial
    assert got.strict_ground_progress
    assert got.significant_ground_split
    assert tuple(sorted(map(len, got.source_ground_cells))) == (3, 5)
    assert got.coset is not None and got.coset.contains(witness)
    assert got.partition_orbit_states > 0


def test_cycle_relation_becomes_explicit_smaller_pair_recurrence_target():
    v, k = 9, 2
    G, gens, _ = induced_ground_group(v, k)
    edges = {(i, (i + 1) % v) for i in range(v)}
    source = graph_edge_colors(v, edges)
    target = relabel_target(source, gens[1])

    first_order = signed_johnson_ground_profile_partition_si(
        G, source, target, root_n=64, max_partition_states=2048
    )
    assert first_order.status == "undetermined_signed_ground_profile_no_split", first_order

    got = signed_johnson_ground_pair_relation_si(
        G, source, target, root_n=64, max_partition_states=2048
    )
    assert got.status == "verified_signed_ground_pair_relation_recurrence_target", got
    assert not got.exact and not got.terminal_certified
    assert got.local_cost_certified
    assert got.pair_relation_nontrivial
    assert got.pair_rank >= 2
    assert got.strict_ground_progress
    assert got.ground_size == 9
    assert G.degree == 36
    assert not got.significant_ground_split
    assert got.coset is None


def test_pair_signature_is_invariant_under_signed_complement():
    v, k = 6, 3
    G, _, complement = induced_ground_group(v, k, include_complement=True)
    assert complement is not None
    source = tuple((7 * i + 3) % 5 for i in range(G.degree))
    target = relabel_target(source, complement)

    got = signed_johnson_ground_pair_relation_si(
        G, source, target, root_n=64, max_partition_states=512
    )
    assert got.complement_in_image
    assert got.source_pair_weights == got.target_pair_weights
    assert got.status not in {
        "exact_empty_signed_ground_pair_invariant",
        "exact_empty_signed_ground_pair_coherent_invariant",
        "exact_empty_signed_ground_pair_partition_orbit",
    }
