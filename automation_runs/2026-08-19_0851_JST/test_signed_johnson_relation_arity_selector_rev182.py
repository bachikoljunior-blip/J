from itertools import combinations

from johnson_ground_relational_lift_v1 import _standard_subsets
from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_relation_arity_selector_v1 import (
    adaptive_signed_johnson_relation_candidate_si,
    choose_complement_safe_relation_arity,
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


def cyclic_design_blocks(v, bases):
    blocks = set()
    for base in bases:
        for shift in range(v):
            blocks.add(tuple(sorted((x + shift) % v for x in base)))
    return frozenset(blocks)


def test_pair_homogeneous_but_triple_informative_design_selects_arity_three():
    # The union of these two Z9 orbits is a 2-(9,4,3) design but not a 3-design.
    # Thus every pair has the same selected-block incidence statistics, while
    # triple incidences split.  This is a concrete hard case where rev178's pair
    # view is exhausted but a strictly-smaller t=3 image exposes new structure.
    v, k = 9, 4
    selected = cyclic_design_blocks(v, ((0, 1, 2, 4), (0, 1, 4, 6)))
    subsets = _standard_subsets(v, k)
    source = tuple(int(subset in selected) for subset in subsets)
    tokens = tuple(_color_token(x) for x in source)

    pair_incidence = {
        sum(1 for block in selected if set(pair) <= set(block))
        for pair in combinations(range(v), 2)
    }
    triple_incidence = {
        sum(1 for block in selected if set(triple) <= set(block))
        for triple in combinations(range(v), 3)
    }
    assert pair_incidence == {3}
    assert len(triple_incidence) > 1

    choice = choose_complement_safe_relation_arity(
        v, k, tokens, tokens, complement_in_image=False
    )
    assert choice.status == "selected_informative_relation_arity", choice
    assert choice.considered_arities == (2, 3)
    assert choice.arity == 3
    assert choice.image_degree == 84 < len(source) == 126
    assert choice.relation_rank > 1


def test_adaptive_selector_reuses_relation_candidate_to_close_j63_star_string():
    v, k = 6, 3
    G, gens = induced_ground_group(v, k)
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in subset) for subset in subsets)
    witness = gens[1]
    target = relabel_target(source, witness)

    got = adaptive_signed_johnson_relation_candidate_si(
        G,
        source,
        target,
        root_n=32,
        max_image_si_nodes=100000,
        max_candidate_group_order=256,
    )
    assert got.status.startswith("exact_w1r_relation_image_candidate_"), got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert got.coset is not None and got.coset.contains(witness)
    assert got.coset.subgroup.order == 120
    check = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert check.certified, check
