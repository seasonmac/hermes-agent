"""Bounded local Responses fixture; synthetic usage, never a model client."""

import hashlib
import http.server
import json
import threading


BODY = "SYNTHETIC_ONLY: preserve this message exactly."
TOOL = {
    "name": "collab_send",
    "description": "Deliver a synthetic message to the local preflight recorder.",
    "inputSchema": {
        "type": "object",
        "properties": {name: {"type": "string"} for name in ("request_id", "target", "body")},
        "required": ["request_id", "target", "body"],
        "additionalProperties": False,
    },
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def effective_tools(body):
    tools = list(body.get("tools", []))
    for item in body.get("input", []):
        if item.get("type") == "additional_tools":
            tools.extend(item.get("tools", []))
    return tools


class Fixture:
    def __init__(self):
        self.requests = []
        self.failures = []
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_POST(self):
                try:
                    assert self.path == "/v1/responses", "unexpected endpoint"
                    assert not self.headers.get("Authorization"), "credentials unexpectedly supplied"
                    assert not self.headers.get("Content-Encoding"), "compressed request not supported"
                    body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    index = len(owner.requests) + 1
                    assert index <= 4, "unexpected extra request"
                    attempt = "codex-before" if index <= 2 else "codex-after"
                    user_inputs = [x for x in body.get("input", []) if x.get("role") == "user"]
                    assert attempt in json.dumps(user_inputs), "wrong fixture stage"
                    rec = {
                        "index": index, "path": self.path, "attempt": attempt,
                        "authorization_present": False, "model": body.get("model"),
                        "request_hash": digest(body), "request_bytes": len(json.dumps(body).encode()),
                        "tools": effective_tools(body), "input": body.get("input", []),
                        "body_keys": sorted(body),
                        "tool_advertisement_fields": {k: v for k, v in body.items()
                                                      if k not in {"input", "metadata", "client_metadata"}},
                    }
                    owner.requests.append(rec)
                    assert "collab_send(args:" in json.dumps(rec["tools"]), "tool declaration not advertised"
                    if index % 2:
                        arguments = {"request_id": attempt, "target": "peer-fixture", "body": BODY}
                        item = {"type": "custom_tool_call", "call_id": "call_" + attempt,
                                "name": "exec", "namespace": "functions",
                                "input": "text(await tools.collab_send(" + json.dumps(arguments) + "));"}
                    else:
                        assert "receipt:" + attempt in json.dumps(body.get("input", [])), "receipt missing"
                        item = {"type": "message", "id": "msg_" + attempt, "role": "assistant",
                                "content": [{"type": "output_text", "text": "DONE:" + attempt}]}
                    usage = {"input_tokens": 11, "input_tokens_details": {"cached_tokens": 3},
                             "output_tokens": 2, "output_tokens_details": {"reasoning_tokens": 1},
                             "total_tokens": 13}
                    rec["synthetic_usage"] = usage
                    events = [
                        {"type": "response.created", "response": {"id": "resp_" + str(index)}},
                        {"type": "response.output_item.done", "item": item},
                        {"type": "response.completed", "response": {"id": "resp_" + str(index), "usage": usage}},
                    ]
                    encoded = "".join("data: " + json.dumps(x) + "\n\n" for x in events).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                except Exception as exc:
                    owner.failures.append(str(exc))
                    self.send_error(400, "fixture contract rejected")

        self.http = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.http.daemon_threads = True
        self.worker = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.worker.start()

    def close(self):
        self.http.shutdown()
        self.http.server_close()
        self.worker.join(timeout=3)
