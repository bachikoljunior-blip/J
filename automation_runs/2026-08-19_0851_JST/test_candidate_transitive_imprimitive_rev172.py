from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain
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


def block_cycle(k, b):
    n = k * b
    p = list(range(n))
    for i in range(k):
        for j in range(b):
            p[i * b + j] = ((i + 1) % k) * b + j
    return tuple(p)


def within_first_block_cycle(k, b):
    n = k * b
    p = list(range(n))
    for j in range(b):
        p[j] = (j + 1) % b
    return tuple(p)


def large_imprimitive_group(k=3, b=11):
    return schreier_stabilizer_chain([
        block_cycle(k, b),
        within_first_block_cycle(k, b),
    ])


def test_large_transitive_candidate_uses_unique_imprimitive_small_image_recursion():
    H = large_imprimitive_group(3, 11)
    n = H.degree
    assert H.order > 16
    assert len(H.levels[0].orbit) == n

    r = transposition(n, 0, 1)
    candidate = RightCoset(H, r)
    h = block_cycle(3, 11)
    witness = compose(r, h)
    source = tuple(range(n))
    target = relabel_target(source, witness)

    got = candidate_coset_string_isomorphism_u2(
        candidate,
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=16,
    )
    assert got.exact and got.coset is not None
    assert got.status.startswith("exact_translated_exact_imprimitive_small_image_recursive_coset")
    assert got.coset.contains(witness)
    accounting = validate_quasipoly_recurrence_tree_v3(got.accounting)
    assert accounting.certified, accounting


def test_large_primitive_giant_candidate_remains_typed_fail_closed():
    n = 9
    H = schreier_stabilizer_chain([cycle(n), transposition(n)])
    candidate = RightCoset(H, identity(n))
    got = candidate_coset_string_isomorphism_u2(
        candidate,
        (0,) * n,
        (0,) * n,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=64,
    )
    assert got.status == "undetermined_primitive_giant_local_certificates"
    assert not got.exact and got.coset is None
    assert not got.local_cost_certified
