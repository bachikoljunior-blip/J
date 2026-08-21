from __future__ import annotations

from dataclasses import dataclass
from math import log2

from quasipoly_recurrence_accounting_v1 import _log2_sum_exp
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4


@dataclass(frozen=True)
class DesignFullStringChildResourceProof:
    status: str
    expected_branch_count: int
    accounted_branch_count: int
    child_log2_work_bounds: tuple[float, ...]
    combined_log2_work_bound: float
    allowed_log2_work: float
    nodes_checked: int
    certified: bool
    reason: str


def certify_design_full_string_child_resources(
    children,
    *,
    expected_branch_count: int,
    original_root_degree: int,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> DesignFullStringChildResourceProof:
    """Bind every executed full-string child to its recurrence proof exactly once."""
    children = tuple(children)
    expected = int(expected_branch_count)
    root = int(original_root_degree)
    if expected < 0 or root <= 0 or quasipoly_power < 1 or quasipoly_constant <= 0:
        raise ValueError("invalid Design child resource proof parameters")
    allowed = quasipoly_constant * (log2(max(2, root)) ** quasipoly_power)
    if len(children) != expected:
        return DesignFullStringChildResourceProof(
            "incomplete_design_full_string_child_execution", expected,
            len(children), (), 0.0, allowed, 0, False,
            "the complete surviving tuple cover was not executed",
        )
    bounds = []
    nodes = 0
    for child in children:
        if not child.exact or not child.local_cost_certified:
            return DesignFullStringChildResourceProof(
                "uncertified_design_full_string_child", expected, len(bounds),
                tuple(bounds), 0.0, allowed, nodes, False,
                "an executed full-string child lacks exact cost-certified proof evidence",
            )
        validation = validate_quasipoly_recurrence_tree_v4(
            child.accounting,
            quasipoly_power=quasipoly_power,
            quasipoly_constant=quasipoly_constant,
        )
        if not validation.certified:
            return DesignFullStringChildResourceProof(
                validation.status, expected, len(bounds), tuple(bounds),
                validation.log2_work_bound, allowed,
                nodes + validation.nodes_checked, False, validation.reason,
            )
        bounds.append(float(validation.log2_work_bound))
        nodes += int(validation.nodes_checked)
    combined = _log2_sum_exp(bounds)
    certified = combined <= allowed + 1e-9
    return DesignFullStringChildResourceProof(
        "certified_design_full_string_child_resources" if certified else "design_full_string_child_budget_exceeded",
        expected, len(children), tuple(bounds), combined, allowed, nodes,
        certified,
        "every executed child is linked once to a valid recurrence proof and their complete branch sum fits the original-root envelope"
        if certified else
        "the executed children are individually certified but their complete branch sum exceeds the original-root envelope",
    )


__all__ = ["DesignFullStringChildResourceProof", "certify_design_full_string_child_resources"]
