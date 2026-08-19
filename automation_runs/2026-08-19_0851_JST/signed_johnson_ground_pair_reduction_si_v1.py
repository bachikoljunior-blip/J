from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import ceil, log2

from babai_recurrence_contract_v1 import (
    RecurrenceCertificate,
    RecurrenceChild,
    RecurrenceValidation,
    validate_babai_recurrence_step,
)
from certified_group_enumeration_v1 import enumerate_schreier_group_exact
from coherent_pair_refinement import CoherentPairRefinement, coherent_refine_pair_relation
from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import _standard_subsets, lift_primitive_johnson_to_ground_relation
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from signed_johnson_ground_profile_partition_si_v1 import (
    _color_token,
    _signed_partition_transporter,
)


@dataclass(frozen=True)
class SignedGroundPairReductionProof(ProofCarryingCoset):
    ground_size: int = 0
    subset_size: int = 0
    source_pair_rank: int = 0
    target_pair_rank: int = 0
    source_ground_cells: tuple[tuple[int, ...], ...] = ()
    target_ground_cells: tuple[tuple[int, ...], ...] = ()
    largest_ground_cell: int = 0
    significant_ground_split: bool = False
    partition_orbit_states: int = 0
    candidate_stabilizer_order: int = 0
    candidate_elements_checked: int = 0
    recurrence_certificate: RecurrenceCertificate | None = None
    recurrence_validation: RecurrenceValidation | None = None
    complement_in_image: bool = False


def _histogram(tokens):
    return tuple(sorted(Counter(tokens).items()))


def _signed_pair_weights(v, k, values, *, complement_in_image):
    """Canonical unordered-pair colors induced by the actual colored k-relation.

    For a ground pair {a,b}, the ordinary signature is the color histogram of
    k-subsets containing both points.  If the faithful signed Johnson image has
    the exceptional complement bit (necessarily v=2k), complement swaps
    `contains both` with `contains neither`; the unordered pair of those two
    histograms is therefore invariant under either parity.
    """
    tokens = tuple(_color_token(x) for x in values)
    subsets = _standard_subsets(v, k)
    if len(tokens) != len(subsets):
        raise AssertionError("colored Johnson relation length mismatch")

    signatures = []
    for a, b in combinations(range(v), 2):
        containing = _histogram(
            tokens[i]
            for i, subset in enumerate(subsets)
            if a in subset and b in subset
        )
        if complement_in_image:
            if v != 2 * k:
                raise AssertionError("signed complement image is impossible away from v=2k")
            excluding = _histogram(
                tokens[i]
                for i, subset in enumerate(subsets)
                if a not in subset and b not in subset
            )
            signature = ("signed-pair",) + tuple(sorted((containing, excluding)))
        else:
            signature = ("pair", containing)
        signatures.append(((a, b), signature))

    labels = {
        signature: i
        for i, signature in enumerate(sorted({s for _, s in signatures}))
    }
    return tuple((pair, labels[signature]) for pair, signature in signatures)


def _shape(refinement: CoherentPairRefinement):
    return tuple(len(cell) for cell in refinement.color_classes)


def _maps_string(source, target, permutation):
    return all(source[i] == target[permutation[i]] for i in range(len(source)))


def _enumerate_candidate_coset_exact(
    candidate: RightCoset,
    source,
    target,
    *,
    root_n,
    max_group_order,
    group_order_poly_power,
):
    H = candidate.subgroup
    allowed = min(max_group_order, root_n ** group_order_poly_power)
    if H.order > allowed:
        return None, 0, allowed

    elements = enumerate_schreier_group_exact(H, max_elements=allowed)
    if elements is None or len(elements) != H.order:
        raise AssertionError("candidate stabilizer passed the exact-order gate but enumeration disagreed")

    candidates = tuple(compose(candidate.representative, h) for h in elements)
    if any(not candidate.contains(p) for p in candidates):
        raise AssertionError("candidate stabilizer enumeration left the exact partition coset")
    matches = tuple(p for p in candidates if _maps_string(source, target, p))
    checked = len(candidates)

    if not matches:
        return RightCoset(schreier_stabilizer_chain([identity(H.degree)]), identity(H.degree)), -checked, allowed

    witness = min(matches)
    translated = tuple(compose(inverse(witness), p) for p in matches)
    subgroup = schreier_stabilizer_chain(translated or (identity(H.degree),))
    result = RightCoset(subgroup, witness)
    if subgroup.order != len(matches):
        raise AssertionError("pair-split exact matches did not reconstruct the expected subgroup order")
    if any(not result.contains(p) for p in matches):
        raise AssertionError("reconstructed pair-split SI coset lost an exact match")

    reconstructed = tuple(p for p in candidates if result.contains(p))
    checked += len(candidates)
    if reconstructed != matches:
        raise AssertionError("reconstructed pair-split SI coset differs from the exact candidate scan")
    return result, checked, allowed


def _proof(
    status,
    coset,
    *,
    root_n,
    current_degree,
    exact,
    cost_certified,
    local_bound,
    terminal,
    accounting,
    reason,
    ground_size,
    subset_size,
    source_refinement=None,
    target_refinement=None,
    source_cells=(),
    target_cells=(),
    significant=False,
    orbit_states=0,
    stabilizer_order=0,
    candidate_checked=0,
    recurrence_certificate=None,
    recurrence_validation=None,
    complement_in_image=False,
):
    return SignedGroundPairReductionProof(
        status,
        coset,
        "signed_johnson_ground_pair_reduction",
        root_n,
        current_degree,
        True,
        exact,
        cost_certified,
        local_bound,
        terminal,
        (),
        accounting,
        abs(candidate_checked),
        reason,
        ground_size=ground_size,
        subset_size=subset_size,
        source_pair_rank=0 if source_refinement is None else source_refinement.rank,
        target_pair_rank=0 if target_refinement is None else target_refinement.rank,
        source_ground_cells=tuple(source_cells),
        target_ground_cells=tuple(target_cells),
        largest_ground_cell=max((len(c) for c in source_cells), default=0),
        significant_ground_split=significant,
        partition_orbit_states=orbit_states,
        candidate_stabilizer_order=stabilizer_order,
        candidate_elements_checked=abs(candidate_checked),
        recurrence_certificate=recurrence_certificate,
        recurrence_validation=recurrence_validation,
        complement_in_image=complement_in_image,
    )


def signed_johnson_ground_pair_reduction_si(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    max_class_fraction: float = 0.9,
    partition_state_poly_power: int = 2,
    max_partition_states: int = 4096,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 4096,
    max_recognition_nodes: int = 500000,
):
    """W1R pair-certificate path on the exact signed Johnson ground relation.

    This is the next structural layer after rev177 point profiles.  It constructs
    a complement-safe colored relation on *ground pairs* from the full colored
    k-subset relation, applies stable coherent/2-WL refinement, and accepts a
    split only when the induced point partition is canonical and significant.

    The split is connected to the existing Babai recurrence contract and to an
    exact original-domain partition transporter.  If the resulting partition
    stabilizer has polynomially/hard-cap small certified order, only that smaller
    candidate stabilizer is enumerated and the full original colored relation is
    checked exactly.  If it is still large, the exact candidate partition coset
    and verified shrinking recurrence are returned as a non-exact filter for the
    next recursive child.  No represented signed-group enumeration is performed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = m
    if root_n < m:
        raise ValueError("root_n must dominate the current Johnson domain")
    if not (0.0 < max_class_fraction < 1.0):
        raise ValueError("max_class_fraction must be in (0,1)")
    if partition_state_poly_power < 1 or candidate_group_order_poly_power < 1:
        raise ValueError("invalid polynomial caps")
    if max_partition_states < 1 or max_candidate_group_order < 1:
        raise ValueError("invalid hard caps")

    lift = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=max_recognition_nodes,
    )
    v = int(lift.ground_size)
    k = int(lift.subset_size)
    if lift.status != "exact_johnson_ground_relational_lift" or not lift.strict_auxiliary_progress:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=max(1, min(root_n, v or m)),
            operation_kind="signed_ground_pair_unresolved", canonical=True,
            cost_certified=False, local_log2_cost_bound=0.0, children=(),
            terminal_certified=False, reason="Johnson ground lift was not certified",
        )
        return _proof(
            "undetermined_signed_ground_pair_lift", None,
            root_n=root_n, current_degree=m, exact=False, cost_certified=False,
            local_bound=0.0, terminal=False, accounting=accounting,
            reason=lift.reason, ground_size=v, subset_size=k,
        )

    complement_in_image = any(bool(g.complement) for g in lift.lifted_generators)
    source_weights = _signed_pair_weights(
        v, k, lift.source_on_standard_subsets,
        complement_in_image=complement_in_image,
    )
    target_weights = _signed_pair_weights(
        v, k, lift.target_on_standard_subsets,
        complement_in_image=complement_in_image,
    )
    source_ref = coherent_refine_pair_relation(
        v, source_weights, max_class_fraction=max_class_fraction
    )
    target_ref = coherent_refine_pair_relation(
        v, target_weights, max_class_fraction=max_class_fraction
    )

    if source_ref.status == "undetermined_round_limit" or target_ref.status == "undetermined_round_limit":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_ground_pair_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="coherent pair refinement exceeded its certified round bound",
        )
        return _proof(
            "undetermined_signed_ground_pair_refinement", None,
            root_n=root_n, current_degree=m, exact=False, cost_certified=False,
            local_bound=0.0, terminal=False, accounting=accounting,
            reason=accounting.reason, ground_size=v, subset_size=k,
            source_refinement=source_ref, target_refinement=target_ref,
            complement_in_image=complement_in_image,
        )

    source_shape = _shape(source_ref)
    target_shape = _shape(target_ref)
    if source_shape != target_shape:
        local_bound = 36.0 * log2(max(2, root_n)) + 36.0
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v,
            operation_kind="signed_ground_pair_invariant_terminal",
            canonical=True, cost_certified=True,
            local_log2_cost_bound=local_bound, children=(),
            terminal_certified=True,
            reason="stable complement-safe coherent pair fibers have different canonical shapes",
        )
        return _proof(
            "exact_empty_signed_ground_pair_invariant", None,
            root_n=root_n, current_degree=m, exact=True, cost_certified=True,
            local_bound=local_bound, terminal=True, accounting=accounting,
            reason="any signed Johnson isomorphism must preserve the stable coherent pair-fiber shape",
            ground_size=v, subset_size=k,
            source_refinement=source_ref, target_refinement=target_ref,
            source_cells=source_ref.color_classes, target_cells=target_ref.color_classes,
            complement_in_image=complement_in_image,
        )

    significant = source_ref.significant_split and target_ref.significant_split
    if not significant:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_ground_pair_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="actual colored relation produced a stable complement-safe ground-pair relation but no significant point split",
        )
        return _proof(
            "undetermined_signed_ground_pair_no_split", None,
            root_n=root_n, current_degree=m, exact=False, cost_certified=False,
            local_bound=0.0, terminal=False, accounting=accounting,
            reason="W1R must proceed to higher-arity/local-certificate structure",
            ground_size=v, subset_size=k,
            source_refinement=source_ref, target_refinement=target_ref,
            source_cells=source_ref.color_classes, target_cells=target_ref.color_classes,
            complement_in_image=complement_in_image,
        )

    source_cells = source_ref.color_classes
    target_cells = target_ref.color_classes
    cell_sizes = tuple(len(cell) for cell in source_cells)
    largest = max(cell_sizes)
    if largest > max_class_fraction * v + 1e-12:
        raise AssertionError("coherent refinement reported a non-significant split as significant")

    certificate = RecurrenceCertificate(
        parent_domain_size=v,
        children=tuple(
            RecurrenceChild(
                domain_size=size,
                multiplicity=1,
                canonical_partition_cells=tuple(sorted(cell_sizes)),
            )
            for size in cell_sizes
        ),
        progress_kind="signed_ground_coherent_pair_partition",
        local_certificate_count=len(source_weights),
        canonical=True,
        complexity_charge=ceil(log2(max(2, len(source_weights) + 1))),
        reason="actual colored k-subset relation induced a complement-safe ground-pair relation whose stable coherent diagonal fibers split the ground",
    )
    validation = validate_babai_recurrence_step(
        certificate,
        max_branch_factor=v,
        min_shrink_fraction=max(0.01, 1.0 - max_class_fraction),
    )
    if not validation.progress_verified:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_ground_pair_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False,
            reason="the claimed coherent pair split failed the independent recurrence obligations",
        )
        return _proof(
            "signed_ground_pair_split_failed_recurrence_contract", None,
            root_n=root_n, current_degree=m, exact=False, cost_certified=False,
            local_bound=0.0, terminal=False, accounting=accounting,
            reason=accounting.reason, ground_size=v, subset_size=k,
            source_refinement=source_ref, target_refinement=target_ref,
            source_cells=source_cells, target_cells=target_cells,
            significant=True, recurrence_certificate=certificate,
            recurrence_validation=validation,
            complement_in_image=complement_in_image,
        )

    allowed_states = min(max_partition_states, root_n ** partition_state_poly_power)
    transport = _signed_partition_transporter(
        group,
        lift.lifted_generators,
        source_cells,
        target_cells,
        max_states=allowed_states,
    )
    if transport.status == "undetermined_signed_ground_partition_orbit_limit":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_ground_pair_split_filter",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False, reason=transport.reason,
        )
        return _proof(
            transport.status, None,
            root_n=root_n, current_degree=m, exact=False, cost_certified=False,
            local_bound=0.0, terminal=False, accounting=accounting,
            reason=transport.reason, ground_size=v, subset_size=k,
            source_refinement=source_ref, target_refinement=target_ref,
            source_cells=source_cells, target_cells=target_cells,
            significant=True, orbit_states=transport.orbit_states,
            recurrence_certificate=certificate, recurrence_validation=validation,
            complement_in_image=complement_in_image,
        )

    execution_units = (
        max(1, len(source_weights) * v)
        + max(1, transport.action_steps * (v + 1))
    )
    local_bound = log2(max(1, execution_units)) + 44.0 * log2(max(2, root_n)) + 48.0

    if transport.status == "no_signed_ground_partition_transporter":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_ground_pair_partition_terminal",
            canonical=True, cost_certified=True,
            local_log2_cost_bound=local_bound, children=(), terminal_certified=True,
            reason="complete bounded partition orbit contains no target coherent pair partition",
        )
        return _proof(
            "exact_empty_signed_ground_pair_partition_orbit", None,
            root_n=root_n, current_degree=m, exact=True, cost_certified=True,
            local_bound=local_bound, terminal=True, accounting=accounting,
            reason=transport.reason, ground_size=v, subset_size=k,
            source_refinement=source_ref, target_refinement=target_ref,
            source_cells=source_cells, target_cells=target_cells,
            significant=True, orbit_states=transport.orbit_states,
            recurrence_certificate=certificate, recurrence_validation=validation,
            complement_in_image=complement_in_image,
        )
    if transport.status != "signed_ground_partition_transporter_coset":
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v, operation_kind="signed_ground_pair_unresolved",
            canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
            children=(), terminal_certified=False, reason=transport.reason,
        )
        return _proof(
            "undetermined_signed_ground_pair_transport", None,
            root_n=root_n, current_degree=m, exact=False, cost_certified=False,
            local_bound=0.0, terminal=False, accounting=accounting,
            reason=transport.reason, ground_size=v, subset_size=k,
            source_refinement=source_ref, target_refinement=target_ref,
            source_cells=source_cells, target_cells=target_cells,
            significant=True, orbit_states=transport.orbit_states,
            recurrence_certificate=certificate, recurrence_validation=validation,
            complement_in_image=complement_in_image,
        )

    candidate = RightCoset(transport.stabilizer, transport.transporter)
    exact_result, candidate_checked, allowed_order = _enumerate_candidate_coset_exact(
        candidate,
        source,
        target,
        root_n=root_n,
        max_group_order=max_candidate_group_order,
        group_order_poly_power=candidate_group_order_poly_power,
    )
    if exact_result is None:
        accounting = RecurrenceAccountingNode(
            n=root_n, m=v,
            operation_kind="signed_ground_pair_split_filter",
            canonical=True, cost_certified=True,
            local_log2_cost_bound=local_bound, children=(), terminal_certified=False,
            reason="canonical pair split and exact original-domain partition candidate coset are available; candidate stabilizer remains above the polynomial exact-enumeration cap",
        )
        return _proof(
            "verified_signed_ground_pair_split_filter", candidate,
            root_n=root_n, current_degree=m, exact=False, cost_certified=True,
            local_bound=local_bound, terminal=False, accounting=accounting,
            reason="the next W1R child must recursively solve the exact candidate coset rather than enumerate it",
            ground_size=v, subset_size=k,
            source_refinement=source_ref, target_refinement=target_ref,
            source_cells=source_cells, target_cells=target_cells,
            significant=True, orbit_states=transport.orbit_states,
            stabilizer_order=transport.stabilizer.order,
            recurrence_certificate=certificate, recurrence_validation=validation,
            complement_in_image=complement_in_image,
        )

    if candidate_checked < 0:
        checked = -candidate_checked
        terminal_status = "exact_empty_signed_ground_pair_split_candidate"
        result_coset = None
        terminal_reason = "complete enumeration of the polynomially bounded exact partition candidate coset found no full colored-relation isomorphism"
    else:
        checked = candidate_checked
        terminal_status = "exact_signed_ground_pair_split_coset"
        result_coset = exact_result
        terminal_reason = "the polynomially bounded exact partition candidate coset was completely scanned and reconstructed as the full original-domain SI right coset"

    scan_bound = log2(max(1, transport.stabilizer.order)) + 16.0 * log2(max(2, m)) + 28.0
    local_bound = max(local_bound, scan_bound)
    accounting = RecurrenceAccountingNode(
        n=root_n, m=v,
        operation_kind="signed_ground_pair_split_small_stabilizer_terminal",
        canonical=True, cost_certified=True,
        local_log2_cost_bound=local_bound, children=(), terminal_certified=True,
        reason=terminal_reason,
    )
    return _proof(
        terminal_status, result_coset,
        root_n=root_n, current_degree=m, exact=True, cost_certified=True,
        local_bound=local_bound, terminal=True, accounting=accounting,
        reason=terminal_reason, ground_size=v, subset_size=k,
        source_refinement=source_ref, target_refinement=target_ref,
        source_cells=source_cells, target_cells=target_cells,
        significant=True, orbit_states=transport.orbit_states,
        stabilizer_order=transport.stabilizer.order,
        candidate_checked=checked,
        recurrence_certificate=certificate, recurrence_validation=validation,
        complement_in_image=complement_in_image,
    )
