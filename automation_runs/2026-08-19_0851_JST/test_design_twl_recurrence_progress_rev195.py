from itertools import combinations

from design_twl_recurrence_progress_v1 import certify_design_twl_recurrence_progress


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
    return v, k, tuple(int(S in lines) for S in coords)


def test_fano_one_point_design_split_certifies_auxiliary_shrink():
    v, k, colors = _fano()
    got = certify_design_twl_recurrence_progress(
        v, k, colors, (0,), root_n=64,
        max_tuple_states=1000, max_rounds=32, max_work_units=10_000_000,
    )
    assert got.status == "certified_design_auxiliary_split_progress"
    assert got.design_status == "certified_twl_alpha_coloring"
    assert got.aux_shrink_certified
    assert got.max_child_aux_size == 6
    assert max(got.child_aux_sizes) <= 0.9 * v


def test_disconnected_triangles_imprimitive_output_certifies_two_shrunk_children():
    v, k = 6, 2
    edges = set(combinations((0, 1, 2), 2)) | set(combinations((3, 4, 5), 2))
    coords = tuple(combinations(range(v), k))
    colors = tuple(int(S in edges) for S in coords)
    got = certify_design_twl_recurrence_progress(
        v, k, colors, (), root_n=64,
        max_tuple_states=100, max_rounds=16, max_work_units=2_000_000,
    )
    assert got.status == "certified_design_auxiliary_split_progress"
    assert got.design_status == "certified_twl_imprimitive_alpha_partition"
    assert got.child_aux_sizes == (3, 3)
    assert got.aux_shrink_certified


def test_cycle5_upcc_is_not_misreported_as_recurrence_progress():
    v, k = 5, 2
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    coords = tuple(combinations(range(v), k))
    colors = tuple(int(S in edges) for S in coords)
    got = certify_design_twl_recurrence_progress(
        v, k, colors, (), root_n=32,
        max_tuple_states=100, max_rounds=16, max_work_units=1_000_000,
    )
    assert got.design_status == "certified_twl_upcc"
    assert got.status == "requires_full_split_or_johnson"
    assert not got.aux_shrink_certified
    assert got.split_or_johnson_result is not None


def test_johnson_graph_upcc_reduces_to_strictly_smaller_ground():
    ground = 5
    vertices = tuple(combinations(range(ground), 2))
    index = {S: i for i, S in enumerate(vertices)}
    v, k = len(vertices), 2
    coords = tuple(combinations(range(v), 2))
    colors = tuple(
        int(len(set(vertices[a]).intersection(vertices[b])) == 1)
        for a, b in coords
    )
    got = certify_design_twl_recurrence_progress(
        v, k, colors, (), root_n=64,
        max_tuple_states=200, max_rounds=32, max_work_units=5_000_000,
        max_johnson_nodes=200000,
    )
    assert got.design_status == "certified_twl_upcc"
    assert got.status == "certified_design_upcc_split_or_johnson_progress"
    assert got.aux_shrink_certified
    assert got.max_child_aux_size == ground
    assert got.split_or_johnson_result is not None
    assert got.split_or_johnson_result.status == "exact_johnson_ground_reduction_available"
