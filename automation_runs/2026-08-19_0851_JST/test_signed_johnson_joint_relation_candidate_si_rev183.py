from itertools import combinations

from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import SignedJohnsonGroundGenerator, _standard_subsets
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from recursive_point_image_coset_intersection import right_coset_intersection_recursive
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_joint_relation_candidate_si_v1 import (
    _joint_relation_data,
    choose_joint_complement_safe_relation_arities,
    signed_johnson_joint_relation_image_filter,
)
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


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
    return schreier_stabilizer_chain(domain_gens), domain_gens, ground_gens


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def anchor_string(v, k, anchors):
    subsets = _standard_subsets(v, k)
    return tuple(tuple(int(a in subset) for a in range(anchors)) for subset in subsets)


def test_joint_selector_combines_pair_and_triple_inside_constant_shrink_budget():
    v, k = 10, 4
    source = anchor_string(v, k, 5)
    tokens = tuple(_color_token(x) for x in source)
    got = choose_joint_complement_safe_relation_arities(
        v, k, tokens, tokens,
        complement_in_image=False,
        shrink_fraction=0.9,
    )
    assert got.status == "selected_joint_informative_relations", got
    assert got.arities == (2, 3)
    assert got.image_degree == 45 + 120 == 165
    assert got.image_degree <= got.image_degree_budget == 189
    assert all(rank > 1 for rank in got.relation_ranks)


def test_joint_disjoint_union_image_has_exact_original_preimage_and_full_candidate_closure():
    # Use t=1 and t=2 here so the complete joint-image/preimage regression stays
    # small while exercising the same generator-paired diagonal/disjoint-union
    # plumbing used by W1R-H4 for pair+higher-arity relations.
    v, k = 8, 4
    G, domain_gens, ground_gens = induced_ground_group(v, k)
    source = anchor_string(v, k, 4)
    witness = domain_gens[1]
    target = relabel_target(source, witness)
    source_tokens = tuple(_color_token(x) for x in source)
    target_tokens = tuple(_color_token(x) for x in target)
    lifted = tuple(SignedJohnsonGroundGenerator(g, False) for g in ground_gens)

    joint_gens, source_state, target_state, ranks = _joint_relation_data(
        lifted,
        v,
        k,
        source_tokens,
        target_tokens,
        (1, 2),
        complement=False,
    )
    assert len(source_state) == 8 + 28 == 36 < int(0.9 * G.degree)
    assert all(rank > 1 for rank in ranks)

    image = schreier_stabilizer_chain(joint_gens)
    value_coset = _all_value_preserving_maps(source_state, target_state)
    assert value_coset is not None
    intersection = right_coset_intersection_recursive(
        RightCoset(image, identity(image.degree)),
        value_coset,
        max_nodes=100000,
    )
    assert intersection.status == "exact_intersection_coset", intersection
    assert intersection.coset is not None

    preimage = paired_action_coset_preimage(G, joint_gens, intersection.coset)
    assert preimage.status == "exact_paired_action_coset_preimage", preimage
    assert preimage.coset is not None and preimage.coset.contains(witness)
    assert preimage.preimage_subgroup_order == 24

    full = candidate_coset_string_isomorphism_u2(
        preimage.coset,
        source,
        target,
        root_n=128,
        max_group_order=256,
    )
    assert full.exact and full.coset is not None and full.coset.contains(witness)
    assert full.coset.subgroup.order == 24
    check = validate_quasipoly_recurrence_tree_v3(full.accounting)
    assert check.certified, check


def test_wrapper_fails_closed_when_two_default_pair_higher_arity_images_do_not_fit_budget():
    # J(8,4): pair degree 28 and triple degree 56 are individually smaller than
    # 70, but their sum 84 exceeds the 0.9*70 auxiliary budget.  The wrapper must
    # not silently weaken the constant-factor progress rule merely to combine them.
    v, k = 8, 4
    G, _, _ = induced_ground_group(v, k)
    source = anchor_string(v, k, 4)
    got = signed_johnson_joint_relation_image_filter(
        G,
        source,
        source,
        root_n=128,
        shrink_fraction=0.9,
        max_image_si_nodes=1000,
    )
    assert got.status == "undetermined_signed_johnson_joint_relation_selection", got
    assert not got.exact and got.coset is None
    assert not got.local_cost_certified and not got.terminal_certified
