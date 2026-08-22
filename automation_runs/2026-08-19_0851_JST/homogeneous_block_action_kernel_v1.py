from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from block_action_preimage_coset_v1 import prepare_block_action_preimage
from homogeneous_block_action_provenance_v1 import (
    BlockActionProvenance,
    replay_group_block_action_equivariance,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain

SCHEMA_VERSION = 1
STATUS_EXACT = "exact_block_action_kernel_factorization"
STATUS_FAIL = "fail_closed_block_action_kernel_factorization"


@dataclass(frozen=True)
class BlockActionKernelFactorization:
    schema_version: int
    status: str
    exact: bool
    complete: bool
    provenance_digest: str
    domain_degree: int
    block_count: int
    generator_count: int
    estimated_schreier_work_units: int
    work_cap: int
    source_group_order: int
    target_group_order: int
    quotient_image_order: int
    source_kernel_order: int
    target_kernel_order: int
    source_sift_levels: int
    target_sift_levels: int
    source_kernel_generators: tuple[tuple[int, ...], ...]
    target_kernel_generators: tuple[tuple[int, ...], ...]
    certificate_digest: str
    reason: str


def _fail(reason: str, *, provenance_digest: str = "", work_cap: int = 0) -> BlockActionKernelFactorization:
    return BlockActionKernelFactorization(
        SCHEMA_VERSION,
        STATUS_FAIL,
        False,
        False,
        provenance_digest,
        0,
        0,
        0,
        0,
        work_cap,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        (),
        (),
        "",
        reason,
    )


def _payload(**kwargs):
    return {"schema_version": SCHEMA_VERSION, "status": STATUS_EXACT, **kwargs}


def _digest(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _sat_add(left: int, right: int, cap: int) -> int:
    if left > cap or right > cap or left > cap - right:
        return cap + 1
    return left + right


def _sat_mul(*values: int, cap: int) -> int:
    result = 1
    for value in values:
        if value == 0:
            return 0
        if result > cap // value:
            return cap + 1
        result *= value
    return result


def _chain_work_bound(
    degree: int,
    generator_count: int,
    point_width: int,
    cap: int,
) -> tuple[int, int]:
    """Bound one naive Schreier chain before constructing any permutation.

    At every base level the implementation performs an orbit traversal and a
    complete Schreier-generator pass.  Ten point-width passes per possible
    ``(orbit point, generator)`` pair conservatively cover validation,
    traversal, inversion, the two compositions, comparison, hashing and
    deduplication.  The next generator family has at most ``degree * current``
    candidates.  Values saturate at ``cap + 1`` so the bound itself cannot
    consume unbounded integers.
    """

    current = max(generator_count, 1)
    total = 0
    for _ in range(degree):
        step = _sat_mul(10, degree, current, max(point_width, 1), cap=cap)
        total = _sat_add(total, step, cap)
        current = _sat_mul(degree, current, cap=cap)
    return total, current


def _paired_chain_work_bound(
    domain_degree: int,
    quotient_degree: int,
    generator_count: int,
    cap: int,
) -> tuple[int, int]:
    """Bound paired quotient Schreier work and residual kernel candidates."""

    current = max(generator_count, 1)
    total = 0
    width = domain_degree + quotient_degree
    for _ in range(quotient_degree):
        step = _sat_mul(12, quotient_degree, current, max(width, 1), cap=cap)
        total = _sat_add(total, step, cap)
        current = _sat_mul(quotient_degree, current, cap=cap)
    return total, current


def _factorization_work_bound(
    domain_degree: int,
    block_count: int,
    generator_count: int,
    cap: int,
) -> int:
    """Bound every chain built by the source/target factorization path."""

    domain, _ = _chain_work_bound(domain_degree, generator_count, domain_degree, cap)
    quotient, _ = _chain_work_bound(block_count, generator_count, block_count, cap)
    paired, kernel_candidates = _paired_chain_work_bound(
        domain_degree, block_count, generator_count, cap
    )
    kernel, _ = _chain_work_bound(
        domain_degree, kernel_candidates, domain_degree, cap
    )

    # Per side: one original-domain chain, one explicit quotient chain, then
    # prepare_block_action_preimage builds an image chain, paired chain and
    # kernel chain.  Source and target are both certified.
    per_side = 0
    for component in (domain, quotient, quotient, paired, kernel):
        per_side = _sat_add(per_side, component, cap)
    return _sat_mul(2, per_side, cap=cap)


def certify_block_action_kernel_factorization(
    provenance: BlockActionProvenance,
    *,
    max_domain_degree: int = 4096,
    max_block_count: int = 4096,
    max_generators: int = 10_000,
    max_generator_point_checks: int = 10_000_000,
) -> BlockActionKernelFactorization:
    """Certify the exact kernel/image factorization behind a rev274 block action.

    The input must replay as an exact rev274 block-action provenance certificate.
    We then build deterministic Schreier chains for each original generator group
    and reuse the repository's paired quotient Schreier construction to retain
    full-domain kernel generators while constructing the quotient image.  No
    enumeration of either full group is performed.

    The returned transcript proves, independently on source and target,
    ``|G| = |ker(block action)| * |image(block action)|``.  Rev274's exact
    generator-by-generator intertwining additionally forces the two quotient
    image orders to agree.  This artifact deliberately stops before quotient
    String Isomorphism and before lifting any quotient transporter coset.
    """

    try:
        for name, value in (
            ("max_domain_degree", max_domain_degree),
            ("max_block_count", max_block_count),
            ("max_generators", max_generators),
            ("max_generator_point_checks", max_generator_point_checks),
        ):
            _positive_int(name, value)

        if not isinstance(provenance, BlockActionProvenance):
            raise ValueError("provenance must be a BlockActionProvenance certificate")
        provenance_digest = provenance.certificate_digest
        if not replay_group_block_action_equivariance(provenance):
            raise ValueError("rev274 block-action provenance does not replay exactly")

        n = provenance.domain_degree
        k = provenance.block_count
        generator_count = len(provenance.source_generators)
        if n > max_domain_degree:
            raise ValueError("domain degree exceeds the rev275 preflight cap")
        if k > max_block_count:
            raise ValueError("block count exceeds the rev275 preflight cap")
        if generator_count > max_generators:
            raise ValueError("paired generator count exceeds the rev275 preflight cap")

        work_bound = _factorization_work_bound(
            n, k, generator_count, max_generator_point_checks
        )
        if work_bound > max_generator_point_checks:
            raise ValueError(
                "complete Schreier factorization work bound exceeds the rev275 preflight cap"
            )

        domain_identity = identity(n)
        quotient_identity = identity(k)
        source_group = schreier_stabilizer_chain(provenance.source_generators or (domain_identity,))
        target_group = schreier_stabilizer_chain(provenance.target_generators or (domain_identity,))
        source_quotient = schreier_stabilizer_chain(
            provenance.source_quotient_generators or (quotient_identity,)
        )
        target_quotient = schreier_stabilizer_chain(
            provenance.target_quotient_generators or (quotient_identity,)
        )

        source_prepared = prepare_block_action_preimage(source_group, provenance.source_blocks)
        target_prepared = prepare_block_action_preimage(target_group, provenance.target_blocks)

        if source_prepared.image.order != source_quotient.order:
            raise AssertionError("source paired Schreier image disagrees with rev274 quotient generators")
        if target_prepared.image.order != target_quotient.order:
            raise AssertionError("target paired Schreier image disagrees with rev274 quotient generators")
        if source_quotient.order != target_quotient.order:
            raise AssertionError("rev274 intertwined quotient generator groups have different orders")
        if source_prepared.kernel.order * source_prepared.image.order != source_group.order:
            raise AssertionError("source block action violates |G|=|ker|*|im|")
        if target_prepared.kernel.order * target_prepared.image.order != target_group.order:
            raise AssertionError("target block action violates |G|=|ker|*|im|")

        source_kernel_generators = tuple(source_prepared.kernel.original_generators)
        target_kernel_generators = tuple(target_prepared.kernel.original_generators)
        payload = _payload(
            provenance_digest=provenance_digest,
            domain_degree=n,
            block_count=k,
            generator_count=generator_count,
            estimated_schreier_work_units=work_bound,
            work_cap=max_generator_point_checks,
            source_group_order=source_group.order,
            target_group_order=target_group.order,
            quotient_image_order=source_quotient.order,
            source_kernel_order=source_prepared.kernel.order,
            target_kernel_order=target_prepared.kernel.order,
            source_sift_levels=len(source_prepared.levels),
            target_sift_levels=len(target_prepared.levels),
            source_kernel_generators=source_kernel_generators,
            target_kernel_generators=target_kernel_generators,
        )
        return BlockActionKernelFactorization(
            **payload,
            exact=True,
            complete=True,
            certificate_digest=_digest(payload),
            reason=(
                "rev274 provenance replayed exactly; paired quotient Schreier chains certify the complete "
                "source and target block-action kernels and the common quotient-image order without full-group enumeration"
            ),
        )
    except (AssertionError, TypeError, ValueError) as exc:
        digest = provenance.certificate_digest if isinstance(provenance, BlockActionProvenance) else ""
        return _fail(str(exc), provenance_digest=digest, work_cap=max_generator_point_checks if isinstance(max_generator_point_checks, int) and not isinstance(max_generator_point_checks, bool) else 0)


def replay_block_action_kernel_factorization(
    certificate: BlockActionKernelFactorization,
    provenance: BlockActionProvenance,
) -> bool:
    if not isinstance(certificate, BlockActionKernelFactorization):
        return False
    if certificate.schema_version != SCHEMA_VERSION or certificate.status != STATUS_EXACT:
        return False
    if not certificate.exact or not certificate.complete:
        return False
    if not isinstance(provenance, BlockActionProvenance):
        return False
    if certificate.provenance_digest != provenance.certificate_digest:
        return False
    replay = certify_block_action_kernel_factorization(
        provenance,
        max_domain_degree=max(certificate.domain_degree, 1),
        max_block_count=max(certificate.block_count, 1),
        max_generators=max(certificate.generator_count, 1),
        max_generator_point_checks=max(certificate.work_cap, 1),
    )
    return replay == certificate and replay.certificate_digest == certificate.certificate_digest


__all__ = [
    "BlockActionKernelFactorization",
    "SCHEMA_VERSION",
    "STATUS_EXACT",
    "STATUS_FAIL",
    "certify_block_action_kernel_factorization",
    "replay_block_action_kernel_factorization",
]
