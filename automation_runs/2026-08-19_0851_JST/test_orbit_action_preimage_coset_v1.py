from coset_stabilizer_primitives import RightCoset
from orbit_action_preimage_coset_v1 import orbit_action, orbit_action_preimage_coset
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain


def direct_product_s3_c2(include_transposition=True):
    e = list(range(5))
    cycle = e.copy()
    cycle[0], cycle[1], cycle[2] = 1, 2, 0
    swap01 = e.copy()
    swap01[0], swap01[1] = 1, 0
    swap34 = e.copy()
    swap34[3], swap34[4] = 4, 3
    gens = [tuple(cycle), tuple(swap34)]
    if include_transposition:
        gens.append(tuple(swap01))
    return schreier_stabilizer_chain(gens)


def child_s3_transposition_coset():
    cycle = (1, 2, 0)
    transposition = (1, 0, 2)
    a3 = schreier_stabilizer_chain([cycle])
    return RightCoset(a3, transposition)


def test_exact_child_coset_preimage_has_kernel_times_child_order():
    G = direct_product_s3_c2()
    child = child_s3_transposition_coset()
    r = orbit_action_preimage_coset(G, (0, 1, 2), child)
    assert r.status == "exact_orbit_action_coset_preimage"
    assert r.image_order == 6
    assert r.kernel_order == 2
    assert r.preimage_subgroup_order == 6
    assert r.subgroup.order == r.kernel_order * child.subgroup.order
    assert G.contains(r.representative)
    assert orbit_action(r.representative, (0, 1, 2)) == child.representative
    for h in r.subgroup.original_generators:
        assert G.contains(h)
        assert child.subgroup.contains(orbit_action(h, (0, 1, 2)))


def test_lifted_coset_membership_tracks_child_coset_membership():
    G = direct_product_s3_c2()
    child = child_s3_transposition_coset()
    r = orbit_action_preimage_coset(G, (0, 1, 2), child)
    for h in r.subgroup.original_generators:
        candidate = compose(r.representative, h)
        assert r.coset.contains(candidate)
        assert child.contains(orbit_action(candidate, (0, 1, 2)))


def test_child_subgroup_outside_image_fails_closed():
    G = direct_product_s3_c2(include_transposition=False)
    child = child_s3_transposition_coset()
    r = orbit_action_preimage_coset(G, (0, 1, 2), child)
    assert r.status in {"child_representative_outside_image", "child_subgroup_outside_image"}
    assert r.coset is None


def test_noninvariant_subset_is_rejected():
    G = direct_product_s3_c2()
    trivial = RightCoset(schreier_stabilizer_chain([identity(2)]), identity(2))
    r = orbit_action_preimage_coset(G, (0, 1), trivial)
    assert r.status == "subset_not_invariant"
    assert r.coset is None
