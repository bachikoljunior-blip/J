from __future__ import annotations

from math import log2

from block_action_preimage_coset_v1 import block_action_preimage_coset
from canonical_block_system import canonical_minimal_block_system
from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from giant_block_action_certificates import _block_action
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import r1_string_isomorphism_child
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2
from v2_imprimitive_small_image_v1 import (
    V2ProofCarryingCoset,
    _proof,
    _unresolved,
    enumerate_schreier_group_exact,
)


def imprimitive_small_image_string_isomorphism_v2_recursive(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    quotient_order_poly_power: int = 2,
    max_quotient_image_order: int = 4096,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
) -> V2ProofCarryingCoset:
    """rev171 V2: small quotient image plus recursive small-order kernel closure.

    The quotient-image layer is the exact rev169 operator.  Its only semantic
    change is inside each lifted quotient fiber: candidate U2 first attempts an
    exact small-order H*r terminal, then canonical subgroup-orbit recursion whose
    induced images use S1v2.  Thus a large kernel can still close exactly when
    its invariant orbit images are individually small, while large transitive
    kernel children remain fail-closed structural leaves.
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

    if _all_value_preserving_maps(source, target) is None:
        base = r1_string_isomorphism_child(
            group,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
        )
        return _proof(
            base.status,
            base.coset,
            base.operation_kind,
            base.root_n,
            base.domain_size,
            base.canonical,
            base.exact,
            base.local_cost_certified,
            base.local_log2_cost_bound,
            base.terminal_certified,
            base.children,
            base.accounting,
            base.permutation_candidates_checked,
            base.reason,
        )

    cert = canonical_minimal_block_system(group)
    if cert.status == "multiple_canonical_minimal_block_systems":
        return _unresolved(
            "canonical_imprimitive_family_requires_v2",
            root_n=root_n,
            degree=n,
            reason="multiple equally canonical minimum block systems require a family-aware transitive operator",
        )
    if cert.status != "unique_canonical_minimal_block_system":
        return _unresolved(
            "not_unique_canonical_imprimitive_case",
            root_n=root_n,
            degree=n,
            reason="small-image quotient enumeration requires one unique canonical nontrivial block system",
        )

    blocks = cert.selected_block_system
    q = len(blocks)
    b = len(blocks[0])
    if not (1 < q < n and 1 < b < n and q * b == n):
        raise AssertionError("invalid canonical block dimensions")

    point_to_block = {u: i for i, block in enumerate(blocks) for u in block}
    image_gens = tuple(
        _block_action(g, blocks, point_to_block)
        for g in (group.original_generators or (identity(n),))
    )
    image = schreier_stabilizer_chain(image_gens or (identity(q),))
    allowed_order = min(max_quotient_image_order, root_n ** quotient_order_poly_power)
    if image.order > allowed_order:
        return _unresolved(
            "quotient_image_order_cap",
            root_n=root_n,
            degree=n,
            quotient_order=image.order,
            reason="Schreier-certified quotient image order exceeds the configured cap; no quotient enumeration was attempted",
        )

    image_elements = enumerate_schreier_group_exact(image, max_elements=allowed_order)
    if image_elements is None or len(image_elements) != image.order:
        raise AssertionError("exact quotient image enumeration disagrees with Schreier order")

    fiber_proofs = []
    successful = []
    for quotient_perm in image_elements:
        lift = block_action_preimage_coset(group, blocks, quotient_perm)
        if lift.status != "exact_block_action_preimage_coset" or lift.coset is None:
            raise AssertionError("enumerated quotient image element failed exact preimage lift")
        fiber = candidate_coset_string_isomorphism_u2(
            lift.coset,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=candidate_group_order_poly_power,
            max_group_order=max_candidate_group_order,
        )
        fiber_proofs.append(fiber)
        if not fiber.exact:
            return _unresolved(
                "imprimitive_kernel_child_requires_v2",
                root_n=root_n,
                degree=n,
                children=tuple(fiber_proofs),
                checked=len(image_elements),
                quotient_checked=len(image_elements),
                quotient_order=image.order,
                reason="a quotient fiber still contains a large-order transitive structural child; exact parent result withheld",
            )
        if fiber.coset is not None:
            successful.append(fiber.coset)

    local_bound = log2(max(1, image.order)) + 18.0 * log2(max(2, n)) + 32.0
    if local_bound + 1e-12 < log2(max(1, len(image_elements))):
        raise AssertionError("local V2 charge does not dominate quotient image enumeration")
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="imprimitive_small_quotient",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=tuple(AccountingChild(c.accounting) for c in fiber_proofs),
        terminal_certified=False,
        reason="exact quotient-image enumeration with candidate-U2 small-order/orbit-image proof children",
    )

    checked = len(image_elements) + sum(c.permutation_candidates_checked for c in fiber_proofs)
    if not successful:
        return _proof(
            "exact_empty_imprimitive_small_image_recursive",
            None,
            "imprimitive_small_quotient",
            root_n,
            n,
            True,
            True,
            True,
            local_bound,
            False,
            tuple(fiber_proofs),
            accounting,
            checked,
            "every quotient-image fiber is exactly empty after recursive small-order kernel closure",
            quotient_image_elements_checked=len(image_elements),
            quotient_image_order=image.order,
        )

    r0 = successful[0].representative
    rebuild_gens = []
    expected_size = 0
    for fiber_coset in successful:
        expected_size += fiber_coset.subgroup.order
        rebuild_gens.extend(fiber_coset.subgroup.original_generators)
        rebuild_gens.append(compose(inverse(r0), fiber_coset.representative))
    rebuilt = schreier_stabilizer_chain(rebuild_gens or (identity(n),))
    if rebuilt.order != expected_size:
        raise AssertionError("recursive small-image fiber union is not the claimed exact coset")
    result = RightCoset(rebuilt, r0)
    for fiber_coset in successful:
        if not result.contains(fiber_coset.representative):
            raise AssertionError("reassembled recursive small-image coset lost a fiber representative")
        if any(not rebuilt.contains(g) for g in fiber_coset.subgroup.original_generators):
            raise AssertionError("reassembled recursive small-image subgroup lost a fiber subgroup")

    return _proof(
        "exact_imprimitive_small_image_recursive_coset",
        result,
        "imprimitive_small_quotient",
        root_n,
        n,
        True,
        True,
        True,
        local_bound,
        False,
        tuple(fiber_proofs),
        accounting,
        checked,
        "all quotient-image fibers were exactly lifted and closed using recursive small-order candidate/orbit terminals before cardinality-audited reassembly",
        quotient_image_elements_checked=len(image_elements),
        quotient_image_order=image.order,
    )
