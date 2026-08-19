from itertools import combinations

from johnson_ground_relational_lift_v1 import _standard_subsets
from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_johnson_log_certificate_design_descent_si_v1 import (
    _relation_descent,
    signed_johnson_log_certificate_design_descent_si,
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
    domain_gens = tuple(induce(g) for g in ground_gens)
    return schreier_stabilizer_chain(domain_gens), domain_gens


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def maps_string(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def stabilizes_string(source, p):
    return all(source[i] == source[p[i]] for i in range(len(source)))


def test_generic_log_relation_incidence_finds_significant_point_split():
    v, t = 8, 3
    coords = tuple(combinations(range(v), t))
    source = tuple(int(0 in S) for S in coords)
    target = source
    got = _relation_descent(
        v, coords, source, target, t,
        max_class_fraction=0.9,
        max_johnson_nodes=100000,
    )
    assert got.status == "certified_log_certificate_point_split", got
    assert got.significant_split
    assert tuple(sorted(map(len, got.source_cells))) == (1, 7)
    assert got.arity_path == (3,)


def test_generic_homogeneous_nontrivial_design_fails_closed_instead_of_claiming_split():
    v, t = 8, 3
    coords = tuple(combinations(range(v), t))
    colors = tuple(0 for _ in coords)
    got = _relation_descent(
        v, coords, colors, colors, t,
        max_class_fraction=0.9,
        max_johnson_nodes=100000,
    )
    assert got.status == "homogeneous_design_gate_unresolved", got
    assert not got.significant_split
    assert got.johnson_ground_size is None


def test_wrapper_builds_logarithmic_relation_and_connects_split_to_original_candidate():
    # J(6,3) keeps exact Johnson recognition and candidate continuation fast;
    # the t=3 regression above separately checks genuinely higher arity.
    v, k = 6, 3
    G, domain_gens = induced_ground_group(v, k)
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in S) for S in subsets)
    witness = domain_gens[1]
    target = relabel_target(source, witness)

    got = signed_johnson_log_certificate_design_descent_si(
        G,
        source,
        target,
        root_n=64,
        max_test_sets=1000,
        max_partition_states=256,
        max_candidate_group_order=256,
        max_depth=1,
    )
    assert got.theorem_parameter_gate, got
    assert got.test_arity == 2
    assert got.test_count == 15
    assert got.significant_ground_split, got
    assert got.coset is not None
    assert G.contains(got.coset.representative)
    assert maps_string(source, target, got.coset.representative)
    for generator in got.coset.subgroup.original_generators:
        assert stabilizes_string(source, generator)
    assert got.status.startswith(("verified_log_certificate_partition_filter", "exact_w1r_log_certificate_candidate_")), got
    if got.exact:
        check = validate_quasipoly_recurrence_tree_v3(got.accounting)
        assert check.certified, check


def test_wrapper_test_count_gate_is_fail_closed():
    v, k = 6, 3
    G, _ = induced_ground_group(v, k)
    subsets = _standard_subsets(v, k)
    source = tuple(int(0 in S) for S in subsets)
    got = signed_johnson_log_certificate_design_descent_si(
        G,
        source,
        source,
        root_n=64,
        max_test_sets=10,
    )
    assert got.status == "undetermined_log_certificate_parameter_gate", got
    assert not got.exact and got.coset is None
    assert not got.theorem_parameter_gate
    assert not got.local_cost_certified
