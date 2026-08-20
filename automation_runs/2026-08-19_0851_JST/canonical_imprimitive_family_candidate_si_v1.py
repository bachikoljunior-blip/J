from __future__ import annotations

from math import log2

from block_action_preimage_coset_v1 import block_action_preimage_coset
from coset_stabilizer_primitives import RightCoset
from giant_block_action_certificates import _block_action
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from v2_imprimitive_small_image_v1 import enumerate_schreier_group_exact


def _unresolved(status, *, root_n, degree, reason, children=(), checked=0):
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, degree),
        operation_kind="unresolved_candidate_coset",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=tuple(AccountingChild(c.accounting) for c in children),
        terminal_certified=False,
        reason=reason,
    )
    return ProofCarryingCoset(
        status,
        None,
        "unresolved_candidate_coset",
        root_n,
        degree,
        True,
        False,
        False,
        0.0,
        False,
        tuple(children),
        accounting,
        checked,
        reason,
    )


def _same_right_coset(a, b):
    if a is None or b is None:
        return a is None and b is None
    if a.subgroup.degree != b.subgroup.degree or a.subgroup.order != b.subgroup.order:
        return False
    if any(not b.subgroup.contains(g) for g in a.subgroup.original_generators):
        return False
    if any(not a.subgroup.contains(g) for g in b.subgroup.original_generators):
        return False
    return a.contains(b.representative) and b.contains(a.representative)


def _normalize_system(system, n):
    blocks = tuple(tuple(sorted(int(x) for x in block)) for block in system)
    blocks = tuple(sorted(blocks))
    if len(blocks) < 2 or any(len(block) < 2 for block in blocks):
        raise ValueError("family block system must be nontrivial")
    flat = tuple(sorted(x for block in blocks for x in block))
    if flat != tuple(range(n)):
        raise ValueError("family block system must partition the full domain")
    b = len(blocks[0])
    if any(len(block) != b for block in blocks):
        raise ValueError("transitive invariant block systems must have equal block size")
    return blocks


def solve_canonical_imprimitive_family_string_isomorphism(
    group,
    source_values,
    target_values,
    block_system_family,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    quotient_order_poly_power: int = 2,
    max_quotient_image_order: int = 4096,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_depth: int = 64,
    family_poly_power: int = 2,
    max_family_systems: int = 4096,
    max_johnson_test_sets: int = 200000,
    max_partition_states: int = 4096,
    max_recognition_nodes: int = 500000,
    max_johnson_nodes: int = 500000,
    candidate_dispatch=None,
):
    """Exact SI over every equally canonical minimum block system.

    A multiple-minimum block-system certificate is a canonical *family*, but
    selecting one member by point labels would not be canonical.  This operator
    therefore executes the same exact quotient/preimage String-Isomorphism
    decomposition for every member of that family, requires every decomposition
    to close exactly, and checks that all independently reconstructed answers are
    the same right coset.  The family and every quotient image are polynomially
    gated before enumeration; otherwise the routine fails closed.

    The exact quotient fibers are exposed directly as children of one
    `imprimitive_small_quotient` accounting node.  This preserves the existing
    quotient/kernel progress invariant while charging the extra canonical family
    multiplicity explicitly.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")
    if family_poly_power < 1 or max_family_systems < 1:
        raise ValueError("invalid family gate")

    systems = tuple(_normalize_system(system, n) for system in block_system_family)
    systems = tuple(sorted(set(systems)))
    if len(systems) < 2:
        return _unresolved(
            "undetermined_imprimitive_family_not_multiple",
            root_n=root_n,
            degree=n,
            reason="family-aware operator requires at least two distinct equally canonical minimum block systems",
        )

    allowed_family = min(max_family_systems, root_n ** family_poly_power)
    if len(systems) > allowed_family:
        return _unresolved(
            "undetermined_imprimitive_family_count_gate",
            root_n=root_n,
            degree=n,
            reason="canonical minimum-block-system family exceeds the polynomial family-enumeration gate",
        )

    if candidate_dispatch is None:
        from u2_candidate_coset_string_iso_v5 import candidate_coset_string_isomorphism_u5
        candidate_dispatch = candidate_coset_string_isomorphism_u5

    all_fibers = []
    system_results = []
    quotient_elements_checked = 0
    max_seen_quotient_order = 0

    for blocks in systems:
        q = len(blocks)
        b = len(blocks[0])
        if not (1 < q < n and 1 < b < n and q * b == n):
            raise AssertionError("invalid canonical family block dimensions")

        point_to_block = {u: i for i, block in enumerate(blocks) for u in block}
        raw_gens = tuple(group.original_generators) or (identity(n),)
        image_gens = tuple(_block_action(g, blocks, point_to_block) for g in raw_gens)
        image = schreier_stabilizer_chain(image_gens or (identity(q),))
        max_seen_quotient_order = max(max_seen_quotient_order, int(image.order))
        allowed_order = min(max_quotient_image_order, root_n ** quotient_order_poly_power)
        if image.order > allowed_order:
            return _unresolved(
                "undetermined_imprimitive_family_quotient_order_gate",
                root_n=root_n,
                degree=n,
                reason="an equally canonical block-system quotient image exceeds the configured polynomial enumeration gate",
                children=tuple(all_fibers),
                checked=quotient_elements_checked,
            )

        image_elements = enumerate_schreier_group_exact(image, max_elements=allowed_order)
        if image_elements is None or len(image_elements) != image.order:
            raise AssertionError("exact family quotient enumeration disagrees with Schreier order")
        quotient_elements_checked += len(image_elements)

        successful = []
        for quotient_perm in image_elements:
            lift = block_action_preimage_coset(group, blocks, quotient_perm)
            if lift.status != "exact_block_action_preimage_coset" or lift.coset is None:
                raise AssertionError("enumerated family quotient element failed exact preimage lift")
            fiber = candidate_dispatch(
                lift.coset,
                source,
                target,
                root_n=root_n,
                polylog_power=polylog_power,
                max_explicit_degree=max_explicit_degree,
                group_order_poly_power=candidate_group_order_poly_power,
                max_group_order=max_candidate_group_order,
                max_depth=max_depth,
                max_johnson_test_sets=max_johnson_test_sets,
                max_partition_states=max_partition_states,
                max_recognition_nodes=max_recognition_nodes,
                max_johnson_nodes=max_johnson_nodes,
                family_poly_power=family_poly_power,
                max_family_systems=max_family_systems,
            )
            all_fibers.append(fiber)
            if not fiber.exact:
                return _unresolved(
                    "undetermined_imprimitive_family_fiber",
                    root_n=root_n,
                    degree=n,
                    reason="an exact quotient fiber of an equally canonical block system remains unresolved; family consensus is withheld",
                    children=tuple(all_fibers),
                    checked=quotient_elements_checked,
                )
            if fiber.coset is not None:
                successful.append(fiber.coset)

        if not successful:
            system_results.append(None)
            continue

        r0 = successful[0].representative
        rebuild_gens = []
        expected_size = 0
        for fiber_coset in successful:
            expected_size += fiber_coset.subgroup.order
            rebuild_gens.extend(fiber_coset.subgroup.original_generators)
            rebuild_gens.append(compose(inverse(r0), fiber_coset.representative))
        rebuilt = schreier_stabilizer_chain(rebuild_gens or (identity(n),))
        if rebuilt.order != expected_size:
            raise AssertionError("family quotient-fiber union is not the claimed exact coset")
        result = RightCoset(rebuilt, r0)
        for fiber_coset in successful:
            if not result.contains(fiber_coset.representative):
                raise AssertionError("family reassembly lost a quotient-fiber representative")
            if any(not rebuilt.contains(g) for g in fiber_coset.subgroup.original_generators):
                raise AssertionError("family reassembly lost a quotient-fiber subgroup")
        system_results.append(result)

    reference = system_results[0]
    if any(not _same_right_coset(reference, other) for other in system_results[1:]):
        return _unresolved(
            "undetermined_imprimitive_family_consensus_mismatch",
            root_n=root_n,
            degree=n,
            reason="independently exact canonical block-system decompositions disagreed; fail closed rather than selecting a label-dependent answer",
            children=tuple(all_fibers),
            checked=quotient_elements_checked,
        )

    work_units = max(1, len(systems) + quotient_elements_checked + sum(c.permutation_candidates_checked for c in all_fibers))
    local_bound = log2(work_units) + 24.0 * log2(max(2, n)) + 12.0 * log2(max(2, root_n)) + 48.0
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="imprimitive_small_quotient",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=tuple(AccountingChild(c.accounting) for c in all_fibers),
        terminal_certified=False,
        reason=(
            "all equally canonical minimum block systems were processed; each polynomially bounded quotient image was exactly enumerated, "
            "every lifted fiber closed exactly, and all reconstructed full SI cosets agreed"
        ),
    )
    status = (
        "exact_empty_canonical_imprimitive_family_si"
        if reference is None
        else "exact_canonical_imprimitive_family_si"
    )
    return ProofCarryingCoset(
        status,
        reference,
        "imprimitive_small_quotient",
        root_n,
        n,
        True,
        True,
        True,
        local_bound,
        False,
        tuple(all_fibers),
        accounting,
        quotient_elements_checked + sum(c.permutation_candidates_checked for c in all_fibers),
        (
            f"processed {len(systems)} equally canonical minimum block systems (maximum quotient order {max_seen_quotient_order}) "
            "without choosing a label-dependent member; exact quotient/preimage decompositions reached one consensus SI coset"
        ),
    )


__all__ = ["solve_canonical_imprimitive_family_string_isomorphism"]
