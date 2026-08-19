from itertools import combinations

from johnson_pair_ground_coherent_si_v1 import johnson_pair_ground_coherent_string_isomorphism
from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3


def ground_cycle(v):
    return tuple((i + 1) % v for i in range(v))


def ground_swap(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_symmetric_action(v):
    subsets = tuple(combinations(range(v), 2))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    ground_gens = (ground_swap(v), ground_cycle(v))
    induced = tuple(induce(g) for g in ground_gens)
    return schreier_stabilizer_chain(induced), subsets, induced


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def test_s9_j92_large_group_closes_after_actual_relation_splits_ground():
    G, subsets, gens = induced_symmetric_action(9)
    assert G.degree == 36
    assert G.order == 362880

    # Every edge has an intrinsic color.  Stable coherent refinement therefore
    # separates the nine ground points, while the ambient Johnson group remains S9.
    source = tuple(100 * u + v for u, v in subsets)
    witness = gens[1]
    target = relabel_target(source, witness)

    got = johnson_pair_ground_coherent_string_isomorphism(
        G,
        source,
        target,
        root_n=64,
        max_residual_group_order=64,
    )
    assert got.status == "exact_johnson_pair_ground_relation_coset", got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert got.ground_size == 9
    assert got.domain_size == 36
    assert got.ground_split_verified
    assert got.largest_ground_class == 1
    assert got.candidate_ground_order == 1
    assert got.coset is not None and got.coset.contains(witness)
    assert got.coset.subgroup.order == 1
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_s9_j92_homogeneous_relation_stays_fail_closed_for_next_w1_child():
    G, _, _ = induced_symmetric_action(9)
    source = (0,) * G.degree
    got = johnson_pair_ground_coherent_string_isomorphism(
        G,
        source,
        source,
        root_n=64,
        max_residual_group_order=64,
    )
    assert got.status == "undetermined_homogeneous_ground_coherent_relation", got
    assert not got.exact
    assert not got.ground_split_verified
    assert got.ground_size == 9
