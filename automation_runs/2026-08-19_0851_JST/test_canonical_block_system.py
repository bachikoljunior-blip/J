from permutation_group_schreier import schreier_stabilizer_chain
from canonical_block_system import canonical_minimal_block_system


def cycle_group(n):
    return schreier_stabilizer_chain([tuple((i + 1) % n for i in range(n))])


def symmetric_group(n):
    swap = list(range(n)); swap[0], swap[1] = swap[1], swap[0]
    cycle = tuple((i + 1) % n for i in range(n))
    return schreier_stabilizer_chain([tuple(swap), cycle])


def test_prime_cycle_and_symmetric_group_are_primitive():
    assert canonical_minimal_block_system(cycle_group(7)).status == "primitive_or_trivial"
    assert canonical_minimal_block_system(symmetric_group(8)).status == "primitive_or_trivial"


def test_composite_cycles_have_unique_canonical_minimal_blocks():
    c12 = canonical_minimal_block_system(cycle_group(12))
    assert c12.status == "unique_canonical_minimal_block_system"
    assert c12.minimum_block_size == 2
    assert c12.selected_block_system == tuple((i, i + 6) for i in range(6))

    c25 = canonical_minimal_block_system(cycle_group(25))
    assert c25.status == "unique_canonical_minimal_block_system"
    assert c25.minimum_block_size == 5
    expected = tuple(tuple(range(i, 25, 5)) for i in range(5))
    assert c25.selected_block_system == expected


def test_regular_klein_four_preserves_three_minimal_systems_without_label_choice():
    G = schreier_stabilizer_chain([
        (1, 0, 3, 2),
        (2, 3, 0, 1),
    ])
    cert = canonical_minimal_block_system(G)
    assert cert.status == "multiple_canonical_minimal_block_systems"
    assert cert.minimum_block_size == 2
    assert len(cert.block_systems) == 3
    assert cert.selected_block_system == ()


def test_intransitive_group_returns_canonical_point_orbit_partition():
    G = schreier_stabilizer_chain([(1, 0, 2, 4, 3)])
    cert = canonical_minimal_block_system(G)
    assert cert.status == "canonical_intransitive_orbit_partition"
    assert cert.selected_block_system == ((0, 1), (2,), (3, 4))
