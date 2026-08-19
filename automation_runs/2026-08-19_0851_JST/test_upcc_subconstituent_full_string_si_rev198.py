from itertools import combinations

from permutation_group_schreier import identity, schreier_stabilizer_chain
from upcc_subconstituent_full_string_si_v1 import upcc_subconstituent_full_string_isomorphism


def _cycle_relation(v):
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    coords = tuple(combinations(range(v), 2))
    return tuple(int(S in edges) for S in coords)


def _cyclic_group(v):
    cycle = tuple((i + 1) % v for i in range(v))
    return cycle, schreier_stabilizer_chain([cycle])


def _lifted(group):
    return tuple((g, False) for g in group.original_generators)


def test_cycle5_complete_subconstituent_cover_recovers_constant_string_cyclic_coset():
    v, k = 5, 2
    relation = _cycle_relation(v)
    cycle, group = _cyclic_group(v)
    source = tuple(0 for _ in range(v))
    got = upcc_subconstituent_full_string_isomorphism(
        group,
        _lifted(group),
        v,
        k,
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
        max_group_order=16,
    )
    assert got.status == "exact_upcc_subconstituent_full_string_coset"
    assert got.exact and got.complete
    assert got.partition_pair_count == 50
    assert got.full_string_result is not None and got.full_string_result.coset is not None
    assert got.full_string_result.coset.subgroup.order == group.order == v
    assert got.full_string_result.coset.contains(identity(v))
    assert got.full_string_result.coset.contains(cycle)


def test_cycle5_complete_subconstituent_cover_filters_distinct_string_to_identity():
    v, k = 5, 2
    relation = _cycle_relation(v)
    _cycle, group = _cyclic_group(v)
    source = tuple(range(v))
    got = upcc_subconstituent_full_string_isomorphism(
        group,
        _lifted(group),
        v,
        k,
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
        max_group_order=16,
    )
    assert got.status == "exact_upcc_subconstituent_full_string_coset"
    assert got.full_string_result is not None and got.full_string_result.coset is not None
    assert got.full_string_result.coset.subgroup.order == 1
    assert got.full_string_result.coset.contains(identity(v))


def test_partition_pair_materialization_cap_fails_closed_before_partial_cover():
    v, k = 5, 2
    relation = _cycle_relation(v)
    _cycle, group = _cyclic_group(v)
    source = tuple(0 for _ in range(v))
    got = upcc_subconstituent_full_string_isomorphism(
        group,
        _lifted(group),
        v,
        k,
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
        max_group_order=16,
    )
    assert got.status == "undetermined_upcc_partition_pair_limit"
    assert not got.exact and not got.complete
    assert got.transport_plan is None and got.full_string_result is None
