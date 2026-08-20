from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable

from bipartite_reduce_part2_by_color_v1 import (
    ReducePart2ByColorCertificate,
    reduce_part2_by_color_certificate,
)

CanonicalAtom = tuple
RightSignature = tuple[CanonicalAtom, tuple[int, ...]]
SignatureInventory = tuple[tuple[RightSignature, int], ...]


@dataclass(frozen=True)
class CanonicalRightPartition:
    status: str
    left_color_inventory: tuple[tuple[CanonicalAtom, int], ...]
    right_signature_inventory: SignatureInventory
    ordered_signature_classes: tuple[tuple[int, ...], ...]
    split_index: int | None
    part0: tuple[int, ...]
    part1: tuple[int, ...]
    alpha_balanced: bool
    exact: bool
    reason: str


@dataclass(frozen=True)
class PairedRightPartitionProvenance:
    status: str
    source_partition: CanonicalRightPartition
    target_partition: CanonicalRightPartition
    source_restriction: ReducePart2ByColorCertificate | None
    target_restriction: ReducePart2ByColorCertificate | None
    selected_part_index: int | None
    selected_signature_inventory: SignatureInventory
    provenance_verified: bool
    restriction_pair_complete: bool
    exact: bool
    reason: str


def _canonical_atom(value: Hashable) -> CanonicalAtom:
    """Injectively encode supported typed color atoms into a total order."""
    if value is None:
        return ("none",)
    if isinstance(value, bool):
        return ("bool", int(value))
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("color floats must be finite")
        return ("float", value.hex())
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, bytes):
        return ("bytes", value.hex())
    if isinstance(value, tuple):
        return ("tuple", tuple(_canonical_atom(item) for item in value))
    if isinstance(value, frozenset):
        return ("frozenset", tuple(sorted(_canonical_atom(item) for item in value)))
    raise TypeError(
        "colors must be canonical atoms: None/bool/int/finite-float/str/bytes/tuple/frozenset"
    )


def _normalize_edges(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("edge endpoint outside the declared bipartite parts")
        out.add((a, b))
    return out


def _palette(
    size: int,
    colors: Iterable[Hashable] | None,
    default: Hashable,
) -> tuple[Hashable, ...]:
    out = tuple(default for _ in range(size)) if colors is None else tuple(colors)
    if len(out) != size:
        raise ValueError("vertex-color sequence length mismatch")
    tuple(_canonical_atom(value) for value in out)
    return out


def derive_canonical_right_partition(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    left_colors: Iterable[Hashable] | None = None,
    right_colors: Iterable[Hashable] | None = None,
) -> CanonicalRightPartition:
    """Derive an ordered proper right partition from exact incidence signatures.

    Each right vertex receives ``(right_color, neighbor counts by canonically
    ordered left color)``.  Signature classes are ordered by an injective typed
    encoding.  The boundary minimizing the larger side is selected, with the
    boundary index as a deterministic tie-break.  No vertex label is used.

    A single signature class fails closed: higher-arity Design/coherent
    provenance is a separate obligation.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 1 or n2 < 2:
        raise ValueError("canonical right partition requires left_size>=1 and right_size>=2")
    if not 2 / 3 <= alpha < 1.0:
        raise ValueError("alpha must lie in [2/3,1)")

    left_palette = _palette(n1, left_colors, 0)
    right_palette = _palette(n2, right_colors, 1)
    edge_set = _normalize_edges(n1, n2, edges)

    encoded_left = tuple(_canonical_atom(value) for value in left_palette)
    left_buckets: dict[CanonicalAtom, list[int]] = defaultdict(list)
    for a, color in enumerate(encoded_left):
        left_buckets[color].append(a)
    ordered_left_colors = tuple(sorted(left_buckets))
    left_inventory = tuple((color, len(left_buckets[color])) for color in ordered_left_colors)
    left_color_index = {color: i for i, color in enumerate(ordered_left_colors)}

    count_vectors = [[0] * len(ordered_left_colors) for _ in range(n2)]
    for a, b in edge_set:
        count_vectors[b][left_color_index[encoded_left[a]]] += 1

    classes: dict[RightSignature, list[int]] = defaultdict(list)
    for b in range(n2):
        signature: RightSignature = (
            _canonical_atom(right_palette[b]),
            tuple(count_vectors[b]),
        )
        classes[signature].append(b)

    ordered_signatures = tuple(sorted(classes))
    ordered_classes = tuple(tuple(sorted(classes[sig])) for sig in ordered_signatures)
    inventory: SignatureInventory = tuple(
        (signature, len(classes[signature])) for signature in ordered_signatures
    )
    if len(ordered_classes) < 2:
        return CanonicalRightPartition(
            "canonical_right_partition_no_progress",
            left_inventory,
            inventory,
            ordered_classes,
            None,
            (),
            (),
            False,
            True,
            "all right vertices have one exact degree/color incidence signature; a higher-arity provenance layer is required",
        )

    prefix = 0
    candidates = []
    for boundary in range(1, len(ordered_classes)):
        prefix += len(ordered_classes[boundary - 1])
        suffix = n2 - prefix
        candidates.append((max(prefix, suffix), abs(prefix - suffix), boundary))
    _, _, split_index = min(candidates)
    part0 = tuple(sorted(v for cell in ordered_classes[:split_index] for v in cell))
    part1 = tuple(sorted(v for cell in ordered_classes[split_index:] for v in cell))
    alpha_balanced = max(len(part0), len(part1)) <= alpha * n2 + 1e-12
    return CanonicalRightPartition(
        "canonical_right_partition",
        left_inventory,
        inventory,
        ordered_classes,
        split_index,
        part0,
        part1,
        alpha_balanced,
        True,
        "ordered right signature classes and the minimum-maximum-size boundary are derived without vertex-label choices",
    )


def _selected_inventory(
    partition: CanonicalRightPartition,
    selected_index: int,
) -> SignatureInventory:
    assert partition.split_index is not None
    if selected_index == 0:
        return partition.right_signature_inventory[: partition.split_index]
    if selected_index == 1:
        return partition.right_signature_inventory[partition.split_index :]
    raise ValueError("selected part index must be 0 or 1")


def certify_paired_right_partition_provenance(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
    source_right_colors: Iterable[Hashable] | None = None,
    target_right_colors: Iterable[Hashable] | None = None,
) -> PairedRightPartitionProvenance:
    """Pair a canonical right restriction across source and target instances.

    Equal exact inventories are necessary for a color-preserving bipartite
    isomorphism.  rev200's Exercise 5.5 restriction is run independently.  A
    complete single structural branch is emitted only when every deterministic
    selection invariant agrees.  Ambient transport and full-string intersection
    remain separate obligations.
    """
    src_edges = tuple(source_edges)
    dst_edges = tuple(target_edges)
    src_left = _palette(int(left_size), source_left_colors, 0)
    dst_left = _palette(int(left_size), target_left_colors, 0)
    src_right = _palette(int(right_size), source_right_colors, 1)
    dst_right = _palette(int(right_size), target_right_colors, 1)

    src = derive_canonical_right_partition(
        left_size,
        right_size,
        src_edges,
        alpha=alpha,
        left_colors=src_left,
        right_colors=src_right,
    )
    dst = derive_canonical_right_partition(
        left_size,
        right_size,
        dst_edges,
        alpha=alpha,
        left_colors=dst_left,
        right_colors=dst_right,
    )

    empty_inventory: SignatureInventory = ()
    if src.left_color_inventory != dst.left_color_inventory:
        return PairedRightPartitionProvenance(
            "left_color_inventory_mismatch",
            src,
            dst,
            None,
            None,
            None,
            empty_inventory,
            False,
            False,
            True,
            "a color-preserving bipartite isomorphism must preserve the exact left color inventory",
        )
    if src.right_signature_inventory != dst.right_signature_inventory:
        return PairedRightPartitionProvenance(
            "right_signature_inventory_mismatch",
            src,
            dst,
            None,
            None,
            None,
            empty_inventory,
            False,
            False,
            True,
            "a color-preserving bipartite isomorphism must preserve every exact right degree/color signature and multiplicity",
        )
    if src.status != "canonical_right_partition" or dst.status != "canonical_right_partition":
        return PairedRightPartitionProvenance(
            "canonical_right_partition_no_progress",
            src,
            dst,
            None,
            None,
            None,
            empty_inventory,
            True,
            False,
            True,
            "the paired exact inventories agree but expose no proper degree/color signature split",
        )
    if src.split_index != dst.split_index:
        return PairedRightPartitionProvenance(
            "canonical_partition_selection_invariant_violation",
            src,
            dst,
            None,
            None,
            None,
            empty_inventory,
            False,
            False,
            True,
            "equal ordered inventories produced different deterministic split boundaries",
        )

    src_cert = reduce_part2_by_color_certificate(
        left_size,
        right_size,
        src_edges,
        src.part0,
        src.part1,
        alpha=alpha,
        left_colors=src_left,
    )
    dst_cert = reduce_part2_by_color_certificate(
        left_size,
        right_size,
        dst_edges,
        dst.part0,
        dst.part1,
        alpha=alpha,
        left_colors=dst_left,
    )

    if src_cert.status != dst_cert.status:
        return PairedRightPartitionProvenance(
            "paired_restriction_status_mismatch",
            src,
            dst,
            src_cert,
            dst_cert,
            None,
            empty_inventory,
            False,
            False,
            True,
            "canonical paired restrictions have different exact rev200 statuses; no color-preserving isomorphism can map the inputs",
        )
    if src_cert.status != "certified_reduce_part2_by_color":
        return PairedRightPartitionProvenance(
            "paired_restriction_no_progress",
            src,
            dst,
            src_cert,
            dst_cert,
            None,
            empty_inventory,
            True,
            False,
            True,
            "the canonical partition provenance is paired, but the exact rev200 twin-free restriction gate is not available",
        )

    src_invariants = (
        src_cert.selected_part_index,
        src_cert.part0_largest_left_twin_class,
        src_cert.part1_largest_left_twin_class,
        src_cert.part0_exercise55_gate,
        src_cert.part1_exercise55_gate,
        src_cert.selected_alpha_shrink,
    )
    dst_invariants = (
        dst_cert.selected_part_index,
        dst_cert.part0_largest_left_twin_class,
        dst_cert.part1_largest_left_twin_class,
        dst_cert.part0_exercise55_gate,
        dst_cert.part1_exercise55_gate,
        dst_cert.selected_alpha_shrink,
    )
    if src_invariants != dst_invariants:
        return PairedRightPartitionProvenance(
            "paired_restriction_invariant_mismatch",
            src,
            dst,
            src_cert,
            dst_cert,
            None,
            empty_inventory,
            False,
            False,
            True,
            "the canonical restrictions disagree on exact twin-class selection invariants; no color-preserving isomorphism can map the inputs",
        )

    assert src_cert.selected_part_index is not None
    selected_inventory = _selected_inventory(src, src_cert.selected_part_index)
    if selected_inventory != _selected_inventory(dst, dst_cert.selected_part_index):
        return PairedRightPartitionProvenance(
            "paired_selected_signature_invariant_violation",
            src,
            dst,
            src_cert,
            dst_cert,
            None,
            empty_inventory,
            False,
            False,
            True,
            "equal deterministic selections produced different selected signature inventories",
        )

    return PairedRightPartitionProvenance(
        "paired_right_partition_provenance",
        src,
        dst,
        src_cert,
        dst_cert,
        src_cert.selected_part_index,
        selected_inventory,
        True,
        True,
        True,
        "every color-preserving bipartite isomorphism maps the canonical source signature union to the identical target signature union; ambient transporter and full-string intersection remain separate obligations",
    )
