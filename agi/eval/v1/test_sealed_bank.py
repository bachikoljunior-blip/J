import hashlib
import json

import sealed_bank
from eval_core import REQUIRED_DOMAINS
from sealed_bank import SealedBankProvider, coverage_summary, validate_registry


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def valid_registry():
    families = {domain: [f"{domain}_heldout"] for domain in sorted(REQUIRED_DOMAINS)}
    banks = []
    for domain in sorted(REQUIRED_DOMAINS):
        family = families[domain][0]
        for lineage in ("alpha", "beta"):
            prefix = f"{domain}-{lineage}"
            banks.append(
                {
                    "bank_id": prefix,
                    "domain": domain,
                    "families": [family],
                    "custody_group": f"custody-{lineage}-{domain}",
                    "implementation_lineage": f"impl-{lineage}-{domain}",
                    "visibility": "sealed_nonpublic",
                    "protocol": "agi-taskgen-request-v1",
                    "sealed_content_commitment": h(prefix + "-content"),
                    "seed_schedule_commitment": h(prefix + "-seeds"),
                    "provider": {
                        "type": "container",
                        "image": f"private.invalid/{domain}-{lineage}",
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


def test_valid_registry_requires_two_independent_banks_for_every_family():
    registry = valid_registry()
    assert validate_registry(registry) == []
    summary = coverage_summary(registry)
    for domain in REQUIRED_DOMAINS:
        row = summary[domain][f"{domain}_heldout"]
        assert row == {
            "banks": 2,
            "custody_groups": 2,
            "implementation_lineages": 2,
            "provider_digests": 2,
        }


def test_registry_fails_closed_on_shared_custody_and_digest():
    registry = valid_registry()
    domain = sorted(REQUIRED_DOMAINS)[0]
    rows = [b for b in registry["banks"] if b["domain"] == domain]
    rows[1]["custody_group"] = rows[0]["custody_group"]
    rows[1]["implementation_lineage"] = rows[0]["implementation_lineage"]
    rows[1]["provider"]["digest"] = rows[0]["provider"]["digest"]
    errors = validate_registry(registry)
    joined = "\n".join(errors)
    assert "independent custody groups" in joined
    assert "implementation lineages" in joined
    assert "provider digests" in joined


def test_registry_rejects_inline_generator_content_and_runtime_credentials():
    registry = valid_registry()
    registry["banks"][0]["prompt_template"] = "secret final task template"
    registry["banks"][0]["provider"]["credential_env"] = ["TOKEN"]
    errors = "\n".join(validate_registry(registry))
    assert "inline secret/content keys" in errors
    assert "must not require runtime credentials" in errors


def test_sealed_bank_container_is_offline_and_has_no_host_secret_surface(monkeypatch):
    bank = valid_registry()["banks"][0]
    monkeypatch.setattr(sealed_bank, "_immutable_image_ref", lambda image, digest: digest)
    provider = SealedBankProvider.from_bank(bank)
    cmd = provider.build_command()
    assert cmd[cmd.index("--network") + 1] == "none"
    assert "--pull" in cmd and cmd[cmd.index("--pull") + 1] == "never"
    assert "--read-only" in cmd
    assert "--cap-drop" in cmd and "ALL" in cmd
    assert "no-new-privileges" in cmd
    serialized = json.dumps(cmd)
    assert "--env" not in cmd
    assert "--mount" not in cmd
    assert bank["provider"]["digest"] in serialized
