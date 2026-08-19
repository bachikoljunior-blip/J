from permutation_group_schreier import schreier_stabilizer_chain
from s1_structural_classifier_v1 import classify_s1_structure


def cycle(n):
    return tuple((i + 1) % n for i in range(n))


def test_canonical_intransitive_partition_is_detected_without_si_search():
    g1 = (1, 0, 2, 3, 4, 5)
    g2 = (0, 1, 3, 2, 4, 5)
    G = schreier_stabilizer_chain([g1, g2])
    got = classify_s1_structure(G, root_n=64, max_explicit_degree=1)
    assert got.status == "canonical_intransitive_partition"
    assert got.canonical
    assert max(got.child_measures) < G.degree


def test_transitive_imprimitive_cycle_has_canonical_block_dispatch():
    G = schreier_stabilizer_chain([cycle(6)])
    got = classify_s1_structure(G, root_n=64, max_explicit_degree=1)
    assert got.status in {"canonical_imprimitive_block_system", "canonical_imprimitive_family"}
    assert got.canonical
    assert 1 < got.block_size < 6
    assert 1 < got.quotient_degree < 6


def test_prime_cycle_is_primitive_non_giant():
    G = schreier_stabilizer_chain([cycle(5)])
    got = classify_s1_structure(G, root_n=64, max_explicit_degree=1)
    assert got.status == "primitive_non_giant"
    assert got.canonical and got.giant_type is None


def test_symmetric_group_is_primitive_giant():
    n = 5
    transposition = (1, 0, 2, 3, 4)
    G = schreier_stabilizer_chain([cycle(n), transposition])
    got = classify_s1_structure(G, root_n=64, max_explicit_degree=1)
    assert got.status == "primitive_giant_local_certificates"
    assert got.canonical
    assert got.giant_type is not None
