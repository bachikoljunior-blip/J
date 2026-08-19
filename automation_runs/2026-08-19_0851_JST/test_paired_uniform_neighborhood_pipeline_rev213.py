from itertools import combinations

from paired_uniform_neighborhood_pipeline_v1 import (
    build_paired_uniform_neighborhood_candidate_cover,
)
from paired_uniform_neighborhood_provenance_v1 import (
    certify_paired_uniform_neighborhood_provenance,
)
from permutation_group_schreier import schreier_stabilizer_chain


def _fano_edges():
    lines = [
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    ]
    return tuple((a, b) for a, line in enumerate(lines) for b in line)


def _swap_group():
    swap = (1, 0, 2, 3, 4, 5, 6)
    return swap, schreier_stabilizer_chain([swap])


def test_fano_provenance_is_mechanically_wired_to_49_design_pairs_and_9_ambient_survivors():
    edges = _fano_edges()
    provenance = certify_paired_uniform_neighborhood_provenance(7, 7, edges, edges)
    assert provenance.status == "certified_paired_uniform_neighborhood_test_relation_provenance"
    swap, group = _swap_group()
    got = build_paired_uniform_neighborhood_candidate_cover(
        group,
        ((swap, False),),
        provenance,
        root_n=7,
        design_alpha=0.9,
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
        max_partition_states=10,
    )
    assert got.status == "certified_paired_uniform_neighborhood_candidate_cover"
    assert got.exact
    assert got.complete_cover
    assert not got.exact_empty
    assert got.parent_provenance_required
    assert got.relation_branch_count == 49
    assert got.ambient_survivor_count == 9
    assert got.design_plan is not None
    assert got.tuple_transport is not None


def test_exact_empty_degree_provenance_short_circuits_all_downstream_branching():
    source = _fano_edges()
    target = list(source)
    target.remove((0, 0))
    provenance = certify_paired_uniform_neighborhood_provenance(7, 7, source, tuple(target))
    assert provenance.exact_empty
    swap, group = _swap_group()
    got = build_paired_uniform_neighborhood_candidate_cover(
        group,
        ((swap, False),),
        provenance,
        root_n=7,
    )
    assert got.status == "exact_empty_paired_uniform_neighborhood_provenance"
    assert got.exact_empty
    assert got.complete_cover
    assert got.exact
    assert got.design_plan is None
    assert got.tuple_transport is None


def test_complete_uniform_neighborhood_johnson_case_bypasses_design_tuple_cover():
    neighborhoods = tuple(combinations(range(4), 2))
    edges = tuple((a, b) for a, pair in enumerate(neighborhoods) for b in pair)
    provenance = certify_paired_uniform_neighborhood_provenance(6, 4, edges, edges)
    assert provenance.paired_johnson_certified
    # Pipeline is not asked to invent a Johnson transporter here; it returns the
    # exact structural alternative for the existing Johnson branch to consume.
    identity = tuple(range(4))
    group = schreier_stabilizer_chain([identity])
    got = build_paired_uniform_neighborhood_candidate_cover(
        group,
        ((identity, False),),
        provenance,
        root_n=4,
    )
    assert got.status == "paired_uniform_neighborhood_johnson_alternative"
    assert got.exact
    assert got.complete_cover
    assert not got.exact_empty
    assert got.design_plan is None
