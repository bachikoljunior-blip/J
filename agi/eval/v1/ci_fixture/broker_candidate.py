"""Toy candidate that can only reach evaluator tools through /broker/broker.sock."""
import json
import socket
import sys

req = json.load(sys.stdin)
sock_path = req.get("broker_socket", "/broker/broker.sock")


def call(request):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(sock_path)
        s.sendall(json.dumps(request).encode() + b"\n")
        f = s.makefile("rb")
        return json.loads(f.readline())


calc = call({"id": 1, "tool": "calculator", "args": {"expression": "19*23"}})
provider = call({"id": 2, "tool": "secret.check", "args": {"probe": "present"}})
denied = call({"id": 3, "tool": "shell", "args": {"command": "id"}})
external = ((provider.get("result") or {}).get("external_service") or {})
answer = (
    calc.get("ok") is True
    and (calc.get("result") or {}).get("value") == 437
    and provider.get("ok") is True
    and (provider.get("result") or {}).get("credential_present") is True
    and external.get("authorized") is True
    and external.get("probe") == "present"
    and denied.get("ok") is False
    and denied.get("error") == "PolicyViolation"
)
json.dump(
    {
        "answer": answer,
        "diagnostics": {
            "calc": calc,
            "provider": provider,
            "denied": denied,
        },
    },
    sys.stdout,
)
