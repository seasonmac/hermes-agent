"""Offline evidence audit. Does not import harnesses or open network connections."""

import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent


def load(name):
    return json.loads((BASE/name).read_text())


def main():
    codex = load("observations/codex.json")
    hermes = load("observations/hermes.json")
    assert codex["status"] == hermes["status"] == "passed"
    assert codex["real_model_calls"] == hermes["real_model_calls"] == 0
    assert codex["real_model_tokens"] == hermes["real_model_tokens"] == 0
    assert not hermes["gateway_started_or_connected"]
    assert len(codex["fixture_requests"]) == 4 and not codex["fixture_failures"]
    assert codex["experimental_gate"]["error"]["code"] == -32600
    assert "experimentalApi" in codex["experimental_gate"]["error"]["message"]
    for phase in ("gate_server_exit", "first_server_exit", "last_server_exit"):
        assert codex[phase] == {"exit_code": 0, "forced": False}
    assert codex["resume_request_delta"] == 0
    assert [x["method"] for x in codex["resume_rpc"]] == ["thread/resume", "thread/read"]
    assert set(codex["resume_rpc"][0]["params"]) == {"threadId"}
    tid = codex["thread_start"]["result"]["thread"]["id"]
    assert tid == codex["resume"]["result"]["thread"]["id"]
    assert len(codex["read_after_resume"]["result"]["thread"]["turns"]) == 1
    for attempt, total in zip(codex["attempts"], (26, 52)):
        call = attempt["tool_calls"][0]["params"]
        assert len(attempt["tool_calls"]) == 1
        assert call["threadId"] == tid and call["turnId"] == attempt["native_turn_id"]
        assert call["tool"] == "collab_send" and call["callId"]
        assert call["arguments"]["body"] == codex["intent"]["body"]
        assert attempt["terminal"]["params"]["turn"]["status"] == "completed"
        assert attempt["usage"][-1]["tokenUsage"]["total"]["totalTokens"] == total
    first, resumed = [codex["fixture_requests"][n]["tools"] for n in (0, 2)]
    assert first and first == resumed
    assert "collab_send(args:" in json.dumps(first)
    assert not any(t.get("name") == "collaboration" for t in first)
    for request in codex["fixture_requests"]:
        assert not request["authorization_present"]
        assert request["path"] == "/v1/responses"
        assert request["synthetic_usage"]["total_tokens"] == 13
    assert sum(x["synthetic_usage"]["total_tokens"] for x in codex["fixture_requests"]) == 52
    assert len(hermes["runs"]) == 3
    unguarded, guarded, safe = hermes["runs"]
    for run in hermes["runs"]:
        assert run["exit_code"] == 0 and not run["audit_blocks"]
    for run in (unguarded, guarded):
        assert run["policy"] == {"toolsets": ["t0p_collaboration"], "safe_mode": False,
                                 "ignore_user_config": False, "yolo": False}
        assert [d["function"]["name"] for d in run["tool_definitions"]] == ["collab_send"]
        assert run["safe_mode_policy_toolsets"] == []
        cases = run["dispatch_cases"]
        assert cases["normal"]["accepted"] and cases["normal"]["receipt"] == "receipt:hermes-dispatch"
        assert cases["normal"]["arguments"] == run["intent"]["arguments"]
        assert cases["normal"]["observed"]["turn_id"] is None
        assert cases["normal"]["observed"]["tool_call_id"] is None
        for name in ("missing_context", "child_shared_conversation", "stale_session", "forged_body_identity", "unauthorized_target"):
            assert cases[name]["accepted"] is False and cases[name]["receipt"] is None
        assert "NOT invoked" in cases["extra_sender_parameter"]["error"]
    assert unguarded["dispatch_cases"]["unselected_tool"] == {"unselected_handler_ran": True}
    assert "T0P_ALLOWLIST" in guarded["dispatch_cases"]["unselected_tool"]["error"]
    assert safe["safe_mode_skips_plugin_loading"] and safe["plugins"] == []
    calibration = load("calibration.json")
    assert calibration["real_model_cost_calibration"] == "not_run"
    assert calibration["T0_P_complete"] is False
    for relative, expected in calibration["artifact_sha256"].items():
        assert hashlib.sha256((BASE/relative).read_bytes()).hexdigest() == expected, relative
    print("PASS: Codex cold tools/history/counters; Hermes loader/identity/selection/guard; artifact hashes. Zero live harness or model calls in this audit.")


if __name__ == "__main__":
    main()
