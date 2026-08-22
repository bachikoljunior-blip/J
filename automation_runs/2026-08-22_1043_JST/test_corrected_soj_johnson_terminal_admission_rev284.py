from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations
from pathlib import Path
import sys
import unittest

_HERE = Path(__file__).resolve().parent
_MAIN_RUN = _HERE.parent / "2026-08-19_0851_JST"
for _path in (_HERE, _MAIN_RUN):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from corrected_soj_johnson_terminal_admission_v1 import (  # noqa: E402
    admit_corrected_soj_johnson_small_ground_terminal,
    replay_corrected_soj_johnson_small_ground_terminal,
)
from permutation_group_schreier import schreier_stabilizer_chain  # noqa: E402


@dataclass(frozen=True)
class Transition:
    status: str = "certified_corrected_soj_explicit_johnson_embedding"
    transition_kind: str = "johnson_embedding"
    theorem_input_gate: bool = True
    canonical: bool = True
    exact: bool = True
    progress_certified: bool = True
    multiplicative_cost: float = 8.0
    max_multiplicative_cost: float = 16.0
    small_size_before: int | None = None
    small_size_after: int | None = None
    alpha: float | None = None
    johnson_ground_size: int | None = 5
    johnson_subset_size: int | None = 2
    johnson_vertex_count: int | None = 10
    reason: str = "certified test transition"


def _cycle(n: int) -> tuple[int, ...]:
    return tuple((i + 1) % n for i in range(n))


def _transposition(n: int, a: int = 0, b: int = 1) -> tuple[int, ...]:
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _induced_subset_permutation(ground_perm, *, v: int = 5, k: int = 2):
    standard = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(standard)}
    return tuple(
        index[tuple(sorted(ground_perm[x] for x in subset))]
        for subset in standard
    )


def _johnson_fixture():
    coords = tuple(combinations(range(5), 2))
    relation = {
        (i, j): 2 - len(set(coords[i]).intersection(coords[j]))
        for i in range(len(coords))
        for j in range(i + 1, len(coords))
    }
    generators = (
        _induced_subset_permutation(_cycle(5)),
        _induced_subset_permutation(_transposition(5)),
    )
    group = schreier_stabilizer_chain(generators)
    return coords, relation, group


class Rev284CorrectedSOJJohnsonTerminalAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.coords, self.relation, self.group = _johnson_fixture()
        self.transition = Transition()
        self.base = dict(
            embedding=self.coords,
            pair_relation_distance=self.relation,
            group=self.group,
            source_values=(0,) * 10,
            target_values=(0,) * 10,
            root_n=32,
            transition_cost_bound_certified=True,
        )

    def test_exact_nonempty_small_ground_terminal_is_admitted(self):
        result = admit_corrected_soj_johnson_small_ground_terminal(
            self.transition,
            **self.base,
        )
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.status, "certified_corrected_soj_johnson_small_ground_terminal")
        self.assertEqual(result.terminal_proof.status, "exact_primitive_johnson_ground_coset")
        self.assertEqual(result.terminal_proof.johnson_ground_size, 5)
        self.assertEqual(result.terminal_proof.johnson_subset_size, 2)
        self.assertEqual(result.terminal_proof.coset.subgroup.order, 120)
        self.assertTrue(result.identity.replay_stable)
        self.assertTrue(result.admission_digest.startswith("sha256:"))
        self.assertGreaterEqual(result.transition_log2_cost_bound, 4.0)

    def test_exact_empty_small_ground_terminal_is_admitted(self):
        target = (1,) + (0,) * 9
        result = admit_corrected_soj_johnson_small_ground_terminal(
            self.transition,
            **{**self.base, "target_values": target},
        )
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.terminal_proof.status, "exact_empty_primitive_johnson_ground")
        self.assertIsNone(result.terminal_proof.coset)

    def test_pair_relation_tamper_fails_closed(self):
        bad = dict(self.relation)
        bad[(0, 1)] += 1
        result = admit_corrected_soj_johnson_small_ground_terminal(
            self.transition,
            **{**self.base, "pair_relation_distance": bad},
        )
        self.assertFalse(result.certified)
        self.assertIn("intersection relation", result.reason)
        self.assertIsNone(result.terminal_proof)

    def test_ambient_generator_must_preserve_supplied_johnson_relation(self):
        arbitrary_swap = _transposition(10, 0, 1)
        bad_group = schreier_stabilizer_chain((arbitrary_swap,))
        result = admit_corrected_soj_johnson_small_ground_terminal(
            self.transition,
            **{**self.base, "group": bad_group},
        )
        self.assertFalse(result.certified)
        self.assertIn("does not preserve", result.reason)
        self.assertIsNone(result.terminal_proof)

    def test_transition_shape_and_cost_certificate_are_required(self):
        wrong = replace(self.transition, status="corrected_soj_transition_not_certified")
        result = admit_corrected_soj_johnson_small_ground_terminal(wrong, **self.base)
        self.assertFalse(result.certified)
        self.assertIn("certified explicit Johnson", result.reason)

        no_cost = admit_corrected_soj_johnson_small_ground_terminal(
            self.transition,
            **{**self.base, "transition_cost_bound_certified": False},
        )
        self.assertFalse(no_cost.certified)
        self.assertIn("cost certificate", no_cost.reason)

    def test_small_ground_cap_stays_recursive_and_fail_closed(self):
        result = admit_corrected_soj_johnson_small_ground_terminal(
            self.transition,
            **self.base,
            max_ground_degree=4,
        )
        self.assertFalse(result.certified)
        self.assertEqual(
            result.status,
            "corrected_soj_johnson_requires_recursive_ground_handling",
        )
        self.assertEqual(result.terminal_proof.status, "undetermined_johnson_ground_cap")

    def test_opaque_identity_and_forced_envelope_failure_are_rejected(self):
        opaque = object()
        result = admit_corrected_soj_johnson_small_ground_terminal(
            self.transition,
            **{**self.base, "source_values": (opaque,) + (0,) * 9},
        )
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "unstable_corrected_soj_johnson_terminal_identity")

        tiny = admit_corrected_soj_johnson_small_ground_terminal(
            self.transition,
            **self.base,
            quasipoly_constant=1e-12,
        )
        self.assertFalse(tiny.certified)
        self.assertEqual(tiny.status, "corrected_soj_johnson_terminal_envelope_exceeded")

    def test_replay_binds_transition_embedding_group_strings_and_resources(self):
        result = admit_corrected_soj_johnson_small_ground_terminal(
            self.transition,
            **self.base,
        )
        self.assertTrue(result.certified, result.reason)
        self.assertTrue(
            replay_corrected_soj_johnson_small_ground_terminal(
                result,
                self.transition,
                **self.base,
            )
        )
        tampered = dict(self.relation)
        tampered[(0, 1)] += 1
        self.assertFalse(
            replay_corrected_soj_johnson_small_ground_terminal(
                result,
                self.transition,
                **{**self.base, "pair_relation_distance": tampered},
            )
        )
        self.assertFalse(
            replay_corrected_soj_johnson_small_ground_terminal(
                result,
                replace(self.transition, max_multiplicative_cost=32.0),
                **self.base,
            )
        )


if __name__ == "__main__":
    unittest.main()
