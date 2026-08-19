from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_string_child_dispatch_v1 import proof_carrying_string_child_dispatch
from recursive_point_image_coset_intersection import right_coset_intersection_recursive


def symmetric_group(n):
    e = list(range(n))
    swap = e.copy(); swap[0], swap[1] = 1, 0
    cycle = tuple((i + 1) % n for i in range(n))
    return schreier_stabilizer_chain([tuple(swap), cycle])


def two_s4_orbits():
    n = 8
    e = list(range(n))
    gens = []
    for offset in (0, 4):
        swap = e.copy(); swap[offset], swap[offset + 1] = offset + 1, offset
        cycle = e.copy()
        for i in range(4):
            cycle[offset + i] = offset + ((i + 1) % 4)
        gens.extend((tuple(swap), tuple(cycle)))
    return schreier_stabilizer_chain(gens)


def test_small_terminal_matches_exact_intersection_and_embeds_cost_node():
    G = symmetric_group(4)
    candidate = RightCoset(G, identity(4))
    src = (0, 0, 1, 1)
    dst = (0, 0, 1, 1)
    got = proof_carrying_string_child_dispatch(
        candidate, src, dst, primary_domain_size=64, polylog_power=1
    )
    # ceil(log2 64)=6, so m=4 is a mechanically charged terminal.
    assert got.status == "exact_coset_small_terminal"
    assert got.exact and not got.empty and got.coset is not None
    assert got.terminal_cost_certified and got.accounting_node is not None
    assert got.accounting_node.terminal_certified
    assert got.accounting_node.cost_certified

    exact = right_coset_intersection_recursive(
        candidate, _all_value_preserving_maps(src, dst)
    )
    assert exact.status == "exact_intersection_coset"
    assert got.coset.subgroup.order == exact.coset.subgroup.order


def test_large_intransitive_child_is_not_sent_to_opaque_terminal():
    G = two_s4_orbits()
    got = proof_carrying_string_child_dispatch(
        RightCoset(G, identity(8)),
        [0] * 8,
        [0] * 8,
        primary_domain_size=8,
        polylog_power=1,
    )
    assert got.status == "requires_intransitive_recursive_dispatch"
    assert not got.exact
    assert got.coset is None
    assert not got.terminal_cost_certified
    assert got.accounting_node is None
    assert got.structure.status == "canonical_intransitive_orbit_partition"


def test_large_primitive_child_requires_primitive_dispatch():
    G = symmetric_group(7)
    got = proof_carrying_string_child_dispatch(
        RightCoset(G, identity(7)),
        [0] * 7,
        [0] * 7,
        primary_domain_size=7,
        polylog_power=1,
    )
    assert got.status == "requires_primitive_recursive_dispatch"
    assert not got.exact and got.coset is None
    assert got.structure.status == "primitive_or_trivial"


def test_value_multiplicity_mismatch_is_exact_empty_without_search():
    G = symmetric_group(7)
    got = proof_carrying_string_child_dispatch(
        RightCoset(G, identity(7)),
        (0, 0, 0, 1, 1, 1, 2),
        (0, 0, 1, 1, 1, 2, 2),
        primary_domain_size=7,
        polylog_power=1,
    )
    assert got.status == "exact_empty_value_multiplicity"
    assert got.exact and got.empty and got.coset is None
    assert got.terminal_cost_certified and got.accounting_node is not None
