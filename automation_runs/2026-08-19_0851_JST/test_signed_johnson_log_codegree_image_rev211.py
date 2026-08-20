from itertools import combinations

from coset_stabilizer_primitives import RightCoset
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v4 import validate_quasipoly_recurrence_tree_v4
from signed_johnson_complement_safe_image_si_v1 import complement_safe_t_relation_signatures
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_log_certificate_design_descent_si_v1 import _relation_descent
from u2_candidate_coset_string_iso_v5 import candidate_coset_string_isomorphism_u5
from u2_candidate_coset_string_iso_v6 import candidate_coset_string_isomorphism_u6


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_symmetric_on_subsets(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {S: i for i, S in enumerate(subsets)}

    def induce(sigma):
        return tuple(index[tuple(sorted(sigma[x] for x in S))] for S in subsets)

    return schreier_stabilizer_chain(tuple(induce(g) for g in (swap01(v), cycle(v))))


def hidden_j42_triple_colors():
    # Six ground points are the six 2-subsets of a hidden 4-set.  Color each
    # 3-subset by its number of J(4,2) adjacency edges.  The induced t=2 local
    # relation is homogeneous on points but distinguishes the exact J(4,2)
    # edge/nonedge pair scheme, which is precisely rev184's structural leaf.
    hidden = tuple(combinations(range(4), 2))

    def adjacent(a, b):
        return len(set(hidden[a]).intersection(hidden[b])) == 1

    out = []
    for S in combinations(range(6), 3):
        out.append(sum(int(adjacent(a, b)) for a, b in combinations(S, 2)))
    return tuple(out)


def test_rev211_closes_rev184_second_johnson_structural_leaf_via_pair_image():
    G = induced_symmetric_on_subsets(6, 3)
    source = hidden_j42_triple_colors()
    candidate = RightCoset(G, identity(G.degree))

    lift = lift_primitive_johnson_to_ground_relation(G, source, source)
    assert lift.status == "exact_johnson_ground_relational_lift", lift
    tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    rel = complement_safe_t_relation_signatures(6, 3, tokens, 2, complement_in_image=False)
    descent = _relation_descent(
        6,
        tuple(combinations(range(6), 2)),
        rel,
        rel,
        2,
        max_class_fraction=0.9,
        max_johnson_nodes=100000,
    )
    assert descent.status == "certified_log_certificate_johnson_descent", descent
    assert (descent.johnson_ground_size, descent.johnson_subset_size) == (4, 2)

    # The ambient S_6 has order 720, so even the normal polynomial candidate cap
    # leaves rev210 unresolved.  The pair filter reduces it to Aut(J(4,2)), order 48.
    before = candidate_coset_string_isomorphism_u5(
        candidate,
        source,
        source,
        root_n=64,
        max_explicit_degree=2,
        max_group_order=256,
        max_johnson_nodes=100000,
    )
    assert not before.exact, before

    got = candidate_coset_string_isomorphism_u6(
        candidate,
        source,
        source,
        root_n=64,
        max_explicit_degree=2,
        max_group_order=256,
        max_johnson_nodes=100000,
    )
    assert got.exact and got.coset is not None, got
    assert got.status.startswith("exact_w1r_log_codegree_pair_candidate_"), got
    # Aut(J(4,2)) includes the exceptional complement on hidden 2-subsets.
    assert got.coset.subgroup.order == 48
    check = validate_quasipoly_recurrence_tree_v4(got.accounting)
    assert check.certified, check


def test_rev211_preserves_fail_closed_image_node_gate():
    G = induced_symmetric_on_subsets(6, 3)
    source = hidden_j42_triple_colors()
    # Directly force the exact pair-image intersection below the nodes it needs.
    from signed_johnson_log_codegree_image_si_v1 import signed_johnson_log_codegree_image_candidate_si

    got = signed_johnson_log_codegree_image_candidate_si(
        G,
        source,
        source,
        root_n=64,
        candidate_dispatch=candidate_coset_string_isomorphism_u6,
        max_image_si_nodes=1,
        max_explicit_degree=2,
        max_candidate_group_order=64,
        max_johnson_nodes=100000,
    )
    assert not got.exact
    assert got.status == "undetermined_log_codegree_pair_image_node_limit", got
