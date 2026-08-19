from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v2 import validate_quasipoly_recurrence_tree_v2
from recursive_point_image_coset_intersection import right_coset_intersection_recursive
from s1_string_isomorphism_v1 import s1_string_isomorphism


def triple_cycle(offset, n=9):
    p = list(range(n))
    a, b, c = offset, offset + 1, offset + 2
    p[a], p[b], p[c] = b, c, a
    return tuple(p)


def test_intransitive_parent_recurses_to_three_exact_t1_children():
    G = schreier_stabilizer_chain([
        triple_cycle(0), triple_cycle(3), triple_cycle(6)
    ])
    values = tuple(range(9))
    got = s1_string_isomorphism(
        G, values, values,
        root_n=64,
        max_explicit_degree=3,
    )
    assert got.status == "exact_intransitive_s1_coset"
    assert got.exact and got.coset is not None
    assert len(got.children) == 3
    assert all(c.status == "exact_small_intersection_coset" for c in got.children)
    assert got.coset.subgroup.order == 1
    accounting = validate_quasipoly_recurrence_tree_v2(got.accounting)
    assert accounting.certified, accounting

    # Differential check against the old exact whole-domain oracle; this is a
    # correctness oracle only, not a complexity witness.
    value_coset = _all_value_preserving_maps(values, values)
    exact = right_coset_intersection_recursive(
        RightCoset(G, identity(9)), value_coset, max_nodes=100000
    )
    assert exact.status == "exact_intersection_coset"
    assert exact.coset is not None
    assert exact.coset.subgroup.order == got.coset.subgroup.order
    assert exact.coset.contains(got.coset.representative)
    assert got.coset.contains(exact.coset.representative)


def test_one_empty_orbit_child_proves_global_emptiness():
    G = schreier_stabilizer_chain([
        triple_cycle(0), triple_cycle(3), triple_cycle(6)
    ])
    # Global multiplicities agree (three 0s, three 1s, three 2s), so T1 cannot
    # reject at the root.  The first two invariant orbits have incompatible local
    # multiplicities, forcing emptiness to be established by the orbit recursion.
    source = (0, 0, 0, 1, 1, 1, 2, 2, 2)
    target = (0, 0, 1, 0, 1, 1, 2, 2, 2)
    got = s1_string_isomorphism(
        G, source, target,
        root_n=64,
        max_explicit_degree=3,
    )
    assert got.status == "exact_empty_orbit_partition"
    assert got.exact and got.coset is None
    assert got.children[-1].exact and got.children[-1].coset is None
    assert validate_quasipoly_recurrence_tree_v2(got.accounting).certified


def test_large_transitive_imprimitive_child_stops_at_named_structure_without_node_cap():
    n = 20
    cycle = tuple((i + 1) % n for i in range(n))
    G = schreier_stabilizer_chain([cycle])
    got = s1_string_isomorphism(
        G, (0,) * n, (0,) * n,
        root_n=n,
        max_explicit_degree=20,
    )
    assert not got.exact and got.coset is None
    assert got.status in {
        "undetermined_canonical_imprimitive_block_system",
        "undetermined_canonical_imprimitive_family",
    }
    assert got.permutation_candidates_checked == 0
