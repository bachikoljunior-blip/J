from permutation_group_schreier import schreier_stabilizer_chain
from quotient_imprimitivity_reduction import reduce_quotient_imprimitivity


def cycle_group(n):
    return schreier_stabilizer_chain([tuple((i + 1) % n for i in range(n))])


def test_composite_cycle_quotients_reduce_canonically():
    for n, block_size, block_count in ((12, 2, 6), (25, 5, 5)):
        G = cycle_group(n)
        r = reduce_quotient_imprimitivity(G, [(i,) for i in range(n)], [0] * n)
        assert r.status == "unique_canonical_imprimitive_quotient"
        assert r.block_size == block_size
        assert r.block_count == block_count
        assert len(r.block_system) == block_count


def test_prime_cycle_is_certified_primitive():
    n = 7
    G = cycle_group(n)
    r = reduce_quotient_imprimitivity(G, [(i,) for i in range(n)], [0] * n)
    assert r.status == "primitive_quotient_action"
    assert r.quotient_group_order == 7


def test_klein_four_keeps_all_minimal_systems_unselected():
    G = schreier_stabilizer_chain([(1, 0, 3, 2), (2, 3, 0, 1)])
    r = reduce_quotient_imprimitivity(G, [(i,) for i in range(4)], [0] * 4)
    assert r.status == "multiple_minimal_quotient_block_systems"
    assert r.block_size == 2
    assert r.alternative_minimal_system_count == 3
    assert r.block_system == ()


def test_coloring_can_make_exact_quotient_intransitive():
    n = 8
    G = cycle_group(n)
    values = [0] * n
    values[0] = 1
    r = reduce_quotient_imprimitivity(G, [(i,) for i in range(n)], values)
    assert r.status == "canonical_intransitive_quotient_split"
    assert (0,) in r.block_system
