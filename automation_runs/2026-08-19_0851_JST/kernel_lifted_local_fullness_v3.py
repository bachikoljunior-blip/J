from __future__ import annotations

from dataclasses import dataclass

from babai_local_certificate_parameter_gate_v1 import (
    BabaiLocalCertificateParameterGate,
    babai_local_certificate_parameter_gate,
)
from kernel_lifted_local_fullness_v2 import (
    KernelLiftedLocalFullnessV2,
    kernel_lifted_local_fullness_v2,
)


@dataclass(frozen=True)
class KernelLiftedLocalFullnessV3:
    exact_result: KernelLiftedLocalFullnessV2
    parameter_gate: BabaiLocalCertificateParameterGate
    theorem_scale_recurrence_evidence: bool
    reason: str


def kernel_lifted_local_fullness_v3(group, blocks, values, test_set, **kwargs):
    """Attach the exact Babai theorem parameter gate to rev158 execution.

    rev158's `recurrence_child_bound_verified` certifies only the measured
    affected-kernel child-size inequality.  The local-certificates theorem also
    requires max(8,2+log2 n) < |T| <= m/10.  This wrapper makes the conjunction
    explicit so small correctness fixtures or merely O(log n) test sets can never
    be mistaken for theorem-scale recurrence evidence.
    """
    blocks = tuple(tuple(b) for b in blocks)
    T = tuple(sorted(set(int(x) for x in test_set)))
    exact = kernel_lifted_local_fullness_v2(
        group, blocks, values, T, **kwargs
    )
    gate = babai_local_certificate_parameter_gate(
        group.degree, len(blocks), len(T)
    )
    certified = bool(
        exact.recurrence_child_bound_verified and gate.certified
    )
    return KernelLiftedLocalFullnessV3(
        exact,
        gate,
        certified,
        (
            "exact local fullness plus affected-child shrink and the published local-certificate parameter window are all certified"
            if certified
            else "exact correctness may hold, but theorem-scale recurrence evidence is withheld unless both affected-child shrink and the published parameter window are certified"
        ),
    )
