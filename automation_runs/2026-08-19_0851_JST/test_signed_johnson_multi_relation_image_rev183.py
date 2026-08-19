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
    complement_safe_t_subset_image_generators,
)
from signed_johnson_multi_relation_image_si_v1 import (
    _block_diagonal_generators,
    signed_johnson_multi_relation_candidate_si,
)


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


def test_block_diagonal_pairing_preserves_pure_complement_kernel_across_arities():
    v, k = 8, 4
    e = identity(v)
    c = cycle(v)
    lifted = (
        SignedJohnsonGroundGenerator(e, True),
        SignedJohnsonGroundGenerator(c, False),
    )
    original_gens = (
        _induce_signed_ground_generator(v, k, e, True),
        _induce_signed_ground_generator(v, k, c, False),
    )
    G = schreier_stabilizer_chain(original_gens)

    families = []
    for t in (2, 3):
        _, gens, _ = complement_safe_t_subset_image_generators(lifted, v, t)
        families.append(gens)
    combined, degree = _block_diagonal_generators(families)
    assert degree == 28 + 56 == 84
    assert combined[0] == identity(degree)

    image = schreier_stabilizer_chain(combined)
    whole_image = RightCoset(image, identity(degree))
    preimage = paired_action_coset_preimage(G, combined, whole_image)
    assert preimage.status == "exact_paired_action_coset_preimage", preimage
    assert preimage.kernel_order == 2
    assert preimage.image_order == 8
    assert preimage.preimage_subgroup_order == G.order == 16


def test_joint_relation_pipeline_closes_full_j63_star_string():
    v, k = 6, 3
    G, gens = induced_ground_group(v, k)
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in subset) for subset in subsets)
    witness = gens[1]
    target = relabel_target(source, witness)

    got = signed_johnson_multi_relation_candidate_si(
        G,
        source,
        target,
        root_n=32,
        max_image_si_nodes=100000,
        max_candidate_group_order=256,
    )
    assert got.status.startswith("exact_w1r_multi_relation_candidate_"), got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert got.coset is not None and got.coset.contains(witness)
    assert got.coset.subgroup.order == 120
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_constant_fraction_budget_fails_closed_when_no_informative_image_fits():
    v, k = 6, 3
    G, _ = induced_ground_group(v, k)
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in subset) for subset in subsets)
    got = signed_johnson_multi_relation_candidate_si(
        G,
        source,
        source,
        root_n=32,
        max_aux_fraction=0.5,
    )
    assert got.status == "undetermined_signed_johnson_design_aggregation_required"
    assert not got.exact and not got.local_cost_certified
    assert got.coset is None
