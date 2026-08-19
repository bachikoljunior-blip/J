from itertools import combinations

from johnson_ground_relational_lift_v1 import _standard_subsets
from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_johnson_relation_image_candidate_si_v1 import (
    signed_johnson_relation_image_candidate_string_isomorphism,
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


def test_relation_image_filter_then_small_candidate_closes_full_j63_string():
    v, k = 6, 3
    G, gens = induced_ground_group(v, k)
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in subset) for subset in subsets)
    witness = gens[1]
    target = relabel_target(source, witness)

    got = signed_johnson_relation_image_candidate_string_isomorphism(
        G,
        source,
        target,
        relation_arity=2,
        root_n=32,
        max_image_si_nodes=100000,
        max_candidate_group_order=256,
    )
    assert got.status.startswith("exact_w1r_relation_image_candidate_"), got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert got.coset is not None and got.coset.contains(witness)
    # The source string is the family of 3-subsets containing one distinguished
    # ground point, whose S6 stabilizer has order 5! = 120.
    assert got.coset.subgroup.order == 120
    check = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert check.certified, check
