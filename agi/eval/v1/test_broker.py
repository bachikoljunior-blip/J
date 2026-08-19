from broker import BrokerPolicy, BrokerServer, broker_call


def test_broker_allows_only_frozen_tools_and_logs(tmp_path):
    policy = BrokerPolicy.from_public({"broker": {"tools": ["calculator", "kv.get", "kv.put"], "max_requests": 4}})
    sock = tmp_path / "broker.sock"
    with BrokerServer(sock, policy) as server:
        r = broker_call(sock, {"id": 1, "tool": "calculator", "args": {"expression": "19*23"}})
        assert r == {"id": 1, "ok": True, "result": {"value": 437}}
        assert broker_call(sock, {"id": 2, "tool": "kv.put", "args": {"key": "x", "value": 7}})["ok"]
        assert broker_call(sock, {"id": 3, "tool": "kv.get", "args": {"key": "x"}})["result"]["value"] == 7
        denied = broker_call(sock, {"id": 4, "tool": "shell", "args": {}})
        assert not denied["ok"] and denied["error"] == "PolicyViolation"
        assert server.events[-1]["violation"] is True


def test_broker_budget_exhaustion(tmp_path):
    sock = tmp_path / "broker.sock"
    with BrokerServer(sock, BrokerPolicy({"calculator"}, max_requests=1)) as server:
        assert broker_call(sock, {"id": "a", "tool": "calculator", "args": {"expression": "2+2"}})["ok"]
        denied = broker_call(sock, {"id": "b", "tool": "calculator", "args": {"expression": "3+3"}})
        assert not denied["ok"]
        assert server.events[-1]["violation"]


def test_calculator_rejects_code_execution(tmp_path):
    sock = tmp_path / "broker.sock"
    with BrokerServer(sock, BrokerPolicy({"calculator"})):
        r = broker_call(sock, {"id": 1, "tool": "calculator", "args": {"expression": "__import__('os').system('id')"}})
        assert not r["ok"] and r["error"] == "PolicyViolation"
