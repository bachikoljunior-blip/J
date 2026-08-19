from itertools import combinations

from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import (
    SignedJohnsonGroundGenerator,
    _induce_signed_ground_generator,
    _standard_subsets,
)
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_johnson_complement_safe_image_si_v1 import (
    complement_safe_t_relation_signatures,
    complement_safe_t_subset_image_generators,
    signed_johnson_complement_safe_relation_image_si,
)
from signed_johnson_ground_profile_partition_si_v1 import _color_token


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_ground_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    ground_gens = (swap01(v), cycle(v))
    domain_gens = tuple(induce(g) for g in ground_gens)
    return schreier_stabilizer_chain(domain_gens), domain_gens


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def test_pure_signed_complement_is_kernel_of_complement_safe_pair_image():
    v, k, t = 6, 3, 2
    e_ground = identity(v)
    complement = _induce_signed_ground_generator(v, k, e_ground, True)
    G = schreier_stabilizer_chain([complement])
    lifted = (SignedJohnsonGroundGenerator(e_ground, True),)

    coords, image_gens, parity = complement_safe_t_subset_image_generators(lifted, v, t)
    assert len(coords) == 15
    assert parity == (True,)
    assert image_gens == (identity(len(coords)),)

    image = schreier_stabilizer_chain(image_gens)
    target = RightCoset(image, identity(image.degree))
    preimage = paired_action_coset_preimage(G, image_gens, target)
    assert preimage.status == "exact_paired_action_coset_preimage", preimage
    assert image.order == 1
    assert preimage.kernel_order == 2
    assert preimage.preimage_subgroup_order == 2
    assert preimage.coset is not None and preimage.coset.contains(complement)


def test_s6_j63_pair_image_si_returns_exact_original_domain_filter():
    v, k = 6, 3
    G, gens = induced_ground_group(v, k)
    assert G.order == 720
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in subset) for subset in subsets)
    witness = gens[1]
    target = relabel_target(source, witness)

    got = signed_johnson_complement_safe_relation_image_si(
        G,
        source,
        target,
        relation_arity=2,
        root_n=32,
        max_image_si_nodes=100000,
    )
    assert got.status == "verified_signed_johnson_relation_image_filter", got
    assert not got.exact and not got.terminal_certified
    assert got.local_cost_certified
    assert got.strict_image_progress
    assert got.image_degree == 15 < G.degree == 20
    assert got.image_order == G.order == 720
    assert got.kernel_order == 1
    assert got.relation_rank > 1
    assert got.coset is not None and got.coset.contains(witness)
    assert 0 < got.preimage_filter_order < G.order
    assert got.preimage_filter_order == got.image_si_order
    # This object is deliberately a filter, not a completed recurrence leaf.
    # The global recurrence verifier must therefore reject it until the remaining
    # full k-subset color restriction is attached as a child.
    accounting_check = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert not accounting_check.certified
    assert accounting_check.status == "uncertified_terminal"


def test_signed_higher_arity_signature_is_equivariant_under_complement():
    v, k, t = 8, 4, 3
    subsets = _standard_subsets(v, k)
    sigma = cycle(v)
    signed = SignedJohnsonGroundGenerator(sigma, True)
    domain_p = _induce_signed_ground_generator(v, k, sigma, True)

    source = tuple((sum(subset) + 3 * subset[0]) % 5 for subset in subsets)
    target = relabel_target(source, domain_p)
    source_tokens = tuple(_color_token(x) for x in source)
    target_tokens = tuple(_color_token(x) for x in target)
    source_sig = complement_safe_t_relation_signatures(
        v, k, source_tokens, t, complement_in_image=True
    )
    target_sig = complement_safe_t_relation_signatures(
        v, k, target_tokens, t, complement_in_image=True
    )
    coords, image_gens, parity = complement_safe_t_subset_image_generators((signed,), v, t)
    assert len(coords) == 56
    assert parity == (True,)
    q = image_gens[0]
    assert all(source_sig[i] == target_sig[q[i]] for i in range(len(coords)))
