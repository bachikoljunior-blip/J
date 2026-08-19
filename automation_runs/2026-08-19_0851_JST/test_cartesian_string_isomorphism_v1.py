from cartesian_string_isomorphism_v1 import cartesian_string_isomorphism_v1
from permutation_group_schreier import schreier_stabilizer_chain


def cycle(m):
    return tuple((i + 1) % m for i in range(m))


def swap(m):
    p = list(range(m))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def product_action_generator(m, factor, p):
    out = list(range(m * m))
    for a in range(m):
        for b in range(m):
            aa, bb = (p[a], b) if factor == 0 else (a, p[b])
            out[a * m + b] = aa * m + bb
    return tuple(out)


def product_symmetric_group(m):
    return schreier_stabilizer_chain([
        product_action_generator(m, 0, cycle(m)),
        product_action_generator(m, 0, swap(m)),
        product_action_generator(m, 1, cycle(m)),
        product_action_generator(m, 1, swap(m)),
    ])


def relabel_target(source, p):
    inv = [0] * len(p)
    for i, j in enumerate(p):
        inv[j] = i
    return tuple(source[inv[j]] for j in range(len(p)))


def test_cartesian_pipeline_exactly_rejects_row_versus_diagonal():
    m = 5
    G = product_symmetric_group(m)
    source = tuple(1 if a == 0 else 0 for a in range(m) for b in range(m))
    target = tuple(1 if a == b else 0 for a in range(m) for b in range(m))
    got = cartesian_string_isomorphism_v1(
        G,
        source,
        target,
        root_n=64,
        max_group_order=256,
        max_candidate_group_order=64,
    )
    assert got.status == "exact_empty_cartesian_coordinate_filter"
    assert got.exact and got.coset is None
    assert got.coordinate_degree == 10
    assert got.coordinate_action_faithful
    assert not got.complexity_accounting_closed


def test_cartesian_pipeline_exactly_lifts_and_verifies_related_strings():
    m = 5
    G = product_symmetric_group(m)
    source = tuple((a + 2 * b) % 3 for a in range(m) for b in range(m))
    witness = product_action_generator(m, 0, cycle(m))
    target = relabel_target(source, witness)
    got = cartesian_string_isomorphism_v1(
        G,
        source,
        target,
        root_n=64,
        max_group_order=256,
        max_candidate_group_order=64,
    )
    assert got.status == "exact_cartesian_string_isomorphism"
    assert got.exact and got.coset is not None
    assert got.coset.contains(witness)
    assert got.preimage_proof is not None
    assert got.preimage_proof.kernel_order == 1
    assert got.preimage_proof.preimage_subgroup_order == got.reduced_proof.coset.subgroup.order
    assert got.final_candidate_proof is not None and got.final_candidate_proof.exact
    assert not got.complexity_accounting_closed
