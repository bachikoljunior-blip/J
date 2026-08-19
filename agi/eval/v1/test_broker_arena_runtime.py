import json
from pathlib import Path

import run_broker_arena_harness as runner

DIGEST = "sha256:" + "a" * 64
PROVIDER_DIGEST = "sha256:" + "b" * 64


def fixture_rows():
    public = {
        "task_id": "t",
        "domain": "software_engineering",
        "family": "broker",
        "prompt": "test",
        "arena": {
            "network": "none",
            "broker": {
                "tools": ["calculator", "secret.check"],
                "max_requests": 4,
                "cost_per_call": {"secret.check": 0.25},
            },
        },
    }
    private = {
        "task_id": "t",
        "grader": {"type": "boolean", "expected": True},
        "human_reference_lower_bound": 0.1,
        "tool_providers": {
            "secret.check": {
                "type": "container",
                "image": "provider-image",
                "digest": PROVIDER_DIGEST,
                "network": "provider-private-net",
                "credential_env": ["API_KEY"],
            }
        },
    }
    return public, private


def test_broker_runtime_accepts_private_provider_without_public_provider_config():
    public, private = fixture_rows()
    providers, policy = runner._broker_runtime(public, private)
    assert set(providers) == {"secret.check"}
    assert policy.allowed_tools == {"calculator", "secret.check"}
    assert policy.cost_per_call == {"secret.check": 0.25}
    serialized_public = json.dumps(public)
    assert "provider-image" not in serialized_public
    assert "provider-private-net" not in serialized_public
    assert "API_KEY" not in serialized_public


def test_candidate_request_and_container_command_expose_only_unix_socket(monkeypatch, tmp_path):
    public, _ = fixture_rows()
    socket_path = tmp_path / "broker" / "broker.sock"
    request = runner._candidate_request(public, final=True, broker_socket=socket_path)
    assert request["broker_socket"] == "/broker/broker.sock"
    assert "provider-image" not in json.dumps(request)
    monkeypatch.setattr(runner, "_immutable_image_ref", lambda image, digest: digest)
    input_dir, work_dir, broker_dir = tmp_path / "input", tmp_path / "work", tmp_path / "broker"
    input_dir.mkdir()
    work_dir.mkdir()
    broker_dir.mkdir(exist_ok=True)
    cmd = runner.build_container_command(public, ["candidate"], DIGEST, input_dir, work_dir, broker_dir)
    assert cmd[cmd.index("--network") + 1] == "none"
    mount_values = [cmd[i + 1] for i, value in enumerate(cmd[:-1]) if value == "--mount"]
    assert any("dst=/broker" in value and "readonly" in value for value in mount_values)
    serialized_cmd = json.dumps(cmd)
    assert "provider-private-net" not in serialized_cmd
    assert "provider-image" not in serialized_cmd
    assert "API_KEY" not in serialized_cmd
