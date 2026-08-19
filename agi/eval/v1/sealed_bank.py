"""Fail-closed contract for independently custodied sealed task-generator banks.

This is evaluator infrastructure, not final task content and not an AGI candidate.
Final generator implementations are expected to live in non-public immutable
container images that are staged for the evaluator before candidate evaluation.
The public/auditable registry contains identities and cryptographic commitments,
not templates, answers, credentials, or generator source.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from eval_core import REQUIRED_DOMAINS, canonical_json

REGISTRY_SCHEMA = "agi-sealed-bank-registry-v1"
PROTOCOL = "agi-taskgen-request-v1"
SHA256_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
FORBIDDEN_INLINE_KEYS = {
    "answer",
    "answer_key",
    "command",
    "credential",
    "credentials",
    "expected",
    "grader",
    "private_key",
    "prompt_template",
    "secret",
    "source",
    "source_code",
    "template",
}
MAX_PROVIDER_OUTPUT = 2_000_000


def _find_forbidden_inline(value: Any, prefix: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            name = str(key)
            if name.lower() in FORBIDDEN_INLINE_KEYS:
                found.append(f"{prefix}.{name}")
            found.extend(_find_forbidden_inline(child, f"{prefix}.{name}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_inline(child, f"{prefix}[{index}]"))
    return found


def _is_commitment(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    raw = value[7:] if value.startswith("sha256:") else value
    return bool(HEX_RE.fullmatch(raw))


def validate_registry(registry: dict, *, required_domains: set[str] | None = None) -> list[str]:
    """Validate bank identity, secrecy surface, family coverage, and custody independence."""
    errors: list[str] = []
    required_domains = set(required_domains or REQUIRED_DOMAINS)
    if registry.get("schema") != REGISTRY_SCHEMA:
        errors.append(f"schema must be {REGISTRY_SCHEMA}")
        return errors
    forbidden = _find_forbidden_inline(registry)
    if forbidden:
        errors.append(f"registry contains inline secret/content keys: {forbidden[:10]}")

    minimum = registry.get("minimum_independent_custodies_per_family", 2)
    if not isinstance(minimum, int) or minimum < 2 or minimum > 8:
        errors.append("minimum_independent_custodies_per_family must be integer in [2,8]")
        minimum = 2

    required_families = registry.get("required_families")
    if not isinstance(required_families, dict):
        errors.append("required_families must be a mapping")
        required_families = {}
    for domain in sorted(required_domains):
        families = required_families.get(domain)
        if not isinstance(families, list) or not families or not all(isinstance(x, str) and ID_RE.fullmatch(x) for x in families):
            errors.append(f"required domain {domain} needs a non-empty valid family list")
    extra_domains = sorted(set(required_families) - required_domains)
    if extra_domains:
        errors.append(f"required_families contains non-required domains: {extra_domains}")

    banks = registry.get("banks")
    if not isinstance(banks, list) or not banks:
        errors.append("banks must be a non-empty list")
        return errors

    ids: set[str] = set()
    coverage: dict[tuple[str, str], list[dict]] = defaultdict(list)
    global_commitments: dict[str, str] = {}
    for index, bank in enumerate(banks):
        prefix = f"bank[{index}]"
        if not isinstance(bank, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        bank_id = bank.get("bank_id")
        if not isinstance(bank_id, str) or not ID_RE.fullmatch(bank_id):
            errors.append(f"{prefix} invalid bank_id")
            bank_id = f"invalid-{index}"
        elif bank_id in ids:
            errors.append(f"duplicate bank_id {bank_id}")
        ids.add(str(bank_id))

        domain = bank.get("domain")
        if domain not in required_domains:
            errors.append(f"{prefix} domain must be a required domain")
        families = bank.get("families")
        if not isinstance(families, list) or not families or not all(isinstance(x, str) and ID_RE.fullmatch(x) for x in families):
            errors.append(f"{prefix} families must be a non-empty list of identifiers")
            families = []
        declared = set(required_families.get(domain, [])) if domain in required_families else set()
        unknown_families = sorted(set(families) - declared)
        if unknown_families:
            errors.append(f"{prefix} families not preregistered for {domain}: {unknown_families}")

        custody = bank.get("custody_group")
        if not isinstance(custody, str) or not ID_RE.fullmatch(custody):
            errors.append(f"{prefix} invalid custody_group")
        lineage = bank.get("implementation_lineage")
        if not isinstance(lineage, str) or not ID_RE.fullmatch(lineage):
            errors.append(f"{prefix} invalid implementation_lineage")
        if bank.get("visibility") != "sealed_nonpublic":
            errors.append(f"{prefix} visibility must be sealed_nonpublic")
        if bank.get("protocol") != PROTOCOL:
            errors.append(f"{prefix} protocol must be {PROTOCOL}")

        provider = bank.get("provider")
        if not isinstance(provider, dict):
            errors.append(f"{prefix} provider must be a mapping")
            provider = {}
        if provider.get("type") != "container":
            errors.append(f"{prefix} provider.type must be container")
        image = provider.get("image")
        if not isinstance(image, str) or not image.strip():
            errors.append(f"{prefix} provider.image required")
        digest = provider.get("digest")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{prefix} immutable provider sha256 digest required")
        if provider.get("network", "none") != "none":
            errors.append(f"{prefix} final generator provider network must be none")
        if "credential_env" in provider:
            errors.append(f"{prefix} generator provider must not require runtime credentials")

        content_commitment = bank.get("sealed_content_commitment")
        seed_commitment = bank.get("seed_schedule_commitment")
        if not _is_commitment(content_commitment):
            errors.append(f"{prefix} invalid sealed_content_commitment")
        if not _is_commitment(seed_commitment):
            errors.append(f"{prefix} invalid seed_schedule_commitment")
        if _is_commitment(content_commitment):
            normalized = str(content_commitment).removeprefix("sha256:").lower()
            prior = global_commitments.get(normalized)
            if prior is not None:
                errors.append(f"{prefix} reuses sealed content commitment from {prior}")
            else:
                global_commitments[normalized] = str(bank_id)

        for family in families:
            if domain in required_domains and family in declared:
                coverage[(str(domain), family)].append(bank)

    for domain in sorted(required_domains):
        for family in required_families.get(domain, []):
            rows = coverage.get((domain, family), [])
            if len(rows) < minimum:
                errors.append(f"coverage {domain}/{family}: {len(rows)} banks < required {minimum}")
                continue
            custodians = {str(x.get("custody_group")) for x in rows}
            lineages = {str(x.get("implementation_lineage")) for x in rows}
            digests = {str((x.get("provider") or {}).get("digest")) for x in rows}
            commitments = {str(x.get("sealed_content_commitment")) for x in rows}
            if len(custodians) < minimum:
                errors.append(f"coverage {domain}/{family}: only {len(custodians)} independent custody groups")
            if len(lineages) < minimum:
                errors.append(f"coverage {domain}/{family}: only {len(lineages)} implementation lineages")
            if len(digests) < minimum:
                errors.append(f"coverage {domain}/{family}: only {len(digests)} provider digests")
            if len(commitments) < minimum:
                errors.append(f"coverage {domain}/{family}: only {len(commitments)} content commitments")
    return errors


def coverage_summary(registry: dict, *, required_domains: set[str] | None = None) -> dict[str, Any]:
    required_domains = set(required_domains or REQUIRED_DOMAINS)
    required_families = registry.get("required_families") or {}
    banks = registry.get("banks") or []
    result: dict[str, Any] = {}
    for domain in sorted(required_domains):
        family_rows: dict[str, Any] = {}
        for family in required_families.get(domain, []):
            rows = [b for b in banks if isinstance(b, dict) and b.get("domain") == domain and family in (b.get("families") or [])]
            family_rows[family] = {
                "banks": len(rows),
                "custody_groups": len({str(r.get("custody_group")) for r in rows}),
                "implementation_lineages": len({str(r.get("implementation_lineage")) for r in rows}),
                "provider_digests": len({str((r.get("provider") or {}).get("digest")) for r in rows}),
            }
        result[domain] = family_rows
    return result


def registry_commitment(registry: dict) -> str:
    import hashlib

    return hashlib.sha256(canonical_json(registry).encode()).hexdigest()


def _immutable_image_ref(image: str, digest: str) -> str:
    if shutil.which("docker") is None:
        raise RuntimeError("docker executable not available")
    inspected = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    local_id = inspected.stdout.strip() if inspected.returncode == 0 else ""
    if local_id and local_id == digest:
        return digest
    if "@sha256:" in image:
        return image
    return f"{image}@{digest}"


@dataclass(frozen=True)
class SealedBankProvider:
    bank_id: str
    image: str
    digest: str
    timeout_s: int = 60
    memory_mb: int = 512
    cpus: float = 1.0
    max_output_bytes: int = 512 * 1024

    @classmethod
    def from_bank(cls, bank: dict) -> "SealedBankProvider":
        provider = bank.get("provider") or {}
        if provider.get("type") != "container":
            raise ValueError("sealed bank provider.type must be container")
        digest = str(provider.get("digest", ""))
        if not SHA256_RE.fullmatch(digest):
            raise ValueError("sealed bank immutable sha256 digest required")
        if provider.get("network", "none") != "none":
            raise ValueError("sealed bank provider network must be none")
        if "credential_env" in provider:
            raise ValueError("sealed bank providers cannot require runtime credentials")
        timeout_s = int(provider.get("timeout_s", 60))
        memory_mb = int(provider.get("memory_mb", 512))
        cpus = float(provider.get("cpus", 1.0))
        max_output = int(provider.get("max_output_bytes", 512 * 1024))
        if not 1 <= timeout_s <= 600:
            raise ValueError("sealed bank timeout_s out of range")
        if not 64 <= memory_mb <= 8192:
            raise ValueError("sealed bank memory_mb out of range")
        if not 0.1 <= cpus <= 16:
            raise ValueError("sealed bank cpus out of range")
        if not 1 <= max_output <= MAX_PROVIDER_OUTPUT:
            raise ValueError("sealed bank max_output_bytes out of range")
        return cls(str(bank["bank_id"]), str(provider["image"]), digest.lower(), timeout_s, memory_mb, cpus, max_output)

    def build_command(self) -> list[str]:
        ref = _immutable_image_ref(self.image, self.digest)
        return [
            "docker",
            "run",
            "--rm",
            "-i",
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--memory",
            f"{self.memory_mb}m",
            "--cpus",
            str(self.cpus),
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=32m",
            ref,
        ]

    def generate(self, *, domain: str, family: str, seed: str, nonce: str) -> dict[str, Any]:
        request = {
            "schema": PROTOCOL,
            "bank_id": self.bank_id,
            "domain": domain,
            "family": family,
            "seed": seed,
            "nonce": nonce,
        }
        proc = subprocess.run(
            self.build_command(),
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=self.timeout_s,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"sealed bank {self.bank_id} failed with return code {proc.returncode}")
        raw = proc.stdout.encode()
        if len(raw) > self.max_output_bytes:
            raise RuntimeError(f"sealed bank {self.bank_id} output exceeds limit")
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"sealed bank {self.bank_id} emitted invalid JSON") from e
        if not isinstance(out, dict) or not isinstance(out.get("public"), dict) or not isinstance(out.get("private"), dict):
            raise RuntimeError(f"sealed bank {self.bank_id} must return public/private objects")
        return out
