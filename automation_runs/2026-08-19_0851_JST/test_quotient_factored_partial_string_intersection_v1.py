from local_fullness_certificates import exact_string_stabilizer
from permutation_group_schreier import schreier_stabilizer_chain
from quotient_factored_partial_string_intersection_v1 import (
    quotient_factored_partial_string_intersection,
)


def s5_with_independent_c2_orbit():
    n = 7
    e = list(range(n))
    swap01 = e.copy(); swap01[0], swap01[1] = 1, 0
    cycle5 = e.copy()
    for i in range(5):
        cycle5[i] = (i + 1) % 5
    swap_extra = e.copy(); swap_extra[5], swap_extra[6] = 6, 5
    G = schreier_stabilizer_chain(
        [tuple(swap01), tuple(cycle5), tuple(swap_extra)]
    )
    return G, [(i,) for i in range(5)]


def test_double_recursion_matches_exact_segment_stabilizer():
    G, blocks = s5_with_independent_c2_orbit()
    values = (0, 0, 1, 1, 2, 8, 9)
    active = tuple(range(5))
    got = quotient_factored_partial_string_intersection(
        G, blocks, values, active, max_quotient_leaves=1000
    )
    assert got.status == "exact_quotient_factored_partial_string_intersection"
    assert got.coset is not None
    assert got.quotient_order == 120
    assert got.quotient_leaves == 120
    assert got.largest_kernel_child_domain == 1
    assert got.certified_kernel_child_bound == 1
    assert got.recurrence_child_bound_verified

    masked = tuple(("active", values[i]) if i in active else ("inactive", None)
                   for i in range(G.degree))
    exact = exact_string_stabilizer(G, masked)
    assert exact.status == "exact_intersection_coset"
    assert exact.coset is not None
    assert got.coset.subgroup.order == exact.coset.subgroup.order == 8
    assert all(exact.coset.subgroup.contains(g) for g in got.coset.subgroup.original_generators)
    assert all(got.coset.subgroup.contains(g) for g in exact.coset.subgroup.original_generators)


def test_quotient_leaf_budget_fails_closed():
    G, blocks = s5_with_independent_c2_orbit()
    got = quotient_factored_partial_string_intersection(
        G, blocks, [0] * G.degree, tuple(range(5)), max_quotient_leaves=10
    )
    assert got.status == "undetermined_quotient_leaf_limit"
    assert got.coset is None
