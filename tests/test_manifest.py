from jagi_eval.manifest import validate_candidate_manifest


def valid_manifest():
    return {
        "candidate_id": "candidate-001",
        "artifact_sha256": "a" * 64,
        "runtime_sha256": "b" * 64,
        "model_boundary": {
            "includes_project_solver": False,
            "allows_undisclosed_remote_cognition": False,
            "components": ["planner", "learner", "memory"],
        },
        "tools": [
            {
                "name": "compiler",
                "category": "deterministic",
                "logs_arguments_digest": True,
                "logs_result_digest": True,
            },
            {
                "name": "browser",
                "category": "retrieval",
                "logs_arguments_digest": True,
                "logs_result_digest": True,
            },
        ],
        "network_endpoints": [
            {"name": "public-web", "declared": True, "provides_general_cognition": False}
        ],
    }


def test_valid_manifest_passes():
    result = validate_candidate_manifest(valid_manifest())
    assert result.valid, result.reasons


def test_project_solver_cannot_be_inside_candidate():
    manifest = valid_manifest()
    manifest["model_boundary"]["includes_project_solver"] = True
    result = validate_candidate_manifest(manifest)
    assert not result.valid


def test_external_general_model_is_rejected():
    manifest = valid_manifest()
    manifest["tools"].append(
        {
            "name": "remote-agi",
            "category": "general_model",
            "logs_arguments_digest": True,
            "logs_result_digest": True,
        }
    )
    result = validate_candidate_manifest(manifest)
    assert not result.valid
    assert any("prohibited" in reason for reason in result.reasons)


def test_undeclared_endpoint_is_rejected():
    manifest = valid_manifest()
    manifest["network_endpoints"].append(
        {"name": "mystery", "declared": False, "provides_general_cognition": False}
    )
    assert not validate_candidate_manifest(manifest).valid
