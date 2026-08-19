from collections import Counter
from itertools import combinations

from babai_recurrence_contract_v1 import validate_babai_recurrence_step
from johnson_ground_relational_lift_v1 import _standard_subsets
from signed_johnson_complement_safe_image_si_v1 import (
    complement_safe_t_relation_signatures,
)
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_local_guide_partition_plan_v1 import (
    build_local_guide_partition_plan,
)


def cyclic_design_blocks(v, bases):
    blocks = set()
    for base in bases:
        for shift in range(v):
            blocks.add(tuple(sorted((x + shift) % v for x in base)))
    return frozenset(blocks)


def test_triple_relation_guides_split_the_z9_pair_homogeneous_design():
    v, k, r = 9, 4, 3
    selected = cyclic_design_blocks(v, ((0, 1, 2, 4), (0, 1, 4, 6)))
    subsets = _standard_subsets(v, k)
    values = tuple(int(subset in selected) for subset in subsets)
    tokens = tuple(_color_token(x) for x in values)
    relation = complement_safe_t_relation_signatures(
        v, k, tokens, r, complement_in_image=False
    )

    plan = build_local_guide_partition_plan(
        v, r, relation, relation, root_n=126
    )
    assert plan.status == "verified_quasipoly_local_guide_partition_plan", plan
    assert plan.guide_size == 1
    assert len(plan.source_outcomes) == len(plan.target_outcomes) == 9
    assert all(x.significant_split for x in plan.source_outcomes)
    assert {x.partition_cells for x in plan.source_outcomes} == {(6, 2, 1)}
    assert {x.largest_cell for x in plan.source_outcomes} == {6}
    assert plan.compatible_guide_pairs == 81
    assert plan.quasipolynomial_guide_bound_verified
    assert plan.recurrence is not None and plan.recurrence_validation is not None
    assert plan.recurrence_validation.progress_verified
    checked = validate_babai_recurrence_step(
        plan.recurrence, max_branch_factor=81, min_shrink_fraction=0.1
    )
    assert checked.progress_verified


def test_complement_safe_relation_transports_the_complete_guide_fingerprint_family():
    v, k, r = 8, 4, 3
    subsets = _standard_subsets(v, k)
    index = {subset: i for i, subset in enumerate(subsets)}
    U = set(range(v))
    source = tuple((sum(subset) + subset[0]) % 4 for subset in subsets)
    target = [None] * len(subsets)
    for i, subset in enumerate(subsets):
        comp = tuple(sorted(U.difference(subset)))
        target[index[comp]] = source[i]
    target = tuple(target)

    src_relation = complement_safe_t_relation_signatures(
        v, k, tuple(_color_token(x) for x in source), r,
        complement_in_image=True,
    )
    dst_relation = complement_safe_t_relation_signatures(
        v, k, tuple(_color_token(x) for x in target), r,
        complement_in_image=True,
    )
    plan = build_local_guide_partition_plan(
        v, r, src_relation, dst_relation, root_n=70
    )
    src_fps = Counter(x.fingerprint for x in plan.source_outcomes)
    dst_fps = Counter(x.fingerprint for x in plan.target_outcomes)
    assert src_fps == dst_fps
    assert plan.status != "exact_empty_local_guide_fingerprint_invariant"
