from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from canonical_partition_transporter_v1 import (
    CanonicalPartitionTransport,
    canonical_partition_transporter,
)
from coset_stabilizer_primitives import RightCoset, pointwise_stabilizer_chain
from permutation_group_schreier import (
    StabilizerChain,
    compose,
    identity,
    orbit_transversal,
)
from relation_twin_design_wiring_v1 import (
    RelationTwinDesignWiring,
    wire_no_large_twin_relation_into_design,
)


@dataclass(frozen=True)
class OrderedTupleTransport:
    status: str
    source_tuple: tuple[int, ...]
    target_tuple: tuple[int, ...]
    coset: RightCoset | None
    orbit_steps: int
    exact: bool
    reason: str


@dataclass(frozen=True)
class AmbientDesignTupleBranch:
    source_tuple: tuple[int, ...]
    target_tuple: tuple[int, ...]
    coset: RightCoset
    stabilizer_order: int


@dataclass(frozen=True)
class AmbientDesignTupleCover:
    status: str
    wiring: RelationTwinDesignWiring
    ambient_group_order: int
    original_branch_count: int
    surviving_branch_count: int
    branches: tuple[AmbientDesignTupleBranch, ...]
    unary_transport: CanonicalPartitionTransport | None
    exact_empty: bool
    parent_provenance_verified: bool
    ambient_pairing_complete: bool
    full_string_integration_complete: bool
    exact: bool
    reason: str


def ordered_tuple_transporter(
    group: StabilizerChain,
    source_tuple: Iterable[int],
    target_tuple: Iterable[int],
) -> OrderedTupleTransport:
    """Exact transporter coset for one ordered injective tuple pair inside G.

    If a representative r maps x_i to y_i, every other such element p satisfies
    p r^{-1} in the pointwise stabilizer of the target tuple. With this repository's
    right-action compose convention that is exactly the RightCoset returned below.
    The representative is constructed one coordinate at a time with Schreier orbit
    transversals while the already-hit target points are fixed.
    """
    source = tuple(int(x) for x in source_tuple)
    target = tuple(int(y) for y in target_tuple)
    n = int(group.degree)
    if len(source) != len(target):
        return OrderedTupleTransport(
            "tuple_length_mismatch", source, target, None, 0, True,
            "ordered source and target tuple lengths differ",
        )
    if len(set(source)) != len(source) or len(set(target)) != len(target):
        raise ValueError("Design individualization tuples must be injective")
    if any(x < 0 or x >= n for x in source + target):
        raise ValueError("tuple point outside ambient group domain")

    representative = identity(n)
    stabilizer = group
    orbit_steps = 0
    for i, (x, y) in enumerate(zip(source, target)):
        current = representative[x]
        gens = stabilizer.original_generators or (identity(n),)
        orbit, transversal = orbit_transversal(current, gens, n)
        orbit_steps += len(orbit)
        if y not in transversal:
            return OrderedTupleTransport(
                "no_ordered_tuple_transporter", source, target, None,
                orbit_steps, True,
                "target coordinate is outside the orbit of the current source image under the stabilizer of earlier target coordinates",
            )
        representative = compose(representative, transversal[y])
        stabilizer = pointwise_stabilizer_chain(group, target[: i + 1])

    if any(representative[x] != y for x, y in zip(source, target)):
        raise AssertionError("constructed tuple transporter does not map source to target")
    return OrderedTupleTransport(
        "ordered_tuple_transporter_coset", source, target,
        RightCoset(stabilizer, representative), orbit_steps, True,
        "representative maps the ordered individualized tuple exactly and the subgroup is the exact ambient pointwise stabilizer of its target tuple",
    )


def pair_design_witnesses_inside_ambient_action(
    right_group: StabilizerChain,
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    max_subsets: int = 200000,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_twl_rounds: int | None = None,
    max_twl_work_units: int = 500000000,
    max_branch_pairs: int = 200000,
    max_partition_states: int = 200000,
) -> AmbientDesignTupleCover:
    """W1R-H6-R3c2a: intersect rev204 Design branches with the ambient right action.

    Rev204 deliberately constructs its exact Design witness family under arbitrary
    relabeling of the derived right-ground relation. That is the correct canonical
    combinatorial layer, but recursive String Isomorphism must stay inside the
    actual allowed parent group. This bridge therefore re-derives rev204 from the
    parent bipartite inputs and intersects its complete witness cover with a supplied
    exact right-ground StabilizerChain.

    For arity >=2 every individualized tuple pair is replaced by its exact ambient
    transporter coset; unreachable pairs are removed. Because rev204 enumerates the
    complete first successful witness level, an ambient relation isomorphism must
    occur in one surviving coset. If none survives, the ambient SI instance is exact
    empty. For the unary direct-coloring case, the ordered color partition is paired
    with the existing exact partition-transporter primitive on singleton blocks.

    This closes ambient *witness pairing*. It intentionally does not claim that the
    structural split/UPCC output has already been intersected with the original full
    string; each returned coset is the exact child domain for that next operation.
    """
    if int(right_group.degree) != int(right_size):
        raise ValueError("ambient right-group degree must equal right_size")

    wiring = wire_no_large_twin_relation_into_design(
        left_size,
        right_size,
        tuple(source_edges),
        tuple(target_edges),
        alpha=alpha,
        max_subsets=max_subsets,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_twl_rounds=max_twl_rounds,
        max_twl_work_units=max_twl_work_units,
        max_branch_pairs=max_branch_pairs,
    )
    group_order = int(right_group.order)

    if wiring.exact_empty:
        return AmbientDesignTupleCover(
            "exact_empty_rev204_parent", wiring, group_order, 0, 0, (), None,
            True, wiring.parent_provenance_verified, True, False, True,
            "rev204 already established an exact paired invariant mismatch before ambient witness pairing",
        )

    if wiring.status == "certified_unary_relation_half_bounded_coloring":
        blocks = tuple((i,) for i in range(int(right_size)))
        transport = canonical_partition_transporter(
            right_group,
            blocks,
            wiring.source_unary_partition,
            wiring.target_unary_partition,
            max_states=max_partition_states,
        )
        if transport.status == "undetermined_partition_orbit_limit":
            return AmbientDesignTupleCover(
                "undetermined_unary_ambient_partition_orbit_limit", wiring,
                group_order, 1, 0, (), transport, False, True, False, False,
                False, transport.reason,
            )
        if transport.status in {"partition_shape_mismatch", "no_partition_transporter"}:
            return AmbientDesignTupleCover(
                "exact_empty_unary_ambient_partition", wiring, group_order,
                1, 0, (), transport, True, True, True, False, True,
                "the exact ambient right action contains no transporter between the ordered unary relation colorings",
            )
        if transport.status != "partition_transporter_coset" or transport.transporter is None or transport.source_stabilizer is None:
            raise AssertionError("unexpected exact unary partition-transporter status")
        return AmbientDesignTupleCover(
            "certified_unary_ambient_partition_coset", wiring, group_order,
            1, 1, (), transport, False, True, True, False, True,
            "rev204's unary relation coloring is paired inside the actual ambient right action with an exact transporter and source-stabilizer coset",
        )

    if wiring.status != "certified_relation_design_branch_plan" or wiring.branch_plan is None:
        return AmbientDesignTupleCover(
            "ambient_design_tuple_pairing_not_applicable", wiring, group_order,
            0, 0, (), None, False, wiring.parent_provenance_verified,
            False, False, wiring.exact,
            "rev204 did not reach the complete no-large-twin Design branch plan handled by this ambient pairing child",
        )

    plan = wiring.branch_plan
    if not plan.complete or plan.status != "certified_complete_design_branch_plan":
        return AmbientDesignTupleCover(
            "undetermined_incomplete_rev204_design_plan", wiring, group_order,
            int(plan.branch_count), 0, (), None, False,
            wiring.parent_provenance_verified, False, False, False,
            "rev204 Design branch plan is not complete enough for exact ambient filtering",
        )

    branches = []
    for source_tuple, target_tuple in plan.branches:
        transported = ordered_tuple_transporter(right_group, source_tuple, target_tuple)
        if transported.status == "no_ordered_tuple_transporter":
            continue
        if transported.status != "ordered_tuple_transporter_coset" or transported.coset is None:
            raise AssertionError("unexpected ordered tuple transporter status")
        branches.append(
            AmbientDesignTupleBranch(
                tuple(source_tuple),
                tuple(target_tuple),
                transported.coset,
                int(transported.coset.subgroup.order),
            )
        )

    if not branches:
        return AmbientDesignTupleCover(
            "exact_empty_ambient_design_witness_cover", wiring, group_order,
            int(plan.branch_count), 0, (), None, True, True, True, False, True,
            "the complete rev204 witness Cartesian cover contains no tuple pair reachable by the actual ambient right group",
        )

    return AmbientDesignTupleCover(
        "certified_ambient_design_witness_coset_cover", wiring, group_order,
        int(plan.branch_count), len(branches), tuple(branches), None,
        False, True, True, False, True,
        "every surviving Design witness pair is represented by an exact ambient transporter coset; completeness follows from rev204's full first-successful witness-level cover, while full-string intersection remains the next child",
    )
