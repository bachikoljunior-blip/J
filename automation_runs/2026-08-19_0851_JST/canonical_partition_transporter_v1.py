from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple

from giant_block_action_certificates import _block_action
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
)

Partition = Tuple[Tuple[int, ...], ...]


@dataclass(frozen=True)
class CanonicalPartitionTransport:
    status: str
    quotient_degree: int
    orbit_states: int
    source: Partition
    target: Partition
    transporter: Optional[Permutation]
    source_stabilizer: Optional[StabilizerChain]
    reason: str


def _normalize_partition(cells, m: int) -> Partition:
    out = tuple(tuple(sorted(set(int(x) for x in cell))) for cell in cells)
    if any(not cell for cell in out):
        raise ValueError("partition cells must be nonempty")
    flat = [x for cell in out for x in cell]
    if sorted(flat) != list(range(m)) or len(flat) != len(set(flat)):
        raise ValueError("ordered cells must partition the quotient domain exactly")
    return out


def _act_partition(partition: Partition, quotient_perm: Permutation) -> Partition:
    return tuple(tuple(sorted(quotient_perm[x] for x in cell)) for cell in partition)


def canonical_partition_transporter(
    group: StabilizerChain,
    blocks,
    source_cells,
    target_cells=None,
    *,
    max_states=200000,
) -> CanonicalPartitionTransport:
    """Exact, bounded transporter for an ordered canonical quotient partition.

    The cells are *colored/ordered* cells: an allowed map must send source cell i
    to target cell i.  Search is performed on quotient-partition states but the
    recorded transporters and Schreier generators are permutations of the full
    original domain.  Thus the returned stabilizer is the preimage in `group` of
    the quotient subgroup preserving every canonical cell setwise.

    This routine is deliberately exact and may be exponential; exceeding the
    state budget is an undetermined fail-closed result.  Complexity certification
    is a separate recurrence obligation.
    """
    blocks = tuple(tuple(b) for b in blocks)
    m = len(blocks)
    if m < 1:
        raise ValueError("at least one quotient block is required")
    source = _normalize_partition(source_cells, m)
    target = source if target_cells is None else _normalize_partition(target_cells, m)
    if tuple(map(len, source)) != tuple(map(len, target)):
        return CanonicalPartitionTransport(
            "partition_shape_mismatch", m, 0, source, target, None, None,
            "ordered canonical cells have different sizes",
        )

    point_to_block = {u: i for i, block in enumerate(blocks) for u in block}
    domain_gens = group.original_generators or (identity(group.degree),)
    quotient_gens = tuple(_block_action(g, blocks, point_to_block) for g in domain_gens)

    ident = identity(group.degree)
    trans = {source: ident}
    queue = deque([source])
    found = source == target

    while queue:
        state = queue.popleft()
        tx = trans[state]
        for g, qg in zip(domain_gens, quotient_gens):
            nxt = _act_partition(state, qg)
            if nxt not in trans:
                if len(trans) >= max_states:
                    return CanonicalPartitionTransport(
                        "undetermined_partition_orbit_limit", m, len(trans),
                        source, target, None, None,
                        "partition orbit exploration exceeded max_states",
                    )
                trans[nxt] = compose(tx, g)
                queue.append(nxt)
                if nxt == target:
                    found = True

    # Schreier generators for the stabilizer of the full ordered source state.
    stabilizer_gens = []
    for state, tx in trans.items():
        for g, qg in zip(domain_gens, quotient_gens):
            nxt = _act_partition(state, qg)
            ty = trans[nxt]
            h = compose(compose(tx, g), inverse(ty))
            if h != ident:
                stabilizer_gens.append(h)
    stabilizer = schreier_stabilizer_chain(stabilizer_gens or [ident])

    if not found:
        return CanonicalPartitionTransport(
            "no_partition_transporter", m, len(trans), source, target,
            None, stabilizer,
            "target canonical partition is outside the ambient quotient orbit",
        )

    return CanonicalPartitionTransport(
        "partition_transporter_coset", m, len(trans), source, target,
        trans[target], stabilizer,
        "returned transporter maps each ordered source cell to the corresponding target cell; source_stabilizer is its exact ambient preimage stabilizer",
    )
