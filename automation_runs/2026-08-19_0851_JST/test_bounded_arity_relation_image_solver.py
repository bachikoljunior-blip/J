import unittest

from bounded_arity_relation_image_solver import (
    BoundedArityRelationImage,
    RelationSpec,
    find_bounded_arity_relation_image_isomorphism,
    verify_bounded_arity_relation_image_isomorphism,
)


def _undirected_edges(pairs):
    return frozenset(
        directed
        for left, right in pairs
        for directed in ((left, right), (right, left))
    )


class BoundedArityRelationImageSolverTests(unittest.TestCase):
    def test_finds_and_verifies_relabelled_unary_binary_witness(self):
        source = BoundedArityRelationImage(
            ("a", "b", "c", "d"),
            (
                RelationSpec("anchor", 1, (("a",),)),
                RelationSpec("left_block", 1, (("a",), ("b",))),
                RelationSpec(
                    "step",
                    2,
                    (("a", "a"), ("a", "c"), ("c", "b"), ("b", "d"), ("d", "a")),
                ),
            ),
        )
        expected = {"a": 30, "b": 10, "c": 40, "d": 20}
        target = BoundedArityRelationImage(
            (10, 20, 30, 40),
            (
                RelationSpec(
                    "step",
                    2,
                    tuple((expected[left], expected[right]) for left, right in source.relation("step").tuples),
                ),
                RelationSpec("left_block", 1, ((30,), (10,))),
                RelationSpec("anchor", 1, ((30,),)),
            ),
        )

        witness = find_bounded_arity_relation_image_isomorphism(source, target)

        self.assertIsNotNone(witness)
        assert witness is not None
        self.assertTrue(witness.exact)
        self.assertEqual(witness.mapping, expected)
        self.assertEqual(witness.image_of("c"), 40)
        self.assertTrue(
            verify_bounded_arity_relation_image_isomorphism(source, target, witness.mapping)
        )

    def test_exactly_rejects_same_degree_profile_nonisomorphic_graphs(self):
        cycle_six = BoundedArityRelationImage(
            tuple(range(6)),
            (
                RelationSpec(
                    "adjacent",
                    2,
                    _undirected_edges(((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0))),
                ),
            ),
        )
        two_triangles = BoundedArityRelationImage(
            tuple("abcdef"),
            (
                RelationSpec(
                    "adjacent",
                    2,
                    _undirected_edges(
                        (("a", "b"), ("b", "c"), ("c", "a"), ("d", "e"), ("e", "f"), ("f", "d"))
                    ),
                ),
            ),
        )

        self.assertIsNone(
            find_bounded_arity_relation_image_isomorphism(cycle_six, two_triangles)
        )

    def test_symmetric_instance_returns_deterministic_first_witness(self):
        source = BoundedArityRelationImage(
            (0, 1, 2, 3),
            (RelationSpec("edge", 2, _undirected_edges(((0, 1), (1, 2), (2, 3), (3, 0)))),),
        )
        target_domain = ("z", "x", "w", "y")
        target = BoundedArityRelationImage(
            target_domain,
            (
                RelationSpec(
                    "edge",
                    2,
                    _undirected_edges((("z", "x"), ("x", "w"), ("w", "y"), ("y", "z"))),
                ),
            ),
        )

        first = find_bounded_arity_relation_image_isomorphism(source, target)
        second = find_bounded_arity_relation_image_isomorphism(source, target)

        self.assertIsNotNone(first)
        self.assertEqual(first, second)
        assert first is not None
        self.assertEqual(first.mapping, {0: "z", 1: "x", 2: "w", 3: "y"})

    def test_empty_structures_have_empty_exact_witness(self):
        source = BoundedArityRelationImage((), (RelationSpec("empty", 2, ()),))
        target = BoundedArityRelationImage((), (RelationSpec("empty", 2, ()),))

        witness = find_bounded_arity_relation_image_isomorphism(source, target)

        self.assertIsNotNone(witness)
        assert witness is not None
        self.assertEqual(witness.mapping, {})
        self.assertEqual(witness.candidates_checked, 0)

    def test_relation_signature_mismatch_is_rejected(self):
        source = BoundedArityRelationImage((0,), (RelationSpec("mark", 1, ((0,),)),))
        wrong_name = BoundedArityRelationImage((1,), (RelationSpec("other", 1, ((1,),)),))
        wrong_cardinality = BoundedArityRelationImage((1,), (RelationSpec("mark", 1, ()),))

        self.assertIsNone(find_bounded_arity_relation_image_isomorphism(source, wrong_name))
        self.assertIsNone(
            find_bounded_arity_relation_image_isomorphism(source, wrong_cardinality)
        )
        self.assertFalse(
            verify_bounded_arity_relation_image_isomorphism(source, wrong_name, {0: 1})
        )

    def test_input_contract_rejects_unsupported_or_malformed_relations(self):
        with self.assertRaisesRegex(ValueError, "arity 1 or 2"):
            RelationSpec("ternary", 3, ((0, 1, 2),))
        with self.assertRaisesRegex(ValueError, "tuple of length"):
            RelationSpec("binary", 2, ((0,),))
        with self.assertRaisesRegex(ValueError, "outside the domain"):
            BoundedArityRelationImage((0,), (RelationSpec("mark", 1, ((1,),)),))
        with self.assertRaisesRegex(ValueError, "duplicate relation name"):
            BoundedArityRelationImage(
                (0,),
                (RelationSpec("mark", 1, ()), RelationSpec("mark", 1, ((0,),))),
            )


if __name__ == "__main__":
    unittest.main()
