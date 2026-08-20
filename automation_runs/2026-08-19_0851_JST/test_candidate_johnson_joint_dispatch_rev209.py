from itertools import combinations
from math import factorial

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3


OLD_GROUND_CAP = 8


def _swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def _cycle(v):
    return tuple((i + 1) % v for i in range(v))


def _induced_symmetric_johnson_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(index[tuple(sorted(sigma[x] for x in subset))] for subset in subsets)

    gens = tuple(induce(g) for g in (_swap01(v), _cycle(v)))
    return schreier_stabilizer_chain(gens)


def _distinguished_point_string(v, k):
    subsets = tuple(combinations(range(v), k))
    return tuple(int(0 in subset) for subset in subsets)


def _assert_above_old_cap_new_exact(v, k):
    # The pre-rev209 primitive Johnson terminal is configured with
    # max_ground_degree=8 by candidate-v2. These cases deliberately use a
    # larger recovered Johnson ground. A one-point coloring keeps the exact
    # expected answer large (S_{v-1}) while avoiding an artificial all-distinct
    # full-string stabilizer that makes the smoke test needlessly expensive.
    assert v > OLD_GROUND_CAP

    group = _induced_symmetric_johnson_group(v, k)
    m = group.degree
    source = _distinguished_point_string(v, k)
    candidate = RightCoset(group, identity(m))

    new = candidate_coset_string_isomorphism_u3(
        candidate,
        source,
        source,
        root_n=m,
        max_explicit_degree=OLD_GROUND_CAP,
        max_group_order=256,
    )
    assert new.exact, new.reason
    assert new.coset is not None
    assert new.coset.subgroup.order == factorial(v - 1)
    return new


def test_rev209_joint_relation_dispatch_closes_j10_4_above_old_ground_cap():
    new = _assert_above_old_cap_new_exact(10, 4)
    assert "joint_relation" in new.status


def test_rev209_adaptive_relation_dispatch_closes_j9_4_when_two_relation_budget_does_not_fit():
    # C(9,2)+C(9,3)=120 exceeds 0.9*C(9,4)=113, so the two-relation selector
    # cannot fire. The adaptive single-relation fallback still closes exactly.
    new = _assert_above_old_cap_new_exact(9, 4)
    assert "relation_image_candidate" in new.status


def test_rev209_profile_terminal_closes_j9_2_when_no_lower_arity_exists():
    # k=2 has no configured t>=2 relation below k, so both relation-image routes
    # are exhausted. The complete pair relation is determined by the [1,8]
    # ground-profile partition, whose ambient orbit has only nine states, while
    # the exact stabilizer is S8.
    new = _assert_above_old_cap_new_exact(9, 2)
    assert new.coset.subgroup.order == 40320
    assert "signed_ground_profile" in new.status
