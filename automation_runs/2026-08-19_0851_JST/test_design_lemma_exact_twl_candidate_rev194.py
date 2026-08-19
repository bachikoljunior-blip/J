from itertools import combinations

from design_lemma_exact_twl_candidate_si_v1 import exact_twl_design_candidate_string_isomorphism
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _fano():
    v, k = 7, 3
    lines = {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }
    coords = tuple(combinations(range(v), k))
    colors = tuple(int(S in lines) for S in coords)
    # An order-7 automorphism of this concrete Fano labeling.
    cycle = (1, 3, 5, 2, 0, 6, 4)
    return v, k, colors, cycle


def _lifted(group):
    return tuple((g, False) for g in group.original_generators)


def test_fano_theorem_faithful_path_composes_to_exact_full_string_coset():
    v, k, relation, cycle = _fano()
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
    assert got.branch_plan.individualization_length == 1
    assert got.branch_plan.branch_count == 49
    assert got.full_string_result is not None and got.full_string_result.coset is not None
    assert got.full_string_result.coset.subgroup.order == 7
    assert got.full_string_result.coset.contains(identity(v))
    assert got.full_string_result.coset.contains(cycle)


def test_fano_distinct_string_filters_the_exact_design_cover_to_identity():
    v, k, relation, cycle = _fano()
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


def test_cycle5_upcc_branch_reuses_exact_transport_and_full_string_union():
    v, k = 5, 2
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
        max_tuple_states=100,
        max_twl_rounds=16,
        max_twl_work_units=2_000_000,
        max_partition_states=32,
        max_group_order=8,
    )
    assert got.status == "exact_twl_design_full_string_coset"
    assert got.branch_plan.individualization_length == 0
    assert got.branch_plan.branch_count == 1
    assert got.branch_plan.source_family.witness_outcomes[0].status == "certified_twl_upcc"
    assert got.full_string_result.coset.subgroup.order == 5


def test_homogeneous_relation_remains_fail_closed_at_symmetry_gate():
    v, k = 8, 3
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
