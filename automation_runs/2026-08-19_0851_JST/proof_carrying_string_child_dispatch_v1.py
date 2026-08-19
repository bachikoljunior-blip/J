from __future__ import annotations

from dataclasses import dataclass
from math import ceil, lgamma, log, log2
from typing import Optional, Tuple

from canonical_block_system import CanonicalBlockSystemCertificate, canonical_minimal_block_system
from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from recursive_point_image_coset_intersection import right_coset_intersection_recursive


@dataclass(frozen=True)
class ProofCarryingStringChild:
    status: str
    coset: Optional[RightCoset]
    exact: bool
    empty: bool
    primary_domain_size: int
    child_domain_size: int
    small_terminal_threshold: int
    canonical: bool
    terminal_cost_certified: bool
    terminal_log2_work_bound: float
    accounting_node: Optional[RecurrenceAccountingNode]
    structure: CanonicalBlockSystemCertificate
    reason: str


def _terminal_log2_bound(m: int, n: int) -> float:
    """Conservative closed-form state/work charge for a small exact SI terminal.

    The recursive point-image terminal never needs to distinguish more than m!
    permutations on its child domain.  We additionally charge a polynomial
    (n+1)^4 factor for membership/Schreier bookkeeping rather than using an
    observed node cap as evidence.  This is deliberately loose but mechanical.
    """
    return lgamma(m + 1) / log(2.0) + 4.0 * log2(max(2, n + 1))


def proof_carrying_string_child_dispatch(
    candidate: RightCoset,
    source_values,
    target_values,
    *,
    primary_domain_size: int,
    polylog_power: int = 2,
    max_terminal_nodes: int = 500000,
) -> ProofCarryingStringChild:
    """Dispatch one child SI call without treating a node cap as a proof.

    A child of size m <= ceil((log2 n)^polylog_power) may use the repository's
    exact point-image intersection as a terminal, because this routine attaches a
    closed-form m! times polynomial work charge independent of the observed search
    count.  Larger children are *not* sent to that opaque terminal.  Instead the
    canonical intransitive/imprimitive/primitive structure of the child subgroup
    is returned and the caller must recursively dispatch that structural case.

    The returned RecurrenceAccountingNode is the exact terminal execution object
    when one exists.  No accounting node is fabricated for an unresolved large
    child.
    """
    src = tuple(source_values)
    dst = tuple(target_values)
    m = candidate.subgroup.degree
    n = int(primary_domain_size)
    if len(src) != m or len(dst) != m:
        raise ValueError("child string/domain size mismatch")
    if n < m or n <= 0:
        raise ValueError("primary domain must be positive and at least child size")
    if polylog_power < 1:
        raise ValueError("polylog_power must be positive")

    threshold = max(1, ceil(log2(max(2, n)) ** polylog_power))
    structure = canonical_minimal_block_system(candidate.subgroup)
    value_coset = _all_value_preserving_maps(src, dst)
    if value_coset is None:
        bound = 4.0 * log2(max(2, n + 1))
        node = RecurrenceAccountingNode(
            n=n,
            m=max(1, m),
            operation_kind="terminal_value_multiplicity",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=bound,
            children=(),
            terminal_certified=True,
            reason="value multiplicity mismatch is an exact empty terminal",
        )
        return ProofCarryingStringChild(
            "exact_empty_value_multiplicity", None, True, True, n, m,
            threshold, True, True, bound, node, structure,
            "source/target value multiplicities differ; exact emptiness needs no opaque SI search",
        )

    if m <= threshold:
        exact = right_coset_intersection_recursive(
            candidate, value_coset, max_nodes=max_terminal_nodes
        )
        if exact.status == "undetermined_node_limit":
            return ProofCarryingStringChild(
                "undetermined_small_terminal_execution", None, False, False,
                n, m, threshold, True, False, 0.0, None, structure,
                "small-domain terminal exceeded the engineering execution limit; closed-form charge does not permit inventing a result",
            )
        bound = _terminal_log2_bound(m, n)
        node = RecurrenceAccountingNode(
            n=n,
            m=max(1, m),
            operation_kind="small_exact_si_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=bound,
            children=(),
            terminal_certified=True,
            reason="exact child SI executed under a closed-form m! polynomial work charge",
        )
        if exact.status == "empty_intersection":
            return ProofCarryingStringChild(
                "exact_empty_small_terminal", None, True, True, n, m,
                threshold, True, True, bound, node, structure,
                "small child SI is exactly empty and carries a closed-form terminal work bound",
            )
        if exact.status != "exact_intersection_coset" or exact.coset is None:
            return ProofCarryingStringChild(
                "undetermined_small_terminal_status", None, False, False,
                n, m, threshold, True, False, 0.0, None, structure,
                "unexpected exact-intersection status; fail closed",
            )
        return ProofCarryingStringChild(
            "exact_coset_small_terminal", exact.coset, True, False, n, m,
            threshold, True, True, bound, node, structure,
            "small child SI returned its exact coset and the same execution object carries the mechanical terminal charge",
        )

    status_map = {
        "canonical_intransitive_orbit_partition": "requires_intransitive_recursive_dispatch",
        "unique_canonical_minimal_block_system": "requires_imprimitive_recursive_dispatch",
        "multiple_canonical_minimal_block_systems": "requires_canonical_block_family_dispatch",
        "primitive_or_trivial": "requires_primitive_recursive_dispatch",
    }
    status = status_map.get(structure.status, "requires_unknown_structural_dispatch")
    return ProofCarryingStringChild(
        status, None, False, False, n, m, threshold, True, False, 0.0,
        None, structure,
        "child exceeds the mechanically charged terminal threshold; structural recursion is required and no opaque exact result or cost certificate is manufactured",
    )
