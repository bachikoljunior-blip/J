from itertools import combinations

from johnson_ground_relational_lift_v1 import _standard_subsets
from permutation_group_schreier import schreier_stabilizer_chain
from signed_johnson_log_design_lemma_si_v2 import signed_johnson_log_design_lemma_si_v2


def _cycle(v):
    return tuple((i + 1) % v for i in range(v))


def _swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def _induced_symmetric_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {S: i for i, S in enumerate(subsets)}

    def induce(sigma):
        return tuple(index[tuple(sorted(sigma[x] for x in S))] for S in subsets)

    return schreier_stabilizer_chain([induce(_swap01(v)), induce(_cycle(v))])


def test_h6_wrapper_preserves_h5_resolved_significant_split_path():
    v, k = 6, 3
    group = _induced_symmetric_group(v, k)
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in S) for S in subsets)
    got = signed_johnson_log_design_lemma_si_v2(
        group,
        source,
        source,
        root_n=64,
        max_test_sets=1000,
        max_partition_states=256,
        max_candidate_group_order=256,
        max_depth=1,
    )
    assert got.status.startswith("delegated_")
    assert got.design_result is None
    assert got.h5_result.status != "undetermined_log_certificate_design_gate"


def test_h6_wrapper_connects_homogeneous_h5_gate_to_exact_symmetry_defect_check():
    v, k = 6, 3
    group = _induced_symmetric_group(v, k)
    source = tuple(0 for _ in _standard_subsets(v, k))
    got = signed_johnson_log_design_lemma_si_v2(
        group,
        source,
        source,
        root_n=64,
        max_test_sets=1000,
        max_partition_states=256,
        max_design_wl_rounds=64,
        max_candidate_group_order=256,
        max_depth=1,
    )
    assert got.h5_result.status == "undetermined_log_certificate_design_gate"
    assert got.status == "undetermined_w1r_h6_design_candidate"
    assert got.design_result is not None
    assert got.design_result.branch_plan.source_family.status == "undetermined_design_symmetry_defect_gate"
    assert not got.exact
    assert not got.local_cost_certified
