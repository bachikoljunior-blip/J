from itertools import combinations

from permutation_group_schreier import schreier_stabilizer_chain
from canonical_orbital_size_relation import canonical_orbital_size_relation
from johnson_pair_relation_recognizer import recognize_johnson_pair_relation


def induced_action_on_k_subsets(v, k, ground_generators):
    vertices = list(combinations(range(v), k))
    index = {S: i for i, S in enumerate(vertices)}
    out = []
    for g in ground_generators:
        p = []
        for S in vertices:
            T = tuple(sorted(g[x] for x in S))
            p.append(index[T])
        out.append(tuple(p))
    return schreier_stabilizer_chain(out)


def symmetric_ground_generators(n):
    swap = list(range(n)); swap[0], swap[1] = swap[1], swap[0]
    cycle = tuple((i + 1) % n for i in range(n))
    return [tuple(swap), cycle]


def test_s5_on_two_subsets_exposes_johnson_relation_canonically():
    G = induced_action_on_k_subsets(5, 2, symmetric_ground_generators(5))
    relation = canonical_orbital_size_relation(G)
    assert relation.status == "canonical_orbital_size_pair_relation"
    assert relation.signature_count == 2
    cert = recognize_johnson_pair_relation(10, relation.pair_weights)
    assert cert.status == "exact_johnson_color_relation"
    assert (cert.ground_size, cert.subset_size) == (5, 2)


def test_prime_regular_cycle_coarsens_honestly_to_one_pair_color():
    n = 7
    G = schreier_stabilizer_chain([tuple((i + 1) % n for i in range(n))])
    relation = canonical_orbital_size_relation(G)
    assert relation.signature_count == 1
    assert relation.signatures == ((0, (7, 7)),)
    assert {w for _, w in relation.pair_weights} == {0}


def test_relabeling_conjugation_preserves_signature_multiset():
    G = induced_action_on_k_subsets(5, 2, symmetric_ground_generators(5))
    base = canonical_orbital_size_relation(G)
    q = tuple(reversed(range(G.degree)))
    qi = tuple(reversed(range(G.degree)))
    moved_gens = []
    for g in G.original_generators:
        moved_gens.append(tuple(q[g[qi[i]]] for i in range(G.degree)))
    moved = canonical_orbital_size_relation(schreier_stabilizer_chain(moved_gens))
    assert base.signatures == moved.signatures
    assert sorted(w for _, w in base.pair_weights) == sorted(w for _, w in moved.pair_weights)
