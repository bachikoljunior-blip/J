from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import ceil, log2
from typing import Optional, Tuple

from block_action_preimage_coset_v1 import block_action_preimage_coset
from giant_block_action_certificates import _block_action, analyze_giant_block_action
from orbit_factored_partial_string_coset_intersection_v1 import (
    orbit_factored_partial_string_coset_intersection,
)
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    compose,
    identity,
    schreier_stabilizer_chain,
)


@dataclass(frozen=True)
class AffectedSegmentAutomorphism:
    status: str
    subgroup: Optional[StabilizerChain]
    active_points: Tuple[int, ...]
    quotient_degree: int
    quotient_elements_enumerated: int
    accepted_quotient_elements: int
    quotient_log2_multiplicative_cost: float
    largest_recursive_child_domain: int
    certified_child_domain_bound: int
    recurrence_child_bound_verified: bool
    child_search_nodes: Tuple[int, ...]
    reason: str


def _enumerate_group(chain: StabilizerChain, max_elements: int):
    if max_elements <= 0:
        raise ValueError("max_elements must be positive")
    e = identity(chain.degree)
    gens = chain.original_generators or (e,)
    seen = {e}
    todo = deque([e])
    while todo:
        x = todo.popleft()
        for g in gens:
            y = compose(x, g)
            if y in seen:
                continue
            seen.add(y)
            if len(seen) > max_elements:
                return None
            todo.append(y)
    if len(seen) != chain.order:
        raise AssertionError("quotient enumeration disagrees with Schreier-chain order")
    return tuple(sorted(seen))


def _same_subgroup(a: StabilizerChain, b: StabilizerChain) -> bool:
    if a.degree != b.degree or a.order != b.order:
        return False
    return (
        all(b.contains(g) for g in (a.original_generators or (identity(a.degree),)))
        and all(a.contains(g) for g in (b.original_generators or (identity(b.degree),)))
    )


def _preserves_segment(p: Permutation, values, active) -> bool:
    A = set(active)
    return {p[x] for x in A} == A and all(values[p[x]] == values[x] for x in A)


def affected_segment_automorphism_group(
    group: StabilizerChain,
    quotient_blocks,
    values,
    active_points,
    *,
    max_quotient_elements=2000000,
    max_child_nodes=200000,
) -> AffectedSegmentAutomorphism:
    """Compute Aut_group(values restricted to an affected invariant segment).

    The current quotient action must be a certified giant.  Rather than intersect
    the whole group with a full-domain Young group, this routine enumerates the
    current quotient image (the permitted O(log n)! multiplicative branch in the
    local-certificates regime).  For each quotient element q it takes the exact
    kernel*q preimage coset and imposes string constraints only on `active_points`.
    Inactive kernel orbits are skipped; active kernel orbits are solved by rev161's
    exact orbit-factored partial SI executor and lifted back by paired Schreier
    preimages.  The nonempty quotient fibers are then reassembled into the exact
    segment-automorphism subgroup.

    `recurrence_child_bound_verified` is deliberately separate from correctness.
    It is true only when the active segment is contained in the current affected
    set and every executed kernel-orbit child fits the exact Affected Orbits Lemma
    bound already audited by `analyze_giant_block_action`.
    """
    vals = tuple(values)
    blocks = tuple(tuple(b) for b in quotient_blocks)
    active = tuple(sorted(set(int(x) for x in active_points)))
    if len(vals) != group.degree:
        raise ValueError("string/domain size mismatch")

    giant = analyze_giant_block_action(group, blocks)
    t = len(blocks)
    if giant.giant_type is None:
        return AffectedSegmentAutomorphism(
            "giant_action_required", None, active, t, 0, 0, 0.0,
            0, 0, False, (),
            "current segment group does not have an A_t/S_t quotient image",
        )

    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    e_q = identity(t)
    image_gens = tuple(
        _block_action(g, blocks, point_to_block)
        for g in (group.original_generators or (identity(group.degree),))
    )
    image = schreier_stabilizer_chain(image_gens or (e_q,))
    quotient_elements = _enumerate_group(image, max_quotient_elements)
    if quotient_elements is None:
        return AffectedSegmentAutomorphism(
            "undetermined_quotient_enumeration_limit", None, active, t,
            max_quotient_elements, 0, log2(max(1, max_quotient_elements)),
            0, ceil(giant.largest_group_orbit / t), False, (),
            "exact quotient enumeration exceeded max_quotient_elements; no segment subgroup was manufactured",
        )

    accepted = []
    common_kernel_segment = None
    all_nodes = []
    largest_child = 0
    all_child_orbits = []

    for q in quotient_elements:
        lift = block_action_preimage_coset(group, blocks, q)
        if lift.status != "exact_block_action_preimage_coset" or lift.coset is None:
            raise AssertionError("enumerated quotient element failed exact preimage lift")
        part = orbit_factored_partial_string_coset_intersection(
            lift.coset, vals, active, max_child_nodes=max_child_nodes
        )
        largest_child = max(largest_child, part.largest_active_child_domain)
        all_nodes.extend(part.child_search_nodes)
        all_child_orbits.extend(part.active_orbit_children)
        if part.status in {
            "empty_intersection",
            "empty_intersection_local_value_multiplicity",
        }:
            continue
        if part.status == "undetermined_child_intersection_limit":
            return AffectedSegmentAutomorphism(
                "undetermined_child_intersection_limit", None, active, t,
                len(quotient_elements), len(accepted), log2(max(1, len(quotient_elements))),
                largest_child, ceil(giant.largest_group_orbit / t), False,
                tuple(all_nodes),
                "an affected kernel-orbit child SI exceeded max_child_nodes",
            )
        if part.status != "exact_orbit_factored_partial_string_intersection" or part.coset is None:
            return AffectedSegmentAutomorphism(
                "undetermined_partial_intersection_status", None, active, t,
                len(quotient_elements), len(accepted), log2(max(1, len(quotient_elements))),
                largest_child, ceil(giant.largest_group_orbit / t), False,
                tuple(all_nodes),
                "partial string preimage intersection did not return an exact/empty result",
            )
        if common_kernel_segment is None:
            common_kernel_segment = part.coset.subgroup
        elif not _same_subgroup(common_kernel_segment, part.coset.subgroup):
            raise AssertionError("nonempty quotient fibers disagree on the segment-stabilizing kernel")
        accepted.append((q, part.coset.representative))

    if common_kernel_segment is None:
        raise AssertionError("identity quotient fiber must contain the identity segment automorphism")

    domain_gens = list(common_kernel_segment.original_generators)
    domain_gens.extend(rep for q, rep in accepted if q != e_q)
    segment_group = schreier_stabilizer_chain(domain_gens or [identity(group.degree)])
    if any(not group.contains(g) for g in segment_group.original_generators):
        raise AssertionError("segment automorphism subgroup escaped source group")
    if any(not _preserves_segment(g, vals, active) for g in segment_group.original_generators):
        raise AssertionError("constructed segment subgroup generator violates the active string segment")

    seg_image_gens = tuple(
        _block_action(g, blocks, point_to_block)
        for g in (segment_group.original_generators or (identity(group.degree),))
    )
    seg_image = schreier_stabilizer_chain(seg_image_gens or (e_q,))
    accepted_images = {q for q, _ in accepted}
    if seg_image.order != len(accepted_images) or any(not seg_image.contains(q) for q in accepted_images):
        raise AssertionError("reassembled segment subgroup has the wrong quotient image")

    child_bound = ceil(giant.largest_group_orbit / t)
    affected = set(giant.affected_points)
    recurrence_verified = bool(
        giant.affected_orbit_lemma_verified
        and set(active) <= affected
        and all(set(O) <= affected and len(O) <= child_bound for O in all_child_orbits)
    )
    return AffectedSegmentAutomorphism(
        "exact_affected_segment_automorphism_group",
        segment_group,
        active,
        t,
        len(quotient_elements),
        len(accepted_images),
        log2(max(1, len(quotient_elements))),
        largest_child,
        child_bound,
        recurrence_verified,
        tuple(all_nodes),
        "exact segment automorphism subgroup reassembled from quotient fibers; inactive kernel orbits were skipped and every executed active fiber was an explicit child SI call",
    )
