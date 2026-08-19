from __future__ import annotations

from dataclasses import dataclass
from math import lgamma, log, log2


PHASE_CLIQUE = 0
PHASE_UPCC = 1
PHASE_JOHNSON = 2


@dataclass(frozen=True)
class StructuralAccountingChild:
    node: "StructuralRecurrenceAccountingNode"
    multiplicity: int = 1


@dataclass(frozen=True)
class StructuralRecurrenceAccountingNode:
    n: int
    m: int
    structural_phase: int
    operation_kind: str
    canonical: bool
    cost_certified: bool
    progress_certified: bool
    local_log2_cost_bound: float
    children: tuple[StructuralAccountingChild, ...] = ()
    terminal_certified: bool = False
    reason: str = ""


@dataclass(frozen=True)
class StructuralQuasipolyValidation:
    status: str
    certified: bool
    log2_work_bound: float
    allowed_log2_work: float
    nodes_checked: int
    max_depth: int
    structural_upgrades_checked: int
    reason: str


def _log2_sum_exp(values):
    values = tuple(values)
    if not values:
        return 0.0
    top = max(values)
    return top + log2(sum(2.0 ** (value - top) for value in values))


def _log2_factorial(k: int) -> float:
    if k < 0:
        raise ValueError("factorial input must be nonnegative")
    return lgamma(k + 1) / log(2.0)


def validate_structural_quasipoly_recurrence_tree(
    root: StructuralRecurrenceAccountingNode,
    *,
    shrink_fraction: float = 0.9,
    polylog_power: int = 2,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> StructuralQuasipolyValidation:
    """Validate numeric shrink plus separately certified finite structural progress.

    The original recurrence checker only accepts constant-factor auxiliary shrink
    and small-auxiliary reset.  Some Split-or-Johnson implementations also expose
    structural transformations that do not immediately decrease the numeric
    auxiliary size.  This validator can account for such a transformation only
    when the caller has *independently* certified that exact algorithmic step and
    marks ``progress_certified=True``.  The phase integer is merely a well-founded
    accounting rank; it is not itself a proof that a clique->UPCC or UPCC->Johnson
    transformation exists for a given instance.

    A ``structural_upgrade`` edge must preserve or reduce m and strictly increase
    the finite phase rank. Numeric-shrink/reset edges may restart the phase on a
    genuinely smaller instance. Every nonterminal node also needs canonicality,
    a certified local multiplicative cost, and an independently certified progress
    step. Branch multiplicities are composed by log-sum-exp and the complete tree
    must remain inside the configured quasipolynomial envelope.

    This validator accepts proof evidence; it never manufactures a missing
    Split-or-Johnson step, recursive child, or cost certificate.
    """
    if not 0.0 < shrink_fraction < 1.0:
        raise ValueError("shrink_fraction must be in (0,1)")
    if polylog_power < 1 or quasipoly_power < 1 or quasipoly_constant <= 0:
        raise ValueError("invalid quasipolynomial parameters")
    if root.n <= 0 or root.m <= 0 or root.m > root.n:
        return StructuralQuasipolyValidation(
            "invalid_root_measure", False, 0.0, 0.0, 0, 0, 0,
            "root requires 1 <= m <= n",
        )

    root_n = root.n
    allowed = quasipoly_constant * (log2(max(2, root_n)) ** quasipoly_power)
    active = set()
    nodes_checked = 0
    max_depth = 0
    upgrades = 0

    class Invalid(Exception):
        def __init__(self, status, reason):
            self.status = status
            self.reason = reason

    def rec(node, depth):
        nonlocal nodes_checked, max_depth, upgrades
        oid = id(node)
        if oid in active:
            raise Invalid("cyclic_structural_accounting_trace", "recurrence accounting graph must be acyclic")
        active.add(oid)
        nodes_checked += 1
        max_depth = max(max_depth, depth)

        if node.n <= 0 or node.m <= 0 or node.m > node.n:
            raise Invalid("invalid_measure", "every node requires 1 <= m <= n")
        if node.structural_phase not in {PHASE_CLIQUE, PHASE_UPCC, PHASE_JOHNSON}:
            raise Invalid("invalid_structural_phase", "structural phase must be clique, UPCC, or Johnson")
        if not node.canonical:
            raise Invalid("noncanonical_accounting_step", "every accounted step must be label-invariant")
        if not node.cost_certified:
            raise Invalid("uncertified_local_cost", "every accounted node needs a mechanical local cost certificate")
        if node.local_log2_cost_bound < 0:
            raise Invalid("invalid_local_cost", "local log2 cost must be nonnegative")

        if not node.children:
            if not node.terminal_certified:
                raise Invalid("uncertified_terminal", "leaf lacks an exact/certified terminal condition")
            active.remove(oid)
            return float(node.local_log2_cost_bound)
        if node.terminal_certified:
            raise Invalid("terminal_with_children", "a certified terminal may not also recurse")
        if not node.progress_certified:
            raise Invalid(
                "uncertified_progress_step",
                "a nonterminal recurrence node must carry an independent proof of the algorithmic progress step",
            )

        threshold = max(1.0, log2(max(2, node.n)) ** polylog_power)
        terms = []
        for edge in node.children:
            if edge.multiplicity <= 0:
                raise Invalid("invalid_branch_multiplicity", "child multiplicities must be positive")
            child = edge.node
            if child.n > node.n or child.m > child.n:
                raise Invalid("measure_increase", "recurrence may not increase n and always requires m<=n")

            if node.operation_kind == "aux_shrink":
                if child.m > shrink_fraction * node.m + 1e-12:
                    raise Invalid("insufficient_auxiliary_shrink", "aux_shrink must reduce m by the configured constant fraction")
            elif node.operation_kind == "structural_upgrade":
                if child.m > node.m:
                    raise Invalid("structural_upgrade_measure_increase", "structural upgrade may not increase the auxiliary domain")
                if child.structural_phase <= node.structural_phase:
                    raise Invalid("nonprogressing_structural_upgrade", "structural upgrade must strictly increase the finite phase rank")
                upgrades += 1
            elif node.operation_kind == "small_aux_reset":
                if node.m > threshold + 1e-12:
                    raise Invalid("premature_auxiliary_enumeration", "small_aux_reset is allowed only once m is polylogarithmic in n")
                if child.n > shrink_fraction * node.n + 1e-12:
                    raise Invalid("insufficient_primary_shrink", "small_aux_reset must significantly reduce n")
                if node.local_log2_cost_bound + 1e-12 < _log2_factorial(node.m):
                    raise Invalid("undercharged_auxiliary_enumeration", "declared cost does not cover enumeration of S_m")
            else:
                raise Invalid("unknown_progress_kind", "nonterminal operation must be aux_shrink, structural_upgrade, or small_aux_reset")

            sub = rec(child, depth + 1)
            terms.append(log2(edge.multiplicity) + sub)

        total = float(node.local_log2_cost_bound) + _log2_sum_exp(terms)
        active.remove(oid)
        return total

    try:
        work = rec(root, 0)
    except Invalid as exc:
        return StructuralQuasipolyValidation(
            exc.status, False, 0.0, allowed, nodes_checked, max_depth, upgrades, exc.reason
        )

    if work > allowed + 1e-9:
        return StructuralQuasipolyValidation(
            "quasipolynomial_bound_exceeded", False, work, allowed,
            nodes_checked, max_depth, upgrades,
            "certified local bounds compose above the configured quasipolynomial envelope",
        )
    return StructuralQuasipolyValidation(
        "certified_structural_quasipolynomial_recurrence", True, work, allowed,
        nodes_checked, max_depth, upgrades,
        "all paths use independently certified constant-factor shrink, finite structural-rank progress, or certified small-auxiliary reset and the complete branching tree fits the quasipolynomial envelope",
    )
