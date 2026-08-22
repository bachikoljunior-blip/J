from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Optional, Sequence

from block_action_preimage_coset_v1 import (
    BlockActionPreimageCoset,
    lift_prepared_block_action_preimage,
    prepare_block_action_preimage,
)
from homogeneous_block_action_provenance_v1 import (
    BlockActionProvenance,
    replay_group_block_action_equivariance,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain, validate_perm

SCHEMA_VERSION = 1
STATUS_EXACT = "exact_homogeneous_block_quotient_preimage"
STATUS_EXACT_EMPTY = "exact_empty_homogeneous_block_quotient_preimage"
STATUS_FAIL = "fail_closed_homogeneous_block_quotient_preimage"


@dataclass(frozen=True)
class HomogeneousBlockQuotientPreimage:
    schema_version: int
    status: str
    exact: bool
    complete: bool
    side: str
    provenance_digest: str
    quotient_permutation: tuple[int, ...]
    domain_degree: int
    quotient_degree: int
    domain_order: int
    image_order: int
    kernel_order: int
    representative: Optional[tuple[int, ...]]
    kernel_generators: tuple[tuple[int, ...], ...]
    certificate_digest: str
    reason: str


def _payload(**kwargs):
    return {"schema_version": SCHEMA_VERSION, **kwargs}


def _digest(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _certificate(
    *,
    status: str,
    exact: bool,
    complete: bool,
    side: str,
    provenance_digest: str,
    quotient_permutation: tuple[int, ...],
    domain_degree: int,
    quotient_degree: int,
    domain_order: int,
    image_order: int,
    kernel_order: int,
    representative: Optional[tuple[int, ...]],
    kernel_generators: tuple[tuple[int, ...], ...],
    reason: str,
) -> HomogeneousBlockQuotientPreimage:
    payload = _payload(
        status=status,
        exact=exact,
        complete=complete,
        side=side,
        provenance_digest=provenance_digest,
        quotient_permutation=quotient_permutation,
        domain_degree=domain_degree,
        quotient_degree=quotient_degree,
        domain_order=domain_order,
        image_order=image_order,
        kernel_order=kernel_order,
        representative=representative,
        kernel_generators=kernel_generators,
        reason=reason,
    )
    return HomogeneousBlockQuotientPreimage(**payload, certificate_digest=_digest(payload))


def _fail(reason: str, *, side: str = "", provenance_digest: str = "", quotient_permutation=()):
    return _certificate(
        status=STATUS_FAIL,
        exact=False,
        complete=False,
        side=side,
        provenance_digest=provenance_digest,
        quotient_permutation=tuple(quotient_permutation),
        domain_degree=0,
        quotient_degree=0,
        domain_order=0,
        image_order=0,
        kernel_order=0,
        representative=None,
        kernel_generators=(),
        reason=reason,
    )


def _selected_action(provenance: BlockActionProvenance, side: str):
    if side == "source":
        return provenance.source_blocks, provenance.source_generators
    if side == "target":
        return provenance.target_blocks, provenance.target_generators
    raise ValueError("side must be 'source' or 'target'")


def _validated_quotient_permutation(value: Sequence[int], degree: int) -> tuple[int, ...]:
    perm = validate_perm(value)
    if len(perm) != degree:
        raise ValueError("quotient permutation has wrong degree")
    return perm


def lift_certified_block_quotient_preimage(
    provenance: BlockActionProvenance,
    side: str,
    quotient_permutation: Sequence[int],
) -> HomogeneousBlockQuotientPreimage:
    """Lift one quotient permutation through a replayed rev274 block action.

    This is deliberately narrower than quotient String-Isomorphism: the caller
    supplies one quotient permutation.  A successful result is the exact fiber
    of the certified block-action homomorphism, represented as kernel * r in the
    repository's right-coset convention.  If Schreier sifting proves the supplied
    quotient permutation is outside the image, the result is exact empty.
    """
    provenance_digest = getattr(provenance, "certificate_digest", "")
    try:
        if not replay_group_block_action_equivariance(provenance):
            return _fail(
                "rev274 group block-action provenance did not replay exactly",
                side=str(side),
                provenance_digest=str(provenance_digest),
            )
        blocks, generators = _selected_action(provenance, side)
        qperm = _validated_quotient_permutation(quotient_permutation, provenance.block_count)
        domain_gens = tuple(generators) or (identity(provenance.domain_degree),)
        group = schreier_stabilizer_chain(domain_gens)
        prepared = prepare_block_action_preimage(group, blocks)
        if prepared.kernel.order * prepared.image.order != group.order:
            return _fail(
                "prepared block-action factorization violated |G|=|ker|*|im|",
                side=side,
                provenance_digest=provenance.certificate_digest,
                quotient_permutation=qperm,
            )
        lifted: BlockActionPreimageCoset = lift_prepared_block_action_preimage(prepared, qperm)
        common = dict(
            side=side,
            provenance_digest=provenance.certificate_digest,
            quotient_permutation=qperm,
            domain_degree=provenance.domain_degree,
            quotient_degree=provenance.block_count,
            domain_order=group.order,
            image_order=prepared.image.order,
            kernel_order=prepared.kernel.order,
            kernel_generators=tuple(prepared.kernel.original_generators),
        )
        if lifted.status == "quotient_not_in_image":
            return _certificate(
                status=STATUS_EXACT_EMPTY,
                exact=True,
                complete=True,
                representative=None,
                reason="paired Schreier sift proves the supplied quotient permutation has no original-domain preimage",
                **common,
            )
        if lifted.status != "exact_block_action_preimage_coset" or lifted.coset is None or lifted.representative is None:
            return _fail(
                "generic block-action preimage primitive returned an unrecognized nonexact outcome",
                side=side,
                provenance_digest=provenance.certificate_digest,
                quotient_permutation=qperm,
            )
        if lifted.kernel.order != prepared.kernel.order or lifted.image_order != prepared.image.order:
            return _fail(
                "generic preimage evidence disagreed with the prepared exact homomorphism",
                side=side,
                provenance_digest=provenance.certificate_digest,
                quotient_permutation=qperm,
            )
        return _certificate(
            status=STATUS_EXACT,
            exact=True,
            complete=True,
            representative=tuple(lifted.representative),
            reason="replayed rev274 provenance plus paired Schreier sifting returned the complete original-domain fiber kernel * representative",
            **common,
        )
    except (TypeError, ValueError, AssertionError) as exc:
        return _fail(
            str(exc),
            side=str(side),
            provenance_digest=str(provenance_digest),
        )


def replay_homogeneous_block_quotient_preimage(
    provenance: BlockActionProvenance,
    certificate: HomogeneousBlockQuotientPreimage,
) -> bool:
    if not isinstance(certificate, HomogeneousBlockQuotientPreimage):
        return False
    if certificate.schema_version != SCHEMA_VERSION:
        return False
    if certificate.status not in (STATUS_EXACT, STATUS_EXACT_EMPTY):
        return False
    if not certificate.exact or not certificate.complete:
        return False
    replay = lift_certified_block_quotient_preimage(
        provenance,
        certificate.side,
        certificate.quotient_permutation,
    )
    return replay == certificate and replay.certificate_digest == certificate.certificate_digest


__all__ = [
    "HomogeneousBlockQuotientPreimage",
    "SCHEMA_VERSION",
    "STATUS_EXACT",
    "STATUS_EXACT_EMPTY",
    "STATUS_FAIL",
    "lift_certified_block_quotient_preimage",
    "replay_homogeneous_block_quotient_preimage",
]
