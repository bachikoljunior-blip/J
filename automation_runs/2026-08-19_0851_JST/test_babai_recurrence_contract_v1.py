from babai_recurrence_contract_v1 import (
    RecurrenceCertificate,
    RecurrenceChild,
    validate_babai_recurrence_step,
)


def test_verified_canonical_shrinking_step():
    cert = RecurrenceCertificate(
        parent_domain_size=100,
        children=(
            RecurrenceChild(70, multiplicity=2, canonical_partition_cells=(40, 60)),
            RecurrenceChild(55, multiplicity=1, canonical_partition_cells=(40, 60)),
        ),
        progress_kind="local_certificate_partition",
        local_certificate_count=12,
        canonical=True,
        complexity_charge=3,
        reason="fixture",
    )
    r = validate_babai_recurrence_step(cert, max_branch_factor=4)
    assert r.status == "verified_local_recurrence_step"
    assert r.progress_verified
    assert r.charged_log2_work >= 3


def test_noncanonical_step_fails_closed():
    cert = RecurrenceCertificate(
        20, (RecurrenceChild(10),), "fixture", 1, False, 0, "fixture"
    )
    assert not validate_babai_recurrence_step(cert).progress_verified


def test_nonshrinking_child_fails_closed():
    cert = RecurrenceCertificate(
        20, (RecurrenceChild(20),), "fixture", 1, True, 0, "fixture"
    )
    r = validate_babai_recurrence_step(cert)
    assert r.status == "insufficient_progress"
    assert not r.progress_verified


def test_partition_must_cover_parent():
    cert = RecurrenceCertificate(
        20, (RecurrenceChild(10, canonical_partition_cells=(5, 5)),),
        "fixture", 1, True, 0, "fixture"
    )
    assert validate_babai_recurrence_step(cert).status == "invalid_partition"


def test_branch_budget_fails_closed():
    cert = RecurrenceCertificate(
        20, (RecurrenceChild(10, multiplicity=5),), "fixture", 1, True, 0, "fixture"
    )
    assert validate_babai_recurrence_step(cert, max_branch_factor=4).status == "branch_limit_exceeded"
