from affected_segment_automorphism_v1 import affected_segment_automorphism_group
from local_fullness_certificates import exact_string_stabilizer
from permutation_group_schreier import schreier_stabilizer_chain


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


def test_affected_segment_group_matches_exact_masked_stabilizer_and_skips_unaffected_orbit():
    G, blocks = s5_with_independent_c2_orbit()
    values = (0, 0, 1, 1, 2, 8, 9)
    active = tuple(range(5))
    got = affected_segment_automorphism_group(
        G, blocks, values, active, max_quotient_elements=1000
    )
    assert got.status == "exact_affected_segment_automorphism_group"
    assert got.subgroup is not None
    assert got.quotient_elements_enumerated == 120
    assert got.accepted_quotient_elements == 4
    assert got.largest_recursive_child_domain == 1
    assert got.certified_child_domain_bound == 1
    assert got.recurrence_child_bound_verified

    masked = tuple(("active", values[i]) if i in active else ("inactive", None)
                   for i in range(G.degree))
    exact = exact_string_stabilizer(G, masked)
    assert exact.status == "exact_intersection_coset"
    assert exact.coset is not None
    assert got.subgroup.order == exact.coset.subgroup.order == 8
    assert all(exact.coset.subgroup.contains(g) for g in got.subgroup.original_generators)
    assert all(got.subgroup.contains(g) for g in exact.coset.subgroup.original_generators)


def test_quotient_enumeration_limit_fails_closed():
    G, blocks = s5_with_independent_c2_orbit()
    got = affected_segment_automorphism_group(
        G, blocks, [0] * G.degree, tuple(range(5)), max_quotient_elements=10
    )
    assert got.status == "undetermined_quotient_enumeration_limit"
    assert got.subgroup is None
