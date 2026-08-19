from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Tuple

from block_action_preimage_coset_v1 import block_action_preimage_coset
from giant_block_action_certificates import analyze_giant_block_action
from permutation_group_schreier import group_orbit, identity


@dataclass(frozen=True)
class AffectedKernelRecurrencePlan:
    status: str
    primary_domain_size: int
    giant_degree: int
    affected_points: Tuple[int, ...]
    kernel_orbits: Tuple[Tuple[int, ...], ...]
    largest_child_domain: int
    certified_child_bound: int
    strict_primary_shrink: bool
    execution_cost_certified: bool
    reason: str


def affected_kernel_recurrence_plan(group, blocks) -> AffectedKernelRecurrencePlan:
    """Expose the exact shrinking subproblems behind a giant-action kernel step.

    This routine does not pretend that the current generic coset-intersection
    search already executes Babai's recurrence with the claimed asymptotic cost.
    Instead it extracts the exact quotient kernel by the paired-Schreier preimage
    primitive and partitions affected points into exact kernel orbits.  rev114's
    audited affected-orbit lemma is then converted into a mechanically checked
    child-domain bound.  The final flag remains false until the actual string-
    isomorphism intersection is implemented by these children rather than by the
    existing global resource-bounded search.
    """
    blocks = tuple(tuple(b) for b in blocks)
    giant = analyze_giant_block_action(group, blocks)
    n = group.degree
    k = len(blocks)
    if giant.giant_type is None:
        return AffectedKernelRecurrencePlan(
            "giant_action_required", n, k, (), (), n, n, False, False,
            "designated quotient action is not S_k/A_k",
        )
    if not giant.affected_orbit_lemma_verified:
        return AffectedKernelRecurrencePlan(
            "affected_kernel_bound_unverified", n, k, giant.affected_points,
            (), n, n, False, False,
            "rev114 affected-kernel orbit lemma audit failed",
        )

    preimage = block_action_preimage_coset(group, blocks, identity(k))
    if preimage.status != "exact_block_action_preimage_coset":
        raise AssertionError("identity quotient must have an exact kernel preimage")
    kernel = preimage.kernel

    remaining = set(giant.affected_points)
    orbits = []
    while remaining:
        x = min(remaining)
        orbit = tuple(sorted(set(group_orbit(kernel, x)) & set(giant.affected_points)))
        if not orbit:
            raise AssertionError("affected point has empty kernel orbit")
        orbits.append(orbit)
        remaining -= set(orbit)
    orbits = tuple(sorted(orbits, key=lambda o: (len(o), o)))

    largest = max(map(len, orbits), default=0)
    # rev114 proves each kernel orbit inside an affected G-orbit has size at
    # most |G-orbit|/k; its recorded largest G-orbit gives this uniform bound.
    bound = ceil(giant.largest_group_orbit / k) if k else n
    if largest > bound:
        raise AssertionError("measured affected kernel orbit violates rev114 bound")
    strict = bool(orbits) and largest < giant.largest_group_orbit

    return AffectedKernelRecurrencePlan(
        "certified_affected_kernel_child_partition",
        n,
        k,
        giant.affected_points,
        orbits,
        largest,
        bound,
        strict,
        False,
        "exact kernel orbits provide strictly smaller candidate recurrence domains; actual coset-intersection execution has not yet been refactored to use these children, so complexity execution remains uncertified",
    )
