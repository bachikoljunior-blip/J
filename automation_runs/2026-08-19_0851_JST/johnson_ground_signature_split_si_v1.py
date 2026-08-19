from __future__ import annotations

from collections import Counter
from math import log2

from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


def _hist(values):
    try:
        return frozenset(Counter(values).items())
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc


def _signed_ground_signatures(v, k, standard_subsets, values):
    signatures = []
    for a in range(v):
        inside = [values[i] for i, subset in enumerate(standard_subsets) if a in subset]
        outside = [values[i] for i, subset in enumerate(standard_subsets) if a not in subset]
        signatures.append(frozenset((_hist(inside), _hist(outside))))
    return tuple(signatures)


def _cells_by_reference_order(source_signatures, target_signatures):
    order = []
    seen = set()
    for sig in source_signatures:
        if sig not in seen:
            seen.add(sig)
            order.append(sig)
    if set(target_signatures) != seen:
        return None
    src = tuple(tuple(i for i, sig in enumerate(source_signatures) if sig == key) for key in order)
    dst = tuple(tuple(i for i, sig in enumerate(target_signatures) if sig == key) for key in order)
    if tuple(map(len, src)) != tuple(map(len, dst)):
        return None
    return src, dst


def _signed_subset_profile(subset, cells, v, k):
    counts = tuple(sum(1 for x in subset if x in cell) for cell in cells)
    if v == 2 * k:
        complement_counts = tuple(len(cell) - count for cell, count in zip(cells, counts))
        return frozenset((counts, complement_counts))
    return counts


def _subset_profile_cells(v, k, standard_subsets, source_ground_cells, target_ground_cells, coordinate):
    source_profiles = tuple(
        _signed_subset_profile(subset, source_ground_cells, v, k)
        for subset in standard_subsets
    )
    target_profiles = tuple(
        _signed_subset_profile(subset, target_ground_cells, v, k)
        for subset in standard_subsets
    )
    ordered = _cells_by_reference_order(source_profiles, target_profiles)
    if ordered is None:
        return None
    source_std_cells, target_std_cells = ordered
    current_by_std = [None] * len(coordinate)
    for current, std in enumerate(coordinate):
        current_by_std[std] = current
    source_current = tuple(
        tuple(sorted(current_by_std[std] for std in cell)) for cell in source_std_cells
    )
    target_current = tuple(
        tuple(sorted(current_by_std[std] for std in cell)) for cell in target_std_cells
    )
    return source_current, target_current


def _charge_child(child: ProofCarryingCoset, *, orbit_states: int, m: int, v: int, recognition_nodes: int):
    if not child.exact or not child.local_cost_certified:
        return child
    execution_units = max(1, int(orbit_states) + int(recognition_nodes) + m * max(1, v))
    extra = log2(execution_units) + 18.0 * log2(max(2, m)) + 12.0 * log2(max(2, v)) + 28.0
    old = child.accounting
    accounting = RecurrenceAccountingNode(
        n=old.n,
        m=old.m,
        operation_kind=old.operation_kind,
        canonical=old.canonical,
        cost_certified=old.cost_certified,
        local_log2_cost_bound=old.local_log2_cost_bound + extra,
        children=old.children,
        terminal_certified=old.terminal_certified,
        reason=old.reason + "; rev176 signed-ground incidence split charge added",
    )
    return ProofCarryingCoset(
        "exact_johnson_ground_signature_split_" + child.status,
        child.coset,
        child.operation_kind,
        child.root_n,
        child.domain_size,
        child.canonical,
        child.exact,
        child.local_cost_certified,
        child.local_log2_cost_bound + extra,
        child.terminal_certified,
        child.children,
        accounting,
        child.permutation_candidates_checked,
        "certified signed-ground incidence signatures induced a nontrivial current-domain partition; exact candidate recursion returned the final SI result",
    )


def johnson_ground_signature_split_string_isomorphism(*args, **kwargs):
    """Compatibility entrypoint; corrected recursive interface lives in v2."""
    kwargs.pop("max_explicit_ground_degree", None)
    from johnson_ground_signature_split_si_v2 import johnson_ground_signature_split_string_isomorphism_v2
    return johnson_ground_signature_split_string_isomorphism_v2(*args, **kwargs)
