from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from block_action_preimage_coset_v1 import block_action_preimage_coset
from coset_stabilizer_primitives import RightCoset, point_stabilizer_generators
from giant_block_action_certificates import _block_action, analyze_giant_block_action
from orbit_factored_partial_string_coset_intersection_v1 import (
    orbit_factored_partial_string_coset_intersection,
)
from permutation_group_schreier import (
    StabilizerChain,
    compose,
    identity,
    inverse,
    orbit_transversal,
    schreier_stabilizer_chain,
)


@dataclass(frozen=True)
class QuotientFactoredPartialStringIntersection:
    status: str
    coset: Optional[RightCoset]
    quotient_degree: int
    quotient_order: int
    quotient_nodes: int
    quotient_leaves: int
    kernel_leaf_children: int
    largest_kernel_child_domain: int
    certified_kernel_child_bound: int
    recurrence_child_bound_verified: bool
    child_search_nodes: Tuple[int, ...]
    reason: str


class _LeafLimit(Exception):
    pass


def quotient_factored_partial_string_intersection(
    group: StabilizerChain,
    quotient_blocks,
    values,
    active_points,
    *,
    max_quotient_leaves=2000000,
    max_child_nodes=200000,
) -> QuotientFactoredPartialStringIntersection:
    """Intersect a giant-action group with an affected string segment by double recursion.

    The quotient image is recursively decomposed by point-image stabilizer cosets.
    Only when a quotient branch becomes a singleton do we lift that single image
    to the full domain; its subgroup is then exactly the quotient kernel.  The
    string segment is imposed only at that kernel leaf, where rev161's partial
    orbit executor sends the actual affected kernel orbits to exact child SI.

    Successful quotient branches are reassembled into one exact right coset.  The
    reassembly is checked by cardinality: the resulting subgroup order must equal
    the sum of the disjoint branch-coset sizes.  Thus the execution tree itself is
    explicit and no full-domain generic coset intersection is hidden between the
    quotient recursion and affected kernel children.

    This routine still uses the repository's exact child SI terminal on each
    smaller kernel orbit.  It exposes those calls and their sizes so a higher
    proof-carrying dispatcher can replace non-polylogarithmic terminals rather than
    counting an opaque node cap as a complexity certificate.
    """
    vals = tuple(values)
    blocks = tuple(tuple(b) for b in quotient_blocks)
    active = tuple(sorted(set(int(x) for x in active_points)))
    if len(vals) != group.degree:
        raise ValueError("string/domain size mismatch")
    if max_quotient_leaves <= 0:
        raise ValueError("max_quotient_leaves must be positive")

    giant = analyze_giant_block_action(group, blocks)
    t = len(blocks)
    if giant.giant_type is None:
        return QuotientFactoredPartialStringIntersection(
            "giant_action_required", None, t, 0, 0, 0, 0, 0, 0, False, (),
            "current group does not expose an A_t/S_t quotient on the supplied blocks",
        )

    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    eq = identity(t)
    image_gens = tuple(
        _block_action(g, blocks, point_to_block)
        for g in (group.original_generators or (identity(group.degree),))
    )
    image = schreier_stabilizer_chain(image_gens or (eq,))

    quotient_nodes = 0
    quotient_leaves = 0
    kernel_leaf_children = 0
    largest_kernel_child = 0
    all_search_nodes = []
    all_leaf_orbits = []

    def solve(qcoset: RightCoset):
        nonlocal quotient_nodes, quotient_leaves, kernel_leaf_children
        nonlocal largest_kernel_child
        quotient_nodes += 1
        A = qcoset.subgroup
        gens = A.original_generators or (identity(t),)
        base = next(
            (i for i in range(t) if any(g[i] != i for g in gens)),
            None,
        )
        if base is None:
            quotient_leaves += 1
            if quotient_leaves > max_quotient_leaves:
                raise _LeafLimit
            q = qcoset.representative
            lift = block_action_preimage_coset(group, blocks, q)
            if lift.status != "exact_block_action_preimage_coset" or lift.coset is None:
                raise AssertionError("singleton quotient branch failed paired-Schreier lift")
            part = orbit_factored_partial_string_coset_intersection(
                lift.coset, vals, active, max_child_nodes=max_child_nodes
            )
            kernel_leaf_children += len(part.active_orbit_children)
            largest_kernel_child = max(largest_kernel_child, part.largest_active_child_domain)
            all_search_nodes.extend(part.child_search_nodes)
            all_leaf_orbits.extend(part.active_orbit_children)
            if part.status in {
                "empty_intersection",
                "empty_intersection_local_value_multiplicity",
            }:
                return None
            if part.status == "undetermined_child_intersection_limit":
                raise RuntimeError("child_limit")
            if part.status != "exact_orbit_factored_partial_string_intersection" or part.coset is None:
                raise RuntimeError("partial_status")
            return part.coset

        orbit, trans = orbit_transversal(base, gens, t)
        stab_gens = point_stabilizer_generators(gens, base) or (identity(t),)
        stab = schreier_stabilizer_chain(stab_gens)
        children = []
        for y in orbit:
            child_rep = compose(qcoset.representative, trans[y])
            child = solve(RightCoset(stab, child_rep))
            if child is not None:
                children.append(child)
        if not children:
            return None

        r0 = children[0].representative
        rebuild_gens = []
        expected_size = 0
        for child in children:
            expected_size += child.subgroup.order
            rebuild_gens.extend(child.subgroup.original_generators)
            rebuild_gens.append(compose(inverse(r0), child.representative))
        rebuilt = schreier_stabilizer_chain(
            rebuild_gens or (identity(group.degree),)
        )
        if rebuilt.order != expected_size:
            raise AssertionError(
                "quotient branch reassembly cardinality mismatch: union is not the claimed exact coset"
            )
        result = RightCoset(rebuilt, r0)
        for child in children:
            if not result.contains(child.representative):
                raise AssertionError("reassembled coset lost a successful branch representative")
            if any(not rebuilt.contains(g) for g in child.subgroup.original_generators):
                raise AssertionError("reassembled subgroup lost a successful branch subgroup")
        return result

    try:
        result = solve(RightCoset(image, eq))
    except _LeafLimit:
        return QuotientFactoredPartialStringIntersection(
            "undetermined_quotient_leaf_limit", None, t, image.order,
            quotient_nodes, quotient_leaves, kernel_leaf_children,
            largest_kernel_child, 0, False, tuple(all_search_nodes),
            "quotient point-image recursion exceeded max_quotient_leaves",
        )
    except RuntimeError as exc:
        status = str(exc)
        return QuotientFactoredPartialStringIntersection(
            "undetermined_child_intersection_limit" if status == "child_limit"
            else "undetermined_partial_intersection_status",
            None, t, image.order, quotient_nodes, quotient_leaves,
            kernel_leaf_children, largest_kernel_child, 0, False,
            tuple(all_search_nodes),
            "a smaller kernel child did not return an exact/empty result",
        )

    child_bound = (giant.largest_group_orbit + t - 1) // t
    affected = set(giant.affected_points)
    recurrence_verified = bool(
        giant.affected_orbit_lemma_verified
        and set(active) <= affected
        and all(set(O) <= affected and len(O) <= child_bound for O in all_leaf_orbits)
    )
    if result is None:
        return QuotientFactoredPartialStringIntersection(
            "empty_intersection", None, t, image.order, quotient_nodes,
            quotient_leaves, kernel_leaf_children, largest_kernel_child,
            child_bound, recurrence_verified, tuple(all_search_nodes),
            "every quotient point-image branch was eliminated by an exact affected kernel-orbit child",
        )
    return QuotientFactoredPartialStringIntersection(
        "exact_quotient_factored_partial_string_intersection",
        result, t, image.order, quotient_nodes, quotient_leaves,
        kernel_leaf_children, largest_kernel_child, child_bound,
        recurrence_verified, tuple(all_search_nodes),
        "quotient point-image recursion, singleton paired-Schreier lifts, affected kernel child SI, and exact coset reassembly all completed",
    )
