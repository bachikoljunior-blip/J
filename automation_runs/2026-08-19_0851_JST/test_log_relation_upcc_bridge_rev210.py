from itertools import combinations

from permutation_group_schreier import identity, schreier_stabilizer_chain
from signed_johnson_log_certificate_upcc_si_v2 import _exact_upcc_from_relation


def cycle_relation(v):
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    coords = tuple(combinations(range(v), 2))
    return tuple(int(S in edges) for S in coords)


def cyclic_group(v):
    cycle = tuple((i + 1) % v for i in range(v))
    return cycle, schreier_stabilizer_chain([cycle])


def lifted(group):
    return tuple((g, False) for g in group.original_generators)


def test_existing_upcc_solver_closes_exact_homogeneous_log_relation_child():
    v, t = 5, 2
    relation = cycle_relation(v)
    _cycle, group = cyclic_group(v)
    source = tuple(range(v))
    got = _exact_upcc_from_relation(
        group,
        lifted(group),
        v,
        t,
        relation,
        relation,
        source,
        source,
        root_n=32,
        max_tuple_states=100,
        max_twl_rounds=16,
        max_twl_work_units=1_000_000,
        max_partition_pair_branches=100,
        max_partition_states=100,
        max_candidate_group_order=16,
    )
    assert got.exact and got.complete, got
    assert got.status == "exact_upcc_subconstituent_full_string_coset", got
    assert got.full_string_result is not None and got.full_string_result.coset is not None
    assert got.full_string_result.coset.subgroup.order == 1
    assert got.full_string_result.coset.contains(identity(v))


def test_upcc_crosscut_preserves_fail_closed_materialization_cap():
    v, t = 5, 2
    relation = cycle_relation(v)
    _cycle, group = cyclic_group(v)
    source = tuple(0 for _ in range(v))
    got = _exact_upcc_from_relation(
        group,
        lifted(group),
        v,
        t,
        relation,
        relation,
        source,
        source,
        root_n=32,
        max_tuple_states=100,
        max_twl_rounds=16,
        max_twl_work_units=1_000_000,
        max_partition_pair_branches=10,
        max_partition_states=100,
        max_candidate_group_order=16,
    )
    assert got.status == "undetermined_upcc_partition_pair_limit", got
    assert not got.exact and not got.complete
