from itertools import permutations

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from bounded_relation_image_coset_v1 import exact_bounded_relation_image_coset
from exact_result_replay_verifier_v1 import ReplayCaps


def image(edges):
    return BoundedArityRelationImage(
        range(4),
        (
            RelationSpec("marked", 1, ((0,),)),
            RelationSpec("arc", 2, edges),
        ),
    )


def s4():
    return tuple(permutations(range(4)))


def test_complete_nonempty_coset_and_target_stabilizer():
    source = image(((0, 1), (1, 2), (2, 3)))
    target = BoundedArityRelationImage(
        range(4),
        (
            RelationSpec("marked", 1, ((2,),)),
            RelationSpec("arc", 2, ((2, 0), (0, 3), (3, 1))),
        ),
    )
    got = exact_bounded_relation_image_coset(
        source, target, s4(),
        caps=ReplayCaps(max_degree=64, max_group_size=30),
    )
    assert got.exact and got.complete
    assert got.match_count == 1
    assert len(got.target_stabilizer) == 1
    assert got.replay.accepted


def test_exact_empty_same_degree_and_signature():
    source = image(((0, 1), (1, 2), (2, 3)))
    target = image(((0, 1), (0, 2), (0, 3)))
    got = exact_bounded_relation_image_coset(
        source, target, s4(),
        caps=ReplayCaps(max_degree=64, max_group_size=30),
    )
    assert got.exact and got.complete
    assert got.matches == ()
    assert got.representative is None


def test_symmetric_result_is_complete_right_coset():
    cycle = image(((0, 1), (1, 2), (2, 3), (3, 0)))
    got = exact_bounded_relation_image_coset(
        cycle, cycle, s4(),
        caps=ReplayCaps(max_degree=64, max_group_size=30),
    )
    assert got.exact
    assert got.match_count == len(got.target_stabilizer) == 1  # marked vertex fixes rotation gauge
    assert set(got.matches) == set(got.target_stabilizer)


def test_auxiliary_degree_cap_rejects_before_matching():
    source = image(((0, 1),))
    got = exact_bounded_relation_image_coset(
        source, source, s4(),
        caps=ReplayCaps(max_degree=23, max_group_size=30),
    )
    assert got.status == "undetermined_auxiliary_degree_cap"
    assert not got.exact and got.replay is None


def test_invalid_explicit_group_fails_closed_in_independent_replay():
    source = image(((0, 1),))
    got = exact_bounded_relation_image_coset(
        source, source, ((0, 1, 2, 3), (1, 2, 0, 3)),
        caps=ReplayCaps(max_degree=64, max_group_size=30),
    )
    assert got.status == "fail_closed_replay_invalid_certificate"
    assert not got.exact


def test_duplicate_candidate_is_rejected_by_faithful_point_layer():
    source = BoundedArityRelationImage(range(2), ())
    got = exact_bounded_relation_image_coset(
        source, source, ((0, 1), (0, 1)),
        caps=ReplayCaps(max_degree=8, max_group_size=8),
    )
    assert got.status == "fail_closed_replay_invalid_certificate"


def test_signature_mismatch_is_exact_empty_without_group_scan():
    source = BoundedArityRelationImage(range(2), (RelationSpec("u", 1, ()),))
    target = BoundedArityRelationImage(range(2), (RelationSpec("v", 1, ()),))
    got = exact_bounded_relation_image_coset(source, target, ())
    assert got.status == "exact_empty_relation_signature_mismatch"
    assert got.exact and got.complete
