from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from paired_action_element_image_v1 import paired_action_image_of_element
from paired_giant_action_certificates_v1 import analyze_paired_giant_action
from paired_quotient_factored_partial_string_intersection_v1 import (
    PairedQuotientFactoredPartialStringIntersection,
    paired_quotient_factored_partial_string_intersection,
)
from permutation_group_schreier import StabilizerChain, identity


@dataclass(frozen=True)
class PairedAffectedSegmentAutomorphism:
    status: str
    subgroup: Optional[StabilizerChain]
    paired_image_generators: Tuple[tuple[int, ...], ...]
    exact: bool
    recurrence_child_bound_verified: bool
    execution: Optional[PairedQuotientFactoredPartialStringIntersection]
    reason: str


def _generator_preserves_segment(g, values, active):
    A = set(active)
    return {g[x] for x in A} == A and all(values[g[x]] == values[x] for x in A)


def paired_affected_segment_automorphism_group(
    group: StabilizerChain,
    image_generators,
    values,
    active_points,
    *,
    max_quotient_leaves=2000000,
    max_child_nodes=200000,
) -> PairedAffectedSegmentAutomorphism:
    """Compute Aut_G(values|active) while retaining the structural image pairing.

    The block-specific growing-beard executor could materialize an affected segment
    subgroup but Johnson-ground W1R has only a generator-paired structural action.
    This adapter uses the paired quotient/kernel executor for the exact segment
    intersection and then evaluates the original certified homomorphism on every
    reconstructed subgroup generator.  The next beard layer therefore receives a
    fresh exact subgroup *and* its generator-by-generator structural images.

    If every current generator already preserves the active string segment, no
    recursive SI call is executed; subgroup closure proves the entire group does.
    """
    vals = tuple(values)
    active = tuple(sorted(set(int(x) for x in active_points)))
    if len(vals) != group.degree:
        raise ValueError("string/domain size mismatch")
    if any(x < 0 or x >= group.degree for x in active):
        raise ValueError("active point outside source domain")

    eg = identity(group.degree)
    domain_gens = tuple(group.original_generators) or (eg,)
    images = tuple(tuple(int(x) for x in q) for q in image_generators)
    if len(images) != len(domain_gens):
        raise ValueError("one structural image generator is required per source generator")
    giant = analyze_paired_giant_action(group, images)
    if giant.giant_type is None:
        return PairedAffectedSegmentAutomorphism(
            "giant_action_required", None, (), False, False, None,
            "affected-segment recursion requires a certified paired A_m/S_m structural image",
        )

    if all(_generator_preserves_segment(g, vals, active) for g in domain_gens):
        recurrence = bool(
            giant.affected_orbit_lemma_verified
            and set(active) <= set(giant.affected_points)
        )
        return PairedAffectedSegmentAutomorphism(
            "exact_paired_affected_segment_automorphism_group",
            group, images, True, recurrence, None,
            "every source generator preserves the active segment, so subgroup closure proves the whole group is the exact segment automorphism subgroup without recursive SI",
        )

    execution = paired_quotient_factored_partial_string_intersection(
        group, images, vals, active,
        max_quotient_leaves=max_quotient_leaves,
        max_child_nodes=max_child_nodes,
    )
    if execution.status.startswith("undetermined_") or execution.status == "giant_action_required":
        return PairedAffectedSegmentAutomorphism(
            execution.status, None, (), False, False, execution,
            "paired quotient/kernel segment recursion did not complete exactly; fail closed",
        )
    if execution.status == "empty_intersection":
        raise AssertionError("identity always preserves a string segment")
    if execution.status != "exact_paired_quotient_factored_partial_string_intersection" or execution.coset is None:
        return PairedAffectedSegmentAutomorphism(
            "undetermined_paired_segment_execution_status", None, (), False,
            False, execution, "unexpected paired segment-execution status; fail closed",
        )

    if not execution.coset.contains(eg):
        raise AssertionError("exact group/segment intersection omitted the identity")
    subgroup = execution.coset.subgroup
    if not subgroup.contains(execution.coset.representative):
        raise AssertionError("identity-containing segment right coset did not collapse to its subgroup")

    sub_domain_gens = tuple(subgroup.original_generators) or (eg,)
    sub_images = []
    for g in sub_domain_gens:
        mapped = paired_action_image_of_element(group, images, g)
        if mapped.status != "exact_paired_action_element_image" or mapped.image is None:
            raise AssertionError("reconstructed segment subgroup generator could not be mapped through the certified structural action")
        sub_images.append(mapped.image)
    # This call is both a consistency check and the certificate needed by the next
    # beard layer. A non-giant result is still exact; the caller interprets it as
    # the local non-fullness obstruction.
    analyze_paired_giant_action(subgroup, tuple(sub_images))

    for g in sub_domain_gens:
        if not _generator_preserves_segment(g, vals, active):
            raise AssertionError("reconstructed segment subgroup generator violates the active string segment")

    return PairedAffectedSegmentAutomorphism(
        "exact_paired_affected_segment_automorphism_group",
        subgroup, tuple(sub_images), True,
        execution.recurrence_child_bound_verified, execution,
        "exact affected-segment subgroup was reconstructed by paired structural-image recursion and every new subgroup generator was mapped back into the certified structural action",
    )
