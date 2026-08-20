from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import factorial, log2, prod

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain, validate_perm
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class PrimitiveGiantColorProof(ProofCarryingCoset):
    giant_type: str = ""
    target_color_class_sizes: tuple[int, ...] = ()
    exact_stabilizer_order: int = 0
    witness_parity: int | None = None


def permutation_parity(p):
    p = validate_perm(p)
    return sum(p[i] > p[j] for i in range(len(p)) for j in range(i + 1, len(p))) & 1


def _transposition(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _three_cycle(n, a, b, c):
    p = list(range(n))
    p[a], p[b], p[c] = b, c, a
    return tuple(p)


def _target_color_cells(values):
    cells = defaultdict(list)
    for i, value in enumerate(values):
        cells[value].append(i)
    return tuple(tuple(xs) for xs in cells.values())


def _canonical_color_witness(source, target):
    """Map each source occurrence to the corresponding target occurrence."""
    positions = defaultdict(list)
    for j, value in enumerate(target):
        positions[value].append(j)
    used = defaultdict(int)
    out = []
    for value in source:
        k = used[value]
        if k >= len(positions[value]):
            return None
        out.append(positions[value][k])
        used[value] = k + 1
    return tuple(out)


def _target_color_stabilizer(n, cells, giant_type):
    """Return (prod S_cell) intersected with the represented A_n/S_n giant."""
    e = identity(n)
    if giant_type == "S_n":
        gens = []
        for cell in cells:
            if len(cell) >= 2:
                a = cell[0]
                gens.extend(_transposition(n, a, b) for b in cell[1:])
        chain = schreier_stabilizer_chain(tuple(gens) or (e,))
        expected = prod(factorial(len(cell)) for cell in cells)
        if chain.order != expected:
            raise AssertionError("S_n color stabilizer generators have wrong certified order")
        return chain

    if giant_type != "A_n":
        raise ValueError("giant_type must be A_n or S_n")

    gens = []
    class_swaps = []
    for cell in cells:
        if len(cell) >= 3:
            a, b = cell[0], cell[1]
            gens.extend(_three_cycle(n, a, b, c) for c in cell[2:])
        if len(cell) >= 2:
            class_swaps.append(_transposition(n, cell[0], cell[1]))
    if len(class_swaps) >= 2:
        ref = class_swaps[0]
        gens.extend(compose(ref, other) for other in class_swaps[1:])

    chain = schreier_stabilizer_chain(tuple(gens) or (e,))
    product_order = prod(factorial(len(cell)) for cell in cells)
    expected = product_order // 2 if class_swaps else 1
    if chain.order != expected:
        raise AssertionError("A_n color stabilizer generators have wrong certified order")
    if any(permutation_parity(g) for g in chain.original_generators):
        raise AssertionError("A_n color stabilizer contains an odd generator")
    return chain


def _result(
    status,
    coset,
    *,
    root_n,
    degree,
    giant_type,
    cell_sizes,
    stabilizer_order,
    witness_parity,
    reason,
):
    local_bound = 18.0 * log2(max(2, degree)) + 32.0
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, degree),
        operation_kind="primitive_giant_color_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=True,
        reason=reason,
    )
    return PrimitiveGiantColorProof(
        status,
        coset,
        "primitive_giant_color_terminal",
        root_n,
        degree,
        True,
        True,
        True,
        local_bound,
        True,
        (),
        accounting,
        0,
        reason,
        giant_type=giant_type,
        target_color_class_sizes=tuple(sorted(cell_sizes, reverse=True)),
        exact_stabilizer_order=int(stabilizer_order),
        witness_parity=witness_parity,
    )


def primitive_giant_color_string_isomorphism_terminal(
    group,
    source_values,
    target_values,
    *,
    root_n=None,
):
    """Exact String Isomorphism terminal for a represented A_n or S_n action.

    A primitive group whose exact order is n!/2 or n! is literally A_n or S_n
    on this domain, not merely a quotient containing a giant.  Two strings under
    S_n are isomorphic iff their color multiplicities agree.  Under A_n the only
    additional obstruction occurs when every target color class is a singleton:
    then the unique color-compatible permutation must be even.  If any color class
    has size at least two, a color-preserving transposition toggles witness parity.

    The whole solution set is reconstructed without enumerating the giant group as
    the exact target-color stabilizer intersected with A_n/S_n, times one witness.
    This is a polynomial terminal and therefore strictly stronger at this exact
    singleton-block giant leaf than invoking the general local-certificates theorem.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if root_n is None:
        root_n = n
    root_n = int(root_n)
    if root_n < n or n < 1 or len(source) != n or len(target) != n:
        raise ValueError("invalid root/string/group degree")
    try:
        source_counts = Counter(source)
        target_counts = Counter(target)
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc

    full = factorial(n)
    if group.order == full:
        giant_type = "S_n"
    elif n >= 2 and group.order == full // 2:
        giant_type = "A_n"
    else:
        raise ValueError("terminal requires the represented group to be exactly A_n or S_n")

    cells = _target_color_cells(target)
    cell_sizes = tuple(len(cell) for cell in cells)
    stabilizer = _target_color_stabilizer(n, cells, giant_type)

    if source_counts != target_counts:
        return _result(
            "exact_empty_primitive_giant_color_multiplicity",
            None,
            root_n=root_n,
            degree=n,
            giant_type=giant_type,
            cell_sizes=cell_sizes,
            stabilizer_order=stabilizer.order,
            witness_parity=None,
            reason="source and target color multiplicities differ, so no A_n/S_n element can map the strings",
        )

    witness = _canonical_color_witness(source, target)
    if witness is None or sorted(witness) != list(range(n)):
        raise AssertionError("equal color inventories failed to construct a color-compatible permutation")
    if not all(source[i] == target[witness[i]] for i in range(n)):
        raise AssertionError("constructed giant witness does not map source colors to target colors")

    parity = permutation_parity(witness)
    if giant_type == "A_n" and parity:
        toggle = next((_transposition(n, cell[0], cell[1]) for cell in cells if len(cell) >= 2), None)
        if toggle is None:
            return _result(
                "exact_empty_primitive_alternating_unique_odd_witness",
                None,
                root_n=root_n,
                degree=n,
                giant_type=giant_type,
                cell_sizes=cell_sizes,
                stabilizer_order=stabilizer.order,
                witness_parity=1,
                reason="all color classes are singletons and the unique color-compatible permutation is odd, so A_n contains no solution",
            )
        witness = compose(witness, toggle)
        parity = permutation_parity(witness)
        if parity or not all(source[i] == target[witness[i]] for i in range(n)):
            raise AssertionError("target-color parity toggle failed to produce an even color-compatible witness")

    if not group.contains(witness):
        raise AssertionError("constructed A_n/S_n color witness is outside the represented giant")
    result = RightCoset(stabilizer, witness)
    if not result.contains(witness):
        raise AssertionError("reconstructed giant color coset lost its witness")

    return _result(
        "exact_primitive_giant_color_coset",
        result,
        root_n=root_n,
        degree=n,
        giant_type=giant_type,
        cell_sizes=cell_sizes,
        stabilizer_order=stabilizer.order,
        witness_parity=parity,
        reason="exact A_n/S_n color multiplicity/parity terminal reconstructed the full string-isomorphism set as one right coset",
    )
