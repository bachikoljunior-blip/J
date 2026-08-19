from johnson_pair_relation_recognizer import _johnson_graph
from exact_gi_isomorphism_coset import exact_gi_isomorphism_coset
from johnson_automorphism_action import analyze_johnson_automorphism_action


def test_full_johnson_automorphism_actions_decode_exactly():
    for v, k, expected_order, expected_ground in (
        (5, 2, 120, 120),
        (6, 2, 720, 720),
        (6, 3, 1440, 720),
    ):
        graph = _johnson_graph(v, k)
        gi = exact_gi_isomorphism_coset(graph, graph, max_nodes=500000)
        assert gi.status == "exact_isomorphism_coset"
        cert = analyze_johnson_automorphism_action(gi.coset.subgroup, v, k)
        assert cert.status == "exact_full_johnson_automorphism_action"
        assert cert.quotient_group_order == expected_order
        assert cert.ground_projection_order == expected_ground
        assert cert.expected_full_order == expected_order
        assert all(len(g.ground_permutation) == v for g in cert.generators)


def test_middle_layer_detects_complement_symmetry():
    graph = _johnson_graph(6, 3)
    gi = exact_gi_isomorphism_coset(graph, graph, max_nodes=500000)
    cert = analyze_johnson_automorphism_action(gi.coset.subgroup, 6, 3)
    assert cert.status == "exact_full_johnson_automorphism_action"
    assert cert.complemented_generator_count > 0


def test_non_middle_layer_has_no_complemented_generators():
    graph = _johnson_graph(6, 2)
    gi = exact_gi_isomorphism_coset(graph, graph, max_nodes=500000)
    cert = analyze_johnson_automorphism_action(gi.coset.subgroup, 6, 2)
    assert cert.status == "exact_full_johnson_automorphism_action"
    assert cert.complemented_generator_count == 0
