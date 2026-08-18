from jagi_eval.sealed_suite import validate_sealed_suite


def candidate():
    return {
        "artifact_sha256": "a" * 64,
        "frozen_at": "2026-08-18T10:00:00Z",
        "lineage_root": "lineage-a",
    }


def suite():
    return {
        "suite_id": "sealed-001",
        "suite_sha256": "b" * 64,
        "created_at": "2026-08-18T10:01:00Z",
        "state": "sealed",
        "answers_accessible_to_candidate": False,
        "developer_has_task_access": False,
        "tasks": [
            {
                "sha256": "c" * 64,
                "generated_at": "2026-08-18T10:02:00Z",
                "template_id": "template-1",
                "cluster_id": "cluster-1",
            }
        ],
    }


def test_fresh_post_freeze_suite_is_eligible():
    result = validate_sealed_suite(suite(), candidate())
    assert result.eligible, result.reasons


def test_pre_freeze_task_is_rejected():
    s = suite()
    s["tasks"][0]["generated_at"] = "2026-08-18T09:59:00Z"
    assert not validate_sealed_suite(s, candidate()).eligible


def test_descendant_cannot_reuse_exposed_suite():
    c = candidate()
    c["artifact_sha256"] = "d" * 64
    exposures = [
        {
            "suite_id": "sealed-001",
            "lineage_root": "lineage-a",
            "artifact_sha256": "a" * 64,
            "reason": "scored_reveal",
        }
    ]
    result = validate_sealed_suite(suite(), c, exposures)
    assert not result.eligible
    assert any("lineage" in reason for reason in result.reasons)


def test_same_frozen_candidate_can_only_rerun_verified_infrastructure_failure():
    exposure = {
        "suite_id": "sealed-001",
        "lineage_root": "lineage-a",
        "artifact_sha256": "a" * 64,
        "reason": "verified_infrastructure_rerun",
    }
    assert validate_sealed_suite(suite(), candidate(), [exposure]).eligible
    exposure["reason"] = "scored_reveal"
    assert not validate_sealed_suite(suite(), candidate(), [exposure]).eligible
