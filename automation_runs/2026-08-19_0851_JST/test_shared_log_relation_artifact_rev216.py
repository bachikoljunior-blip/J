from collections import Counter
from dataclasses import FrozenInstanceError, replace
from itertools import combinations

import pytest

import signed_johnson_log_certificate_design_descent_si_v1 as log_design
import signed_johnson_log_codegree_image_si_v1 as pair_image
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from permutation_group_schreier import inverse, schreier_stabilizer_chain
from signed_johnson_log_certificate_design_descent_si_v1 import (
    _codegree_signatures,
    _relation_descent,
    build_signed_johnson_log_relation_artifact,
)
from u2_candidate_coset_string_iso_v6 import candidate_coset_string_isomorphism_u6


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


def hidden_j42_triple_colors():
    hidden = tuple(combinations(range(4), 2))

    def adjacent(a, b):
        return len(set(hidden[a]).intersection(hidden[b])) == 1

    return tuple(
        sum(int(adjacent(a, b)) for a, b in combinations(S, 2))
        for S in combinations(range(6), 3)
    )


def legacy_replay_to_pair(v, coords, source, target, arity):
    """Test-only specification of the production replay removed in rev216."""
    path = [arity]
    while arity > 2:
        for s in range(arity - 1, 1, -1):
            subcoords, src = _codegree_signatures(v, coords, source, s)
            _, dst = _codegree_signatures(v, coords, target, s)
            if Counter(src) != Counter(dst):
                return None
            if len(set(src).union(dst)) > 1:
                coords, source, target, arity = subcoords, src, dst, s
                path.append(arity)
                break
        else:
            return None
    return tuple(coords), tuple(source), tuple(target), tuple(path)


def test_descent_carries_the_exact_terminal_pair_previously_replayed_by_rev214():
    v, arity = 9, 3
    coords = tuple(combinations(range(v), arity))
    base = (0, 1, 3)
    cyclic = {
        tuple(sorted((x + shift) % v for x in base))
        for shift in range(v)
    }
    source = tuple(int(S in cyclic) for S in coords)
    target = source
    legacy = legacy_replay_to_pair(v, coords, source, target, arity)
    assert legacy is not None

    got = _relation_descent(
        v,
        coords,
        source,
        target,
        arity,
        max_class_fraction=0.9,
        max_johnson_nodes=100000,
    )
    pair_coords, pair_source, pair_target, path = legacy
    assert got.status in {
        "certified_log_certificate_johnson_descent",
        "homogeneous_pair_relation_unresolved",
    }
    assert got.arity_path == path == (3, 2)
    assert got.terminal_coords == pair_coords
    assert got.terminal_source_relation == pair_source
    assert got.terminal_target_relation == pair_target


def test_exact_identity_reuses_one_frozen_relation_artifact_across_consumers():
    group, generators, _subsets = induced_ground_group(6, 3)
    source = hidden_j42_triple_colors()
    target = relabel_target(source, generators[0])
    lift = lift_primitive_johnson_to_ground_relation(
        group, source, target, max_recognition_nodes=100000
    )
    assert lift.status == "exact_johnson_ground_relational_lift"
    assert log_design.build_signed_johnson_log_relation_artifact is pair_image.build_signed_johnson_log_relation_artifact

    build_signed_johnson_log_relation_artifact.cache_clear()
    first = log_design.build_signed_johnson_log_relation_artifact(
        lift,
        root_n=64,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    first_info = build_signed_johnson_log_relation_artifact.cache_info()
    second = pair_image.build_signed_johnson_log_relation_artifact(
        lift,
        root_n=64,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    second_info = build_signed_johnson_log_relation_artifact.cache_info()

    assert first.status == "certified_log_relation_descent"
    assert first.descent is not None
    assert first.descent.terminal_coords == tuple(combinations(range(6), 2))
    assert first is second
    assert first_info.misses == 1 and first_info.hits == 0
    assert second_info.misses == 1 and second_info.hits == 1
    with pytest.raises(FrozenInstanceError):
        first.status = "exact_fabricated"

    # Orientation and every resource/theorem gate are proof-key components.
    reversed_orientation = build_signed_johnson_log_relation_artifact(
        replace(
            lift,
            source_on_standard_subsets=lift.target_on_standard_subsets,
            target_on_standard_subsets=lift.source_on_standard_subsets,
        ),
        root_n=64,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    changed_recognition_gate = build_signed_johnson_log_relation_artifact(
        lift,
        root_n=64,
        max_recognition_nodes=100001,
        max_johnson_nodes=100000,
    )
    changed_johnson_gate = build_signed_johnson_log_relation_artifact(
        lift,
        root_n=64,
        max_recognition_nodes=100000,
        max_johnson_nodes=100001,
    )
    changed_fraction = build_signed_johnson_log_relation_artifact(
        lift,
        root_n=64,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
        max_class_fraction=0.8,
    )
    changed_root = build_signed_johnson_log_relation_artifact(
        lift,
        root_n=65,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    changed_test_gate = build_signed_johnson_log_relation_artifact(
        lift,
        root_n=64,
        max_test_sets=199999,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    assert all(
        artifact is not first
        for artifact in (
            reversed_orientation,
            changed_recognition_gate,
            changed_johnson_gate,
            changed_fraction,
            changed_root,
            changed_test_gate,
        )
    )

    # An unhashable fail-closed lift bypasses the LRU and remains fail-closed.
    unhashable = replace(
        lift,
        status="undetermined_test_lift",
        strict_auxiliary_progress=False,
        source_on_standard_subsets=tuple([x] for x in lift.source_on_standard_subsets),
    )
    before = build_signed_johnson_log_relation_artifact.cache_info()
    bypass1 = build_signed_johnson_log_relation_artifact(
        unhashable,
        root_n=64,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    bypass2 = build_signed_johnson_log_relation_artifact(
        unhashable,
        root_n=64,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    after = build_signed_johnson_log_relation_artifact.cache_info()
    assert bypass1.status == bypass2.status == "undetermined_log_relation_johnson_lift"
    assert bypass1 == bypass2 and bypass1 is not bypass2
    assert after == before


def test_actual_rev184_then_rev214_consumers_hit_the_same_artifact():
    group, _generators, _subsets = induced_ground_group(6, 3)
    source = hidden_j42_triple_colors()
    build_signed_johnson_log_relation_artifact.cache_clear()

    structural = log_design.signed_johnson_log_certificate_design_descent_si(
        group,
        source,
        source,
        root_n=64,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    after_structural = build_signed_johnson_log_relation_artifact.cache_info()
    assert structural.status == "verified_log_certificate_johnson_structural_descent"
    assert after_structural.misses == 1 and after_structural.hits == 0

    replayed = log_design.signed_johnson_log_certificate_design_descent_si(
        group,
        source,
        source,
        root_n=64,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    after_replay = build_signed_johnson_log_relation_artifact.cache_info()
    assert replayed == structural
    assert replayed.accounting == structural.accounting
    assert replayed.local_log2_cost_bound == structural.local_log2_cost_bound
    assert after_replay.misses == 1 and after_replay.hits == 1

    pair = pair_image.signed_johnson_log_codegree_image_candidate_si(
        group,
        source,
        source,
        root_n=64,
        candidate_dispatch=candidate_coset_string_isomorphism_u6,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
        max_image_si_nodes=1,
    )
    after_pair = build_signed_johnson_log_relation_artifact.cache_info()
    assert pair.status == "undetermined_log_codegree_pair_image_node_limit"
    assert after_pair.misses == 1 and after_pair.hits >= 2
