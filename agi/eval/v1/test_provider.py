import pytest

from provider import ContainerToolProvider, load_container_providers

DIGEST = "sha256:" + "a" * 64


def test_provider_spec_requires_immutable_digest():
    with pytest.raises(ValueError):
        ContainerToolProvider.from_spec("search", {"type": "container", "image": "x", "digest": "latest"})
    p = ContainerToolProvider.from_spec(
        "search",
        {"type": "container", "image": "x", "digest": DIGEST, "network": "bridge", "credential_env": ["API_KEY"]},
    )
    assert p.digest == DIGEST and p.network == "bridge"


def test_provider_rejects_bad_credential_names():
    with pytest.raises(ValueError):
        ContainerToolProvider.from_spec(
            "x",
            {"type": "container", "image": "x", "digest": DIGEST, "credential_env": ["bad-name"]},
        )


def test_load_multiple_providers():
    row = {
        "tool_providers": {
            "alpha": {"type": "container", "image": "a", "digest": DIGEST},
            "beta": {"type": "container", "image": "b", "digest": "sha256:" + "b" * 64},
        }
    }
    assert set(load_container_providers(row)) == {"alpha", "beta"}
