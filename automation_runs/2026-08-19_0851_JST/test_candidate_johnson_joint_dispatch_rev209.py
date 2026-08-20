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


def _same_inventory_nonisomorphic_target(source):
    # Keep exactly the same global color inventory while moving the 1-set to a
    # lexicographic segment. For the Johnson fixtures below this destroys the
    # canonical lower-arity incidence statistics, so the new relation-image route
    # can prove exact emptiness before an expensive nonempty full-candidate solve.
    ones = sum(int(x == 1) for x in source)
    n = len(source)
    target = tuple(1 if i < ones else 0 for i in range(n))
    assert sorted(source) == sorted(target)
    return target


def _candidate(v, k):
    assert v > OLD_GROUND_CAP
    group = _induced_symmetric_johnson_group(v, k)
    source = _distinguished_point_string(v, k)
    return group, source, RightCoset(group, identity(group.degree))


def test_rev209_joint_relation_dispatch_proves_exact_empty_j10_4_above_old_ground_cap():
    # Default rev183 selection on J(10,4) can fit pair+triple (45+120 <= 189).
    # Use an equal-inventory but lower-arity-invariant-mismatched target so this
    # integration regression exercises the real default joint route without
    # spending CI time solving a huge nonempty full-string stabilizer.
    group, source, candidate = _candidate(10, 4)
    target = _same_inventory_nonisomorphic_target(source)
    got = candidate_coset_string_isomorphism_u3(
        candidate, source, target, root_n=group.degree,
        max_explicit_degree=OLD_GROUND_CAP, max_group_order=256,
    )
    assert got.exact and got.coset is None, got.reason
    assert "joint_relation" in got.status


def test_rev209_adaptive_relation_dispatch_proves_exact_empty_j9_4_when_joint_budget_does_not_fit():
    # C(9,2)+C(9,3)=120 exceeds 0.9*C(9,4)=113.4. The joint selector cannot
    # keep both, so candidate-v3 falls through to the adaptive single-relation
    # route. Again use an equal-inventory mismatch to keep this a fast exact gate.
    group, source, candidate = _candidate(9, 4)
    target = _same_inventory_nonisomorphic_target(source)
    got = candidate_coset_string_isomorphism_u3(
        candidate, source, target, root_n=group.degree,
        max_explicit_degree=OLD_GROUND_CAP, max_group_order=256,
    )
    assert got.exact and got.coset is None, got.reason
    assert "relation" in got.status
    assert "joint_relation" not in got.status


def test_rev209_profile_terminal_closes_j9_2_when_no_lower_arity_exists():
    # k=2 has no configured t>=2 relation below k, so both relation-image routes
    # are exhausted. The complete pair relation is determined by the [1,8]
    # ground-profile partition, whose ambient orbit has only nine states, while
    # the exact stabilizer is S8.
    group, source, candidate = _candidate(9, 2)
    got = candidate_coset_string_isomorphism_u3(
        candidate, source, source, root_n=group.degree,
        max_explicit_degree=OLD_GROUND_CAP, max_group_order=256,
    )
    assert got.exact and got.coset is not None, got.reason
    assert got.coset.subgroup.order == factorial(8)
    assert "signed_ground_profile" in got.status
