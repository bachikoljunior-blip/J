from itertools import combinations

from johnson_ground_relational_lift_v1 import _standard_subsets
from permutation_group_schreier import schreier_stabilizer_chain
from signed_johnson_symmetry_defect_gate_si_v2 import (
    paired_colored_subset_symmetry_defect_gate,
    signed_johnson_log_certificate_symmetry_defect_gate_si,
)


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_ground_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(index[tuple(sorted(sigma[x] for x in subset))] for subset in subsets)

    ground_gens = (swap01(v), cycle(v))
    return schreier_stabilizer_chain(tuple(induce(g) for g in ground_gens))


def fano_lines():
    return {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }


def test_paired_fano_relation_certifies_exact_symmetry_defect_gate():
    coords = tuple(combinations(range(7), 3))
    lines = fano_lines()
    colors = tuple(int(S in lines) for S in coords)
    got = paired_colored_subset_symmetry_defect_gate(
        7, 3, colors, colors, alpha=0.9
    )
    assert got.status == "verified_paired_symmetry_defect_gate", got
    assert got.invariant_compatible and not got.exact_empty
    assert got.design_gate_certified
    assert got.source.largest_symmetric_class == 1
    assert got.target.largest_symmetric_class == 1
    assert got.source_twin_class_sizes == (1, 1, 1, 1, 1, 1, 1)


def test_paired_homogeneous_relation_keeps_design_gate_closed():
    colors = (0,) * len(tuple(combinations(range(7), 3)))
    got = paired_colored_subset_symmetry_defect_gate(
        7, 3, colors, colors, alpha=0.9
    )
    assert got.status == "symmetry_defect_gate_closed", got
    assert got.invariant_compatible and not got.exact_empty
    assert not got.design_gate_certified
    assert got.source.largest_symmetric_class == 7
    assert got.source_twin_class_sizes == (7,)


def test_paired_relation_color_multiplicity_mismatch_is_exact_empty():
    coords = tuple(combinations(range(7), 3))
    lines = fano_lines()
    source = tuple(int(S in lines) for S in coords)
    target = (0,) * len(coords)
    got = paired_colored_subset_symmetry_defect_gate(
        7, 3, source, target, alpha=0.9
    )
    assert got.status == "exact_empty_symmetry_relation_color_multiplicity", got
    assert got.exact_empty and not got.invariant_compatible
    assert not got.design_gate_certified


def test_w1r_wrapper_reopens_rev184_homogeneous_boundary_and_fails_closed_when_defect_gate_is_closed():
    v, k = 6, 3
    G = induced_ground_group(v, k)
    source = (0,) * len(_standard_subsets(v, k))
    got = signed_johnson_log_certificate_symmetry_defect_gate_si(
        G,
        source,
        source,
        root_n=64,
        max_test_sets=1000,
        max_recognition_nodes=100000,
        max_johnson_nodes=100000,
    )
    assert got.status == "undetermined_log_certificate_symmetry_defect_gate_closed", got
    assert got.theorem_parameter_gate
    assert got.test_arity == 2
    assert got.test_count == 15
    assert not got.exact and got.coset is None
    assert got.local_cost_certified
    assert not got.terminal_certified
    assert not got.symmetry_defect_gate_certified
    assert got.source_largest_symmetric_class == v
    assert got.target_largest_symmetric_class == v
    assert got.source_twin_class_sizes == (v,)
    assert got.target_twin_class_sizes == (v,)


def test_non_design_rev184_result_passes_through_without_reclassification():
    v, k = 6, 3
    G = induced_ground_group(v, k)
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in S) for S in subsets)
    got = signed_johnson_log_certificate_symmetry_defect_gate_si(
        G,
        source,
        source,
        root_n=64,
        max_test_sets=1000,
        max_partition_states=256,
        max_candidate_group_order=256,
        max_depth=1,
    )
    assert got.status != "undetermined_log_certificate_design_gate", got
    assert got.status != "verified_log_certificate_symmetry_defect_gate", got
    assert got.status != "undetermined_log_certificate_symmetry_defect_gate_closed", got
