from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from coset_stabilizer_primitives import RightCoset, point_stabilizer_generators
from orbit_factored_partial_string_coset_intersection_v1 import (
    orbit_factored_partial_string_coset_intersection,
)
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from paired_giant_action_certificates_v1 import analyze_paired_giant_action
from permutation_group_schreier import (
    StabilizerChain,
    compose,
    identity,
    inverse,
    orbit_transversal,
    schreier_stabilizer_chain,
    validate_perm,
)


@dataclass(frozen=True)
class PairedQuotientFactoredPartialStringIntersection:
    status: str
    coset: Optional[RightCoset]
    image_degree: int
    image_order: int
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


def _conjugate_chain(chain: StabilizerChain, t):
    e = identity(chain.degree)
    gens = chain.original_generators or (e,)
    return schreier_stabilizer_chain(
        tuple(compose(compose(inverse(t), k), t) for k in gens) or (e,)
    )


def paired_quotient_factored_partial_string_intersection(
    group: StabilizerChain,
    image_generators,
    values,
    active_points,
    *,
    max_quotient_leaves=2000000,
    max_child_nodes=200000,
) -> PairedQuotientFactoredPartialStringIntersection:
    """Intersect an affected string segment through an arbitrary paired giant image.

    This is the action-generic analogue of rev161's block-quotient executor.  The
    structural image is decomposed recursively by point images.  At a singleton
    image leaf, ``paired_action_coset_preimage`` reconstructs the complete
    full-domain kernel coset for that image element; only then is the string
    segment solved on active kernel orbits.  Successful leaves are reassembled by
    exact coset cardinality, so no hidden full-domain SI call sits between the
    structural image recursion and the affected kernel children.
    """
    vals = tuple(values)
    if len(vals) != group.degree:
        raise ValueError("string/domain size mismatch")
    if max_quotient_leaves <= 0 or max_child_nodes <= 0:
        raise ValueError("search limits must be positive")
    active = tuple(sorted(set(int(x) for x in active_points)))
    if any(x < 0 or x >= group.degree for x in active):
        raise ValueError("active point outside source domain")

    eg = identity(group.degree)
    domain_gens = tuple(group.original_generators) or (eg,)
    images = tuple(validate_perm(q) for q in image_generators)
    if len(images) != len(domain_gens):
        raise ValueError("one image generator is required per source generator")
    if not images:
        raise ValueError("image generator list cannot be empty")
    t = len(images[0])
    if any(len(q) != t for q in images):
        raise ValueError("image generator degree mismatch")

    giant = analyze_paired_giant_action(group, images)
    if giant.giant_type is None:
        return PairedQuotientFactoredPartialStringIntersection(
            "giant_action_required", None, t, giant.image_order,
            0, 0, 0, 0, 0, False, (),
            "current generator-paired structural image is not A_t or S_t",
        )

    eq = identity(t)
    image = schreier_stabilizer_chain(images or (eq,))
    trivial_image = schreier_stabilizer_chain((eq,))
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
        gens = A.original_generators or (eq,)
        base = next(
            (i for i in range(t) if any(g[i] != i for g in gens)), None
        )
        if base is None:
            quotient_leaves += 1
            if quotient_leaves > max_quotient_leaves:
                raise _LeafLimit
            singleton = RightCoset(trivial_image, qcoset.representative)
            lift = paired_action_coset_preimage(group, images, singleton)
            if lift.status != "exact_paired_action_coset_preimage" or lift.coset is None:
                raise AssertionError("singleton structural-image branch failed exact paired lift")
            part = orbit_factored_partial_string_coset_intersection(
                lift.coset, vals, active, max_child_nodes=max_child_nodes
            )
            kernel_leaf_children += len(part.active_orbit_children)
            largest_kernel_child = max(
                largest_kernel_child, part.largest_active_child_domain
            )
            all_search_nodes.extend(part.child_search_nodes)
            all_leaf_orbits.extend(part.active_orbit_children)
            if part.status in {
                "empty_intersection",
                "empty_intersection_local_value_multiplicity",
                "active_domain_not_coset_invariant",
                "active_domain_not_subgroup_invariant",
            }:
                return None
            if part.status == "undetermined_child_intersection_limit":
                raise RuntimeError("child_limit")
            if part.status != "exact_orbit_factored_partial_string_intersection" or part.coset is None:
                raise RuntimeError("partial_status")
            return part.coset

        orbit, trans = orbit_transversal(base, gens, t)
        stab_gens = point_stabilizer_generators(gens, base) or (eq,)
        stab = schreier_stabilizer_chain(stab_gens)
        children = []
        for y in orbit:
            ty = trans[y]
            child_subgroup = _conjugate_chain(stab, ty)
            child_rep = compose(qcoset.representative, ty)
            child = solve(RightCoset(child_subgroup, child_rep))
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
        rebuilt = schreier_stabilizer_chain(rebuild_gens or (eg,))
        if rebuilt.order != expected_size:
            raise AssertionError(
                "structural-image branch reassembly cardinality mismatch"
            )
        result = RightCoset(rebuilt, r0)
        for child in children:
            if not result.contains(child.representative):
                raise AssertionError("reassembled coset lost a child representative")
            if any(not rebuilt.contains(g) for g in child.subgroup.original_generators):
                raise AssertionError("reassembled subgroup lost a child subgroup")
        return result

    try:
        result = solve(RightCoset(image, eq))
    except _LeafLimit:
        return PairedQuotientFactoredPartialStringIntersection(
            "undetermined_quotient_leaf_limit", None, t, image.order,
            quotient_nodes, quotient_leaves, kernel_leaf_children,
            largest_kernel_child, 0, False, tuple(all_search_nodes),
            "structural-image point recursion exceeded max_quotient_leaves",
        )
    except RuntimeError as exc:
        return PairedQuotientFactoredPartialStringIntersection(
            "undetermined_child_intersection_limit" if str(exc) == "child_limit"
            else "undetermined_partial_intersection_status",
            None, t, image.order, quotient_nodes, quotient_leaves,
            kernel_leaf_children, largest_kernel_child, 0, False,
            tuple(all_search_nodes),
            "a smaller active kernel child did not return an exact/empty result",
        )

    child_bound = (giant.largest_group_orbit + t - 1) // t
    affected = set(giant.affected_points)
    recurrence_verified = bool(
        giant.affected_orbit_lemma_verified
        and set(active) <= affected
        and all(set(O) <= affected and len(O) <= child_bound for O in all_leaf_orbits)
    )
    if result is None:
        return PairedQuotientFactoredPartialStringIntersection(
            "empty_intersection", None, t, image.order, quotient_nodes,
            quotient_leaves, kernel_leaf_children, largest_kernel_child,
            child_bound, recurrence_verified, tuple(all_search_nodes),
            "every structural-image branch was eliminated by exact active kernel-orbit constraints",
        )
    return PairedQuotientFactoredPartialStringIntersection(
        "exact_paired_quotient_factored_partial_string_intersection",
        result, t, image.order, quotient_nodes, quotient_leaves,
        kernel_leaf_children, largest_kernel_child, child_bound,
        recurrence_verified, tuple(all_search_nodes),
        "paired structural-image recursion, exact singleton preimages, active kernel child SI and coset reassembly all completed",
    )
