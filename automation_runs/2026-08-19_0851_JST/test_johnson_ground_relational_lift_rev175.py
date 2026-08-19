from itertools import combinations

from johnson_ground_relational_lift_v1 import (
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


def induced_action(v, k, *, include_complement=False):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}
    universe = set(range(v))

    def induce(sigma, complement=False):
        out = []
        for subset in subsets:
            moved = tuple(sorted(sigma[x] for x in subset))
            if complement:
                moved = tuple(sorted(universe.difference(moved)))
            out.append(index[moved])
        return tuple(out)

    generators = [induce(swap01(v)), induce(cycle(v))]
    if include_complement:
        generators.append(induce(tuple(range(v)), complement=True))
    return schreier_stabilizer_chain(generators)


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


def test_j63_preserves_exceptional_complement_coset_in_ground_lift():
    H = induced_action(6, 3, include_complement=True)
    source = tuple(i % 3 for i in range(H.degree))
    target = tuple((i // 2) % 4 for i in range(H.degree))

    got = lift_primitive_johnson_to_ground_relation(H, source, target)
    assert got.status == "exact_johnson_ground_relational_lift", got
    assert (got.ground_size, got.subset_size, got.current_degree) == (6, 3, 20)
    assert got.strict_auxiliary_progress
    assert any(g.complement for g in got.lifted_generators)
    for signed in got.lifted_generators:
        induced = _induce_signed_ground_generator(
            got.ground_size,
            got.subset_size,
            signed.ground_permutation,
            signed.complement,
        )
        assert sorted(induced) == list(range(got.current_degree))
