from dataclasses import replace

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from bounded_relation_image_coset_v1 import _induced_permutation, _relation_signature
from coset_stabilizer_primitives import RightCoset
from implicit_relation_image_parent_promotion_v1 import promote_nonempty_exact_relation_preimage
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _image(unary, binary=()):
    return BoundedArityRelationImage(
        ("a", "b", "c"),
        (
            RelationSpec(
                "U",
                1,
                (("a",),) if unary == 0 else (("b",),) if unary == 1 else (("c",),),
            ),
            RelationSpec("R", 2, binary),
        ),
    )


def _s3():
    return schreier_stabilizer_chain(((1, 0, 2), (0, 2, 1)))


def _exact_preimage(source, *, target_stabilizer_generator=(2, 1, 0), representative=(1, 0, 2)):
    domain = _s3()
    signature = _relation_signature(source)
    image_generators = tuple(
        _induced_permutation(generator, signature, domain.degree)
        for generator in domain.original_generators
    )
    image_target_stabilizer = schreier_stabilizer_chain(
        (_induced_permutation(target_stabilizer_generator, signature, domain.degree),)
    )
    image_representative = _induced_permutation(representative, signature, domain.degree)
    preimage = paired_action_coset_preimage(
        domain,
        image_generators,
        RightCoset(image_target_stabilizer, image_representative),
    )
    assert preimage.status == "exact_paired_action_coset_preimage"
    return domain, preimage


def test_promotes_complete_nonempty_original_domain_coset():
    source = _image(0, (("a", "b"), ("a", "c")))
    target = _image(1, (("b", "a"), ("b", "c")))
    domain, preimage = _exact_preimage(source)
    result = promote_nonempty_exact_relation_preimage(source, target, domain, preimage)
    assert result.status == "exact_implicit_relation_parent_coset"
    assert result.exact and result.complete
    assert result.coset == preimage.coset
    assert result.domain_order == 6
    assert result.preimage_subgroup_order == 2
    assert result.image_order == 6
    assert result.kernel_order == 1


def test_rejects_nonexact_upstream_status():
    source = _image(0)
    target = _image(1)
    domain, preimage = _exact_preimage(source)
    preimage = replace(preimage, status="undetermined_cap")
    result = promote_nonempty_exact_relation_preimage(source, target, domain, preimage)
    assert result.status == "fail_closed_upstream_preimage_status"
    assert not result.exact


def test_rejects_wrong_preimage_order_evidence():
    source = _image(0)
    target = _image(1)
    domain, preimage = _exact_preimage(source)
    preimage = replace(preimage, preimage_subgroup_order=3)
    result = promote_nonempty_exact_relation_preimage(source, target, domain, preimage)
    assert result.status == "fail_closed_preimage_order_identity"


def test_rejects_representative_that_does_not_transport_full_relation():
    source = _image(0, (("a", "b"), ("a", "c")))
    target = _image(1, (("b", "a"), ("b", "c")))
    domain, preimage = _exact_preimage(source)
    assert preimage.coset is not None
    broken_coset = RightCoset(preimage.coset.subgroup, identity(3))
    preimage = replace(preimage, representative=identity(3), coset=broken_coset)
    result = promote_nonempty_exact_relation_preimage(source, target, domain, preimage)
    assert result.status == "fail_closed_representative_not_full_relation_transporter"


def test_rejects_subgroup_generator_that_moves_target_relation():
    source = _image(0)
    target = _image(1)
    domain, preimage = _exact_preimage(source)
    bad_subgroup = schreier_stabilizer_chain(((0, 2, 1),))
    assert preimage.coset is not None
    broken_coset = RightCoset(bad_subgroup, preimage.coset.representative)
    preimage = replace(
        preimage,
        target_subgroup_order=2,
        preimage_subgroup_order=2,
        preimage_subgroup=bad_subgroup,
        coset=broken_coset,
    )
    result = promote_nonempty_exact_relation_preimage(source, target, domain, preimage)
    assert result.status == "fail_closed_subgroup_not_target_relation_stabilizer"


def test_signature_mismatch_fails_closed():
    source = BoundedArityRelationImage((0, 1, 2), (RelationSpec("U", 1, ((0,),)),))
    target = BoundedArityRelationImage((0, 1, 2), (RelationSpec("V", 1, ((1,),)),))
    domain, preimage = _exact_preimage(source)
    result = promote_nonempty_exact_relation_preimage(source, target, domain, preimage)
    assert result.status == "fail_closed_relation_signature_mismatch"


def test_action_cap_is_checked_before_relation_transport():
    source = _image(0)
    target = _image(1)
    domain, preimage = _exact_preimage(source)
    result = promote_nonempty_exact_relation_preimage(
        source,
        target,
        domain,
        preimage,
        max_relation_action_point_checks=1,
    )
    assert result.status == "undetermined_parent_relation_action_cap"
    assert not result.exact


def test_membership_sift_cap_fails_closed_before_sifts():
    source = _image(0)
    target = _image(1)
    domain, preimage = _exact_preimage(source)
    result = promote_nonempty_exact_relation_preimage(
        source,
        target,
        domain,
        preimage,
        max_membership_sifts=1,
    )
    assert result.status == "undetermined_parent_membership_sift_cap"


def test_rejects_corrupted_returned_subgroup_even_when_inside_domain_group():
    source = _image(0)
    target = _image(1)
    domain, preimage = _exact_preimage(source)
    # This transposition subgroup has the same order as the exact target image
    # subgroup but does not stabilize target U={b}. Because the domain is S3,
    # it still passes containment and must be rejected by the semantic gate.
    outside = schreier_stabilizer_chain(((0, 2, 1),))
    assert preimage.coset is not None
    corrupted = replace(
        preimage,
        preimage_subgroup=outside,
        coset=RightCoset(outside, preimage.coset.representative),
    )
    result = promote_nonempty_exact_relation_preimage(source, target, domain, corrupted)
    # S3 contains every degree-three permutation, so this artifact is still in
    # the domain group and reaches the stronger target-stabilizer semantic gate.
    assert result.status == "fail_closed_subgroup_not_target_relation_stabilizer"


def test_rejects_coset_subgroup_disagreeing_with_stored_preimage_subgroup():
    source = _image(0)
    target = _image(1)
    domain, preimage = _exact_preimage(source)
    assert preimage.coset is not None
    other = schreier_stabilizer_chain((identity(3),))
    corrupted = replace(
        preimage,
        coset=RightCoset(other, preimage.coset.representative),
    )
    result = promote_nonempty_exact_relation_preimage(source, target, domain, corrupted)
    assert result.status == "fail_closed_preimage_subgroup_mismatch"


def test_rejects_auxiliary_degree_mismatch():
    source = _image(0)
    target = _image(1)
    domain, preimage = _exact_preimage(source)
    corrupted = replace(preimage, image_degree=preimage.image_degree + 1)
    result = promote_nonempty_exact_relation_preimage(source, target, domain, corrupted)
    assert result.status == "fail_closed_auxiliary_degree_mismatch"
