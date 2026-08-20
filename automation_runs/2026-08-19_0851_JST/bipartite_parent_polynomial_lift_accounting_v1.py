from __future__ import annotations

from dataclasses import dataclass
from math import log2

from bipartite_design_parent_union_v1 import solve_design_witness_cover_in_parent_bipartite_action
from bipartite_design_recurrence_gate_v1 import certify_complete_design_cover_recurrence_progress
from coset_stabilizer_primitives import RightCoset
from proof_dag_accounting_v1 import validate_execution_proof_dag
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


@dataclass(frozen=True)
class PolynomialLiftBranchCertificate:
    branch_index: int
    auxiliary_degree: int
    polynomial_degree_gate: bool
    image_status: str
    exact: bool
    accounting_certified: bool
    image_log2_work_bound: float
    translated_log2_work_bound: float
    reason: str
    proof_dag_status: str = "not_checked"
    proof_dag_unique_nodes: int = 0
    proof_dag_execution_occurrences: int = 0
    proof_dag_reused_occurrences: int = 0


@dataclass(frozen=True)
class BipartiteParentPolynomialLiftCertificate:
    status: str
    parent_degree: int
    root_n: int
    right_size: int
    auxiliary_degree_bound: int
    structural_branches: int
    exact_branches: int
    branch_certificates: tuple[PolynomialLiftBranchCertificate, ...]
    structural_log2_cost_bound: float
    union_log2_bookkeeping_bound: float
    wrapper_log2_cost_bound: float
    total_log2_work_bound: float
    allowed_log2_work: float
    polynomial_auxiliary_gate: bool
    exact_parent_union: bool
    certified: bool
    reason: str


def _log2_sum_exp(values):
    values = tuple(float(x) for x in values)
    if not values:
        return 0.0
    top = max(values)
    return top + log2(sum(2.0 ** (x - top) for x in values))


def _candidate_cover_cosets(cover):
    if cover.status == "certified_ambient_design_witness_coset_cover":
        return tuple(branch.coset for branch in cover.branches)
    if cover.status == "certified_unary_ambient_partition_coset":
        transport = cover.unary_transport
        if transport is None or transport.transporter is None or transport.source_stabilizer is None:
            return ()
        return (RightCoset(transport.source_stabilizer, transport.transporter),)
    return ()


def solve_and_certify_design_parent_polynomial_lift(
    parent_group,
    right_image_generators,
    left_points,
    right_points,
    source_edges,
    target_edges,
    *,
    source_left_colors=None,
    target_left_colors=None,
    source_right_colors=None,
    target_right_colors=None,
    root_n=None,
    alpha=0.75,
    max_subsets=200000,
    max_states=200000,
    max_tuple_states=250000,
    max_twl_rounds=None,
    max_twl_work_units=500000000,
    max_branch_pairs=200000,
    max_partition_states=200000,
    max_auxiliary_degree=200000,
    max_image_group_order=256,
    quasipoly_power=5,
    translated_constant=32768.0,
):
    """Certify rev206 exact parent unions through a polynomial auxiliary lift.

    The key H6-C1 observation is that the coupled full-string auxiliary domain is
    not an uncontrolled new recurrence parameter.  Because the left and right
    parts are disjoint subsets of the parent permutation domain,

        M = |L| + |R| + |L||R| <= n + n^2 <= root_n + root_n^2.

    Therefore an already-certified quasipolynomial SI proof on M is still
    quasipolynomial in the original root measure.  This routine consumes the
    exact execution-linked rev206 image proof captured for every complete
    structural branch, validates each proof tree with the existing recurrence
    verifier, charges
    actual branch multiplicity plus the rev206 Design gate and union bookkeeping,
    and checks the composed numeric envelope against a fixed polylogarithmic bound.

    This closes complexity accounting only for rev206 instances whose candidate SI
    branches are already exact proof-carrying solves.  It does not convert an
    unresolved candidate-SI branch into progress and does not claim global H6 or AGI.
    """
    n = int(parent_group.degree)
    root = max(n, int(root_n or n))
    if root < 2:
        root = 2
    if quasipoly_power < 1 or translated_constant <= 0:
        raise ValueError("invalid quasipolynomial envelope")

    union = solve_design_witness_cover_in_parent_bipartite_action(
        parent_group,
        tuple(right_image_generators),
        tuple(left_points),
        tuple(right_points),
        tuple(source_edges),
        tuple(target_edges),
        source_left_colors=source_left_colors,
        target_left_colors=target_left_colors,
        source_right_colors=source_right_colors,
        target_right_colors=target_right_colors,
        root_n=root,
        alpha=alpha,
        max_subsets=max_subsets,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_twl_rounds=max_twl_rounds,
        max_twl_work_units=max_twl_work_units,
        max_branch_pairs=max_branch_pairs,
        max_partition_states=max_partition_states,
        max_auxiliary_degree=max_auxiliary_degree,
        max_image_group_order=max_image_group_order,
    )
    right_size = int(union.ambient_cover.wiring.relation_twin.source.relation.right_size)
    allowed = float(translated_constant) * (log2(max(2, root)) ** int(quasipoly_power))
    aux_bound = root + root * root

    if not union.exact or not union.complete or not union.set_reconstruction_complete:
        return union, BipartiteParentPolynomialLiftCertificate(
            "undetermined_parent_union_not_exact", n, root, right_size, aux_bound,
            union.structural_branches, 0, (), 0.0,
            float(union.explicit_union_log2_bookkeeping_bound), 0.0, 0.0, allowed,
            False, False, False,
            "polynomial-lift accounting requires the complete exact rev206 parent union; unresolved image SI remains a real child",
        )

    gate = certify_complete_design_cover_recurrence_progress(
        union.ambient_cover,
        root_n=root,
        alpha=alpha,
        max_tuple_states=max_tuple_states,
        max_twl_rounds=max_twl_rounds,
        max_twl_work_units=max_twl_work_units,
    )
    if not gate.local_cost_certified:
        return union, BipartiteParentPolynomialLiftCertificate(
            "undetermined_structural_cost_not_certified", n, root, right_size, aux_bound,
            union.structural_branches, 0, (), 0.0,
            float(union.explicit_union_log2_bookkeeping_bound), 0.0, 0.0, allowed,
            False, True, False,
            "the exact parent union exists but its structural Design stage lacks a mechanical local-cost certificate",
        )

    candidates = _candidate_cover_cosets(union.ambient_cover)
    if union.exact_empty and not candidates:
        total = float(gate.local_log2_cost_bound) + float(union.explicit_union_log2_bookkeeping_bound)
        certified = total <= allowed + 1e-9
        return union, BipartiteParentPolynomialLiftCertificate(
            "certified_exact_empty_parent_polynomial_lift" if certified else "quasipolynomial_envelope_exceeded",
            n, root, right_size, aux_bound, union.structural_branches, 0, (),
            float(gate.local_log2_cost_bound), float(union.explicit_union_log2_bookkeeping_bound),
            0.0, total, allowed, True, True, certified,
            "the complete structural cover is exact empty; only certified structural and union bookkeeping costs remain" if certified else
            "the exact-empty proof exceeded the configured translated quasipolynomial envelope",
        )

    if len(candidates) != len(union.branch_results):
        return union, BipartiteParentPolynomialLiftCertificate(
            "undetermined_candidate_branch_trace_mismatch", n, root, right_size, aux_bound,
            union.structural_branches, 0, (), float(gate.local_log2_cost_bound),
            float(union.explicit_union_log2_bookkeeping_bound), 0.0, 0.0, allowed,
            False, True, False,
            "complete rev206 branch results could not be paired one-for-one with the materialized structural candidate cover",
        )

    records = []
    branch_terms = []
    polynomial_gate = True
    exact_count = 0
    for i, (candidate, solved) in enumerate(zip(candidates, union.branch_results)):
        # rev218 captures the exact proof object produced by the rev206 execution.
        # Re-running the candidate solver here used to duplicate real work while
        # composing only one proof-tree charge.  Accounting now consumes the
        # execution-linked immutable proof directly; missing capture fails closed.
        proof = solved.image_candidate_proof
        m = int(solved.auxiliary_degree)
        status = None if proof is None else proof.status
        poly = bool(m and m <= aux_bound)
        polynomial_gate = polynomial_gate and poly
        if proof is None or not proof.exact or not solved.exact or status != solved.image_candidate_status:
            records.append(PolynomialLiftBranchCertificate(
                i, int(m), poly, status, False, False, 0.0, 0.0,
                "the execution-linked candidate image proof is absent or does not match the exact rev206 branch status",
            ))
            continue
        validation = validate_execution_proof_dag(
            proof,
            original_root_n=root,
            polynomial_lift_degree=m,
            quasipoly_power=quasipoly_power,
            quasipoly_constant=translated_constant,
        )
        accounting_ok = bool(validation.certified)
        # The validator's actual composed log-work is already an execution-linked
        # proof-tree bound.  Translation to the parent measure changes only the
        # polynomial variable because M <= root + root^2.
        translated = float(validation.log2_work_bound) if accounting_ok and poly else 0.0
        if accounting_ok and poly:
            branch_terms.append(translated)
            exact_count += 1
        records.append(PolynomialLiftBranchCertificate(
            i, int(m), poly, status, True, accounting_ok,
            float(validation.log2_work_bound), translated,
            "exact candidate-SI accounting tree validates and its auxiliary degree is polynomially bounded by the original parent root" if accounting_ok and poly else
            "candidate-SI exactness or polynomial-lift accounting validation failed closed",
            validation.status,
            validation.unique_nodes,
            validation.execution_occurrences,
            validation.reused_occurrences,
        ))

    all_branches = exact_count == len(candidates)
    # Paired Schreier preimage, auxiliary encoding, exact lift-back and union
    # reconstruction are polynomial wrappers.  Charge a deliberately loose fixed
    # degree envelope plus actual branch multiplicity.  This is separate from the
    # recursive candidate-SI proof trees and cannot hide a failed child.
    max_m = max((r.auxiliary_degree for r in records), default=1)
    wrapper = 24.0 * log2(max(2, max_m)) + 8.0 * log2(max(2, len(candidates))) + 64.0
    recursive = _log2_sum_exp(branch_terms) if branch_terms else 0.0
    total = (
        float(gate.local_log2_cost_bound)
        + float(union.explicit_union_log2_bookkeeping_bound)
        + wrapper
        + recursive
    )
    certified = bool(all_branches and polynomial_gate and total <= allowed + 1e-9)
    if certified:
        status = "certified_exact_parent_polynomial_auxiliary_lift"
        reason = (
            "every complete rev206 branch carries the exact proof produced by its candidate SI execution; each coupled auxiliary degree is bounded by root+root^2, and structural, branch, wrapper, and union costs compose inside the translated quasipolynomial envelope"
        )
    elif not all_branches:
        status = "undetermined_uncertified_candidate_image_accounting"
        reason = "at least one exact rev206 branch lacks a validating proof-carrying candidate-SI accounting tree"
    elif not polynomial_gate:
        status = "undetermined_nonpolynomial_auxiliary_lift"
        reason = "at least one coupled auxiliary degree exceeds the mechanically checked root+root^2 lift bound"
    else:
        status = "quasipolynomial_envelope_exceeded"
        reason = "all child proofs are exact, but their composed translated bound exceeds the configured quasipolynomial envelope"

    return union, BipartiteParentPolynomialLiftCertificate(
        status, n, root, right_size, aux_bound, len(candidates), exact_count,
        tuple(records), float(gate.local_log2_cost_bound),
        float(union.explicit_union_log2_bookkeeping_bound), wrapper, total, allowed,
        polynomial_gate, True, certified, reason,
    )
