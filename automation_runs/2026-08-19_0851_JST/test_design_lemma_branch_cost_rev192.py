from itertools import combinations

from colored_subset_design_branch_plan_v1 import build_colored_subset_design_branch_plan
from design_lemma_branch_cost_certificate_v1 import certify_design_branch_quasipoly_cost


def _fano():
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


def test_fano_7_by_7_branch_cover_has_certified_log_squared_charge():
    v, t, colors = _fano()
    plan = build_colored_subset_design_branch_plan(v, t, colors, colors, max_wl_rounds=64)
    assert plan.branch_count == 49 and plan.individualization_length == 1
    got = certify_design_branch_quasipoly_cost(plan, root_n=64)
    assert got.status == "certified_design_branch_quasipoly_cost"
    assert got.certified
    assert got.branch_count == 49
    assert got.branch_log2_bound == 72.0


def test_too_small_root_fails_logarithmic_parameter_gate():
    v, t, colors = _fano()
    plan = build_colored_subset_design_branch_plan(v, t, colors, colors, max_wl_rounds=64)
    got = certify_design_branch_quasipoly_cost(plan, root_n=7)
    assert got.certified
    got2 = certify_design_branch_quasipoly_cost(plan, root_n=6)
    assert got2.status == "undetermined_design_quasipoly_parameter_gate"
    assert not got2.certified
