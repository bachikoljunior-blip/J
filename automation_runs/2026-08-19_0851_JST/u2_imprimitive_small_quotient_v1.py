from __future__ import annotations

from itertools import permutations
from math import lgamma, log, log2

from block_action_preimage_coset_v1 import block_action_preimage_coset
from canonical_block_system import canonical_minimal_block_system
from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from giant_block_action_certificates import _block_action
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset, r1_string_isomorphism_child
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from u1_candidate_coset_string_iso_v1 import candidate_coset_string_isomorphism_u1


def _log2_factorial(k: int) -> float:
    return lgamma(k + 1) / log(2.0)


def _unresolved(status, *, root_n, degree, reason, children=(), checked=0):
    accounting = RecurrenceAccountingNode(
        n=root_n, m=max(1, degree), operation_kind=status,
        canonical=True, cost_certified=False, local_log2_cost_bound=0.0,
        children=tuple(AccountingChild(c.accounting) for c in children),
        terminal_certified=False, reason=reason,
    )
    return ProofCarryingCoset(
        "undetermined_" + status, None, status, root_n, degree,
        True, False, False, 0.0, False, tuple(children), accounting,
        checked + sum(c.permutation_candidates_checked for c in children), reason,
    )


def imprimitive_small_quotient_string_isomorphism_u2(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    max_explicit_quotient_degree: int = 7,
) -> ProofCarryingCoset:
    """Exact U2 imprimitive recursion when the canonical quotient is small.

    The unique canonical minimum block system defines an exact quotient action.
    Only when its degree is inside both the polylog auxiliary window and the
    explicit quotient cap do we enumerate S_q and retain exactly the quotient
    permutations in the image.  Each image element is lifted to one exact
    kernel*coset fiber by paired Schreier machinery.  That fiber is intersected
    with the two strings solely by U1 proof-carrying kernel-orbit recursion.

    Successful quotient fibers are disjoint.  Their union is reconstructed as one
    exact right coset and audited by an exact cardinality identity.  Large quotient,
    non-unique block family, or unresolved kernel child fails closed; the legacy
    node-capped exact SI routine is never called by this operator.
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
    if max_explicit_quotient_degree < 1:
        raise ValueError("max_explicit_quotient_degree must be positive")

    # Canonical global emptiness is cheaper and independent of the block path.
    if _all_value_preserving_maps(source, target) is None:
        return r1_string_isomorphism_child(
            group, source, target, root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
        )

    cert = canonical_minimal_block_system(group)
    if cert.status == "multiple_canonical_minimal_block_systems":
        return _unresolved(
            "canonical_imprimitive_family_requires_u2",
            root_n=root_n, degree=n,
            reason="multiple equally canonical minimum block systems exist; selecting one by labels would break canonicality",
        )
    if cert.status != "unique_canonical_minimal_block_system":
        return _unresolved(
            "not_unique_canonical_imprimitive_case",
            root_n=root_n, degree=n,
            reason="small-quotient imprimitive operator requires one unique canonical nontrivial block system",
        )

    blocks = cert.selected_block_system
    q = len(blocks)
    b = len(blocks[0])
    if not (1 < q < n and 1 < b < n and q * b == n):
        raise AssertionError("invalid canonical block dimensions")

    threshold = max(1.0, log2(max(2, root_n)) ** polylog_power)
    if q > threshold + 1e-12:
        return _unresolved(
            "nonpolylog_imprimitive_quotient_requires_u2",
            root_n=root_n, degree=n,
            reason="canonical quotient degree exceeds the polylog auxiliary window; quotient enumeration is forbidden",
        )
    if q > max_explicit_quotient_degree:
        return _unresolved(
            "explicit_quotient_cap",
            root_n=root_n, degree=n,
            reason="canonical quotient is mathematically small enough but exceeds the current explicit S_q implementation cap",
        )

    point_to_block = {u: i for i, block in enumerate(blocks) for u in block}
    image_gens = tuple(
        _block_action(g, blocks, point_to_block)
        for g in (group.original_generators or (identity(n),))
    )
    image = schreier_stabilizer_chain(image_gens or (identity(q),))

    quotient_universe = tuple(permutations(range(q)))
    image_elements = tuple(p for p in quotient_universe if image.contains(p))
    if len(image_elements) != image.order:
        raise AssertionError("explicit quotient image enumeration disagrees with Schreier-chain order")

    fiber_proofs = []
    successful = []
    for quotient_perm in image_elements:
        lift = block_action_preimage_coset(group, blocks, quotient_perm)
        if lift.status != "exact_block_action_preimage_coset" or lift.coset is None:
            raise AssertionError("enumerated quotient image element failed exact preimage lift")
        fiber = candidate_coset_string_isomorphism_u1(
            lift.coset, source, target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
        )
        fiber_proofs.append(fiber)
        if not fiber.exact:
            return _unresolved(
                "imprimitive_kernel_child_requires_u2",
                root_n=root_n, degree=n, children=tuple(fiber_proofs),
                checked=len(quotient_universe),
                reason="a lifted quotient fiber reached an unresolved kernel-orbit structural child; exact parent result withheld",
            )
        if fiber.coset is not None:
            successful.append(fiber.coset)

    local_bound = _log2_factorial(q) + 14.0 * log2(max(2, n)) + 28.0
    if local_bound + 1e-12 < log2(max(1, len(quotient_universe))):
        raise AssertionError("local imprimitive charge does not dominate executed S_q scan")
    accounting = RecurrenceAccountingNode(
        n=root_n, m=max(1, n), operation_kind="imprimitive_small_quotient",
        canonical=True, cost_certified=True, local_log2_cost_bound=local_bound,
        children=tuple(AccountingChild(c.accounting) for c in fiber_proofs),
        terminal_certified=False,
        reason="unique canonical block quotient; complete explicit S_q image scan; every quotient fiber is the actual U1 proof object executed",
    )

    checked = len(quotient_universe) + sum(c.permutation_candidates_checked for c in fiber_proofs)
    if not successful:
        return ProofCarryingCoset(
            "exact_empty_imprimitive_small_quotient", None,
            "imprimitive_small_quotient", root_n, n, True, True, True,
            local_bound, False, tuple(fiber_proofs), accounting, checked,
            "every exact quotient-image fiber is empty after proof-carrying kernel-orbit recursion",
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
        raise AssertionError("imprimitive quotient-fiber union is not the claimed exact coset")
    result = RightCoset(rebuilt, r0)
    for fiber_coset in successful:
        if not result.contains(fiber_coset.representative):
            raise AssertionError("reassembled imprimitive coset lost a successful fiber representative")
        if any(not rebuilt.contains(g) for g in fiber_coset.subgroup.original_generators):
            raise AssertionError("reassembled imprimitive subgroup lost a successful fiber subgroup")

    return ProofCarryingCoset(
        "exact_imprimitive_small_quotient_coset", result,
        "imprimitive_small_quotient", root_n, n, True, True, True,
        local_bound, False, tuple(fiber_proofs), accounting, checked,
        "all quotient-image fibers were exactly lifted and recursively solved over smaller kernel orbits; successful disjoint fibers were cardinality-audited into the exact parent coset",
    )
