from itertools import combinations

from johnson_ground_relational_lift_v1 import _standard_subsets
from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_joint_relation_candidate_si_v1 import (
    choose_joint_complement_safe_relation_arities,
    signed_johnson_joint_relation_candidate_string_isomorphism,
    signed_johnson_joint_relation_image_filter,
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


def five_anchor_string(v=10, k=4):
    subsets = _standard_subsets(v, k)
    return tuple(tuple(int(a in subset) for a in range(5)) for subset in subsets)


def test_joint_selector_combines_pair_and_triple_inside_constant_shrink_budget():
    v, k = 10, 4
    source = five_anchor_string(v, k)
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


def test_joint_relation_filter_lifts_complete_candidate_to_original_j104_domain():
    v, k = 10, 4
    G, gens = induced_ground_group(v, k)
    source = five_anchor_string(v, k)
    witness = gens[1]
    target = relabel_target(source, witness)

    got = signed_johnson_joint_relation_image_filter(
        G,
        source,
        target,
        root_n=256,
        shrink_fraction=0.9,
        max_image_si_nodes=200000,
    )
    assert got.status == "verified_signed_johnson_joint_relation_image_filter", got
    assert not got.exact and got.local_cost_certified
    assert got.relation_arities == (2, 3)
    assert got.joint_image_degree == 165 < G.degree == 210
    assert got.coset is not None and got.coset.contains(witness)
    assert got.preimage_filter_order <= G.order
    # The full five-anchor string has S5 symmetry on the unanchored ground points;
    # the joint filter must not exclude that true stabilizer.
    assert got.preimage_filter_order >= 120


def test_joint_relation_candidate_closes_full_five_anchor_string_exactly():
    v, k = 10, 4
    G, gens = induced_ground_group(v, k)
    source = five_anchor_string(v, k)
    witness = gens[1]
    target = relabel_target(source, witness)

    got = signed_johnson_joint_relation_candidate_string_isomorphism(
        G,
        source,
        target,
        root_n=256,
        shrink_fraction=0.9,
        max_image_si_nodes=200000,
        max_candidate_group_order=256,
    )
    assert got.status.startswith("exact_w1r_joint_relation_candidate_"), got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert got.coset is not None and got.coset.contains(witness)
    assert got.coset.subgroup.order == 120
    check = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert check.certified, check
