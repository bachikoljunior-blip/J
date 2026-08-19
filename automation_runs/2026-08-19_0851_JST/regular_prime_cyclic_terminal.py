from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Iterable, Optional, Tuple

from permutation_group_schreier import StabilizerChain, identity, orbit_transversal
from bounded_group_transport import enumerate_group


@dataclass(frozen=True)
class RegularPrimeCyclicTerminal:
    status: str
    degree: int
    subset_size: int
    coordinate_systems_checked: int
    canonical_code: Optional[bytes]
    reason: str


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def _pack_bits(bits) -> bytes:
    out = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        if bit:
            out[i // 8] |= 1 << (7 - (i % 8))
    return bytes(out)


def canonicalize_regular_prime_subset_relation(
    group: StabilizerChain,
    relation: Iterable[Tuple[Iterable[int], bool]],
    *,
    max_group_elements: int = 200000,
    max_coordinate_systems: int = 200000,
    max_relation_entries: int = 200000,
) -> RegularPrimeCyclicTerminal:
    """Exact relabeling-invariant terminal for a prime-degree regular cyclic action.

    A regular cyclic group of prime degree p gives an affine coordinate system
    after choosing (1) an origin point b and (2) any non-identity group element
    g as the +1 step.  Every other such choice is x -> a*x+c with a!=0.
    Enumerating all p(p-1) choices therefore removes both arbitrary origin and
    generator/orientation choices without naming a point or a presented generator.

    `relation` must contain exactly one Boolean entry for every t-subset of the
    degree-p domain, for one fixed t.  Each affine coordinate system encodes the
    relation in lexicographic coordinate-subset order; the minimum packed code is
    invariant under arbitrary relabeling/conjugation of the whole action.

    This routine is deliberately fail-closed outside the exact regular-prime
    case or when explicit resource bounds are exceeded.
    """
    n = group.degree
    if not _is_prime(n) or group.order != n:
        return RegularPrimeCyclicTerminal(
            "not_regular_prime_cyclic", n, 0, 0, None,
            "degree/order do not certify a prime-order regular cyclic action",
        )

    gens = group.original_generators or (identity(n),)
    orbit, _ = orbit_transversal(0, gens, n)
    if len(orbit) != n:
        return RegularPrimeCyclicTerminal(
            "not_regular_prime_cyclic", n, 0, 0, None,
            "prime-order action is not transitive and therefore not regular",
        )

    elements = enumerate_group(group, max_elements=max_group_elements)
    if elements is None:
        return RegularPrimeCyclicTerminal(
            "undetermined_group_element_limit", n, 0, 0, None,
            "group enumeration bound is below the certified prime group order",
        )
    e = identity(n)
    steps = tuple(g for g in elements if g != e)
    if len(steps) != n - 1:
        raise AssertionError("prime regular group has unexpected element count")

    raw = []
    subset_sizes = set()
    for subset, flag in relation:
        T = tuple(sorted(int(x) for x in subset))
        if len(set(T)) != len(T) or any(x < 0 or x >= n for x in T):
            raise ValueError("invalid relation subset")
        subset_sizes.add(len(T))
        raw.append((T, bool(flag)))
    if len(subset_sizes) != 1:
        raise ValueError("relation must use one fixed subset size")
    t = next(iter(subset_sizes))
    expected = comb(n, t)
    if expected > max_relation_entries:
        return RegularPrimeCyclicTerminal(
            "undetermined_relation_entry_limit", n, t, 0, None,
            "complete subset relation exceeds max_relation_entries",
        )
    rel = dict(raw)
    if len(raw) != expected or len(rel) != expected:
        raise ValueError("relation must contain every t-subset exactly once")

    coordinate_systems = n * (n - 1)
    if coordinate_systems > max_coordinate_systems:
        return RegularPrimeCyclicTerminal(
            "undetermined_coordinate_system_limit", n, t, 0, None,
            "p(p-1) affine coordinate systems exceed max_coordinate_systems",
        )

    coordinate_subsets = tuple(combinations(range(n), t))
    best = None
    checked = 0
    for step in steps:
        for base in range(n):
            order = [base]
            for _ in range(1, n):
                order.append(step[order[-1]])
            if len(set(order)) != n:
                raise AssertionError("nonidentity element of prime regular group is not a full cycle")

            bits = []
            for C in coordinate_subsets:
                original_subset = tuple(sorted(order[i] for i in C))
                bits.append(rel[original_subset])
            code = b"RPC1" + n.to_bytes(4, "big") + t.to_bytes(2, "big") + _pack_bits(bits)
            if best is None or code < best:
                best = code
            checked += 1

    return RegularPrimeCyclicTerminal(
        "exact_regular_prime_cyclic_subset_terminal", n, t, checked, best,
        "minimum over every origin and every nonidentity cyclic step removes affine coordinate choice exactly",
    )
