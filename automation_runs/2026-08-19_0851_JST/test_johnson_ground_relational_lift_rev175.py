from itertools import combinations

from johnson_ground_relational_lift_v1 import (
    _decode_johnson_automorphism,
    _induce_signed_ground_generator,
    lift_primitive_johnson_to_ground_relation,
)
from permutation_group_schreier import schreier_stabilizer_chain


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_action(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    return schreier_stabilizer_chain([induce(swap01(v)), induce(cycle(v))])


def test_j92_lifts_to_strictly_smaller_ground_without_enumerating_s9():
    H = induced_action(9, 2)
    source = tuple(i % 5 for i in range(H.degree))
    target = tuple((3 * i + 1) % 7 for i in range(H.degree))

    got = lift_primitive_johnson_to_ground_relation(H, source, target)
    assert got.status == "exact_johnson_ground_relational_lift", got
    assert (got.ground_size, got.subset_size, got.current_degree) == (9, 2, 36)
    assert got.strict_auxiliary_progress
    assert got.equivariant_up_to_johnson_automorphism
    assert len(got.lifted_generators) == len(H.original_generators)
    assert all(not g.complement for g in got.lifted_generators)
    assert sorted(got.source_on_standard_subsets) == sorted(source)
    assert sorted(got.target_on_standard_subsets) == sorted(target)


def test_j63_decoder_preserves_exceptional_complement_bit_exactly():
    v, k = 6, 3
    ident = tuple(range(v))
    p_std = _induce_signed_ground_generator(v, k, ident, True)
    signed = _decode_johnson_automorphism(v, k, p_std)
    assert signed is not None
    assert signed.ground_permutation == ident
    assert signed.complement
    assert _induce_signed_ground_generator(
        v, k, signed.ground_permutation, signed.complement
    ) == p_std
