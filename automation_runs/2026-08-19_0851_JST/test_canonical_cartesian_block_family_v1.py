import random

from canonical_cartesian_block_family_v1 import certify_canonical_cartesian_block_family
from permutation_group_schreier import compose, inverse, schreier_stabilizer_chain


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


def conjugate_by_relabeling(g, q):
    return compose(compose(inverse(q), g), q)


def test_product_action_family_is_exact_cartesian_and_strictly_smaller():
    G = product_symmetric_group(5)
    cert = certify_canonical_cartesian_block_family(G)
    assert G.order == 120 * 120
    assert cert.status == "exact_canonical_cartesian_decomposition"
    assert cert.exact_cartesian
    assert cert.factor_count == 2
    assert cert.blocks_per_factor == 5
    assert cert.minimum_block_size == 5
    assert cert.cartesian_cell_count == 25
    assert cert.coordinate_object_count == 10
    assert cert.strict_coordinate_reduction


def test_cartesian_certificate_is_relabeling_invariant():
    G = product_symmetric_group(4)
    base = certify_canonical_cartesian_block_family(G)
    q = list(range(G.degree))
    random.Random(172).shuffle(q)
    q = tuple(q)
    Gq = schreier_stabilizer_chain([
        conjugate_by_relabeling(g, q) for g in G.original_generators
    ])
    relabeled = certify_canonical_cartesian_block_family(Gq)
    assert relabeled.status == base.status == "exact_canonical_cartesian_decomposition"
    assert relabeled.factor_count == base.factor_count == 2
    assert relabeled.blocks_per_factor == base.blocks_per_factor == 4
    assert relabeled.coordinate_object_count == base.coordinate_object_count == 8
    assert relabeled.cartesian_cell_count == base.cartesian_cell_count == 16
    assert relabeled.strict_coordinate_reduction == base.strict_coordinate_reduction


def test_regular_klein_family_is_preserved_but_not_falsely_called_cartesian():
    a = (1, 0, 3, 2)
    b = (2, 3, 0, 1)
    G = schreier_stabilizer_chain([a, b])
    cert = certify_canonical_cartesian_block_family(G)
    assert G.order == 4
    assert cert.status == "canonical_block_family_not_cartesian"
    assert not cert.exact_cartesian
    assert cert.factor_count == 3
    assert cert.blocks_per_factor == 2
    assert cert.cartesian_cell_count == 8
    assert cert.degree == 4
