from local_certificate_beard_v1 import local_certificate_beard
from local_fullness_certificates import local_fullness_certificate
from permutation_group_schreier import schreier_stabilizer_chain


def sk_with_independent_c2_orbit(k):
    n = k + 2
    e = list(range(n))
    swap01 = e.copy(); swap01[0], swap01[1] = 1, 0
    cycle = e.copy()
    for i in range(k):
        cycle[i] = (i + 1) % k
    swap_extra = e.copy(); swap_extra[k], swap_extra[k + 1] = k + 1, k
    G = schreier_stabilizer_chain(
        [tuple(swap01), tuple(cycle), tuple(swap_extra)]
    )
    return G, [(i,) for i in range(k)]


def test_beard_proves_nonfullness_when_affected_segment_breaks_test_giant():
    G, blocks = sk_with_independent_c2_orbit(5)
    values = (0, 0, 1, 1, 2, 8, 9)
    T = tuple(range(5))
    got = local_certificate_beard(
        G, blocks, values, T, max_quotient_leaves=1000
    )
    assert got.status == "certified_nonfull_giant_obstruction"
    assert got.full is False
    assert len(got.layers) == 1
    assert got.layers[0].largest_kernel_child_domain == 1
    assert got.layers[0].recurrence_child_bound_verified

    exact = local_fullness_certificate(G, blocks, values, T)
    assert exact.full is False


def test_small_stable_beard_does_not_claim_fullness_without_theorem_gate():
    G, blocks = sk_with_independent_c2_orbit(5)
    values = (0, 0, 0, 0, 0, 8, 9)
    got = local_certificate_beard(G, blocks, values, tuple(range(5)))
    assert got.status == "stable_giant_without_unaffected_stabilizer_certificate"
    assert got.full is None
    assert len(got.layers) == 1


def test_s9_stable_beard_materializes_a_genuine_global_fullness_subgroup():
    G, blocks = sk_with_independent_c2_orbit(9)
    values = tuple([0] * 9 + [8, 9])
    got = local_certificate_beard(G, blocks, values, tuple(range(9)))
    assert got.status == "certified_full_by_stable_beard"
    assert got.full is True
    assert got.full_automorphism_subgroup is not None
    assert len(got.layers) == 1
    # The embedded test image is A9; the independent two-point orbit is fixed
    # pointwise in the final positive-certificate subgroup.
    assert got.full_automorphism_subgroup.order == 181440
    assert all(g[9] == 9 and g[10] == 10
               for g in got.full_automorphism_subgroup.original_generators)
    # The aggregation window |T|<=m/10 is deliberately not met in this compact
    # fixture, so exact fullness must not be promoted to theorem-scale accounting.
    assert not got.parameter_gate.certified
    assert not got.theorem_scale_recurrence_evidence
