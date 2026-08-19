from __future__ import annotations

from dataclasses import dataclass
from math import log2


@dataclass(frozen=True)
class BabaiLocalCertificateParameterGate:
    status: str
    primary_domain_size: int
    giant_degree: int
    test_size: int
    strict_lower_bound: float
    upper_bound: float
    certified: bool
    reason: str


def babai_local_certificate_parameter_gate(
    primary_domain_size: int,
    giant_degree: int,
    test_size: int,
) -> BabaiLocalCertificateParameterGate:
    """Check the theorem-side parameter window for Babai local certificates.

    The local-certificates theorem uses a test set T of size t under the
    hypotheses max(8, 2+log2 n) < t <= m/10, where n is the primary permutation
    domain and m is the giant quotient degree.  This gate is deliberately
    separate from the weaker engineering condition t=O(log n): satisfying an
    asymptotic upper bound alone is not enough to invoke the theorem.
    """
    n = int(primary_domain_size)
    m = int(giant_degree)
    t = int(test_size)
    if n <= 0 or m <= 0 or t <= 0:
        return BabaiLocalCertificateParameterGate(
            "invalid_parameters", n, m, t, 0.0, 0.0, False,
            "n, m and test size must all be positive",
        )
    lower = max(8.0, 2.0 + log2(max(1, n)))
    upper = m / 10.0
    if not (t > lower):
        return BabaiLocalCertificateParameterGate(
            "test_set_below_theorem_window", n, m, t, lower, upper, False,
            "test size does not strictly exceed max(8, 2+log2 n)",
        )
    if t > upper:
        return BabaiLocalCertificateParameterGate(
            "giant_degree_too_small_for_test_set", n, m, t, lower, upper, False,
            "test size exceeds m/10, so the local-certificates theorem window is unavailable",
        )
    return BabaiLocalCertificateParameterGate(
        "certified_local_certificate_parameter_window", n, m, t,
        lower, upper, True,
        "test size satisfies max(8, 2+log2 n) < |T| <= m/10",
    )
