from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import log2

from block_action_preimage_coset_v1 import block_action_preimage_coset
from canonical_block_system import canonical_minimal_block_system
from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from giant_block_action_certificates import _block_action
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset, r1_string_isomorphism_child
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from u1_candidate_coset_string_iso_v1 import candidate_coset_string_isomorphism_u1


@dataclass(frozen=True)
class V2ProofCarryingCoset(ProofCarryingCoset):
    """V1-compatible proof object with a quotient-enumeration witness."""

    quotient_image_elements_checked: int = 0
    quotient_image_order: int = 0


def _proof(
    status,
    coset,
    operation_kind,
    root_n,
    degree,
    canonical,
    exact,
    local_cost_certified,
    local_log2_cost_bound,
    terminal_certified,
    children,
    accounting,
    permutation_candidates_checked,
    reason,
    *,
    quotient_image_elements_checked=0,
    quotient_image_order=0,
):
    return V2ProofCarryingCoset(
        status,
        coset,
        operation_kind,
        root_n,
        degree,
        canonical,
        exact,
        local_cost_certified,
        local_log2_cost_bound,
        terminal_certified,
        tuple(children),
        accounting,
        permutation_candidates_checked,
        reason,
        quotient_image_elements_checked=quotient_image_elements_checked,
        quotient_image_order=quotient_image_order,
    )


def _unresolved(
    status,
    *,
    root_n,
    degree,
    reason,
    children=(),
    checked=0,
    quotient_checked=0,
    quotient_order=0,
):
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, degree),
        operation_kind=status,
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=tuple(AccountingChild(c.accounting) for c in children),
        terminal_certified=False,
        reason=reason,
    )
    return _proof(
        "undetermined_" + status,
        None,
        status,
        root_n,
        degree,
        True,
        False,
        False,
        0.0,
        False,
        tuple(children),
        accounting,
        checked + sum(c.permutation_candidates_checked for c in children),
        reason,
        quotient_image_elements_checked=quotient_checked,
        quotient_image_order=quotient_order,
    )


def enumerate_schreier_group_exact(chain, *, max_elements: int):
    """Enumerate exactly the represented group, guarded by its certified order.

    The stabilizer chain supplies the exact group order.  If that order is above
    the mechanical cap, no enumeration is attempted.  Otherwise a deterministic
    generator/inverse BFS is run from the identity and must discover exactly the
    certified number of elements; disagreement is treated as an implementation
    invariant failure rather than silently accepted.
    """
    if max_elements < 1:
        raise ValueError("max_elements must be positive")
    if chain.order > max_elements:
        return None

    ident = identity(chain.degree)
    generators = set(chain.original_generators)
    generators.update(inverse(g) for g in tuple(generators))
    generators.discard(ident)
    steps = tuple(sorted(generators))

    seen = {ident}
    queue = deque([ident])
    while queue:
        current = queue.popleft()
        for step in steps:
            nxt = compose(current, step)
            if nxt in seen:
                continue
            seen.add(nxt)
            if len(seen) > chain.order:
                raise AssertionError("generator BFS exceeded Schreier-certified group order")
            queue.append(nxt)

    if len(seen) != chain.order:
        raise AssertionError("generator BFS did not match Schreier-certified group order")
    return tuple(sorted(seen))


def imprimitive_small_image_string_isomorphism_v2(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    quotient_order_poly_power: int = 2,
    max_quotient_image_order: int = 4096,
) -> V2ProofCarryingCoset:
    """Exact V2 imprimitive recursion for certified small-order quotient images.

    Unlike rev167, this operator never scans S_q.  A unique canonical minimum
    block system defines the quotient action, whose Schreier chain certifies its
    exact image order.  Whenever that order is bounded both by root_n^c and by a
    mechanical implementation cap, the quotient image itself is enumerated by
    generator BFS, even when q is large.  Every image element is exactly lifted
    to a kernel*coset fiber and solved only by proof-carrying U1 kernel-orbit
    recursion.  Large-order images and unresolved kernel children fail closed.
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
    if quotient_order_poly_power < 1 or max_quotient_image_order < 1:
        raise ValueError("invalid quotient image enumeration parameters")

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

    polynomial_cap = root_n ** quotient_order_poly_power
    allowed_order = min(max_quotient_image_order, polynomial_cap)
    if image.order > allowed_order:
        return _unresolved(
            "quotient_image_order_cap",
            root_n=root_n,
            degree=n,
            quotient_order=image.order,
            reason=(
                "Schreier-certified quotient image order exceeds the configured polynomial/implementation cap; "
                "no quotient element enumeration was attempted"
            ),
        )

    image_elements = enumerate_schreier_group_exact(image, max_elements=allowed_order)
    if image_elements is None:
        raise AssertionError("order gate admitted quotient image but exact enumeration refused it")
    if len(image_elements) != image.order:
        raise AssertionError("exact quotient image enumeration disagrees with Schreier order")

    fiber_proofs = []
    successful = []
    for quotient_perm in image_elements:
        lift = block_action_preimage_coset(group, blocks, quotient_perm)
        if lift.status != "exact_block_action_preimage_coset" or lift.coset is None:
            raise AssertionError("enumerated quotient image element failed exact preimage lift")
        fiber = candidate_coset_string_isomorphism_u1(
            lift.coset,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
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
                reason="a lifted quotient fiber reached an unresolved kernel-orbit structural child; exact parent result withheld",
            )
        if fiber.coset is not None:
            successful.append(fiber.coset)

    # Executed quotient work is |image|, not q!.  The polynomial envelope covers
    # Schreier/BFS, exact preimage lifting, and proof-object bookkeeping.
    local_bound = log2(max(1, image.order)) + 18.0 * log2(max(2, n)) + 32.0
    if local_bound + 1e-12 < log2(max(1, len(image_elements))):
        raise AssertionError("local V2 charge does not dominate executed quotient image enumeration")
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="imprimitive_small_quotient",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=tuple(AccountingChild(c.accounting) for c in fiber_proofs),
        terminal_certified=False,
        reason=(
            "unique canonical block quotient; exact Schreier-certified quotient-image BFS; "
            "every enumerated image fiber is the actual U1 proof object executed"
        ),
    )

    checked = len(image_elements) + sum(c.permutation_candidates_checked for c in fiber_proofs)
    if not successful:
        return _proof(
            "exact_empty_imprimitive_small_image",
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
            "every exact quotient-image fiber is empty after proof-carrying kernel-orbit recursion",
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
        raise AssertionError("small-image quotient fiber union is not the claimed exact coset")
    result = RightCoset(rebuilt, r0)
    for fiber_coset in successful:
        if not result.contains(fiber_coset.representative):
            raise AssertionError("reassembled small-image coset lost a successful fiber representative")
        if any(not rebuilt.contains(g) for g in fiber_coset.subgroup.original_generators):
            raise AssertionError("reassembled small-image subgroup lost a successful fiber subgroup")

    return _proof(
        "exact_imprimitive_small_image_coset",
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
        "all certified quotient-image fibers were exactly lifted, recursively solved over smaller kernel orbits, and cardinality-audited into the exact parent coset",
        quotient_image_elements_checked=len(image_elements),
        quotient_image_order=image.order,
    )
