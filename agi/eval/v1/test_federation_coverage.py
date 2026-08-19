from federation_coverage import validate_federation_coverage


def participant(pid, control, signing, impl, *, roles=(), audited=True):
    return {
        "participant_id": pid,
        "control_lineage": control,
        "signing_principal": signing,
        "externally_audited": audited,
        "roles": list(roles),
        "sealed_generator_assignments": [
            {"domain": "math", "family": "novel", "implementation_lineage": impl}
        ],
    }


def test_complete_independent_coverage_passes():
    required = {("math", "novel")}
    records = [
        participant("a", "org-a", "sig-a", "impl-a", roles=("human_calibration", "independent_rerun")),
        participant("b", "org-b", "sig-b", "impl-b", roles=("security_autonomy_observer",)),
    ]
    assert validate_federation_coverage(records, required) == []


def test_relabelled_same_control_fails():
    required = {("math", "novel")}
    records = [
        participant("a1", "same-org", "sig-a", "impl-a", roles=("human_calibration", "independent_rerun", "security_autonomy_observer")),
        participant("a2", "same-org", "sig-b", "impl-b"),
    ]
    errors = validate_federation_coverage(records, required)
    assert any("control_lineage" in e for e in errors)


def test_missing_observer_role_fails_closed():
    required = {("math", "novel")}
    records = [
        participant("a", "org-a", "sig-a", "impl-a", roles=("human_calibration", "independent_rerun")),
        participant("b", "org-b", "sig-b", "impl-b"),
    ]
    errors = validate_federation_coverage(records, required)
    assert "role security_autonomy_observer has no assigned participant" in errors


def test_unaudited_role_does_not_satisfy_gate():
    required = {("math", "novel")}
    records = [
        participant("a", "org-a", "sig-a", "impl-a", roles=("human_calibration", "independent_rerun")),
        participant("b", "org-b", "sig-b", "impl-b", roles=("security_autonomy_observer",), audited=False),
    ]
    errors = validate_federation_coverage(records, required)
    assert "role security_autonomy_observer has no externally audited participant" in errors
