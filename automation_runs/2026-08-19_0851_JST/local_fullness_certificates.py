from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from permutation_group_schreier import Permutation, StabilizerChain, identity, schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset
from recursive_point_image_coset_intersection import right_coset_intersection_recursive
from giant_block_action_certificates import _block_action


@dataclass(frozen=True)
class LocalFullnessCertificate:
    status: str
    test_set: Tuple[int, ...]
    automorphism_order: int
    image_order: int
    full: Optional[bool]
    missing_alt_generator: Optional[Permutation]
    search_nodes: int
    reason: str


def _young_group(values) -> StabilizerChain:
    """Full symmetric product on equal-value position classes."""
    values = tuple(values)
    n = len(values)
    classes = {}
    for i, value in enumerate(values):
        try:
            classes.setdefault(value, []).append(i)
        except TypeError as exc:
            raise ValueError("string values must be hashable") from exc

    e = list(range(n))
    generators = []
    for cls in classes.values():
        if len(cls) < 2:
            continue
        transposition = e.copy()
        transposition[cls[0]], transposition[cls[1]] = transposition[cls[1]], transposition[cls[0]]
        generators.append(tuple(transposition))
        if len(cls) > 2:
            cycle = e.copy()
            for a, b in zip(cls, cls[1:] + cls[:1]):
                cycle[a] = b
            generators.append(tuple(cycle))
    return schreier_stabilizer_chain(generators or [tuple(e)])


def exact_string_stabilizer(group: StabilizerChain, values, *, max_nodes=200000):
    if len(tuple(values)) != group.degree:
        raise ValueError("string/domain size mismatch")
    young = _young_group(values)
    e = identity(group.degree)
    return right_coset_intersection_recursive(
        RightCoset(group, e), RightCoset(young, e), max_nodes=max_nodes
    )


def _alternating_test_generators(k: int, test_set) -> Tuple[Permutation, ...]:
    test_set = tuple(test_set)
    if len(test_set) < 3:
        return ()
    e = list(range(k))
    a, b = test_set[0], test_set[1]
    out = []
    # The cycles (a b c) for c in T\{a,b} generate A(T), extended by
    # the identity on the quotient points outside T.
    for c in test_set[2:]:
        p = e.copy()
        p[a] = b
        p[b] = c
        p[c] = a
        out.append(tuple(p))
    return tuple(out)


def local_fullness_certificate(
    group: StabilizerChain,
    blocks,
    values,
    test_set,
    *,
    max_nodes=200000,
) -> LocalFullnessCertificate:
    """Exact global fullness/non-fullness certificate for a quotient test set.

    A test set T is full exactly when the quotient image of Aut_G(values)
    contains the embedded alternating group A(T). Global string automorphisms are
    computed as G intersect the Young subgroup preserving all value classes.
    Therefore a positive result is backed by global automorphism generators, not
    local-only evidence. A negative result returns a concrete missing even
    generator of A(T). Search limits fail closed.
    """
    blocks = tuple(tuple(b) for b in blocks)
    k = len(blocks)
    T = tuple(sorted(set(int(t) for t in test_set)))
    if any(t < 0 or t >= k for t in T):
        raise ValueError("test-set point outside quotient domain")

    intersection = exact_string_stabilizer(group, values, max_nodes=max_nodes)
    if intersection.status == "undetermined_node_limit":
        return LocalFullnessCertificate(
            "undetermined_search_limit", T, 0, 0, None, None,
            intersection.search_nodes,
            "exact global string-stabilizer search exceeded max_nodes",
        )

    if intersection.status == "empty_intersection":
        raise AssertionError("identity must stabilize every string")
    aut = intersection.coset.subgroup

    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    eq = identity(k)
    domain_gens = aut.original_generators or (identity(group.degree),)
    image_gens = [_block_action(g, blocks, point_to_block) for g in domain_gens]
    image = schreier_stabilizer_chain(image_gens or [eq])

    missing = next(
        (q for q in _alternating_test_generators(k, T) if not image.contains(q)),
        None,
    )
    full = missing is None
    return LocalFullnessCertificate(
        "certified_full" if full else "certified_nonfull",
        T,
        aut.order,
        image.order,
        full,
        missing,
        intersection.search_nodes,
        "global exact string automorphism group projected to quotient; embedded A(T) generator containment checked exactly",
    )
