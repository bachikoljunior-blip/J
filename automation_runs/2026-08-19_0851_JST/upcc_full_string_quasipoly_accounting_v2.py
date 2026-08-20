from __future__ import annotations

from dataclasses import dataclass
from math import log2

from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3


def _log2_sum_exp(values):
    values = tuple(float(x) for x in values)
    if not values:
        return 0.0
    top = max(values)
    return top + log2(sum(2.0 ** (value - top) for value in values))


@dataclass(frozen=True)
class UPCCExecutionAccountingCertificate:
    status: str
    certified: bool
    branches_checked: int
    certified_branch_proofs: int
    structural_log2_overhead_bound: float
    branch_union_log2_work_bound: float
    total_log2_work_bound: float
    allowed_log2_work: float
    accounting: RecurrenceAccountingNode
    reason: str


def certify_upcc_full_string_execution_accounting(
    upcc_result,
    *,
    root_n: int,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
):
    """Charge an already-executed exact rev198 UPCC full-string computation.

    rev198 intentionally stopped short of theorem-scale recurrence certification.
    For a *completed* instance, however, it already stores every exact full-string
    branch proof.  This routine independently validates each stored proof tree with
    the existing v3 recurrence verifier, then composes their certified total-work
    bounds by log-sum-exp and adds the conservative rev198 complete-cover/transport
    bound.  This is an execution-derived terminal certificate: it does not assert
    that all abstract UPCC instances will close, and it refuses any incomplete or
    uncertified branch.

    Treating the resulting completed computation as one terminal is sound because
    the returned local bound includes the full validated work of all nested branch
    proof trees, not just their immediate local costs.  The structural overhead is
    deliberately added in full even though rev198's bound may already include some
    child-local charge; this double counting is conservative.
    """
    r = int(root_n)
    if r < 1 or quasipoly_power < 1 or quasipoly_constant <= 0:
        raise ValueError("invalid root/envelope parameters")
    allowed = quasipoly_constant * (log2(max(2, r)) ** quasipoly_power)
    structural = float(max(0.0, upcc_result.local_log2_cost_bound))

    def leaf(status, certified, checked, certified_count, branch_work, total, reason):
        accounting = RecurrenceAccountingNode(
            n=r,
            m=r,
            operation_kind="upcc_completed_execution_terminal",
            canonical=True,
            cost_certified=bool(certified),
            local_log2_cost_bound=float(total if certified else 0.0),
            children=(),
            terminal_certified=bool(certified),
            reason=reason,
        )
        return UPCCExecutionAccountingCertificate(
            status,
            bool(certified),
            int(checked),
            int(certified_count),
            structural,
            float(branch_work),
            float(total),
            float(allowed),
            accounting,
            reason,
        )

    if not upcc_result.exact or not upcc_result.complete:
        return leaf(
            "unaccounted_incomplete_upcc_execution",
            False, 0, 0, 0.0, 0.0,
            "execution accounting requires rev198 to have completed an exact complete UPCC full-string result",
        )

    full = upcc_result.full_string_result
    if full is None:
        # Exact-empty shape/transporter terminals did not recurse into candidate SI.
        total = structural + 8.0
        if total > allowed + 1e-9:
            return leaf(
                "upcc_execution_bound_exceeded", False, 0, 0, 0.0, total,
                "exact UPCC structural terminal is mechanically bounded but exceeds the configured quasipolynomial envelope",
            )
        return leaf(
            "certified_upcc_structural_terminal_execution", True, 0, 0, 0.0, total,
            "exact complete UPCC structural terminal has no downstream branch proof and its recorded complete-cover cost fits the quasipolynomial envelope",
        )

    proofs = tuple(full.branch_results)
    bounds = []
    for index, proof in enumerate(proofs):
        if not proof.exact:
            return leaf(
                "unaccounted_nonexact_upcc_branch", False, index + 1, len(bounds),
                _log2_sum_exp(bounds), 0.0,
                "rev198 exposed a nonexact full-string branch; completed execution cannot be certified as a terminal",
            )
        check = validate_quasipoly_recurrence_tree_v3(proof.accounting)
        if not check.certified:
            return leaf(
                "unaccounted_upcc_branch_" + check.status, False,
                index + 1, len(bounds), _log2_sum_exp(bounds), 0.0,
                "a stored rev198 branch proof failed the existing quasipolynomial recurrence verifier: " + check.reason,
            )
        bounds.append(float(check.log2_work_bound))

    branch_work = _log2_sum_exp(bounds)
    total = structural + branch_work + log2(max(1, len(proofs))) + 8.0
    if total > allowed + 1e-9:
        return leaf(
            "upcc_execution_bound_exceeded", False, len(proofs), len(bounds),
            branch_work, total,
            "all exact branch proofs are individually certified, but their conservative complete-cover composition exceeds the configured root envelope",
        )
    return leaf(
        "certified_upcc_completed_execution_quasipolynomial", True,
        len(proofs), len(bounds), branch_work, total,
        "every executed rev198 full-string branch has an independently certified proof tree; log-sum-exp branch composition plus the conservative complete UPCC cover/transport charge fits the root quasipolynomial envelope",
    )


__all__ = [
    "UPCCExecutionAccountingCertificate",
    "certify_upcc_full_string_execution_accounting",
]
