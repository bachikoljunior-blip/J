from __future__ import annotations

from dataclasses import dataclass
from math import log2

from coset_stabilizer_primitives import RightCoset
from design_branch_tuple_transport_v1 import DesignTupleTransportPlan
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


@dataclass(frozen=True)
class DesignBranchStringUnionProof(ProofCarryingCoset):
    input_branch_count: int = 0
    exact_branch_count: int = 0
    nonempty_branch_count: int = 0
    reconstructed_stabilizer_order: int = 0
    complete_branch_cover: bool = False


def _log2_sum_exp(values):
    values = tuple(float(x) for x in values)
    if not values:
        return 0.0
    top = max(values)
    return top + log2(sum(2.0 ** (x - top) for x in values))


def _maps_string(source, target, permutation):
    return all(source[i] == target[permutation[i]] for i in range(len(source)))


def _stabilizes_string(values, permutation):
    return all(values[i] == values[permutation[i]] for i in range(len(values)))


def _proof(
    status,
    coset,
    *,
    root_n,
    degree,
    exact,
    cost_certified,
    local_bound,
    children,
    checked,
    reason,
    input_branches,
    exact_branches,
    nonempty_branches,
    stabilizer_order=0,
    complete=False,
):
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, degree),
        operation_kind=(
            "design_branch_union_terminal"
            if exact and cost_certified
            else "unresolved_design_branch_union"
        ),
        canonical=True,
        cost_certified=bool(cost_certified),
        local_log2_cost_bound=float(local_bound) if cost_certified else 0.0,
        children=(),
        terminal_certified=bool(exact and cost_certified),
        reason=reason,
    )
    return DesignBranchStringUnionProof(
        status,
        coset,
        accounting.operation_kind,
        root_n,
        degree,
        True,
        bool(exact),
        bool(cost_certified),
        accounting.local_log2_cost_bound,
        accounting.terminal_certified,
        tuple(children),
        accounting,
        int(checked),
        reason,
        input_branch_count=int(input_branches),
        exact_branch_count=int(exact_branches),
        nonempty_branch_count=int(nonempty_branches),
        reconstructed_stabilizer_order=int(stabilizer_order),
        complete_branch_cover=bool(complete),
    )


def solve_complete_design_tuple_string_isomorphism(
    group,
    source_values,
    target_values,
    transport_plan: DesignTupleTransportPlan,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_depth: int = 64,
) -> DesignBranchStringUnionProof:
    """Solve every exact Design-Lemma tuple branch and reconstruct the full SI coset.

    The input cover is complete: every ambient string isomorphism lies in at least
    one tuple-transporter branch. Each branch is intersected with the full source/
    target strings by the existing proof-carrying candidate-coset SI solver.

    For nonempty exact branch cosets C_i = r_i H_i, choose a witness r. Every
    generator of H_i and every normalized representative difference r_i r^-1
    stabilizes the target string. Conversely, completeness says every target
    automorphism occurs in one normalized branch. Therefore these elements
    generate the entire target-string stabilizer, and its right coset at r is the
    exact full string-isomorphism set. Any unresolved branch, invalid containment,
    or uncertified child accounting withholds the whole answer fail-closed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate the ambient degree")
    if int(transport_plan.original_degree) != n:
        raise ValueError("tuple transport plan has a different original degree")
    if int(transport_plan.surviving_branch_count) != len(transport_plan.branches):
        raise ValueError("tuple transport plan branch count is inconsistent")

    input_count = int(transport_plan.input_branch_count)
    base_bound = float(transport_plan.local_log2_cost_bound)

    if transport_plan.exact_empty:
        return _proof(
            "exact_empty_design_tuple_string_isomorphism",
            None,
            root_n=root_n,
            degree=n,
            exact=True,
            cost_certified=True,
            local_bound=base_bound + 8.0 * log2(max(2, n)) + 16.0,
            children=(),
            checked=0,
            reason=(
                "the upstream complete tuple-transporter cover is exactly empty, "
                "so the ambient full-string isomorphism set is empty"
            ),
            input_branches=input_count,
            exact_branches=0,
            nonempty_branches=0,
            complete=True,
        )

    if (
        not transport_plan.complete
        or transport_plan.status != "certified_complete_design_tuple_transport_cover"
    ):
        return _proof(
            "undetermined_incomplete_design_tuple_transport_cover",
            None,
            root_n=root_n,
            degree=n,
            exact=False,
            cost_certified=False,
            local_bound=0.0,
            children=(),
            checked=0,
            reason=(
                "full string union reconstruction requires a certified complete "
                "upstream tuple-transporter cover"
            ),
            input_branches=input_count,
            exact_branches=0,
            nonempty_branches=0,
            complete=False,
        )

    children = []
    child_work_bounds = []
    nonempty = []
    checked = 0
    for branch in transport_plan.branches:
        if branch.coset is None:
            return _proof(
                "undetermined_missing_design_tuple_candidate_coset",
                None,
                root_n=root_n,
                degree=n,
                exact=False,
                cost_certified=False,
                local_bound=0.0,
                children=tuple(children),
                checked=checked,
                reason="a surviving complete-cover branch lacks its exact candidate coset",
                input_branches=input_count,
                exact_branches=len(children),
                nonempty_branches=len(nonempty),
                complete=False,
            )
        child = candidate_coset_string_isomorphism_u2(
            branch.coset,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=candidate_group_order_poly_power,
            max_group_order=max_candidate_group_order,
            max_depth=max_depth,
        )
        children.append(child)
        checked += int(child.permutation_candidates_checked)
        if not child.exact:
            return _proof(
                "undetermined_design_tuple_string_branch",
                None,
                root_n=root_n,
                degree=n,
                exact=False,
                cost_certified=False,
                local_bound=0.0,
                children=tuple(children),
                checked=checked,
                reason=(
                    "at least one branch in the complete tuple cover remains "
                    "unresolved; a partial union is never exposed"
                ),
                input_branches=input_count,
                exact_branches=len(children) - 1,
                nonempty_branches=len(nonempty),
                complete=False,
            )
        accounting_check = validate_quasipoly_recurrence_tree_v3(child.accounting)
        if not accounting_check.certified:
            return _proof(
                "undetermined_design_tuple_branch_accounting",
                None,
                root_n=root_n,
                degree=n,
                exact=False,
                cost_certified=False,
                local_bound=0.0,
                children=tuple(children),
                checked=checked,
                reason=(
                    "an exact tuple branch lacks a certified quasipolynomial "
                    "proof-tree bound; the full result is withheld"
                ),
                input_branches=input_count,
                exact_branches=len(children),
                nonempty_branches=len(nonempty),
                complete=False,
            )
        child_work_bounds.append(float(accounting_check.log2_work_bound))
        if child.coset is not None:
            nonempty.append(child.coset)

    reconstruction_bound = (
        base_bound
        + _log2_sum_exp(child_work_bounds)
        + log2(max(1, len(children)))
        + 10.0 * log2(max(2, n + len(nonempty)))
        + 32.0
    )

    if not nonempty:
        return _proof(
            "exact_empty_complete_design_tuple_string_union",
            None,
            root_n=root_n,
            degree=n,
            exact=True,
            cost_certified=True,
            local_bound=reconstruction_bound,
            children=tuple(children),
            checked=checked,
            reason=(
                "every branch of the complete tuple-transporter cover has an "
                "exact empty full-string intersection"
            ),
            input_branches=input_count,
            exact_branches=len(children),
            nonempty_branches=0,
            complete=True,
        )

    witness = min(c.representative for c in nonempty)
    if not _maps_string(source, target, witness):
        raise AssertionError("a nonempty exact branch representative does not map the strings")

    stabilizer_generators = []
    for child_coset in nonempty:
        difference = compose(inverse(witness), child_coset.representative)
        if not group.contains(difference) or not _stabilizes_string(target, difference):
            raise AssertionError(
                "normalized branch representative difference is not a target automorphism"
            )
        stabilizer_generators.append(difference)
        for generator in child_coset.subgroup.original_generators:
            if not group.contains(generator) or not _stabilizes_string(target, generator):
                raise AssertionError(
                    "an exact branch subgroup generator is not an ambient target automorphism"
                )
            stabilizer_generators.append(generator)

    target_stabilizer = schreier_stabilizer_chain(
        stabilizer_generators or (identity(n),)
    )
    result = RightCoset(target_stabilizer, witness)

    for child_coset in nonempty:
        if not result.contains(child_coset.representative):
            raise AssertionError("reconstructed full coset lost a nonempty branch witness")
        if any(
            not target_stabilizer.contains(generator)
            for generator in child_coset.subgroup.original_generators
        ):
            raise AssertionError("reconstructed stabilizer lost a branch subgroup")

    return _proof(
        "exact_complete_design_tuple_string_union_coset",
        result,
        root_n=root_n,
        degree=n,
        exact=True,
        cost_certified=True,
        local_bound=reconstruction_bound,
        children=tuple(children),
        checked=checked,
        reason=(
            "all branches in the complete Design-Lemma tuple cover were solved "
            "exactly; normalized branch representatives and branch stabilizers "
            "generate exactly the full target-string stabilizer"
        ),
        input_branches=input_count,
        exact_branches=len(children),
        nonempty_branches=len(nonempty),
        stabilizer_order=target_stabilizer.order,
        complete=True,
    )
