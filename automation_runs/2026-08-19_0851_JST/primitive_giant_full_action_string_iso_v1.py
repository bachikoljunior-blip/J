from __future__ import annotations

from collections import Counter
from math import factorial, log2, prod

from coset_stabilizer_primitives import RightCoset
from giant_block_action_certificates import _paired_kernel_generators, analyze_giant_block_action
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


def _parity(p):
    inv = 0
    for i in range(len(p)):
        for j in range(i + 1, len(p)):
            inv ^= int(p[i] > p[j])
    return inv


def _swap(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _result(status, coset, *, root_n, n, exact, certified, terminal, reason):
    local = 36.0 * log2(max(2, n)) + 72.0 if certified else 0.0
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="primitive_giant_full_action_terminal" if certified else "primitive_giant_full_action_gate",
        canonical=True,
        cost_certified=certified,
        local_log2_cost_bound=local,
        children=(),
        terminal_certified=terminal,
        reason=reason,
    )
    return ProofCarryingCoset(
        status,
        coset,
        accounting.operation_kind,
        root_n,
        n,
        True,
        exact,
        certified,
        local,
        terminal,
        (),
        accounting,
        0,
        reason,
    )


def primitive_giant_full_action_string_isomorphism_terminal(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
):
    """Exact polynomial SI terminal when the literal point action is A_n or S_n.

    The S_n case is the color-class transporter coset.  For A_n we intersect that
    transporter coset with parity exactly: if a target color class has size at
    least two, an odd within-class transposition toggles the witness parity and
    the automorphism subgroup becomes the even kernel of the color stabilizer.
    If every color class is a singleton, the transporter is a singleton and its
    parity decides exact emptiness.

    This is deliberately only a *literal full-action giant* terminal.  It does
    not replace Babai local certificates for a giant quotient with nontrivial
    kernel or for other primitive actions.
    """
    n = int(group.degree)
    source = tuple(source_values)
    target = tuple(target_values)
    if n < 1 or len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    try:
        if Counter(source) != Counter(target):
            return _result(
                "exact_empty_primitive_giant_value_multiplicity",
                None,
                root_n=root_n,
                n=n,
                exact=True,
                certified=True,
                terminal=True,
                reason="source/target color multiplicities differ, so no full-action giant permutation can map the strings",
            )
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc

    if n < 5:
        return _result(
            "undetermined_primitive_giant_degree_gate",
            None,
            root_n=root_n,
            n=n,
            exact=False,
            certified=False,
            terminal=False,
            reason="literal A_n/S_n giant recognition is intentionally certified here only for n>=5",
        )

    singleton_blocks = tuple((i,) for i in range(n))
    giant = analyze_giant_block_action(group, singleton_blocks)
    if giant.giant_type not in ("S_k", "A_k") or giant.kernel_order != 1:
        return _result(
            "undetermined_not_literal_primitive_giant",
            None,
            root_n=root_n,
            n=n,
            exact=False,
            certified=False,
            terminal=False,
            reason="the represented point action is not exactly S_n or A_n with trivial singleton-action kernel",
        )

    source_cells = {}
    target_cells = {}
    for i, value in enumerate(source):
        source_cells.setdefault(value, []).append(i)
    for i, value in enumerate(target):
        target_cells.setdefault(value, []).append(i)

    witness = list(range(n))
    for value, src in source_cells.items():
        dst = target_cells[value]
        if len(src) != len(dst):
            raise AssertionError("multiplicity gate and color cells disagree")
        for a, b in zip(src, dst):
            witness[a] = b
    witness = tuple(witness)
    if sorted(witness) != list(range(n)):
        raise AssertionError("canonical color-class pairing did not produce a permutation")
    if any(source[i] != target[witness[i]] for i in range(n)):
        raise AssertionError("constructed giant witness does not map source to target")

    target_generators = []
    for cell in target_cells.values():
        for a, b in zip(cell, cell[1:]):
            target_generators.append(_swap(n, a, b))
    full_stabilizer = schreier_stabilizer_chain(target_generators or (identity(n),))
    expected_full_order = prod(factorial(len(cell)) for cell in target_cells.values())
    if full_stabilizer.order != expected_full_order:
        raise AssertionError("color-class stabilizer order audit failed")

    if giant.giant_type == "S_k":
        subgroup = full_stabilizer
        representative = witness
        expected_order = expected_full_order
        status = "exact_literal_symmetric_string_coset"
        reason = "literal S_n action: exact string isomorphisms are the target color-class stabilizer right coset of the canonical classwise transporter"
    else:
        representative = witness
        odd_generators = tuple(g for g in full_stabilizer.original_generators if _parity(g))
        if _parity(representative):
            if not odd_generators:
                return _result(
                    "exact_empty_literal_alternating_parity",
                    None,
                    root_n=root_n,
                    n=n,
                    exact=True,
                    certified=True,
                    terminal=True,
                    reason="literal A_n action with singleton color classes has a unique classwise transporter and that transporter is odd",
                )
            representative = compose(representative, odd_generators[0])
        if _parity(representative):
            raise AssertionError("alternating witness parity correction failed")

        if full_stabilizer.original_generators:
            image_generators = tuple((1, 0) if _parity(g) else (0, 1) for g in full_stabilizer.original_generators)
            kernel_generators = _paired_kernel_generators(full_stabilizer.original_generators, image_generators)
            subgroup = schreier_stabilizer_chain(kernel_generators or (identity(n),))
        else:
            subgroup = full_stabilizer
        has_odd = bool(odd_generators)
        expected_order = expected_full_order // 2 if has_odd else expected_full_order
        status = "exact_literal_alternating_string_coset"
        reason = "literal A_n action: exact string isomorphisms are the even kernel of the target color stabilizer, with witness parity corrected inside a nontrivial color class when possible"

    if subgroup.order != expected_order:
        raise AssertionError("literal giant string stabilizer order audit failed")
    if not group.contains(representative):
        raise AssertionError("literal giant witness is outside the certified ambient group")
    if any(not group.contains(g) for g in subgroup.original_generators):
        raise AssertionError("literal giant result subgroup escaped the certified ambient group")
    if any(target[i] != target[g[i]] for g in subgroup.original_generators for i in range(n)):
        raise AssertionError("literal giant result subgroup does not stabilize the target string")

    result = RightCoset(subgroup, representative)
    if not result.contains(representative):
        raise AssertionError("literal giant result coset lost its representative")
    return _result(
        status,
        result,
        root_n=root_n,
        n=n,
        exact=True,
        certified=True,
        terminal=True,
        reason=reason,
    )
