from cartesian_block_family_action_v1 import exact_cartesian_block_family_action
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


def test_s5_product_action_is_faithfully_represented_on_ten_coordinate_blocks():
    G = product_symmetric_group(5)
    got = exact_cartesian_block_family_action(G)
    assert got.status == "exact_faithful_cartesian_coordinate_action"
    assert got.faithful
    assert got.original_degree == 25
    assert got.reduced_degree == 10
    assert got.factor_count == 2
    assert got.blocks_per_factor == 5
    assert got.original_group_order == 120 * 120
    assert got.image_group_order == got.original_group_order
    assert got.image is not None and got.image.degree == 10
    assert got.strict_domain_reduction


def test_noncartesian_multiple_family_is_not_forced_into_product_action():
    a = (1, 0, 3, 2)
    b = (2, 3, 0, 1)
    G = schreier_stabilizer_chain([a, b])
    got = exact_cartesian_block_family_action(G)
    assert got.status == "not_exact_cartesian_family"
    assert not got.faithful
    assert got.image is None
