from itertools import combinations

from johnson_pair_ground_coherent_si_v1 import johnson_pair_ground_coherent_string_isomorphism
from permutation_group_schreier import inverse, schreier_stabilizer_chain


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


def test_s9_j92_high_rank_colors_preserve_observed_coherent_round_limit_fail_closed():
    G, subsets, gens = induced_symmetric_action(9)
    assert G.degree == 36
    assert G.order == 362880

    # rev177 attempted to use full iterative coherent refinement on the actual
    # high-rank colored relation.  The first CI run observed that this adapter
    # reaches its explicit 128-round limit on unique edge colors.  Preserve that
    # boundary as a fail-closed regression: rev178's direct incidence-signature
    # path solves this kind of split without pretending the round-limited 2-WL
    # execution was a success.
    source = tuple(100 * u + v for u, v in subsets)
    target = relabel_target(source, gens[1])
    got = johnson_pair_ground_coherent_string_isomorphism(
        G,
        source,
        target,
        root_n=64,
        max_residual_group_order=64,
    )
    assert got.status == "undetermined_ground_coherent_round_limit", got
    assert not got.exact
    assert not got.ground_split_verified
    assert got.ground_size == 9


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
