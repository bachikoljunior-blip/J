from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional

from canonical_partition_transporter_v1 import canonical_partition_transporter
from coset_stabilizer_primitives import RightCoset
from implicit_relation_image_action_v1 import ImplicitRelationImageAction
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain


@dataclass(frozen=True)
class ImplicitRelationImageValueCoset:
    status: str
    exact: bool
    complete: bool
    auxiliary_degree: int
    partition_orbit_states: int
    coset: Optional[RightCoset]
    reason: str


def _maps(source, target, permutation) -> bool:
    return all(source[i] == target[permutation[i]] for i in range(len(source)))


def _stabilizes(values, permutation) -> bool:
    return all(values[i] == values[permutation[i]] for i in range(len(values)))


def _ordered_cells(values):
    positions = {}
    for point, value in enumerate(values):
        positions.setdefault(value, []).append(point)
    keys = tuple(sorted(positions, key=repr))
    return tuple(tuple(positions[key]) for key in keys), keys


def exact_implicit_relation_image_value_coset(
    action: ImplicitRelationImageAction,
    *,
    max_partition_states: int = 200_000,
) -> ImplicitRelationImageValueCoset:
    """Intersect an implicit relation-image group with the full value transporter.

    The rev257 artifact already supplies the exact image group by generators and
    a faithful auxiliary action.  Equality of feature values is an ordered
    partition condition.  We therefore solve the exact partition transporter in
    the implicit image group, without enumerating its elements.  If one
    transporter ``r`` exists, the source partition stabilizer is conjugated to
    the target stabilizer so the complete solution is returned in the repository
    ``RightCoset`` convention.

    The bounded partition-state orbit is explicit and fail closed.  Original-
    domain preimage integration and original-root quasipolynomial accounting are
    intentionally left to the next child.
    """
    if not isinstance(action, ImplicitRelationImageAction):
        raise TypeError("action must be an ImplicitRelationImageAction")
    if isinstance(max_partition_states, bool) or not isinstance(max_partition_states, int) or max_partition_states < 1:
        raise ValueError("max_partition_states must be a positive integer")

    if action.status.startswith("exact_empty_"):
        return ImplicitRelationImageValueCoset(
            action.status, True, True, action.auxiliary_degree, 0, None,
            action.reason,
        )
    if action.status != "exact_implicit_relation_image_paired_action":
        return ImplicitRelationImageValueCoset(
            "undetermined_implicit_relation_image_action", False, False,
            action.auxiliary_degree, 0, None,
            "value-coset intersection requires the exact rev257 implicit image action",
        )
    if action.image_group is None:
        raise AssertionError("exact implicit image action omitted its image group")

    source = tuple(action.source_features)
    target = tuple(action.target_features)
    m = action.auxiliary_degree
    if len(source) != m or len(target) != m:
        raise AssertionError("rev257 feature strings disagree with auxiliary degree")
    if Counter(source) != Counter(target):
        return ImplicitRelationImageValueCoset(
            "exact_empty_feature_inventory_mismatch", True, True, m, 0, None,
            "the complete auxiliary feature inventories differ, so no image-group element can transport source to target",
        )

    source_cells, source_keys = _ordered_cells(source)
    target_cells, target_keys = _ordered_cells(target)
    if source_keys != target_keys:
        raise AssertionError("equal feature inventories produced different ordered value keys")

    blocks = tuple((i,) for i in range(m))
    transported = canonical_partition_transporter(
        action.image_group,
        blocks,
        source_cells,
        target_cells,
        max_states=max_partition_states,
    )
    if transported.status == "undetermined_partition_orbit_limit":
        return ImplicitRelationImageValueCoset(
            "undetermined_image_value_partition_orbit_limit", False, False, m,
            transported.orbit_states, None,
            "exact image-group partition orbit exceeded max_partition_states before completeness was certified",
        )
    if transported.status in {"partition_shape_mismatch", "no_partition_transporter"}:
        return ImplicitRelationImageValueCoset(
            "exact_empty_implicit_image_value_coset", True, True, m,
            transported.orbit_states, None,
            "the exact implicit image group contains no permutation carrying every source feature class to the corresponding target class",
        )
    if transported.status != "partition_transporter_coset":
        return ImplicitRelationImageValueCoset(
            "undetermined_image_value_partition_transporter", False, False, m,
            transported.orbit_states, None, transported.reason,
        )
    if transported.transporter is None or transported.source_stabilizer is None:
        raise AssertionError("exact partition transporter omitted its witness or stabilizer")

    r = transported.transporter
    if not action.image_group.contains(r) or not _maps(source, target, r):
        raise AssertionError("partition transporter is not an image-group feature transporter")

    rinv = inverse(r)
    target_gens = tuple(
        compose(rinv, compose(g, r))
        for g in transported.source_stabilizer.original_generators
    )
    target_stabilizer = schreier_stabilizer_chain(target_gens or (identity(m),))
    for generator in target_stabilizer.original_generators or (identity(m),):
        if not action.image_group.contains(generator) or not _stabilizes(target, generator):
            raise AssertionError("conjugated target stabilizer escaped the image group or target feature classes")

    coset = RightCoset(target_stabilizer, r)
    return ImplicitRelationImageValueCoset(
        "exact_implicit_relation_image_value_coset", True, True, m,
        transported.orbit_states, coset,
        "implicit image-group ordered-partition transport returned one witness and the complete target-feature stabilizer right coset",
    )


__all__ = ["ImplicitRelationImageValueCoset", "exact_implicit_relation_image_value_coset"]
