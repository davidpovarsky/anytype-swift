#!/usr/bin/env python3
"""Actual owned CLI/HTTPS/wrapper validation using only synthetic fixtures.

No simctl, trust installation, GitHub action, model credential or Any API call.
Private files are removed only after authenticated shutdown, process exit and
listener closure are proved by the fixture's stop command.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import http.client
import ssl
import urllib.parse

import fixture
from protocol import CONTRACT, canonical, digest, require, strict_json
from test_fixture import SCENARIO, rounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--openssl")
    args = parser.parse_args()
    root = Path(args.repo_root).absolute()
    output = Path(args.output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    private_parent = Path(tempfile.mkdtemp(prefix="pinkha-hanlin-owned-lifecycle-")).resolve()
    os.chmod(private_parent, 0o700)
    private = private_parent / "fixture"
    config_path = private / fixture.CONFIG_NAME
    checks = {}
    commands = []
    stopped = False
    connection = None
    source_paths = [Path(__file__), Path(fixture.__file__), Path(__file__).with_name("protocol.py"),
                    root / "Tools/AnyEnginePort/hanlin_fixture_ci.py"]
    before = {str(p.relative_to(root)) if p.is_relative_to(root) else p.name: digest(p.read_bytes())
              for p in source_paths}
    result = {"schema": 1, "status": "FAIL", "scope": "actual_test_fixture_CLI_TLS_and_root_wrapper_only",
              "checks": checks, "commands": commands, "sourcesBefore": before,
              "privateMaterialUploaded": False, "hostTrustModified": False, "AppleUIExecuted": False}

    def command(name, extras=(), *, expected=0):
        argv = [sys.executable, str(Path(fixture.__file__).resolve()), name,
                "--private-config", str(config_path), *extras]
        if name == "start":
            argv = [sys.executable, str(Path(fixture.__file__).resolve()), "start", "--private-dir", str(private),
                    "--safe-result", str(output / "server-result.json"), "--max-age-seconds", "120"]
            if args.openssl: argv.extend(["--openssl", args.openssl])
        completed = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=90 if name == "start" else 30, check=False)
        # Command output is source-allowlisted JSON; never persist an unknown stderr/body.
        parsed = [strict_json(line, 65536) for line in completed.stdout.splitlines() if line.strip()]
        require(completed.returncode == expected and not completed.stderr, "lifecycle_command_failed")
        for item in parsed:
            require(isinstance(item, dict), "lifecycle_output_shape")
        commands.append({"command": name, "exitCode": completed.returncode,
                         "stdoutSHA256": digest(completed.stdout), "stdoutBytes": len(completed.stdout)})
        return parsed[-1]

    try:
        started = command("start")
        checks["actual_start_explicit_temporary_ca_ready"] = started.get("status") == "FIXTURE_READY"
        config = fixture.load_config(config_path)
        module_path = root / "Tools/AnyEnginePort/hanlin_fixture_ci.py"
        spec = importlib.util.spec_from_file_location("owned_hanlin_ci_contract", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        values = module.validate_private_config(config_path, private)
        checks["actual_root_validate_private_config"] = values == config["testRunnerEnvironment"]
        inspect = command("inspect")
        checks["inspect_does_not_claim_unrun_scenario"] = inspect["state"] == "awaiting_scenario" and not inspect["complete"]
        unfinished = command("verify", expected=1)
        checks["verify_refuses_unrun_scenario"] = unfinished.get("code") == "fixture_protocol_incomplete"
        status, _ = fixture.control_request(config, "/scenario", method="POST", body=SCENARIO)
        require(status == 201, "lifecycle_registration")
        origin = urllib.parse.urlsplit(values[fixture.PREFIX + "URL"])
        context = ssl.create_default_context(cafile=config["rootCAPath"])
        connection = http.client.HTTPSConnection("127.0.0.1", origin.port, timeout=5, context=context)
        response_count = 0
        for body in rounds():
            connection.request("POST", "/v1/chat/completions", canonical(body), {
                "Content-Type": "application/json", "Authorization": "Bearer " + config["modelKey"]})
            response = connection.getresponse()
            data = response.read()
            require(response.status == 200 and response.getheader("Content-Length") == str(len(data))
                    and response.getheader("Content-Type") == "text/event-stream; charset=utf-8"
                    and data.endswith(b"data: [DONE]\n\n"), "lifecycle_actual_sse")
            response_count += 1
        checks["actual_https_six_rounds_correct_framing"] = response_count == 6
        verified = command("verify", ["--safe-result", str(output / "verified-provider.json")])
        checks["verify_requires_exact_completed_contract"] = verified["complete"] is True and all(verified["checks"].values())
        safe = canonical(verified)
        checks["safe_result_omits_business_values_and_credentials"] = not any(
            s.encode() in safe for s in [*SCENARIO.values(), config["modelKey"], config["controlToken"]])
        # Keep the actual model HTTP/1.1 connection open while a separate CLI
        # requests shutdown. stop must close owned connections and await exit.
        ended = command("stop")
        stopped = ended.get("ownedChildExited") is True and ended.get("ownedListenerClosed") is True
        checks["stop_waits_for_actual_child_and_listener_with_keepalive_open"] = stopped
        repeated = command("stop")
        checks["exact_stop_retry_proves_same_exited_identity"] = repeated.get("ownedChildExited") is True
        require(all(checks.values()), "lifecycle_assertion_failed")
        result["status"] = "PASS"
    finally:
        if connection is not None: connection.close()
        if not stopped and config_path.exists():
            try:
                ended = command("stop")
                stopped = ended.get("ownedChildExited") is True and ended.get("ownedListenerClosed") is True
            except BaseException:
                pass
        if stopped:
            shutil.rmtree(private_parent)
        result["ownedChildAndListenerStopped"] = stopped
        result["privateDirectoryRemoved"] = not private_parent.exists()
        after = {str(p.relative_to(root)) if p.is_relative_to(root) else p.name: digest(p.read_bytes())
                 for p in source_paths}
        result["sourcesAfter"] = after
        result["sourceStable"] = before == after
        fixture.atomic_json(output / "result.json", result)
    print(json.dumps({"status": result["status"], "checks": len(checks), "sourceStable": result["sourceStable"],
                      "ownedChildAndListenerStopped": stopped, "privateDirectoryRemoved": result["privateDirectoryRemoved"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
