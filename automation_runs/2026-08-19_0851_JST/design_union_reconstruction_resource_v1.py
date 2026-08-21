from __future__ import annotations

from dataclasses import dataclass, replace

from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul


@dataclass(frozen=True)
class DesignUnionReconstructionResourceEnvelope:
    status: str
    degree: int
    ambient_group_order: int
    branch_count: int
    nonempty_branch_count: int
    generator_input_count: int
    membership_and_string_work_upper_bound: int
    schreier_chain_work_upper_bound: int
    work_upper_bound: int
    max_work: int
    admitted: bool
    executed_generator_count: int
    complete: bool
    reason: str


def design_union_reconstruction_resource_envelope(
    ambient_group,
    branch_results,
    *,
    max_work: int,
) -> DesignUnionReconstructionResourceEnvelope:
    """Reserve exact right-coset union reconstruction before it starts.

    Child SI is already complete at this boundary.  We can therefore count the
    exact generator inputs without executing ambient membership sifts, string
    checks, inter-branch delta construction, or the final raw Schreier chain.
    The ambient group order bounds every intermediate subgroup.  Saturation is
    derived only from the caller's arbitrary-precision ``cap+1``.
    """
    frozen = tuple(branch_results)
    cap = int(max_work)
    if cap <= 0:
        raise ValueError("max union reconstruction work must be positive")
    n = int(ambient_group.degree)
    order = int(ambient_group.order)
    if min(n, order) <= 0:
        raise ValueError("invalid ambient Design union group")
    nonempty = tuple(result.coset for result in frozen if result.coset is not None)
    if any(not result.exact for result in frozen):
        raise ValueError("union reconstruction preflight requires exact children")
    if any(coset.subgroup.degree != n for coset in nonempty):
        raise ValueError("Design union child degree mismatch")
    generators = sum(len(coset.subgroup.original_generators) for coset in nonempty)
    # One representative difference is deliberately charged per nonempty branch,
    # including the identity delta for the chosen base branch.
    inputs = generators + len(nonempty)
    stop = cap + 1
    # Each input is ambient-sifted and string-checked.  ``order`` is a safe bound
    # on the raw strong-generator family at every level.
    verification_per_input = _sat_mul(16 * n * n, order, stop)
    verification = _sat_mul(inputs, verification_per_input, stop)
    chain = 0 if not nonempty else _chain_bound(n, max(1, inputs), order, n, stop)
    total = _sat_add(verification, chain, stop)
    admitted = total <= cap
    return DesignUnionReconstructionResourceEnvelope(
        "certified_design_union_reconstruction_work_bound" if admitted else
        "design_union_reconstruction_work_cap_exceeded",
        n, order, len(frozen), len(nonempty), inputs, verification, chain,
        total, cap, admitted, 0, False,
        (
            "all ambient sifts, string checks, inter-branch deltas, and the final Schreier chain fit the finite budget"
            if admitted else
            "the complete union reconstruction exceeds the finite budget before its first ambient sift or Schreier operation"
        ),
    )


def record_design_union_reconstruction_execution(
    envelope: DesignUnionReconstructionResourceEnvelope,
    *,
    executed_generator_count: int,
    complete: bool,
) -> DesignUnionReconstructionResourceEnvelope:
    if not envelope.admitted:
        raise ValueError("cannot record a rejected Design union reconstruction")
    count = int(executed_generator_count)
    if count < 0 or count > envelope.generator_input_count:
        raise ValueError("union generator count exceeds the reserved input family")
    if complete and count != envelope.generator_input_count:
        raise ValueError("complete union reconstruction omitted a reserved generator input")
    return replace(
        envelope,
        executed_generator_count=count,
        complete=bool(complete),
    )


__all__ = [
    "DesignUnionReconstructionResourceEnvelope",
    "design_union_reconstruction_resource_envelope",
    "record_design_union_reconstruction_execution",
]
