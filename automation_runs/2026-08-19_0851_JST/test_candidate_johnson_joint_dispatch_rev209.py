from itertools import combinations

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2 as candidate_v2
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3


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


def _anchor_string(v, k, anchors):
    subsets = tuple(combinations(range(v), k))
    return tuple(tuple(int(a in subset) for a in range(anchors)) for subset in subsets)


def _assert_old_cap_new_exact(v, k, anchors, expected_order):
    group = _induced_symmetric_johnson_group(v, k)
    m = group.degree
    source = _anchor_string(v, k, anchors)
    candidate = RightCoset(group, identity(m))

    old = candidate_v2(
        candidate,
        source,
        source,
        root_n=m,
        max_explicit_degree=8,
        max_group_order=256,
    )
    assert not old.exact
    assert "johnson_ground_cap" in old.status

    new = candidate_coset_string_isomorphism_u3(
        candidate,
        source,
        source,
        root_n=m,
        max_explicit_degree=8,
        max_group_order=256,
    )
    assert new.exact, new.reason
    assert new.coset is not None
    assert new.coset.subgroup.order == expected_order
    return new


def test_rev209_joint_relation_dispatch_closes_j10_4_above_old_ground_cap():
    new = _assert_old_cap_new_exact(10, 4, 8, 2)
    assert "joint_relation" in new.status


def test_rev209_adaptive_relation_dispatch_closes_j9_4_when_two_relation_budget_does_not_fit():
    # For J(9,4), C(9,2)+C(9,3)=120 exceeds 0.9*C(9,4)=113, so rev183's
    # two-relation selector cannot fire.  The rev182 adaptive single-relation
    # fallback can still select an informative strictly smaller relation and
    # reduce the exact full-string candidate to the S2 on the two unanchored
    # ground points.
    new = _assert_old_cap_new_exact(9, 4, 7, 2)
    assert "relation_image_candidate" in new.status
