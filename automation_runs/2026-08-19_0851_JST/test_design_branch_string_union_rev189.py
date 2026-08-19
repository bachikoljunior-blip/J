from itertools import combinations

from colored_subset_design_branch_plan_v1 import build_colored_subset_design_branch_plan
from design_branch_string_union_si_v1 import solve_complete_design_tuple_string_isomorphism
from design_branch_tuple_transport_v1 import transport_complete_design_tuple_branches
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3


def _swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def _cycle(v):
    return tuple((i + 1) % v for i in range(v))


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
    return v, t, coords, tuple(int(S in lines) for S in coords)


def _induce(coords, ground_permutation):
    index = {S: i for i, S in enumerate(coords)}
    return tuple(
        index[tuple(sorted(ground_permutation[x] for x in S))]
        for S in coords
    )


def _relabel_relation(coords, colors, ground_permutation):
    induced = _induce(coords, ground_permutation)
    out = [None] * len(coords)
    for i, j in enumerate(induced):
        out[j] = colors[i]
    return tuple(out), induced


def _induced_symmetric_group(v, coords):
    ground_generators = (_swap01(v), _cycle(v))
    domain_generators = tuple(_induce(coords, g) for g in ground_generators)
    group = schreier_stabilizer_chain(domain_generators)
    pairing = {
        domain: (ground, False)
        for domain, ground in zip(domain_generators, ground_generators)
    }
    lifted = tuple(pairing[g] for g in group.original_generators)
    return group, lifted


def _maps_string(source, target, permutation):
    return all(source[i] == target[permutation[i]] for i in range(len(source)))


def _stabilizes_string(values, permutation):
    return all(values[i] == values[permutation[i]] for i in range(len(values)))


def test_complete_fano_tuple_cover_reconstructs_full_168_element_si_coset():
    v, t, coords, source = _fano()
    q = (3, 5, 1, 6, 0, 4, 2)
    target, induced_q = _relabel_relation(coords, source, q)
    branch_plan = build_colored_subset_design_branch_plan(
        v,
        t,
        source,
        target,
        max_wl_rounds=64,
    )
    group, lifted = _induced_symmetric_group(v, coords)
    transport = transport_complete_design_tuple_branches(
        group,
        lifted,
        branch_plan,
        max_partition_states=64,
    )
    got = solve_complete_design_tuple_string_isomorphism(
        group,
        source,
        target,
        transport,
        root_n=64,
        max_candidate_group_order=1000,
    )
    assert got.status == "exact_complete_design_tuple_string_union_coset", got
    assert got.exact and got.local_cost_certified and got.complete_branch_cover
    assert got.coset is not None
    assert got.nonempty_branch_count == 49
    assert got.reconstructed_stabilizer_order == 168
    assert got.coset.contains(induced_q)
    assert _maps_string(source, target, got.coset.representative)
    assert all(
        _stabilizes_string(target, generator)
        for generator in got.coset.subgroup.original_generators
    )
    accounting = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert accounting.certified, accounting


def test_complete_cover_with_unresolved_candidate_branch_is_withheld():
    v, t, coords, source = _fano()
    branch_plan = build_colored_subset_design_branch_plan(
        v,
        t,
        source,
        source,
        max_wl_rounds=64,
    )
    group, lifted = _induced_symmetric_group(v, coords)
    transport = transport_complete_design_tuple_branches(
        group,
        lifted,
        branch_plan,
        max_partition_states=64,
    )
    got = solve_complete_design_tuple_string_isomorphism(
        group,
        source,
        source,
        transport,
        root_n=len(source),
        max_explicit_degree=1,
        max_candidate_group_order=1,
        max_depth=1,
    )
    assert got.status == "undetermined_design_tuple_string_branch", got
    assert not got.exact and got.coset is None
    assert not got.complete_branch_cover


def test_exact_empty_upstream_transport_remains_exact_empty_terminal():
    v, _t, coords, source = _fano()
    n = len(coords)
    from design_branch_tuple_transport_v1 import DesignTupleTransportPlan

    plan = DesignTupleTransportPlan(
        "exact_empty_design_tuple_transport_cover",
        n,
        v,
        1,
        49,
        0,
        (),
        24.0,
        True,
        True,
        "synthetic exact-empty complete cover",
    )
    group = schreier_stabilizer_chain([identity(n)])
    got = solve_complete_design_tuple_string_isomorphism(
        group,
        source,
        source,
        plan,
        root_n=64,
    )
    assert got.status == "exact_empty_design_tuple_string_isomorphism"
    assert got.exact and got.coset is None and got.complete_branch_cover
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified
