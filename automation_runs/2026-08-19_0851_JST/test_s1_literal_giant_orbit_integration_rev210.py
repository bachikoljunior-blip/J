from math import factorial

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2
from u2_candidate_coset_string_iso_v3 import candidate_coset_string_isomorphism_u3


def _swap(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _symmetric_on_interval(n, start, size):
    return tuple(_swap(n, start + i, start + i + 1) for i in range(size - 1))


def test_s1_v2_reuses_rev208_literal_giant_terminal_above_small_order_cap():
    n = 7
    group = schreier_stabilizer_chain(_symmetric_on_interval(n, 0, n))
    source = (1, 0, 0, 0, 0, 0, 0)

    got = s1_string_isomorphism_v2(
        group,
        source,
        source,
        root_n=64,
        max_group_order=256,
        max_explicit_degree=4,
    )
    assert got.exact and got.coset is not None
    assert "literal_giant" in got.status
    assert got.coset.subgroup.order == factorial(6)


def test_intransitive_candidate_lifts_two_literal_giant_orbit_images_exactly():
    # The parent is not itself S_14/A_14: it is S_7 x S_7 on two invariant
    # orbits.  Candidate-v3 therefore falls through to the existing intransitive
    # U2 recursion.  Each orbit image is a literal S_7 that exceeds the configured
    # small-order cap; rev210 solves those images through the rev208 terminal and
    # the existing exact orbit-action preimage lifts both constraints back through
    # their kernels.
    n = 14
    gens = _symmetric_on_interval(n, 0, 7) + _symmetric_on_interval(n, 7, 7)
    group = schreier_stabilizer_chain(gens)
    assert group.order == factorial(7) ** 2

    source = (1, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0)
    candidate = RightCoset(group, identity(n))
    got = candidate_coset_string_isomorphism_u3(
        candidate,
        source,
        source,
        root_n=64,
        max_group_order=256,
        max_explicit_degree=4,
    )

    assert got.exact and got.coset is not None, got.reason
    assert got.coset.subgroup.order == factorial(6) ** 2
    assert got.status == "exact_candidate_coset_string_isomorphism_v2"
