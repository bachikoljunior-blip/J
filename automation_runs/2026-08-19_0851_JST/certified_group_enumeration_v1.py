from __future__ import annotations

from collections import deque

from permutation_group_schreier import compose, identity, inverse


def enumerate_schreier_group_exact(chain, *, max_elements: int):
    """Enumerate exactly the represented finite group under a hard order cap.

    The stabilizer chain supplies the exact group order. If that order exceeds
    max_elements, no enumeration is attempted. Otherwise deterministic BFS over
    the supplied generators and their inverses must discover exactly chain.order
    elements. Any disagreement is treated as an implementation invariant failure.
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
