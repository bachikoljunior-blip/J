from coset_stabilizer_primitives import RightCoset, pointwise_stabilizer_chain
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain


def extend4(p4):
    return tuple(p4) + (4, 5)


def cycle4():
    return extend4((1, 2, 3, 0))


def swap01():
    return extend4((1, 0, 2, 3))


def kernel_swap():
    return (0, 1, 2, 3, 5, 4)


def project_first4(g):
    q = tuple(g[i] for i in range(4))
    if sorted(q) != list(range(4)):
        raise AssertionError("test group failed to preserve the projected domain")
    return q


def test_exact_preimage_of_nontrivial_image_right_coset():
    G = schreier_stabilizer_chain([cycle4(), swap01(), kernel_swap()])
    assert G.order == 48
    image_gens = tuple(project_first4(g) for g in G.original_generators)
    image = schreier_stabilizer_chain(image_gens)
    assert image.order == 24

    K = pointwise_stabilizer_chain(image, (0,))
    assert K.order == 6
    q = (1, 0, 2, 3)
    target = RightCoset(K, q)

    got = paired_action_coset_preimage(G, image_gens, target)
    assert got.status == "exact_paired_action_coset_preimage", got
    assert got.kernel_order == 2
    assert got.target_subgroup_order == 6
    assert got.preimage_subgroup_order == 12
    assert got.coset is not None

    domain_q = swap01()
    assert got.coset.contains(domain_q)
    assert got.coset.contains(compose(domain_q, kernel_swap()))
    assert not got.coset.contains(identity(6))


def test_target_representative_outside_certified_image_fails_closed():
    a = extend4((1, 2, 0, 3))
    b = extend4((0, 2, 3, 1))
    G = schreier_stabilizer_chain([a, b, kernel_swap()])
    image_gens = tuple(project_first4(g) for g in G.original_generators)
    image = schreier_stabilizer_chain(image_gens)
    assert image.order == 12

    trivial = schreier_stabilizer_chain([identity(4)])
    odd = (1, 0, 2, 3)
    got = paired_action_coset_preimage(G, image_gens, RightCoset(trivial, odd))
    assert got.status == "target_representative_outside_image", got
    assert got.coset is None and got.preimage_subgroup is None
    assert got.kernel_order == 2


def test_inconsistent_generator_pairing_is_rejected():
    G = schreier_stabilizer_chain([cycle4(), swap01(), kernel_swap()])
    image_gens = list(project_first4(g) for g in G.original_generators)
    # Deliberately assign a noncentral S4 transposition to whichever domain
    # generator is the disjoint kernel swap.  This cannot define a homomorphism
    # from S4 x C2 because that domain element commutes with the S4 factor.
    for i, g in enumerate(G.original_generators):
        if g == kernel_swap():
            image_gens[i] = (1, 0, 2, 3)
            break
    image = schreier_stabilizer_chain(image_gens)
    target = RightCoset(schreier_stabilizer_chain([identity(4)]), identity(4))
    try:
        paired_action_coset_preimage(G, tuple(image_gens), target)
    except ValueError as exc:
        assert "well-defined action homomorphism" in str(exc)
    else:
        raise AssertionError("inconsistent generator pairing was accepted")
