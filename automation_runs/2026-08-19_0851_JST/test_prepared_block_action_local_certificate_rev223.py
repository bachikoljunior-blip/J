from __future__ import annotations

import block_action_preimage_coset_v1 as _preimage
from block_action_preimage_coset_v1 import (
    block_action_preimage_coset,
    lift_prepared_block_action_preimage,
    prepare_block_action_preimage,
)
from local_certificate_beard_v1 import local_certificate_beard
from local_fullness_certificates import _alternating_test_generators
from permutation_group_schreier import schreier_stabilizer_chain


def _symmetric_with_independent_pair(k):
    n = k + 2
    identity = list(range(n))
    swap01 = identity.copy()
    swap01[0], swap01[1] = 1, 0
    cycle = identity.copy()
    for i in range(k):
        cycle[i] = (i + 1) % k
    extra = identity.copy()
    extra[k], extra[k + 1] = k + 1, k
    return (
        schreier_stabilizer_chain((tuple(swap01), tuple(cycle), tuple(extra))),
        tuple((i,) for i in range(k)),
    )


def _cyclic_with_independent_pair(k):
    n = k + 2
    identity = list(range(n))
    cycle = identity.copy()
    for i in range(k):
        cycle[i] = (i + 1) % k
    extra = identity.copy()
    extra[k], extra[k + 1] = k + 1, k
    return (
        schreier_stabilizer_chain((tuple(cycle), tuple(extra))),
        tuple((i,) for i in range(k)),
    )


def test_prepared_lifts_equal_one_shot_exact_preimages():
    group, blocks = _symmetric_with_independent_pair(9)
    prepared = prepare_block_action_preimage(group, blocks)
    for target in _alternating_test_generators(9, tuple(range(9))):
        shared = lift_prepared_block_action_preimage(prepared, target)
        one_shot = block_action_preimage_coset(group, blocks, target)
        assert shared.status == one_shot.status == "exact_block_action_preimage_coset"
        assert shared.representative == one_shot.representative
        assert shared.kernel.order == one_shot.kernel.order
        assert shared.coset is not None and one_shot.coset is not None
        assert shared.coset.subgroup.order == one_shot.coset.subgroup.order


def test_one_beard_builds_the_block_homomorphism_once(monkeypatch):
    group, blocks = _symmetric_with_independent_pair(9)
    original = _preimage._paired_chain
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(_preimage, "_paired_chain", counted)
    got = local_certificate_beard(group, blocks, (0,) * group.degree, tuple(range(9)))
    assert got.status == "certified_full_by_stable_beard"
    assert len(_alternating_test_generators(9, tuple(range(9)))) > 1
    assert calls == 1


def test_prepared_outside_image_failure_matches_one_shot():
    group, blocks = _cyclic_with_independent_pair(5)
    prepared = prepare_block_action_preimage(group, blocks)
    target = (1, 0, 2, 3, 4)
    got = lift_prepared_block_action_preimage(prepared, target)
    one_shot = block_action_preimage_coset(group, blocks, target)
    assert got.status == one_shot.status == "quotient_not_in_image"
    assert got.representative is one_shot.representative is None
