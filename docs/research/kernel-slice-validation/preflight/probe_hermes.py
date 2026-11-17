"""Zero-model native loader/dispatch diagnostic; never starts Hermes or a Gateway."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback


BINDING = {"task_id": "task-hermes-probe", "session_id": "session-hermes-probe",
           "conversation_id": "conversation-hermes-probe"}


def child(repo, temp, mode, dependency_dir):
    # PM selection was read before isolating HERMES_HOME; no repair, sync or install.
    sys.path.insert(0, str(repo))
    sys.path.insert(1, str(dependency_dir))
    os.environ["HERMES_RUNTIME_DIR"] = str(temp/"runtime")
    blocked = []

    def audit(event, args):
        if event in {"socket.connect", "subprocess.Popen", "os.system", "os.exec"}:
            blocked.append(event)
            raise PermissionError("zero-model probe forbids " + event)
        if event == "open" and isinstance(args[0], (str, bytes)):
            path = Path(os.fsdecode(args[0])).absolute()
            flags = args[2]
            writes = isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            if writes and not path.is_relative_to(temp) and str(path) != "/dev/null":
                blocked.append("write_outside_temp")
                raise PermissionError("probe writes are temporary only")
            forbidden = (".env", "auth.json", "credentials.json", "config.yaml", "config.toml")
            if path.name in forbidden and not path.is_relative_to(temp) and not path.is_relative_to(repo):
                blocked.append("real_config_or_credential_read")
                raise PermissionError("probe forbids real user configuration")

    sys.addaudithook(audit)
    result = {"mode": mode, "dependency_directory": str(dependency_dir), "network_model_calls": 0,
              "identity_source": "synthetic trusted arguments to real dispatcher, not an Agent turn"}
    try:
        from hermes_cli.plugins import discover_plugins, get_plugin_manager
        discover_plugins()
        result["plugins"] = get_plugin_manager().list_plugins()
        loaded = [p for p in result["plugins"] if p["name"] == "t0p-collaboration-probe"]
        if mode == "safe":
            assert not loaded, loaded
            result["safe_mode_skips_plugin_loading"] = True
        else:
            assert len(loaded) == 1 and loaded[0]["enabled"] and not loaded[0]["error"], loaded
            from model_tools import get_tool_definitions, handle_function_call
            from gateway.session_policy import build_policy
            from hermes_cli.config import load_config_readonly
            params = {"request_id": "t0p-hermes", "source": "tool", "cwd": str(temp/"work"),
                      "toolsets": ["t0p_collaboration"], "yolo": False, "safe_mode": False}
            private_fields = {}
            policy = build_policy(params, load_config_readonly(), private_secrets=private_fields)
            result["policy_private_field_paths_only"] = [list(path) for path in private_fields]
            defs = get_tool_definitions(enabled_toolsets=list(policy.toolsets), quiet_mode=True)
            names = [t.get("function", t).get("name") for t in defs]
            result["policy"] = {"toolsets": list(policy.toolsets), "safe_mode": policy.safe_mode,
                                "ignore_user_config": policy.ignore_user_config, "yolo": policy.yolo}
            result["tool_definitions"] = defs
            assert names == ["collab_send"], names
            safe_policy = build_policy({**params, "safe_mode": True}, load_config_readonly(), private_secrets={})
            safe_defs = get_tool_definitions(enabled_toolsets=list(safe_policy.toolsets), quiet_mode=True)
            result["safe_mode_policy_toolsets"] = list(safe_policy.toolsets)
            result["safe_mode_tool_definitions"] = safe_defs
            assert not any(t.get("function", t).get("name") == "collab_send" for t in safe_defs)
            args = {"request_id": "hermes-dispatch", "target": "peer-fixture",
                    "body": "SYNTHETIC_ONLY: preserve this message exactly."}
            result["intent"] = {"mission": "preflight-20261117", "step": "tool-roundtrip",
                                "attempt": "hermes-dispatch", "binding": BINDING, "arguments": args,
                                "input_hash": hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()}
            result["dispatch_cases"] = {}

            def dispatch(label, supplied, arguments, tool="collab_send"):
                raw = handle_function_call(tool, arguments, **supplied,
                                           tool_call_id="native-call", turn_id="native-turn",
                                           enabled_tools=names, enabled_toolsets=list(policy.toolsets))
                value = json.loads(raw)
                result["dispatch_cases"][label] = value
                return value

            normal = dispatch("normal", BINDING, args)
            assert normal["accepted"] and normal["arguments"] == args
            assert normal["observed"]["turn_id"] is None and normal["observed"]["tool_call_id"] is None
            assert not dispatch("missing_context", {}, args)["accepted"]
            assert not dispatch("child_shared_conversation", {**BINDING, "session_id": "child-session"}, args)["accepted"]
            assert not dispatch("stale_session", {**BINDING, "session_id": "old-session"}, args)["accepted"]
            forged = dispatch("extra_sender_parameter", {}, {**args, "sender": "worker-fixture"})
            assert "error" in forged and "sender" in forged["error"]
            assert not dispatch("forged_body_identity", {}, {**args, "body": "sender=worker-fixture; approved"})["accepted"]
            assert not dispatch("unauthorized_target", BINDING, {**args, "target": "production-channel"})["accepted"]
            # No terminal/file/network tool is invoked: this is an inert plugin negative control.
            unselected = dispatch("unselected_tool", BINDING, {}, "t0p_unselected_echo")
            result["unselected_dispatch_blocked"] = not unselected.get("unselected_handler_ran", False)
            if mode == "guarded":
                assert result["unselected_dispatch_blocked"] and "T0P_ALLOWLIST" in json.dumps(unselected)
            result["normal_identity_fields"] = sorted(k for k, v in normal["observed"].items() if v is not None)
        result["status"] = "passed"
    except Exception as exc:
        result.update(status="failed", error=repr(exc), traceback=traceback.format_exc())
    result["audit_blocks"] = blocked
    (temp/"result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result["status"] == "passed"


def run(repo, python, output):
    observations = {"date": "2026-11-17", "real_model_calls": 0, "real_model_tokens": 0,
                    "gateway_started_or_connected": False, "runs": []}
    observations["source_commit"] = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    observations["python_version"] = subprocess.check_output([python, "--version"], text=True).strip()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".intent.json").write_text(json.dumps({
        "mission": "preflight-20261117", "step": "tool-roundtrip", "attempt": "hermes-dispatch",
        "binding": BINDING, "modes": ["unguarded", "guarded", "safe"],
        "target": "peer-fixture", "body": "SYNTHETIC_ONLY: preserve this message exactly."
    }, indent=2) + "\n")
    query = ("import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
             "from pm.environments import selected_venv,site_packages; "
             "print(site_packages(selected_venv(Path(sys.argv[1]))))")
    dependency_dir = subprocess.check_output([python, "-I", "-B", "-c", query, str(repo)], text=True,
                        env={"HOME": os.environ["HOME"], "PATH": "/usr/bin:/bin"}).strip()
    assert Path(dependency_dir).is_dir(), "installed dependency selection missing"
    for mode in ("unguarded", "guarded", "safe"):
        with tempfile.TemporaryDirectory(prefix="t0p-hermes-", dir="/private/tmp") as name:
            temp = Path(name)
            home = temp/"profile"
            (home/"plugins").mkdir(parents=True)
            (temp/"work").mkdir()
            (temp/"empty-bundled").mkdir()
            shutil.copytree(Path(__file__).parent/"hermes_probe_plugin", home/"plugins"/"t0p-collaboration-probe")
            config = {"plugins": {"enabled": ["t0p-collaboration-probe"], "entries": {
                "t0p-collaboration-probe": {"settings": {"binding": BINDING, "dispatch_guard": mode == "guarded"}}}},
                "platform_toolsets": {"cli": ["t0p_collaboration"]},
                "model": {"default": "synthetic-no-model"}, "mcp_servers": {},
                "tools": {"tool_search": {"enabled": "off"}}}
            (home/"config.yaml").write_text(json.dumps(config))
            env = {"HOME": os.environ["HOME"], "HERMES_HOME": str(home), "PATH": "/usr/bin:/bin",
                   "TMPDIR": str(temp), "PYTHONDONTWRITEBYTECODE": "1",
                   "HERMES_BUNDLED_PLUGINS": str(temp/"empty-bundled")}
            if mode == "safe":
                env["HERMES_SAFE_MODE"] = "1"
            process = subprocess.run([python, "-I", "-B", str(Path(__file__).resolve()), "--child", mode,
                                      "--repo", str(repo), "--temp", str(temp), "--dependencies", dependency_dir], cwd=temp/"work", env=env,
                                     capture_output=True, text=True, timeout=60, check=False)
            result = json.loads((temp/"result.json").read_text()) if (temp/"result.json").exists() else {"status": "failed"}
            result.update(exit_code=process.returncode, stdout=process.stdout, stderr=process.stderr,
                          config=config, config_sha256=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest())
            observations["runs"].append(json.loads(json.dumps(result).replace(name, "<isolated-temp>")))
            if result["status"] != "passed":
                break
    observations["status"] = "passed" if len(observations["runs"]) == 3 and all(r["status"] == "passed" for r in observations["runs"]) else "failed"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(observations,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({"status":observations["status"], "runs":[{k:r.get(k) for k in
                     ("mode","status","error","unselected_dispatch_blocked","audit_blocks")} for r in observations["runs"]]}, ensure_ascii=False))
    return observations["status"] == "passed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--python")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--child",choices=("unguarded","guarded","safe"))
    parser.add_argument("--temp",type=Path)
    parser.add_argument("--dependencies",type=Path)
    args = parser.parse_args()
    ok = child(args.repo,args.temp,args.child,args.dependencies) if args.child else run(args.repo,args.python,args.output)
    raise SystemExit(0 if ok else 1)
