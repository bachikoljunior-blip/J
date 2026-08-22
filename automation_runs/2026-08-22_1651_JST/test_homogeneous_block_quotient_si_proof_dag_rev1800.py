from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from coset_stabilizer_primitives import RightCoset
from homogeneous_block_action_kernel_v1 import certify_block_action_kernel_factorization
from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance
from homogeneous_block_quotient_si_proof_dag_consumer_v1 import (
    STATUS_EMPTY_INVENTORY,
    STATUS_EMPTY_ORBIT,
    STATUS_EXACT,
    homogeneous_block_quotient_si_proof_dag_consumer,
    replay_homogeneous_block_quotient_si_snapshot,
    snapshot_public_rev1200_result,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain

SWAP_BLOCKS = (2, 3, 0, 1)


@dataclass(frozen=True)
class PublicRev1200Result:
    status: str
    exact: bool
    complete: bool
    block_count: int
    quotient_group_order: int
    partition_orbit_states: int
    target_stabilizer_order: int
    coset: object | None
    provenance_digest: str
    factorization_digest: str
    reason: str = "public-contract fixture"


def paired(*, block_bijection=(0, 1), with_swap=True):
    generators = (SWAP_BLOCKS,) if with_swap else ()
    provenance = certify_group_block_action_equivariance(
        ((0, 1), (2, 3)),
        ((0, 1), (2, 3)),
        block_bijection,
        generators,
        generators,
    )
    if not provenance.exact:
        raise AssertionError(provenance.reason)
    factorization = certify_block_action_kernel_factorization(provenance)
    if not factorization.exact:
        raise AssertionError(factorization.reason)
    return provenance, factorization


def public_from_snapshot(snapshot):
    coset = None
    if snapshot.status == STATUS_EXACT:
        subgroup = schreier_stabilizer_chain(
            snapshot.target_stabilizer_generators or (identity(snapshot.block_count),)
        )
        coset = RightCoset(subgroup, snapshot.representative)
    return PublicRev1200Result(
        snapshot.status,
        snapshot.exact,
        snapshot.complete,
        snapshot.block_count,
        snapshot.quotient_group_order,
        snapshot.partition_orbit_states,
        snapshot.target_stabilizer_order,
        coset,
        snapshot.provenance_digest,
        snapshot.factorization_digest,
    )


def exact_public(provenance, factorization, source, target, *, cap=64):
    snapshot = replay_homogeneous_block_quotient_si_snapshot(
        provenance, factorization, source, target, max_partition_states=cap
    )
    return snapshot, public_from_snapshot(snapshot)


class Rev1800HomogeneousBlockQuotientSIProofDAGTests(unittest.TestCase):
    def test_nonempty_public_result_replays_into_certified_terminal(self):
        provenance, factorization = paired()
        snapshot, public = exact_public(
            provenance, factorization, ("red", "blue"), ("blue", "red")
        )
        self.assertEqual(snapshot.status, STATUS_EXACT)
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance,
            factorization,
            ("red", "blue"),
            ("blue", "red"),
            public,
            max_partition_states=64,
        )
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.snapshot, snapshot)
        self.assertTrue(result.proof.coset.contains((1, 0)))
        self.assertFalse(result.proof.coset.contains(identity(2)))
        self.assertTrue(result.identity_validation.certified)
        self.assertTrue(result.dag_validation.certified)

    def test_constant_features_preserve_complete_quotient_stabilizer(self):
        provenance, factorization = paired()
        snapshot, public = exact_public(
            provenance, factorization, ("same", "same"), ("same", "same")
        )
        self.assertEqual(snapshot.target_stabilizer_order, 2)
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("same", "same"), ("same", "same"), public,
            max_partition_states=64,
        )
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.proof.coset.subgroup.order, 2)

    def test_inventory_exact_empty_is_a_certified_empty_terminal(self):
        provenance, factorization = paired()
        snapshot, public = exact_public(
            provenance, factorization, ("a", "a"), ("a", "b")
        )
        self.assertEqual(snapshot.status, STATUS_EMPTY_INVENTORY)
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("a", "a"), ("a", "b"), public,
            max_partition_states=64,
        )
        self.assertTrue(result.certified, result.reason)
        self.assertIsNone(result.proof.coset)
        self.assertEqual(result.proof.permutation_candidates_checked, 0)

    def test_completed_orbit_exact_empty_is_certified(self):
        provenance, factorization = paired(with_swap=False)
        snapshot, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        self.assertEqual(snapshot.status, STATUS_EMPTY_ORBIT)
        self.assertEqual(snapshot.partition_orbit_states, 1)
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("a", "b"), ("b", "a"), public,
            max_partition_states=64,
        )
        self.assertTrue(result.certified, result.reason)
        self.assertIsNone(result.proof.coset)

    def test_nonidentity_block_bijection_remains_cross_coordinate_only(self):
        provenance, factorization = paired(block_bijection=(1, 0), with_swap=False)
        snapshot, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        self.assertEqual(snapshot.representative, (1, 0))
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("a", "b"), ("b", "a"), public,
            max_partition_states=64,
        )
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(tuple(result.proof.coset.representative), (1, 0))

    def test_state_cap_exhaustion_is_rejected_not_exact_empty(self):
        provenance, factorization = paired()
        _, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a"), cap=64
        )
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("a", "b"), ("b", "a"), public,
            max_partition_states=1,
        )
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rejected_homogeneous_block_quotient_si_identity")
        self.assertIn("undetermined", result.reason)

    def test_public_snapshot_tamper_is_rejected(self):
        provenance, factorization = paired()
        snapshot, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        tampered = replace(public, partition_orbit_states=snapshot.partition_orbit_states + 1)
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("a", "b"), ("b", "a"), tampered,
            max_partition_states=64,
        )
        self.assertFalse(result.certified)
        self.assertIn("differs from the independent", result.reason)

    def test_nonexact_public_status_is_rejected(self):
        provenance, factorization = paired()
        _, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        nonexact = replace(
            public,
            status="undetermined_homogeneous_block_quotient_partition_orbit_limit",
            exact=False,
            complete=False,
        )
        with self.assertRaises(ValueError):
            snapshot_public_rev1200_result(nonexact)
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("a", "b"), ("b", "a"), nonexact,
            max_partition_states=64,
        )
        self.assertFalse(result.certified)

    def test_tampered_factorization_is_rejected(self):
        provenance, factorization = paired()
        _, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        tampered = replace(
            factorization,
            quotient_image_order=factorization.quotient_image_order + 1,
        )
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, tampered,
            ("a", "b"), ("b", "a"), public,
            max_partition_states=64,
        )
        self.assertFalse(result.certified)

    def test_tampered_provenance_is_rejected(self):
        provenance, factorization = paired()
        _, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        tampered = replace(provenance, block_bijection=(1, 0))
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            tampered, factorization,
            ("a", "b"), ("b", "a"), public,
            max_partition_states=64,
        )
        self.assertFalse(result.certified)

    def test_invalid_cap_and_root_fail_closed(self):
        provenance, factorization = paired()
        _, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        bad_cap = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("a", "b"), ("b", "a"), public,
            max_partition_states=True,
        )
        self.assertFalse(bad_cap.certified)
        bad_root = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("a", "b"), ("b", "a"), public,
            root_n=2,
            max_partition_states=64,
        )
        self.assertFalse(bad_root.certified)

    def test_snapshot_rejects_malformed_digest(self):
        provenance, factorization = paired()
        _, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        with self.assertRaises(ValueError):
            snapshot_public_rev1200_result(replace(public, provenance_digest="bad"))

    def test_proof_identity_is_hashable_and_replay_stable(self):
        provenance, factorization = paired()
        _, public = exact_public(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        result = homogeneous_block_quotient_si_proof_dag_consumer(
            provenance, factorization,
            ("a", "b"), ("b", "a"), public,
            max_partition_states=64,
        )
        self.assertTrue(result.certified, result.reason)
        identity_value = result.proof.proof_identity
        self.assertTrue(identity_value.replay_stable)
        self.assertIsInstance(hash(identity_value), int)


if __name__ == "__main__":
    unittest.main()
