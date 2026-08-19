from itertools import combinations

from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_johnson_ground_profile_partition_si_v1 import (
    signed_johnson_ground_profile_partition_si,
)
from signed_johnson_ground_relational_si_v1 import (
    signed_johnson_ground_relational_small_order_terminal,
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


def membership_count_colors(v, k, marked):
    marked = set(marked)
    return tuple(
        sum(x in marked for x in subset)
        for subset in combinations(range(v), k)
    )


def test_large_order_j92_closes_by_profile_partition_without_group_enumeration():
    G, gens, _ = induced_ground_group(9, 2)
    assert G.order == 362880

    source = membership_count_colors(9, 2, range(4))
    witness = gens[1]
    target = relabel_target(source, witness)

    legacy = signed_johnson_ground_relational_small_order_terminal(
        G,
        source,
        target,
        root_n=64,
        max_group_order=1024,
    )
    assert legacy.status == "undetermined_signed_ground_group_order_cap"

    got = signed_johnson_ground_profile_partition_si(
        G,
        source,
        target,
        root_n=64,
        max_partition_states=1024,
    )
    assert got.status == "exact_signed_ground_profile_partition_coset", got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert got.relation_profile_determined
    assert got.significant_ground_split
    assert tuple(sorted(map(len, got.source_ground_cells))) == (4, 5)
    assert got.partition_orbit_states == 126
    assert got.compatible_parities == (False,)
    assert got.coset is not None and got.coset.contains(witness)
    assert got.coset.subgroup.order == 24 * 120
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_complement_expanded_j63_filters_the_parity_exactly():
    G, _, complement = induced_ground_group(6, 3, include_complement=True)
    assert G.order == 1440
    assert complement is not None

    source = membership_count_colors(6, 3, range(2))
    target = relabel_target(source, complement)

    legacy = signed_johnson_ground_relational_small_order_terminal(
        G,
        source,
        target,
        root_n=64,
        max_group_order=128,
    )
    assert legacy.status == "undetermined_signed_ground_group_order_cap"

    got = signed_johnson_ground_profile_partition_si(
        G,
        source,
        target,
        root_n=64,
        max_partition_states=128,
    )
    assert got.status == "exact_signed_ground_profile_partition_coset", got
    assert got.exact and got.coset is not None
    assert got.complement_in_image
    assert got.compatible_parities == (True,)
    assert got.significant_ground_split
    assert tuple(sorted(map(len, got.source_ground_cells))) == (2, 4)
    assert got.partition_orbit_states == 15
    assert got.coset.contains(complement)
    assert got.coset.subgroup.order == 2 * 24
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_profile_invariant_mismatch_is_exact_empty():
    G, _, _ = induced_ground_group(9, 2)
    source = membership_count_colors(9, 2, range(4))
    target = list(source)
    target[0] = 999

    got = signed_johnson_ground_profile_partition_si(
        G,
        source,
        tuple(target),
        root_n=64,
        max_partition_states=1024,
    )
    assert got.exact
    assert got.coset is None
    assert got.status in {
        "exact_empty_signed_ground_profile_invariant",
        "exact_empty_signed_ground_profile_table",
    }
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified
