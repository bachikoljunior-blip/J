from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple

from block_action_preimage_coset_v1 import _paired_chain
from coset_stabilizer_primitives import RightCoset
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
    validate_perm,
)

Partition = Tuple[Tuple[int, ...], ...]


@dataclass(frozen=True)
class PairedPartitionTransport:
    status: str
    image_degree: int
    orbit_states: int
    source: Partition
    target: Partition
    image_coset: Optional[RightCoset]
    lifted_coset: Optional[RightCoset]
    reason: str


def _normalize_partition(cells, m: int) -> Partition:
    out = tuple(tuple(sorted(set(int(x) for x in cell))) for cell in cells)
    if any(not cell for cell in out):
        raise ValueError("partition cells must be nonempty")
    flat = [x for cell in out for x in cell]
    if sorted(flat) != list(range(m)) or len(flat) != len(set(flat)):
        raise ValueError("ordered cells must partition the structural image exactly")
    return out


def _act_partition(partition: Partition, q: Permutation) -> Partition:
    return tuple(tuple(sorted(q[x] for x in cell)) for cell in partition)


def paired_partition_transporter(
    group: StabilizerChain,
    image_generators,
    source_cells,
    target_cells=None,
    *,
    max_states=200000,
) -> PairedPartitionTransport:
    """Exact ordered partition transporter through a generator-paired action.

    The partition orbit and source stabilizer are computed solely in the smaller
    structural image.  If the target state is reachable, the resulting complete
    image right coset is lifted with the certified paired homomorphism, yielding
    the complete original-domain candidate coset preserving the ordered canonical
    point colors.  This connects rev184's significant certificate-incidence split
    to the existing candidate recursion without enumerating the represented
    Johnson ambient group.
    """
    if max_states < 1:
        raise ValueError("max_states must be positive")
    eg = identity(group.degree)
    domain_gens = tuple(group.original_generators) or (eg,)
    images = tuple(validate_perm(q) for q in image_generators)
    if len(images) != len(domain_gens):
        raise ValueError("one image generator is required per source generator")
    if not images:
        raise ValueError("image generator list cannot be empty")
    m = len(images[0])
    if any(len(q) != m for q in images):
        raise ValueError("image generator degree mismatch")
    eq = identity(m)
    image = schreier_stabilizer_chain(images or (eq,))
    _levels, kernel_gens = _paired_chain(domain_gens, images)
    kernel = schreier_stabilizer_chain(kernel_gens or (eg,))
    if kernel.order * image.order != group.order:
        raise ValueError("generator pairing does not certify a source-group homomorphism")

    source = _normalize_partition(source_cells, m)
    target = source if target_cells is None else _normalize_partition(target_cells, m)
    if tuple(map(len, source)) != tuple(map(len, target)):
        return PairedPartitionTransport(
            "partition_shape_mismatch", m, 0, source, target, None, None,
            "ordered canonical structural-image cells have different sizes",
        )

    trans = {source: eq}
    queue = deque([source])
    while queue:
        state = queue.popleft()
        tx = trans[state]
        for q in images:
            nxt = _act_partition(state, q)
            if nxt not in trans:
                if len(trans) >= max_states:
                    return PairedPartitionTransport(
                        "undetermined_partition_orbit_limit", m, len(trans),
                        source, target, None, None,
                        "structural-image partition orbit exceeded max_states",
                    )
                trans[nxt] = compose(tx, q)
                queue.append(nxt)

    stabilizer_gens = []
    for state, tx in trans.items():
        for q in images:
            nxt = _act_partition(state, q)
            ty = trans[nxt]
            h = compose(compose(tx, q), inverse(ty))
            if h != eq:
                stabilizer_gens.append(h)
    stabilizer = schreier_stabilizer_chain(stabilizer_gens or (eq,))

    if target not in trans:
        return PairedPartitionTransport(
            "no_partition_transporter", m, len(trans), source, target,
            None, None,
            "target ordered canonical partition is outside the structural-image orbit",
        )

    image_coset = RightCoset(stabilizer, trans[target])
    lifted = paired_action_coset_preimage(group, images, image_coset)
    if lifted.status != "exact_paired_action_coset_preimage" or lifted.coset is None:
        raise AssertionError("reachable structural partition transporter failed exact original-domain preimage lift")
    return PairedPartitionTransport(
        "exact_paired_partition_transporter_coset", m, len(trans), source,
        target, image_coset, lifted.coset,
        "complete ordered partition transporter was solved in the structural image and lifted exactly to the original source group",
    )
