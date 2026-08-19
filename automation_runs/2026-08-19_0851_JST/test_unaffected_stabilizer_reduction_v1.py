from permutation_group_schreier import schreier_stabilizer_chain
from unaffected_stabilizer_reduction_v1 import unaffected_stabilizer_reduction


def s9_with_independent_c2_orbit():
    n = 11
    e = list(range(n))
    swap01 = e.copy()
    swap01[0], swap01[1] = 1, 0
    cycle9 = e.copy()
    for i in range(9):
        cycle9[i] = (i + 1) % 9
    swap_extra = e.copy()
    swap_extra[9], swap_extra[10] = 10, 9
    G = schreier_stabilizer_chain(
        [tuple(swap01), tuple(cycle9), tuple(swap_extra)]
    )
    blocks = [tuple([i]) for i in range(9)]
    return G, blocks


def test_unaffected_pointwise_stabilizer_retains_exact_giant_image():
    G, blocks = s9_with_independent_c2_orbit()
    r = unaffected_stabilizer_reduction(G, blocks)
    assert r.status == "exact_unaffected_pointwise_stabilizer_with_giant_image"
    assert r.theorem_applicable and r.theorem_verified
    assert r.subgroup_giant_type == "S_k"
    assert r.subgroup_image_order == 362880
    assert set(r.unaffected_points) == {9, 10}
    assert set(r.affected_points) == set(range(9))
    assert r.subgroup is not None
    for g in r.subgroup.original_generators:
        assert g[9] == 9 and g[10] == 10


def test_small_giant_hypothesis_fails_closed_even_if_structure_looks_similar():
    n = 8
    e = list(range(n))
    swap01 = e.copy()
    swap01[0], swap01[1] = 1, 0
    cycle6 = e.copy()
    for i in range(6):
        cycle6[i] = (i + 1) % 6
    swap_extra = e.copy()
    swap_extra[6], swap_extra[7] = 7, 6
    G = schreier_stabilizer_chain(
        [tuple(swap01), tuple(cycle6), tuple(swap_extra)]
    )
    blocks = [tuple([i]) for i in range(6)]
    r = unaffected_stabilizer_reduction(G, blocks)
    assert r.status == "unaffected_stabilizer_hypothesis_not_met"
    assert r.subgroup is None
    assert not r.theorem_applicable
