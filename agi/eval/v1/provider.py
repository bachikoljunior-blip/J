"""Trusted isolated tool providers for the evaluator-owned Unix broker."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

MAX_PROVIDER_OUTPUT = 2_000_000
NETWORK_RE = re.compile(r"^(none|bridge|[A-Za-z0-9_.-]{1,64})$")


def _local_or_digest_ref(image: str, digest: str) -> str:
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
class ContainerToolProvider:
    name: str
    image: str
    digest: str
    network: str = "none"
    command: tuple[str, ...] = ()
    credential_env: tuple[str, ...] = ()
    timeout_s: int = 30
    memory_mb: int = 256
    cpus: float = 1.0
    max_output_bytes: int = 512 * 1024

    @classmethod
    def from_spec(cls, name: str, spec: dict) -> "ContainerToolProvider":
        if spec.get("type") != "container":
            raise ValueError(f"provider {name}: type must be container")
        digest = str(spec.get("digest", ""))
        if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
            raise ValueError(f"provider {name}: immutable sha256 digest required")
        image = str(spec.get("image", ""))
        if not image:
            raise ValueError(f"provider {name}: image required")
        network = str(spec.get("network", "none"))
        if not NETWORK_RE.fullmatch(network):
            raise ValueError(f"provider {name}: invalid network name")
        command = tuple(str(x) for x in (spec.get("command") or []))
        creds = tuple(str(x) for x in (spec.get("credential_env") or []))
        if len(set(creds)) != len(creds) or any(not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", x) for x in creds):
            raise ValueError(f"provider {name}: invalid credential_env names")
        timeout_s = int(spec.get("timeout_s", 30))
        memory_mb = int(spec.get("memory_mb", 256))
        cpus = float(spec.get("cpus", 1.0))
        max_output = int(spec.get("max_output_bytes", 512 * 1024))
        if not 1 <= timeout_s <= 600:
            raise ValueError(f"provider {name}: timeout_s out of range")
        if not 32 <= memory_mb <= 8192:
            raise ValueError(f"provider {name}: memory_mb out of range")
        if not 0.1 <= cpus <= 16:
            raise ValueError(f"provider {name}: cpus out of range")
        if not 1 <= max_output <= MAX_PROVIDER_OUTPUT:
            raise ValueError(f"provider {name}: max_output_bytes out of range")
        return cls(name, image, digest.lower(), network, command, creds, timeout_s, memory_mb, cpus, max_output)

    def build_command(self) -> list[str]:
        ref = _local_or_digest_ref(self.image, self.digest)
        cmd = [
            "docker", "run", "--rm", "-i", "--pull", "never",
            "--network", self.network,
            "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", "64",
            "--memory", f"{self.memory_mb}m",
            "--cpus", str(self.cpus),
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=32m",
        ]
        for name in self.credential_env:
            if name not in os.environ:
                raise RuntimeError(f"provider {self.name}: required evaluator credential env {name} missing")
            cmd += ["--env", name]
        cmd += [ref, *self.command]
        return cmd

    def call(self, args: Any, state: dict[str, Any]) -> Any:
        request = json.dumps({"tool": self.name, "args": args}, ensure_ascii=False)
        proc = subprocess.run(
            self.build_command(),
            input=request,
            text=True,
            capture_output=True,
            timeout=self.timeout_s,
            check=False,
        )
        if proc.returncode != 0:
            # Never return provider stderr to the candidate; it may contain secrets.
            raise RuntimeError(f"provider {self.name} failed with return code {proc.returncode}")
        raw = proc.stdout.encode()
        if len(raw) > self.max_output_bytes:
            raise RuntimeError(f"provider {self.name} output exceeds limit")
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"provider {self.name} emitted invalid JSON") from e
        return result


def load_container_providers(private_row: dict) -> dict[str, ContainerToolProvider]:
    raw = private_row.get("tool_providers") or {}
    if not isinstance(raw, dict):
        raise ValueError("tool_providers must be a mapping")
    providers: dict[str, ContainerToolProvider] = {}
    for name, spec in raw.items():
        if not isinstance(name, str) or not name or not isinstance(spec, dict):
            raise ValueError("invalid tool provider entry")
        providers[name] = ContainerToolProvider.from_spec(name, spec)
    return providers
