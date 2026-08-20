from itertools import combinations

from design_full_execution_accounting_v1 import certify_exact_design_full_execution_accounting
from design_lemma_candidate_si_v1 import design_lemma_candidate_string_isomorphism
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3


def _fano_relation():
    v, t = 7, 3
    coords = tuple(combinations(range(v), t))
    lines = {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }
    return v, t, tuple(int(S in lines) for S in coords)


def _cyclic_group(v):
    cycle = tuple((i + 1) % v for i in range(v))
    return cycle, schreier_stabilizer_chain([cycle])


def _solve_fano(full_string):
    v, t, relation = _fano_relation()
    cycle, group = _cyclic_group(v)
    design = design_lemma_candidate_string_isomorphism(
        group,
        ((cycle, False),),
        v,
        t,
        relation,
        relation,
        tuple(full_string),
        tuple(full_string),
        root_n=v,
        max_wl_rounds=64,
        max_partition_states=32,
        max_group_order=8,
    )
    assert design.exact and design.complete and design.theorem_hypotheses_certified
    return design


def test_rev212_certifies_constant_string_fano_full_execution_and_child_recurrences():
    design = _solve_fano([0] * 7)
    cert = certify_exact_design_full_execution_accounting(
        design,
        root_n=7,
        prefix_log2_cost_bound=12.0,
    )
    assert cert.certified, cert.reason
    assert cert.status == "certified_design_full_execution_accounting"
    assert cert.branch_cost.certified
    assert len(cert.child_validations) == len(design.full_string_result.branch_results)
    assert all(check.certified for check in cert.child_validations)
    assert cert.total_log2_work_bound <= cert.allowed_log2_work
    assert validate_quasipoly_recurrence_tree_v3(cert.accounting).certified


def test_rev212_certifies_distinct_string_fano_full_execution_without_hiding_branch_cost():
    design = _solve_fano(range(7))
    assert design.full_string_result is not None
    assert design.full_string_result.coset is not None
    assert design.full_string_result.coset.subgroup.order == 1

    cert = certify_exact_design_full_execution_accounting(design, root_n=7)
    assert cert.certified, cert.reason
    assert cert.branch_count == design.branch_plan.branch_count
    assert cert.branch_cost.branch_log2_bound >= 0.0
    assert cert.child_union_log2_work_bound >= 0.0
    assert cert.total_log2_work_bound >= cert.design_log2_cost_bound


def test_rev212_fails_closed_when_same_exact_execution_is_forced_outside_configured_envelope():
    design = _solve_fano(range(7))
    cert = certify_exact_design_full_execution_accounting(
        design,
        root_n=7,
        quasipoly_constant=0.01,
    )
    assert not cert.certified
    assert cert.status == "undetermined_design_execution_quasipoly_envelope"
    assert not cert.accounting.cost_certified
    assert not cert.accounting.terminal_certified
