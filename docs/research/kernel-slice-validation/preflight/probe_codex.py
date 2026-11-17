"""Diagnostic only: installed Codex + local fixture, no real model or credentials."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import traceback

from fixture_responses import BODY, TOOL, Fixture, digest


CONFIG = '''cli_auth_credentials_store="file"
model="gpt-6.1-sol"
model_provider="preflight_fixture"
web_search="disabled"
[model_providers.preflight_fixture]
name="Zero paid local preflight fixture"
base_url="http://127.0.0.1:{port}/v1"
wire_api="responses"
requires_openai_auth=false
request_max_retries=0
stream_max_retries=0
[agents]
enabled=false
[features]
enable_request_compression=false
respect_system_proxy=true
plugins=false
apps=false
recommended_plugins=false
skill_search=false
shell_tool=false
multi_agent_v2=false
multi_agent_v2_dynamic_tools=false
[skills]
include_instructions=false
[skills.bundled]
enabled=false
[cloud.skills]
enabled=false
[analytics]
enabled=false
'''


class Client:
    def __init__(self, binary, env, work, experimental):
        self.events, self.responses, self.stderr, self.requests = [], {}, [], []
        self.counter = 0
        self.cv = threading.Condition()
        self.p = subprocess.Popen([binary, "app-server", "--strict-config"], cwd=work, env=env,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, bufsize=1)
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()
        self.err_reader = threading.Thread(target=lambda: self.stderr.extend(self.p.stderr.readlines()), daemon=True)
        self.err_reader.start()
        self.rpc("initialize", {"clientInfo": {"name": "zero_paid_preflight", "version": "1"},
                                "capabilities": {"experimentalApi": experimental}})
        self.send({"method": "initialized"})

    def read(self):
        for line in self.p.stdout:
            value = json.loads(line)
            with self.cv:
                if "id" in value and ("result" in value or "error" in value):
                    self.responses[value["id"]] = value
                else:
                    self.events.append(value)
                self.cv.notify_all()

    def send(self, value):
        self.p.stdin.write(json.dumps(value) + "\n")
        self.p.stdin.flush()

    def rpc(self, method, params):
        self.counter += 1
        ident = self.counter
        self.requests.append({"id": ident, "method": method, "params": params})
        self.send({"id": ident, "method": method, "params": params})
        with self.cv:
            assert self.cv.wait_for(lambda: ident in self.responses, timeout=20), "RPC timeout: " + method
            return self.responses[ident]

    def turn(self, tid, attempt):
        start = len(self.events)
        result = self.rpc("turn/start", {"threadId": tid, "input": [{"type": "text", "text": attempt}]})
        assert "error" not in result, result
        turn_id = result["result"]["turn"]["id"]
        cursor, tool_calls, end = start, [], time.monotonic() + 25
        while time.monotonic() < end:
            with self.cv:
                if cursor >= len(self.events):
                    self.cv.wait(timeout=.1)
                    continue
                event = self.events[cursor]
                cursor += 1
            if "id" in event:
                assert event.get("method") == "item/tool/call", event
                p = event["params"]
                assert p["threadId"] == tid and p["turnId"] == turn_id
                assert p["tool"] == "collab_send" and p["callId"]
                assert p["arguments"] == {"request_id": attempt, "target": "peer-fixture", "body": BODY}
                tool_calls.append(event)
                self.send({"id": event["id"], "result": {"success": True,
                           "contentItems": [{"type": "inputText", "text": "receipt:" + attempt}]}})
            if event.get("method") == "turn/completed" and event["params"]["turn"]["id"] == turn_id:
                assert event["params"]["turn"]["status"] == "completed", event
                assert len(tool_calls) == 1, tool_calls
                usage = [e["params"] for e in self.events[start:cursor]
                         if e.get("method") == "thread/tokenUsage/updated"]
                assert usage, "no usage event"
                expected = 26 if attempt == "codex-before" else 52
                assert usage[-1]["tokenUsage"]["total"]["totalTokens"] == expected, usage
                return {"native_turn_id": turn_id, "tool_calls": tool_calls, "terminal": event, "usage": usage}
        raise TimeoutError("turn did not terminate")

    def close(self):
        self.p.stdin.close()
        forced = False
        try:
            self.p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            forced = True
            self.p.terminate()
            try:
                self.p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait(timeout=5)
        self.reader.join(timeout=2)
        self.err_reader.join(timeout=2)
        return {"exit_code": self.p.returncode, "forced": forced}


def run(binary, output):
    result = {"date": "2026-11-17", "real_model_calls": 0, "real_model_tokens": 0,
              "synthetic_usage_not_cost_calibration": True, "checks": {}, "attempts": []}
    result["binary_sha256"] = hashlib.sha256(Path(binary).read_bytes()).hexdigest()
    result["version"] = subprocess.run([binary, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    fixture = Fixture()
    client = None
    with tempfile.TemporaryDirectory(prefix="t0p-codex-", dir="/private/tmp") as temp:
        home, work = Path(temp)/"state", Path(temp)/"work"
        home.mkdir(); work.mkdir()
        config = CONFIG.format(port=fixture.http.server_port)
        (home/"config.toml").write_text(config)
        result["config_template"] = CONFIG
        result["config_sha256"] = hashlib.sha256(config.encode()).hexdigest()
        result["intent"] = {"mission": "preflight-20261117", "step": "tool-roundtrip", "body": BODY,
                            "body_sha256": hashlib.sha256(BODY.encode()).hexdigest(), "tool_schema_sha256": digest(TOOL)}
        result["intent"]["request_ids"] = ["codex-before", "codex-after"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.with_suffix(".intent.json").write_text(json.dumps(result["intent"], indent=2) + "\n")
        env = {"HOME": os.environ["HOME"], "CODEX_HOME": str(home), "PATH": "/usr/bin:/bin",
               "TMPDIR": temp, "NO_PROXY": "*", "no_proxy": "*"}
        result["child_env_keys"] = sorted(env)
        try:
            strict = subprocess.run([binary, "app-server", "--strict-config", "--print-startup-config"],
                                    cwd=work, env=env, capture_output=True, text=True, timeout=20, check=False)
            result["strict_config"] = {"exit_code": strict.returncode, "stdout": strict.stdout, "stderr": strict.stderr}
            assert strict.returncode == 0, "strict config rejected"
            params = {"cwd": str(work), "model": "gpt-6.1-sol", "modelProvider": "preflight_fixture",
                      "approvalPolicy": "never", "sandbox": "read-only", "baseInstructions": "Synthetic local fixture only.",
                      "dynamicTools": [TOOL]}
            client = Client(binary, env, work, False)
            denied = client.rpc("thread/start", params)
            result["experimental_gate"] = denied
            assert "error" in denied and "experimental" in json.dumps(denied).lower(), denied
            assert len(fixture.requests) == 0
            result["gate_server_exit"] = client.close(); client = None
            result["checks"]["experimental_gate"] = True
            client = Client(binary, env, work, True)
            created = client.rpc("thread/start", params)
            assert "error" not in created, created
            tid = created["result"]["thread"]["id"]
            result["thread_start"] = created
            result["attempts"].append(client.turn(tid, "codex-before"))
            result["first_server_events"] = client.events
            result["first_server_exit"] = client.close(); client = None
            assert result["first_server_exit"] == {"exit_code": 0, "forced": False}
            assert len(fixture.requests) == 2
            client = Client(binary, env, work, True)
            before = len(fixture.requests)
            resumed = client.rpc("thread/resume", {"threadId": tid})
            assert "error" not in resumed, resumed
            assert resumed["result"]["thread"]["id"] == tid
            read = client.rpc("thread/read", {"threadId": tid, "includeTurns": True})
            assert "error" not in read and len(read["result"]["thread"]["turns"]) == 1, read
            assert len(fixture.requests) == before
            result["resume"] = resumed; result["read_after_resume"] = read
            result["resume_request_delta"] = len(fixture.requests) - before
            result["resume_rpc"] = client.requests[-2:]
            result["attempts"].append(client.turn(tid, "codex-after"))
            result["second_server_events"] = client.events
            assert len(fixture.requests) == 4 and not fixture.failures
            first_tools, resumed_tools = fixture.requests[0]["tools"], fixture.requests[2]["tools"]
            assert first_tools == resumed_tools, "effective tools changed after cold recovery"
            assert not any(t.get("name") == "collaboration" for t in first_tools), "native subagents still advertised"
            result["checks"].update(normal_callback=True, cold_history_resume=True, cold_dynamic_tool_callback=True,
                                     identical_effective_tool_schema=True, synthetic_cumulative_usage=True)
            result["status"] = "passed"
        except Exception as exc:
            result["status"] = "failed"
            result["error"] = repr(exc)
            result["traceback"] = traceback.format_exc()
        finally:
            if client:
                result["last_server_exit"] = client.close()
                result["last_server_events"] = client.events
                result["last_server_stderr"] = "".join(client.stderr)
                if result["last_server_exit"] != {"exit_code": 0, "forced": False}:
                    result["status"] = "failed"
                    result["error"] = "last server did not exit cleanly"
            fixture.close()
            result["fixture_requests"] = fixture.requests
            result["fixture_failures"] = fixture.failures
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2).replace(temp, "<isolated-temp>") + "\n")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "fixture_requests": len(fixture.requests),
                      "error": result.get("error"), "output": str(output)}, ensure_ascii=False))
    return result["status"] == "passed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.binary, args.output) else 1)
