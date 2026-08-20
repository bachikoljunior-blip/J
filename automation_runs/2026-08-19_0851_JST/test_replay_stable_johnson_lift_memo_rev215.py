from dataclasses import FrozenInstanceError
from itertools import combinations

import pytest

import signed_johnson_log_certificate_design_descent_si_v1 as log_design
import signed_johnson_log_codegree_image_si_v1 as pair_image
from johnson_ground_relational_lift_v1 import (
    lift_primitive_johnson_to_ground_relation,
)
from permutation_group_schreier import inverse, schreier_stabilizer_chain


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

    generators = tuple(induce(g) for g in (swap01(v), cycle(v)))
    return schreier_stabilizer_chain(generators), generators, subsets


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def test_exact_proof_identity_reuses_immutable_johnson_lift_across_dispatchers():
    group, generators, subsets = induced_ground_group(5, 2)
    source = tuple((sum(subset) + subset[0]) % 3 for subset in subsets)
    target = relabel_target(source, generators[0])

    # Both dispatcher layers import the same replay-stable proof entry point.
    assert log_design.lift_primitive_johnson_to_ground_relation is pair_image.lift_primitive_johnson_to_ground_relation
    assert pair_image.lift_primitive_johnson_to_ground_relation is lift_primitive_johnson_to_ground_relation

    lift_primitive_johnson_to_ground_relation.cache_clear()
    first = log_design.lift_primitive_johnson_to_ground_relation(
        group,
        list(source),
        list(target),
        max_recognition_nodes=50000,
    )
    after_first = lift_primitive_johnson_to_ground_relation.cache_info()
    second = pair_image.lift_primitive_johnson_to_ground_relation(
        group,
        tuple(source),
        tuple(target),
        max_recognition_nodes=50000,
    )
    after_second = lift_primitive_johnson_to_ground_relation.cache_info()

    assert first.status == "exact_johnson_ground_relational_lift"
    assert first.strict_auxiliary_progress
    assert first is second
    assert after_first.misses == 1 and after_first.hits == 0
    assert after_second.misses == 1 and after_second.hits == 1
    assert second.recognition_search_nodes == first.recognition_search_nodes > 0

    # Resource gates and string contents are part of the identity.  Neither may
    # alias an artifact proved under different inputs.
    changed_gate = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=50001,
    )
    changed_target = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        tuple(reversed(target)),
        max_recognition_nodes=50000,
    )
    final_info = lift_primitive_johnson_to_ground_relation.cache_info()
    assert changed_gate is not first
    assert changed_target is not first
    assert final_info.misses == 3 and final_info.hits == 1

    with pytest.raises(FrozenInstanceError):
        first.status = "exact_fabricated"


def test_unhashable_color_values_bypass_memo_without_changing_exact_result():
    group, generators, subsets = induced_ground_group(5, 2)
    source = [[(sum(subset) + subset[0]) % 3] for subset in subsets]
    target = relabel_target(source, generators[0])

    lift_primitive_johnson_to_ground_relation.cache_clear()
    first = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=50000,
    )
    second = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=50000,
    )
    info = lift_primitive_johnson_to_ground_relation.cache_info()

    assert first.status == second.status == "exact_johnson_ground_relational_lift"
    assert first == second and first is not second
    assert info.hits == info.misses == info.currsize == 0
