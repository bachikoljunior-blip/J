from __future__ import annotations

from dataclasses import dataclass
from math import log2

from design_lemma_branch_cost_certificate_v1 import (
    DesignBranchCostCertificate,
    certify_design_branch_quasipoly_cost,
)
from design_lemma_candidate_si_v1 import DesignLemmaCandidateSI
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from quasipoly_recurrence_accounting_v3 import (
    QuasipolyAccountingValidation,
    validate_quasipoly_recurrence_tree_v3,
)


@dataclass(frozen=True)
class DesignFullExecutionAccountingCertificate:
    status: str
    root_n: int
    ground_size: int
    branch_count: int
    exact_design_result: bool
    theorem_hypotheses_certified: bool
    branch_cost: DesignBranchCostCertificate
    child_validations: tuple[QuasipolyAccountingValidation, ...]
    prefix_log2_cost_bound: float
    design_log2_cost_bound: float
    child_union_log2_work_bound: float
    total_log2_work_bound: float
    allowed_log2_work: float
    accounting: RecurrenceAccountingNode
    certified: bool
    reason: str


def _log2_sum_exp(values):
    values = tuple(float(x) for x in values)
    if not values:
        return 0.0
    top = max(values)
    return top + log2(sum(2.0 ** (x - top) for x in values))


def _uncertified(
    status,
    *,
    design,
    root_n,
    branch_cost,
    validations=(),
    prefix=0.0,
    child_union=0.0,
    allowed=0.0,
    reason,
):
    v = int(design.branch_plan.vertex_count)
    accounting = RecurrenceAccountingNode(
        n=int(root_n),
        m=max(1, min(int(root_n), v)),
        operation_kind="unresolved_design_full_execution_accounting",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=False,
        reason=reason,
    )
    return DesignFullExecutionAccountingCertificate(
        status,
        int(root_n),
        v,
        int(design.branch_plan.branch_count),
        bool(design.exact),
        bool(design.theorem_hypotheses_certified),
        branch_cost,
        tuple(validations),
        float(prefix),
        float(design.local_log2_cost_bound),
        float(child_union),
        0.0,
        float(allowed),
        accounting,
        False,
        reason,
    )


def certify_exact_design_full_execution_accounting(
    design: DesignLemmaCandidateSI,
    *,
    root_n: int,
    prefix_log2_cost_bound: float = 0.0,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> DesignFullExecutionAccountingCertificate:
    """Flatten one *executed exact* Design-Lemma solve into a cost-certified terminal.

    rev190 already proves exact set reconstruction when every tuple branch has been
    intersected with the original full string.  rev191 intentionally withholds a
    complexity certificate for that Design path, while rev192 separately certifies
    the complete tuple-pair branch multiplicity.  This function joins those proof
    obligations without inventing progress for an unresolved structural child.

    For a nonempty full-string cover every executed child is a ProofCarryingCoset.
    We require each child's actual recurrence tree to pass the existing v3 verifier
    and compose their *validated total work* with log-sum-exp.  The complete Design
    execution cost is then conservatively bounded by

      prefix + rev190 explicit Design/transport/union bound
      + rev192 theorem branch-charge bound + logsumexp(validated child work)
      + a fixed polynomial bookkeeping envelope.

    This deliberately double-charges some local branch work already present in the
    rev190 union bound; overcharging is safe and avoids relying on undocumented
    cancellation.  Certification succeeds only if the resulting numeric bound fits
    the same configured quasipolynomial envelope in the original root measure.

    The result is a terminal accounting node because all recursive branch SI calls
    have already executed exactly and their complete validated costs have been
    absorbed numerically.  It is not a certificate for a merely structural Design
    outcome or for children whose proof accounting is still fail-closed.
    """
    root = int(root_n)
    if root < 1 or quasipoly_power < 1 or quasipoly_constant <= 0:
        raise ValueError("invalid root/quasipolynomial parameters")
    prefix = float(prefix_log2_cost_bound)
    if prefix < 0:
        raise ValueError("prefix_log2_cost_bound must be nonnegative")

    branch_cost = certify_design_branch_quasipoly_cost(
        design.branch_plan,
        root_n=root,
    )
    allowed = float(quasipoly_constant) * (log2(max(2, root)) ** int(quasipoly_power))

    if not design.exact or not design.complete:
        return _uncertified(
            "undetermined_nonexact_design_execution",
            design=design, root_n=root, branch_cost=branch_cost,
            prefix=prefix, allowed=allowed,
            reason="full execution accounting requires a complete exact Design-Lemma result",
        )
    if not design.theorem_hypotheses_certified:
        return _uncertified(
            "undetermined_design_theorem_gate",
            design=design, root_n=root, branch_cost=branch_cost,
            prefix=prefix, allowed=allowed,
            reason="exact finite execution is not enough: the Design theorem hypotheses must also be mechanically certified",
        )
    if not branch_cost.certified:
        return _uncertified(
            "undetermined_design_branch_charge",
            design=design, root_n=root, branch_cost=branch_cost,
            prefix=prefix, allowed=allowed,
            reason="the complete Design branch cover lacks the rev192 quasipolynomial branch-charge certificate",
        )

    validations = []
    child_work = []
    full = design.full_string_result
    if full is not None:
        if not full.exact or not full.complete:
            return _uncertified(
                "undetermined_incomplete_design_full_string",
                design=design, root_n=root, branch_cost=branch_cost,
                prefix=prefix, allowed=allowed,
                reason="Design result exposes a non-complete full-string branch execution",
            )
        for child in full.branch_results:
            if not child.exact or not child.local_cost_certified:
                return _uncertified(
                    "undetermined_design_child_cost",
                    design=design, root_n=root, branch_cost=branch_cost,
                    validations=validations, prefix=prefix, allowed=allowed,
                    reason="an executed Design tuple branch is exact as a set but lacks proof-carrying local cost certification",
                )
            check = validate_quasipoly_recurrence_tree_v3(
                child.accounting,
                quasipoly_power=quasipoly_power,
                quasipoly_constant=quasipoly_constant,
            )
            validations.append(check)
            if not check.certified:
                return _uncertified(
                    "undetermined_design_child_recurrence",
                    design=design, root_n=root, branch_cost=branch_cost,
                    validations=validations, prefix=prefix, allowed=allowed,
                    reason="an executed exact Design tuple branch has an accounting tree rejected by the existing recurrence verifier: " + check.status,
                )
            child_work.append(check.log2_work_bound)

    child_union = _log2_sum_exp(child_work)
    v = int(design.branch_plan.vertex_count)
    bookkeeping = 12.0 * log2(max(2, root)) + 48.0
    total = (
        prefix
        + float(design.local_log2_cost_bound)
        + float(branch_cost.branch_log2_bound)
        + float(child_union)
        + bookkeeping
    )
    if total > allowed + 1e-9:
        return _uncertified(
            "undetermined_design_execution_quasipoly_envelope",
            design=design, root_n=root, branch_cost=branch_cost,
            validations=validations, prefix=prefix, child_union=child_union,
            allowed=allowed,
            reason="the mechanically composed exact Design execution exceeds the configured quasipolynomial envelope",
        )

    accounting = RecurrenceAccountingNode(
        n=root,
        m=max(1, min(root, v)),
        operation_kind="design_full_execution_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=total,
        children=(),
        terminal_certified=True,
        reason=(
            "complete exact Design theorem execution; rev192 branch multiplicity and every executed full-string child recurrence were independently certified and numerically absorbed into this terminal bound"
        ),
    )
    final_check = validate_quasipoly_recurrence_tree_v3(
        accounting,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not final_check.certified:
        raise AssertionError("constructed Design full-execution terminal failed recurrence validation")

    return DesignFullExecutionAccountingCertificate(
        "certified_design_full_execution_accounting",
        root,
        v,
        int(design.branch_plan.branch_count),
        True,
        True,
        branch_cost,
        tuple(validations),
        prefix,
        float(design.local_log2_cost_bound),
        float(child_union),
        float(total),
        float(allowed),
        accounting,
        True,
        "exact Design execution, theorem gate, branch charge, child proof trees, and final root-scale quasipolynomial envelope all certified",
    )
