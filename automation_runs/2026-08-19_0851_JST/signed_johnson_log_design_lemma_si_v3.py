from __future__ import annotations

from dataclasses import dataclass

from design_full_execution_accounting_v1 import (
    DesignFullExecutionAccountingCertificate,
    certify_exact_design_full_execution_accounting,
)
from proof_carrying_si_v1 import ProofCarryingCoset
from signed_johnson_log_design_lemma_si_v2 import (
    W1RH6LogDesignProof,
    signed_johnson_log_design_lemma_si_v2,
)


@dataclass(frozen=True)
class W1RH6CostCertifiedLogDesignProof:
    status: str
    proof: ProofCarryingCoset | None
    h6_result: W1RH6LogDesignProof
    execution_accounting: DesignFullExecutionAccountingCertificate | None
    exact: bool
    cost_certified: bool
    reason: str


def signed_johnson_log_design_lemma_si_v3(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
    **kwargs,
) -> W1RH6CostCertifiedLogDesignProof:
    """rev213: attach rev212 accounting to the actual rev191 H6 execution path.

    rev191 deliberately separated exact finite Design execution from global cost
    certification.  rev212 can now certify such an execution when rev192's branch
    charge and every actually executed full-string child proof tree fit the root
    quasipolynomial envelope.  This wrapper performs exactly that composition.

    H5 outcomes that rev191 merely delegates are preserved unchanged: if H5 already
    returned an exact proof-carrying result, that object remains authoritative.
    The new path fires only when rev191 actually reached and exactly solved the H6
    Design branch.  Exact set reconstruction with rejected/missing accounting is
    still returned as *unresolved for theorem-scale closure*; it is never promoted
    into a cost-certified SI proof.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if root_n is None:
        root_n = n
    root = int(root_n)

    h6 = signed_johnson_log_design_lemma_si_v2(
        group,
        source,
        target,
        root_n=root,
        **kwargs,
    )

    if h6.design_result is None:
        h5 = h6.h5_result
        if h5.exact and h5.local_cost_certified:
            return W1RH6CostCertifiedLogDesignProof(
                "delegated_cost_certified_" + h5.status,
                h5,
                h6,
                None,
                True,
                True,
                "rev191 delegated an already exact proof-carrying H5 result; no H6 Design accounting composition was required",
            )
        return W1RH6CostCertifiedLogDesignProof(
            "delegated_unresolved_" + h5.status,
            None,
            h6,
            None,
            bool(h5.exact),
            False,
            "rev191 did not execute the H6 Design branch and its delegated H5 result is not a cost-certified exact terminal",
        )

    design = h6.design_result
    if not h6.exact or not design.exact:
        return W1RH6CostCertifiedLogDesignProof(
            "undetermined_w1r_h6_design_execution",
            None,
            h6,
            None,
            False,
            False,
            "the H6 Design branch remains nonexact, so complexity accounting cannot convert it into a solved SI child",
        )

    cert = certify_exact_design_full_execution_accounting(
        design,
        root_n=root,
        prefix_log2_cost_bound=h6.h5_result.local_log2_cost_bound,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not cert.certified:
        return W1RH6CostCertifiedLogDesignProof(
            "exact_set_but_uncertified_w1r_h6_design_cost",
            None,
            h6,
            cert,
            True,
            False,
            "rev191 reconstructed the exact H6 Design full-string set, but rev212 rejected its root-scale execution accounting: " + cert.status,
        )

    full = design.full_string_result
    children = () if full is None else tuple(full.branch_results)
    checked = sum(child.permutation_candidates_checked for child in children)
    proof = ProofCarryingCoset(
        "exact_cost_certified_w1r_h6_design_full_string",
        h6.coset,
        "design_full_execution_terminal",
        root,
        n,
        True,
        True,
        True,
        cert.total_log2_work_bound,
        True,
        children,
        cert.accounting,
        checked,
        "rev191 exact H6 Design set reconstruction plus rev192 branch charge and independently validated child recurrence trees fit the original-root quasipolynomial envelope",
    )
    return W1RH6CostCertifiedLogDesignProof(
        "exact_cost_certified_w1r_h6_design_full_string",
        proof,
        h6,
        cert,
        True,
        True,
        "exact H6 Design execution is now both set-correct and root-scale cost-certified without weakening any unresolved structural branch",
    )
