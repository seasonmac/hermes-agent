"""Disposable diagnostic plugin, installed only into the probe's temporary home."""

import json


def register(ctx):
    binding = ctx.get_config("binding")
    guarded = ctx.get_config("dispatch_guard", False)

    def send(args, **kwargs):
        observed = {k: kwargs.get(k) for k in (
            "task_id", "session_id", "conversation_id", "turn_id", "tool_call_id", "turn_origin")}
        identity = {k: kwargs.get(k) for k in ("task_id", "session_id", "conversation_id")}
        accepted = identity == binding and not kwargs.get("turn_origin")
        accepted = accepted and args.get("target") == "peer-fixture"
        # No actual messaging: report exactly what the real dispatcher supplied.
        return json.dumps({"accepted": accepted, "observed": observed, "arguments": args,
                           "author": "worker-fixture" if accepted else None,
                           "receipt": "receipt:" + args.get("request_id", "") if accepted else None})

    def echo(args, **kwargs):
        return json.dumps({"unselected_handler_ran": True})

    def guard(tool_name, args, **kwargs):
        if guarded and tool_name != "collab_send":
            return {"action": "block", "message": "T0P_ALLOWLIST: not an admitted probe tool"}

    schema = {"name": "collab_send", "description": "Synthetic local send; no external transport.",
              "parameters": {"type": "object", "properties": {
                  k: {"type": "string"} for k in ("request_id", "target", "body")},
                  "required": ["request_id", "target", "body"], "additionalProperties": False}}
    ctx.register_tool("collab_send", "t0p_collaboration", schema, send)
    ctx.register_tool("t0p_unselected_echo", "t0p_unselected",
                      {"name": "t0p_unselected_echo", "description": "Harmless negative-control echo.",
                       "parameters": {"type": "object", "properties": {}}}, echo)
    ctx.register_hook("pre_tool_call", guard)
