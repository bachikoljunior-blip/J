import hashlib
import json

import pytest

import qualify_sealed_banks as qsb
from eval_core import REQUIRED_DOMAINS
from freeze_sealed_banks import freeze


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def registry():
    families = {domain: [f"{domain}_heldout"] for domain in sorted(REQUIRED_DOMAINS)}
    banks = []
    for domain in sorted(REQUIRED_DOMAINS):
        for lineage in ("alpha", "beta"):
            prefix = f"{domain}-{lineage}"
            banks.append(
                {
                    "bank_id": prefix,
                    "domain": domain,
                    "families": families[domain],
                    "custody_group": f"custody-{prefix}",
                    "implementation_lineage": f"impl-{prefix}",
                    "visibility": "sealed_nonpublic",
                    "protocol": "agi-taskgen-request-v1",
                    "sealed_content_commitment": h(prefix + "-content"),
                    "seed_schedule_commitment": h(prefix + "-seed"),
                    "provider": {
                        "type": "container",
                        "image": f"private.invalid/{prefix}",
                        "digest": "sha256:" + h(prefix + "-image"),
                        "network": "none",
                    },
                }
            )
    return {
        "schema": "agi-sealed-bank-registry-v1",
        "minimum_independent_custodies_per_family": 2,
        "required_families": families,
        "banks": banks,
    }


def manifest():
    return {"schema": "test", "domains": sorted(REQUIRED_DOMAINS)}


def test_qualification_report_contains_hashes_not_raw_tasks(monkeypatch):
    reg = registry()
    man = manifest()
    lock = freeze(reg, man)
    digests = {bank["provider"]["image"]: bank["provider"]["digest"] for bank in reg["banks"]}
    monkeypatch.setattr(qsb, "_staged_image_id", lambda image: digests[image])

    raw_marker = "RAW-QUALIFICATION-CONTENT-MUST-NOT-BE-RECORDED"

    def fake_generate(self, *, domain, family, seed, nonce):
        assert seed.startswith(qsb.QUALIFICATION_PREFIX)
        return {
            "public": {"prompt": raw_marker + ":" + domain + ":" + family},
            "private": {"grader": {"type": "boolean", "expected": True}, "private_note": raw_marker},
        }

    monkeypatch.setattr(qsb.SealedBankProvider, "generate", fake_generate)
    report = qsb.qualify(reg, man, lock, nonce="0123456789abcdef")
    assert report["passed"] is True
    assert len(report["qualified"]) == len(reg["banks"])
    serialized = json.dumps(report)
    assert raw_marker not in serialized
    assert all(row["structural_validation"] == "passed" for row in report["qualified"])


def test_qualification_fails_closed_on_tampered_lock(monkeypatch):
    reg = registry()
    man = manifest()
    lock = freeze(reg, man)
    lock["registry_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="bank lock"):
        qsb.qualify(reg, man, lock, nonce="0123456789abcdef")


def test_qualification_records_staged_digest_failure_without_task_output(monkeypatch):
    reg = registry()
    man = manifest()
    lock = freeze(reg, man)
    monkeypatch.setattr(qsb, "_staged_image_id", lambda image: "sha256:" + "0" * 64)
    report = qsb.qualify(reg, man, lock, nonce="0123456789abcdef")
    assert report["passed"] is False
    assert report["qualified"] == []
    assert len(report["failures"]) == len(reg["banks"])
    assert all("digest mismatch" in row["error"] for row in report["failures"])
