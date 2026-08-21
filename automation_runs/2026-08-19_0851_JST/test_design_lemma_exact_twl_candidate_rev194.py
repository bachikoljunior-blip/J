from itertools import combinations

from design_lemma_exact_twl_candidate_si_v1 import exact_twl_design_candidate_string_isomorphism
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _lifted(group):
    return tuple((g, False) for g in group.original_generators)


def test_cycle11_theorem_faithful_path_composes_to_exact_full_string_coset():
    v, k = 11, 2
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    relation = tuple(int(S in edges) for S in combinations(range(v), k))
    cycle = tuple((i + 1) % v for i in range(v))
    group = schreier_stabilizer_chain([cycle])
    source = tuple(0 for _ in range(v))
    got = exact_twl_design_candidate_string_isomorphism(
        group,
        _lifted(group),
        v,
        k,
        relation,
        relation,
        source,
        source,
        root_n=64,
        max_states=100,
        max_tuple_states=1000,
        max_twl_rounds=32,
        max_twl_work_units=60_000_000,
        max_partition_states=64,
        max_group_order=16,
    )
    assert got.status == "exact_twl_design_full_string_coset"
    assert got.theorem_hypotheses_certified
    assert got.theorem_fidelity_certified
    assert got.branch_cost_certified
    assert got.exact and got.complete
    assert got.branch_plan.individualization_length == 0
    assert got.branch_plan.branch_count == 1
    assert got.full_string_result is not None and got.full_string_result.coset is not None
    assert got.full_string_result.coset.subgroup.order == 11
    assert got.full_string_result.coset.contains(identity(v))
    assert got.full_string_result.coset.contains(cycle)
    assert got.transport_resource_envelope is not None
    assert got.transport_resource_envelope.admitted
    assert got.transport_resource_envelope.complete
    assert got.transport_resource_envelope.executed_branches == 1
    assert got.transport_resource_envelope.charged_work_upper_bound > 0


def test_cycle11_distinct_string_filters_the_exact_design_cover_to_identity():
    v, k = 11, 2
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    relation = tuple(int(S in edges) for S in combinations(range(v), k))
    cycle = tuple((i + 1) % v for i in range(v))
    group = schreier_stabilizer_chain([cycle])
    source = tuple(range(v))
    got = exact_twl_design_candidate_string_isomorphism(
        group,
        _lifted(group),
        v,
        k,
        relation,
        relation,
        source,
        source,
        root_n=64,
        max_states=100,
        max_tuple_states=1000,
        max_twl_rounds=32,
        max_twl_work_units=60_000_000,
        max_partition_states=64,
        max_group_order=16,
    )
    assert got.status == "exact_twl_design_full_string_coset"
    assert got.full_string_result is not None and got.full_string_result.coset is not None
    assert got.full_string_result.coset.subgroup.order == 1
    assert got.full_string_result.coset.contains(identity(v))


def test_cycle11_upcc_branch_reuses_exact_transport_and_full_string_union():
    v, k = 11, 2
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    coords = tuple(combinations(range(v), k))
    relation = tuple(int(S in edges) for S in coords)
    cycle = tuple((i + 1) % v for i in range(v))
    group = schreier_stabilizer_chain([cycle])
    source = tuple(0 for _ in range(v))
    got = exact_twl_design_candidate_string_isomorphism(
        group,
        _lifted(group),
        v,
        k,
        relation,
        relation,
        source,
        source,
        root_n=32,
        max_tuple_states=200,
        max_twl_rounds=16,
        max_twl_work_units=2_000_000,
        max_partition_states=32,
        max_group_order=16,
    )
    assert got.status == "exact_twl_design_full_string_coset"
    assert got.branch_plan.individualization_length == 0
    assert got.branch_plan.branch_count == 1
    assert got.branch_plan.source_family.witness_outcomes[0].status == "certified_twl_upcc"
    assert got.full_string_result.coset.subgroup.order == 11


def test_homogeneous_relation_remains_fail_closed_at_symmetry_gate():
    v, k = 12, 3
    relation = tuple(0 for _ in combinations(range(v), k))
    ident = identity(v)
    group = schreier_stabilizer_chain([ident])
    got = exact_twl_design_candidate_string_isomorphism(
        group,
        _lifted(group),
        v,
        k,
        relation,
        relation,
        tuple(0 for _ in range(v)),
        tuple(0 for _ in range(v)),
        root_n=64,
    )
    assert got.status == "undetermined_exact_twl_design_branch_plan"
    assert not got.theorem_hypotheses_certified
    assert not got.exact and not got.complete
