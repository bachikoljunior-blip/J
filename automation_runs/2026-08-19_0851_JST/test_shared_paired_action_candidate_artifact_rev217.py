from dataclasses import FrozenInstanceError
from itertools import combinations

import signed_johnson_joint_relation_candidate_si_v1 as joint_consumer
import signed_johnson_log_codegree_image_si_v1 as log_consumer
import signed_johnson_relation_image_candidate_si_v1 as relation_consumer
from coset_stabilizer_primitives import RightCoset, pointwise_stabilizer_chain
from paired_action_full_candidate_filter_v1 import (
    build_paired_action_full_candidate_artifact,
    build_paired_action_preimage_artifact,
)
from permutation_group_schreier import identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from signed_johnson_relation_image_candidate_si_v1 import (
    signed_johnson_relation_image_candidate_string_isomorphism,
)
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


def _extend4(p4):
    return tuple(p4) + (4, 5)


def _cycle4():
    return _extend4((1, 2, 3, 0))


def _swap01():
    return _extend4((1, 0, 2, 3))


def _kernel_swap():
    return (0, 1, 2, 3, 5, 4)


def _project_first4(g):
    return tuple(g[i] for i in range(4))


def _paired_example():
    group = schreier_stabilizer_chain([_cycle4(), _swap01(), _kernel_swap()])
    images = tuple(_project_first4(g) for g in group.original_generators)
    image = schreier_stabilizer_chain(images)
    subgroup = pointwise_stabilizer_chain(image, (0,))
    image_coset = RightCoset(subgroup, (1, 2, 3, 0))
    source = tuple(range(6))
    rinv = inverse(_cycle4())
    target = tuple(source[rinv[j]] for j in range(6))
    return group, images, image_coset, source, target


def _candidate_parameters(**overrides):
    values = {
        "polylog_power": 2,
        "max_explicit_degree": 8,
        "group_order_poly_power": 2,
        "max_group_order": 256,
        "max_depth": 64,
    }
    values.update(overrides)
    return tuple(values.items())


def _unresolved_dispatch(candidate, source, target, *, root_n, **kwargs):
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=candidate.subgroup.degree,
        operation_kind="test_resource_cap",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=False,
        reason="synthetic test resource cap",
    )
    return ProofCarryingCoset(
        "undetermined_test_resource_cap",
        candidate,
        accounting.operation_kind,
        root_n,
        candidate.subgroup.degree,
        True,
        False,
        False,
        0.0,
        False,
        (),
        accounting,
        0,
        accounting.reason,
    )


def test_frozen_full_artifact_reuses_complete_identity_and_misses_gate_changes():
    group, images, image_coset, source, target = _paired_example()
    build_paired_action_preimage_artifact.cache_clear()
    build_paired_action_full_candidate_artifact.cache_clear()

    first = build_paired_action_full_candidate_artifact(
        group,
        images,
        image_coset,
        source,
        target,
        root_n=8,
        candidate_dispatch=candidate_coset_string_isomorphism_u2,
        candidate_parameters=_candidate_parameters(),
    )
    second = build_paired_action_full_candidate_artifact(
        group,
        images,
        image_coset,
        source,
        target,
        root_n=8,
        candidate_dispatch=candidate_coset_string_isomorphism_u2,
        candidate_parameters=tuple(reversed(_candidate_parameters())),
    )
    assert first is second
    assert first.status == "exact_paired_action_full_candidate", first
    assert first.candidate is not None and first.candidate.exact
    assert first.preimage.coset is not None
    assert first.preimage.coset.contains(_cycle4())
    assert first.candidate.coset is not None and first.candidate.coset.contains(_cycle4())
    assert build_paired_action_full_candidate_artifact.cache_info().hits == 1
    assert build_paired_action_preimage_artifact.cache_info().misses == 1

    try:
        first.status = "forged"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("paired-action artifact was mutable")

    changed_gate = build_paired_action_full_candidate_artifact(
        group,
        images,
        image_coset,
        source,
        target,
        root_n=8,
        candidate_dispatch=candidate_coset_string_isomorphism_u2,
        candidate_parameters=_candidate_parameters(max_group_order=255),
    )
    changed_root = build_paired_action_full_candidate_artifact(
        group,
        images,
        image_coset,
        source,
        target,
        root_n=9,
        candidate_dispatch=candidate_coset_string_isomorphism_u2,
        candidate_parameters=_candidate_parameters(),
    )
    reverse_coset = RightCoset(image_coset.subgroup, inverse(image_coset.representative))
    changed_orientation = build_paired_action_full_candidate_artifact(
        group,
        images,
        reverse_coset,
        target,
        source,
        root_n=8,
        candidate_dispatch=candidate_coset_string_isomorphism_u2,
        candidate_parameters=_candidate_parameters(),
    )
    assert changed_gate is not first
    assert changed_root is not first
    assert changed_orientation is not first


def test_nonrestricting_and_resource_capped_children_remain_fail_closed():
    group = schreier_stabilizer_chain([(1, 2, 0), (1, 0, 2)])
    images = tuple(group.original_generators)
    image = schreier_stabilizer_chain(images)
    whole_image = RightCoset(image, identity(3))
    dispatch_calls = []

    def must_not_dispatch(*args, **kwargs):
        dispatch_calls.append(1)
        raise AssertionError("same-domain candidate was recursively dispatched")

    nonrestricting = build_paired_action_full_candidate_artifact(
        group,
        images,
        whole_image,
        (0, 1, 0),
        (0, 1, 0),
        root_n=3,
        candidate_dispatch=must_not_dispatch,
    )
    assert nonrestricting.status == "undetermined_paired_action_nonrestricting_candidate"
    assert nonrestricting.nonrestricting
    assert not dispatch_calls
    assert nonrestricting.candidate is not None and not nonrestricting.candidate.exact

    pgroup, pimages, pcoset, source, target = _paired_example()
    capped = build_paired_action_full_candidate_artifact(
        pgroup,
        pimages,
        pcoset,
        source,
        target,
        root_n=8,
        candidate_dispatch=_unresolved_dispatch,
        candidate_parameters=(("max_nodes", 1),),
    )
    assert capped.status.endswith("undetermined_test_resource_cap"), capped
    assert capped.preimage.coset is not None
    assert capped.candidate is not None and not capped.candidate.exact


def test_unhashable_strings_bypass_cache_without_changing_fail_closed_result():
    group, images, image_coset, source, target = _paired_example()
    unhashable_source = tuple([x] for x in source)
    unhashable_target = tuple([x] for x in target)
    build_paired_action_full_candidate_artifact.cache_clear()
    a = build_paired_action_full_candidate_artifact(
        group,
        images,
        image_coset,
        unhashable_source,
        unhashable_target,
        root_n=8,
        candidate_dispatch=_unresolved_dispatch,
    )
    b = build_paired_action_full_candidate_artifact(
        group,
        images,
        image_coset,
        unhashable_source,
        unhashable_target,
        root_n=8,
        candidate_dispatch=_unresolved_dispatch,
    )
    assert a is not b
    assert a.status == b.status
    assert not a.candidate.exact and not b.candidate.exact
    assert build_paired_action_full_candidate_artifact.cache_info().currsize == 0
    frozen_snapshot = a.source_identity
    unhashable_source[0].append("mutated-after-proof")
    assert a.source_identity == frozen_snapshot


def _cycle(v):
    return tuple((i + 1) % v for i in range(v))


def _ground_swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def _induced_ground_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    generators = tuple(induce(g) for g in (_ground_swap01(v), _cycle(v)))
    return schreier_stabilizer_chain(generators), generators, subsets


def test_all_three_consumers_share_builder_and_actual_relation_path_hits_preimage_cache():
    assert (
        relation_consumer.build_paired_action_full_candidate_artifact
        is joint_consumer.build_paired_action_full_candidate_artifact
        is log_consumer.build_paired_action_full_candidate_artifact
    )
    group, generators, subsets = _induced_ground_group(6, 3)
    source = tuple(int(0 in subset) for subset in subsets)
    witness = generators[1]
    winv = inverse(witness)
    target = tuple(source[winv[j]] for j in range(len(source)))
    build_paired_action_preimage_artifact.cache_clear()
    build_paired_action_full_candidate_artifact.cache_clear()
    got = signed_johnson_relation_image_candidate_string_isomorphism(
        group,
        source,
        target,
        relation_arity=2,
        root_n=32,
        max_image_si_nodes=100000,
        max_candidate_group_order=256,
    )
    assert got.exact and got.coset is not None and got.coset.contains(witness), got
    # The filter builds the preimage; the shared full-candidate artifact replays
    # the same complete identity and must receive that exact cached object.
    assert build_paired_action_preimage_artifact.cache_info().hits >= 1
    assert build_paired_action_full_candidate_artifact.cache_info().misses == 1
