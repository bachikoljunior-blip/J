from itertools import combinations

from permutation_group_schreier import schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from upcc_full_string_quasipoly_accounting_v2 import certify_upcc_full_string_execution_accounting
from upcc_subconstituent_full_string_si_v1 import upcc_subconstituent_full_string_isomorphism


def cycle_relation(v):
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    return tuple(int(S in edges) for S in combinations(range(v), 2))


def cyclic_group(v):
    cycle = tuple((i + 1) % v for i in range(v))
    return schreier_stabilizer_chain([cycle])


def lifted(group):
    return tuple((g, False) for g in group.original_generators)


def solve_cycle5(source, *, branch_cap=100):
    v = 5
    group = cyclic_group(v)
    relation = cycle_relation(v)
    return upcc_subconstituent_full_string_isomorphism(
        group,
        lifted(group),
        v,
        2,
        relation,
        relation,
        source,
        source,
        root_n=32,
        max_tuple_states=100,
        max_twl_rounds=16,
        max_twl_work_units=1_000_000,
        max_partition_pair_branches=branch_cap,
        max_partition_states=100,
        max_group_order=16,
    )


def test_completed_upcc_branch_proofs_compose_to_certified_terminal():
    got = solve_cycle5(tuple(range(5)))
    assert got.exact and got.complete and got.full_string_result is not None
    cert = certify_upcc_full_string_execution_accounting(got, root_n=32)
    assert cert.certified, cert
    assert cert.certified_branch_proofs == cert.branches_checked
    assert cert.total_log2_work_bound <= cert.allowed_log2_work
    replay = validate_quasipoly_recurrence_tree_v3(cert.accounting)
    assert replay.certified, replay


def test_incomplete_upcc_execution_never_becomes_accounted_terminal():
    got = solve_cycle5(tuple(0 for _ in range(5)), branch_cap=10)
    assert not got.exact and not got.complete
    cert = certify_upcc_full_string_execution_accounting(got, root_n=32)
    assert not cert.certified
    replay = validate_quasipoly_recurrence_tree_v3(cert.accounting)
    assert not replay.certified
