from itertools import combinations

from design_lemma_candidate_si_v1 import design_lemma_candidate_string_isomorphism
from permutation_group_schreier import identity, schreier_stabilizer_chain


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


def test_fano_design_path_composes_to_exact_constant_string_cyclic_coset():
    v, t, relation = _fano_relation()
    cycle, group = _cyclic_group(v)
    source = tuple(0 for _ in range(v))
    got = design_lemma_candidate_string_isomorphism(
        group, ((cycle, False),), v, t, relation, relation, source, source,
        root_n=v, max_wl_rounds=64, max_partition_states=32, max_group_order=8,
    )
    assert got.status == "exact_design_lemma_full_string_coset"
    assert got.theorem_hypotheses_certified
    assert got.exact and got.complete
    assert got.full_string_result is not None and got.full_string_result.coset is not None
    assert got.full_string_result.coset.subgroup.order == group.order == v
    assert got.full_string_result.coset.contains(identity(v))
    assert got.full_string_result.coset.contains(cycle)


def test_fano_design_path_filters_to_identity_on_distinct_full_string():
    v, t, relation = _fano_relation()
    cycle, group = _cyclic_group(v)
    source = tuple(range(v))
    got = design_lemma_candidate_string_isomorphism(
        group, ((cycle, False),), v, t, relation, relation, source, source,
        root_n=v, max_wl_rounds=64, max_partition_states=32, max_group_order=8,
    )
    assert got.status == "exact_design_lemma_full_string_coset"
    assert got.exact and got.complete
    assert got.full_string_result is not None and got.full_string_result.coset is not None
    assert got.full_string_result.coset.subgroup.order == 1
    assert got.full_string_result.coset.contains(identity(v))


def test_homogeneous_relation_fails_closed_at_exact_symmetry_defect_gate():
    v, t = 8, 3
    relation = tuple(0 for _ in combinations(range(v), t))
    ident = identity(v)
    group = schreier_stabilizer_chain([ident])
    got = design_lemma_candidate_string_isomorphism(
        group, ((ident, False),), v, t, relation, relation,
        tuple(0 for _ in range(v)), tuple(0 for _ in range(v)), root_n=v,
        max_wl_rounds=32,
    )
    assert got.status == "undetermined_design_lemma_branch_plan"
    assert not got.theorem_hypotheses_certified
    assert not got.exact and not got.complete
    assert got.transport_plan is None and got.full_string_result is None
