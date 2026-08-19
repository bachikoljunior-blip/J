from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from canonical_cartesian_block_family_v1 import certify_canonical_cartesian_block_family
from cartesian_block_family_action_v1 import exact_cartesian_block_family_action
from coset_stabilizer_primitives import RightCoset
from paired_action_preimage_coset_v1 import paired_action_preimage_coset
from permutation_group_schreier import identity
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


@dataclass(frozen=True)
class CartesianStringIsomorphismResult:
    status: str
    exact: bool
    coset: RightCoset | None
    original_degree: int
    coordinate_degree: int
    coordinate_action_faithful: bool
    reduced_proof: object | None
    preimage_proof: object | None
    final_candidate_proof: object | None
    complexity_accounting_closed: bool
    reason: str


def _block_histogram(values, block):
    try:
        return frozenset(Counter(values[u] for u in block).items())
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc


def _cartesian_image_generators(group, family):
    n = group.degree
    t = len(family)
    q = len(family[0])
    out_gens = []
    for g in (group.original_generators or (identity(n),)):
        out = list(range(t * q))
        for factor_index, system in enumerate(family):
            lookup = {frozenset(block): j for j, block in enumerate(system)}
            for block_index, block in enumerate(system):
                image_block = frozenset(g[u] for u in block)
                if image_block not in lookup:
                    raise AssertionError("Cartesian factor is not invariant under domain generator")
                out[factor_index * q + block_index] = factor_index * q + lookup[image_block]
        out_gens.append(tuple(out))
    return tuple(out_gens)


def cartesian_string_isomorphism_v1(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    max_group_order: int = 4096,
    max_candidate_group_order: int = 256,
) -> CartesianStringIsomorphismResult:
    """Exact Cartesian SI when reduced marginals plus lifted candidate U2 close.

    The factor-block histogram string is a necessary invariant on the faithful
    coordinate action.  Its exact reduced SI coset is lifted through a generic
    paired Schreier homomorphism preimage.  Candidate U2 then intersects that
    exact preimage coset with the full original strings, so a returned exact
    result is the true original SI set, not merely a marginal match.

    Complexity accounting for the combined filter/lift/final pipeline is not yet
    folded into one recurrence proof node; exact correctness and recurrence-cost
    closure are therefore reported separately.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = group.degree
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    family_cert = certify_canonical_cartesian_block_family(group)
    action = exact_cartesian_block_family_action(group)
    if not family_cert.exact_cartesian or not action.faithful or action.image is None:
        return CartesianStringIsomorphismResult(
            "cartesian_si_unavailable",
            False,
            None,
            n,
            0,
            False,
            None,
            None,
            None,
            False,
            "no exact faithful Cartesian coordinate action is available",
        )

    family = family_cert.block_system_family
    blocks = tuple(block for system in family for block in system)
    source_colors = tuple(_block_histogram(source, block) for block in blocks)
    target_colors = tuple(_block_histogram(target, block) for block in blocks)
    reduced = s1_string_isomorphism_v2(
        action.image,
        source_colors,
        target_colors,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        max_group_order=max_group_order,
    )
    if not reduced.exact:
        return CartesianStringIsomorphismResult(
            "cartesian_reduced_si_unresolved",
            False,
            None,
            n,
            action.reduced_degree,
            True,
            reduced,
            None,
            None,
            False,
            "the coordinate-block marginal SI child remains unresolved",
        )
    if reduced.coset is None:
        return CartesianStringIsomorphismResult(
            "exact_empty_cartesian_coordinate_filter",
            True,
            None,
            n,
            action.reduced_degree,
            True,
            reduced,
            None,
            None,
            False,
            "the exact coordinate-block marginal SI set is empty, which proves the original SI set empty",
        )

    image_gens = _cartesian_image_generators(group, family)
    preimage = paired_action_preimage_coset(group, image_gens, reduced.coset)
    if preimage.status != "exact_paired_action_preimage_coset" or preimage.coset is None:
        raise AssertionError("faithful coordinate candidate coset failed exact paired preimage lifting")
    if preimage.kernel_order != 1:
        raise AssertionError("exact Cartesian coordinate action unexpectedly has nontrivial paired kernel")

    final = candidate_coset_string_isomorphism_u2(
        preimage.coset,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        max_group_order=max_candidate_group_order,
    )
    if final.exact:
        return CartesianStringIsomorphismResult(
            "exact_cartesian_string_isomorphism",
            True,
            final.coset,
            n,
            action.reduced_degree,
            True,
            reduced,
            preimage,
            final,
            False,
            "reduced marginal candidates were exactly lifted and then exactly intersected with full original strings; combined quasipolynomial accounting is the remaining proof obligation",
        )
    return CartesianStringIsomorphismResult(
        "cartesian_candidate_requires_structural_refinement",
        False,
        None,
        n,
        action.reduced_degree,
        True,
        reduced,
        preimage,
        final,
        False,
        "the exact reduced candidate coset was lifted, but its full-string intersection still contains a large-order structural child",
    )
