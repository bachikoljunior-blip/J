from itertools import combinations

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain
from primitive_johnson_ground_terminal_v1 import primitive_johnson_ground_string_isomorphism_terminal
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


def cycle(n):
    return tuple((i + 1) % n for i in range(n))


def transposition(n, a=0, b=1):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def relabel_target(source, p):
    inv = [0] * len(p)
    for i, j in enumerate(p):
        inv[j] = i
    return tuple(source[inv[j]] for j in range(len(p)))


def induced_symmetric_action_on_pairs(v):
    vertices = list(combinations(range(v), 2))
    index = {edge: i for i, edge in enumerate(vertices)}
    swap = list(range(v))
    swap[0], swap[1] = swap[1], swap[0]
    cyc = tuple((i + 1) % v for i in range(v))
    gens = []
    for g in (tuple(swap), cyc):
        gens.append(tuple(index[tuple(sorted(g[x] for x in edge))] for edge in vertices))
    return schreier_stabilizer_chain(gens), vertices, index


def induced_pair_perm(vertices, index, ground_perm):
    return tuple(index[tuple(sorted(ground_perm[x] for x in edge))] for edge in vertices)


def test_primitive_non_giant_j82_is_exact_via_small_ground_not_s28():
    H, vertices, index = induced_symmetric_action_on_pairs(8)
    assert H.degree == 28
    assert H.order == 40320
    ground_cycle = cycle(8)
    q = induced_pair_perm(vertices, index, ground_cycle)
    source = tuple(range(H.degree))
    target = relabel_target(source, q)

    got = primitive_johnson_ground_string_isomorphism_terminal(
        H,
        source,
        target,
        root_n=64,
        max_ground_degree=8,
    )
    assert got.status == "exact_primitive_johnson_ground_coset"
    assert got.exact and got.coset is not None
    assert got.coset.contains(q)
    assert got.johnson_ground_size == 8
    assert got.johnson_subset_size == 2
    assert got.ground_permutations_checked == 40320
    accounting = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert accounting.certified, accounting


def test_candidate_right_coset_translates_exact_johnson_terminal_back():
    H, vertices, index = induced_symmetric_action_on_pairs(8)
    n = H.degree
    r = transposition(n, 0, 1)
    candidate = RightCoset(H, r)
    h = induced_pair_perm(vertices, index, cycle(8))
    witness = compose(r, h)
    source = tuple(range(n))
    target = relabel_target(source, witness)

    got = candidate_coset_string_isomorphism_u2(
        candidate,
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=256,
    )
    assert got.status.startswith("exact_translated_exact_primitive_johnson_ground_coset")
    assert got.exact and got.coset is not None
    assert got.coset.contains(witness)
    accounting = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert accounting.certified, accounting


def test_nonjohnson_primitive_candidate_stays_typed_fail_closed():
    n = 29
    H = schreier_stabilizer_chain([cycle(n)])
    candidate = RightCoset(H, identity(n))
    got = candidate_coset_string_isomorphism_u2(
        candidate,
        tuple(range(n)),
        tuple(range(n)),
        root_n=64,
        max_explicit_degree=8,
        max_group_order=16,
    )
    assert got.status == "undetermined_primitive_non_giant_not_johnson"
    assert not got.exact and got.coset is None
    assert not got.local_cost_certified
