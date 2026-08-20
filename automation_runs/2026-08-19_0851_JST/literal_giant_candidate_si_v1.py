from __future__ import annotations

from collections import Counter
from math import factorial, log2

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


def _swap(n: int, a: int, b: int):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _cycle3(n: int, a: int, b: int, c: int):
    p = list(range(n))
    p[a], p[b], p[c] = b, c, a
    return tuple(p)


def _parity(p) -> int:
    n = len(p)
    seen = [False] * n
    cycles = 0
    for i in range(n):
        if seen[i]:
            continue
        cycles += 1
        j = i
        while not seen[j]:
            seen[j] = True
            j = p[j]
    return (n - cycles) & 1


def _color_cells(values):
    cells = {}
    for i, value in enumerate(values):
        cells.setdefault(value, []).append(i)
    return tuple(tuple(cell) for cell in cells.values())


def _symmetric_color_stabilizer(n: int, cells):
    gens = []
    for cell in cells:
        for i in range(len(cell) - 1):
            gens.append(_swap(n, cell[i], cell[i + 1]))
    return schreier_stabilizer_chain(tuple(gens) or (identity(n),))


def _alternating_color_stabilizer(n: int, cells):
    """Generate (product_C S_C) intersect A_n without enumerating A_n."""
    gens = []
    odd_capable = []
    for cell in cells:
        if len(cell) >= 3:
            a, b = cell[0], cell[1]
            for c in cell[2:]:
                gens.append(_cycle3(n, a, b, c))
        if len(cell) >= 2:
            odd_capable.append((cell[0], cell[1]))

    if len(odd_capable) >= 2:
        a, b = odd_capable[0]
        base = _swap(n, a, b)
        for c, d in odd_capable[1:]:
            gens.append(compose(base, _swap(n, c, d)))

    return schreier_stabilizer_chain(tuple(gens) or (identity(n),))


def _proof(status, coset, *, root_n, n, group_type, exact, terminal, reason):
    local_bound = 40.0 * log2(max(2, n)) + 48.0
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, n),
        operation_kind="literal_giant_color_transport",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=terminal,
        reason=reason,
    )
    return ProofCarryingCoset(
        status,
        coset,
        "literal_giant_color_transport",
        root_n,
        n,
        True,
        exact,
        True,
        local_bound,
        terminal,
        (),
        accounting,
        0,
        reason + f"; certified literal giant type={group_type}",
    )


def exact_literal_giant_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
):
    """Exact String Isomorphism for a literal natural-domain S_n or A_n action.

    If a represented degree-n subgroup has order n! it is S_n.  If n>=5 and it
    has order n!/2, its index in S_n is two and it is A_n.  In either case a
    string transporter can be built from color classes directly.  The complete
    solution set is one right coset of the target-color stabilizer (intersected
    with A_n in the alternating case), so no giant-group enumeration or local-
    certificate recursion is needed for this literal natural-action terminal.
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
    if n < 5:
        return _proof(
            "undetermined_literal_giant_degree",
            None,
            root_n=root_n,
            n=n,
            group_type="none",
            exact=False,
            terminal=False,
            reason="literal giant terminal is reserved for natural-domain degree at least five",
        )

    full = factorial(n)
    if group.order == full:
        group_type = "S_n"
    elif group.order * 2 == full:
        group_type = "A_n"
    else:
        return _proof(
            "undetermined_not_literal_giant",
            None,
            root_n=root_n,
            n=n,
            group_type="none",
            exact=False,
            terminal=False,
            reason="represented subgroup order is neither n! nor n!/2",
        )

    try:
        if Counter(source) != Counter(target):
            return _proof(
                "exact_empty_literal_giant_value_multiplicity",
                None,
                root_n=root_n,
                n=n,
                group_type=group_type,
                exact=True,
                terminal=True,
                reason="source and target color multiplicities differ, so no permutation can be a string transporter",
            )
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc

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
            raise AssertionError("multiplicity equality lost while constructing literal giant transporter")
        for a, b in zip(src, dst):
            witness[a] = b
    witness = tuple(witness)
    if sorted(witness) != list(range(n)):
        raise AssertionError("color-class pairing did not construct a permutation")
    if any(source[i] != target[witness[i]] for i in range(n)):
        raise AssertionError("constructed literal giant witness does not transport the string")

    cells = _color_cells(target)
    if group_type == "S_n":
        stabilizer = _symmetric_color_stabilizer(n, cells)
        expected_order = 1
        for cell in cells:
            expected_order *= factorial(len(cell))
        if stabilizer.order != expected_order:
            raise AssertionError("symmetric color stabilizer order mismatch")
    else:
        odd_cell = next((cell for cell in cells if len(cell) >= 2), None)
        if _parity(witness):
            if odd_cell is None:
                return _proof(
                    "exact_empty_literal_alternating_parity",
                    None,
                    root_n=root_n,
                    n=n,
                    group_type=group_type,
                    exact=True,
                    terminal=True,
                    reason="the unique color transporter is odd and the target color stabilizer has no odd element to correct its parity",
                )
            witness = compose(witness, _swap(n, odd_cell[0], odd_cell[1]))
            if _parity(witness):
                raise AssertionError("alternating parity correction failed")
            if any(source[i] != target[witness[i]] for i in range(n)):
                raise AssertionError("alternating parity correction broke string transport")

        stabilizer = _alternating_color_stabilizer(n, cells)
        product = 1
        for cell in cells:
            product *= factorial(len(cell))
        expected_order = product // 2 if odd_cell is not None else 1
        if stabilizer.order != expected_order:
            raise AssertionError("alternating color stabilizer order mismatch")

    if not group.contains(witness):
        raise AssertionError("literal giant witness is not contained in the represented group")
    if any(not group.contains(g) for g in stabilizer.original_generators):
        raise AssertionError("constructed color-stabilizer generator escaped the represented literal giant")

    result = RightCoset(stabilizer, witness)
    return _proof(
        "exact_literal_giant_string_isomorphism",
        result,
        root_n=root_n,
        n=n,
        group_type=group_type,
        exact=True,
        terminal=True,
        reason="direct color-class transport and an exact Young-subgroup parity kernel reconstruct the complete string-isomorphism coset inside the literal S_n/A_n natural action",
    )
