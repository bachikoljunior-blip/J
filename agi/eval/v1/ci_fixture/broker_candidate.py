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

out = {
    "calc": call({"id": 1, "tool": "calculator", "args": {"expression": "19*23"}}),
    "provider": call({"id": 2, "tool": "secret.check", "args": {"probe": "present"}}),
    "denied": call({"id": 3, "tool": "shell", "args": {"command": "id"}}),
}
json.dump(out, sys.stdout)
