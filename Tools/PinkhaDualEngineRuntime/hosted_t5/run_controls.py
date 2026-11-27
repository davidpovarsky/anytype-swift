#!/usr/bin/env python3
"""One bounded Mac execution of all eleven NEW custody/control cases.

No Xcode, simulator, native account, network, old test replay or private-key
transfer. The original Commands and command-admission barrier own both child
groups. Only synthetic bytes are encrypted/restored; no source runs on import.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from types import ModuleType

sys.dont_write_bytecode = True

import publication
from profile import require, strict_json

ORIGINALS = {
    "shared": ("Tools/CurrentAppleValidation/combined_heart_semantics/build15/combined_heart_semantics_current.py", "1dcd02a4413b26c201e8a38772484eff48e448ae4398af2fd4ee1fc6a5675736"),
    "lifetime": ("Tools/PinkhaDualEngineRuntime/hosted_core13/run.py", "cf16f08fefcc0d639e1f924a230c2fefb8bcc7af4f311e9e03191165908a29c8"),
    "t5": ("Tools/CurrentAppleValidation/combined_heart_semantics/build15/combined_host_acceptance_app15.py", "e574f30bd123e6645f093951744a924bf2e9190be6c7474480eb6ec8f58d8eed"),
    "signals": ("Tools/Hanlin/host_command.py", "5f09813c5719f5ea3920c003e58ac6b2b5633f276686bf6c5ef8bc6f9f39a807"),
}
PYTHON_METHODS = (
    "test_original_stage_failure_survives_receipt_io_failure",
    "test_closed_source_profile_cannot_admit_a_runtime",
    "test_unresolved_original_group_forbids_preserve_shutdown_and_next_command",
    "test_terminal_io_failure_does_not_replace_prior_native_error",
    "test_first_terminal_io_failure_replaces_only_an_explicit_null_cause",
    "test_ui_publication_uses_only_original_selected_attachment_references",
)
NODE_METHODS = (
    "ciphertext seal preserves original evidence and refuses replacement",
    "unowned scope and mismatched Node are rejected before a ciphertext is created",
    "a private scope symlink never expands the finite owned input",
    "authenticated receiver restores exact file bytes and refuses an existing destination",
    "tampered GCM ciphertext creates no plaintext file or destination",
)
RECEIVER_CLOSURE_SHA = "7f7e5dce6a6c5f82c8573126d4892f01a93440d7531f2d452f0b29ca1fd2d2e7"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_declarations(root, kind, names, bindings=None):
    relative, expected = ORIGINALS[kind]
    path = root / relative
    require(path.resolve() == path and not path.is_symlink() and sha(path) == expected, "Exact original lifecycle source required")
    text = path.read_text(); tree = ast.parse(text)
    selected = []
    for name in names:
        found = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name]
        require(len(found) == 1, "One exact lifecycle declaration required")
        selected.append(found[0])
    module = ModuleType("t5_control_original_" + kind)
    module.__file__ = str(path)
    module.__dict__.update({"Path": Path, "contextmanager": contextmanager, "hashlib": hashlib, "json": json, "os": os, "re": re,
        "shutil": shutil, "signal": signal, "stat": stat, "subprocess": subprocess, "sys": sys, "time": time,
        "FLOOR": 2 * 1024**3, **(bindings or {})})
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *selected], type_ignores=[])), str(path), "exec"), module.__dict__)
    return module


def qualify_source(args):
    require(args.source.is_absolute() and args.source.resolve() == args.source
            and args.source_index.is_file() and sha(args.source_index) == args.source_index_sha256, "Exact frozen control input required")
    index = strict_json(args.source_index.read_bytes())
    require(index["schema"] == "pinkha-hosted-t5-source-index-v1" and index["readyForRuntime"] is False
            and index["testsExecuted"] == 0, "Only reviewed closed source is eligible for this control run")
    rows = index["files"]
    require(set(rows) == {path.name for path in args.source.iterdir() if path.is_file()}
            and sum(row["bytes"] for row in rows.values()) < 1024**2, "Complete bounded source index required")
    for name, pin in rows.items():
        path = args.source / name
        require(path.resolve() == path and not path.is_symlink() and path.stat().st_size == pin["bytes"]
                and sha(path) == pin["sha256"], "Frozen control source changed")
    tree = ast.parse((args.source / "test_control.py").read_text())
    case = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "SourceControl")
    actual = tuple(node.name for node in case.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    require(actual == PYTHON_METHODS, "Exactly the six authored Python controls required")
    tests = (args.source / "custody_crypto.test.mjs").read_text()
    require(tuple(re.findall(r"^test\('([^']+)'", tests, re.MULTILINE)) == NODE_METHODS,
            "Exactly the five authored Node controls required")
    require(sha(args.source / "recipient-public.pem") == publication.RECIPIENT_SHA, "Exact existing public recipient required")
    return index


def receiver_identity(args):
    require(sha(args.receiver_node_closure) == RECEIVER_CLOSURE_SHA, "Original observed complete Mac Node closure required")
    observed = strict_json(args.receiver_node_closure.read_bytes())
    images = sorted(observed["images"], key=lambda row: row["path"])
    require(len(images) == 18 and sum(row["bytes"] for row in images) == 89563424
            and observed["machine"] == "arm64" and observed["macOS"] == "27.0", "Actual reviewed receiver scope differs")
    for row in images:
        path = Path(row["path"])
        require(path.resolve() == path and str(path) == row["resolvedPath"] and path.is_file()
                and path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], "Actual Node dependency changed")
    executable = "/opt/homebrew/Cellar/node@22/22.23.5_2/bin/node"
    row = next(row for row in images if row["path"] == executable)
    key, parent = args.receiver_private_key, args.receiver_private_key.parent
    require(key.resolve() == key and not key.is_symlink() and key.is_file()
            and stat.S_IMODE(key.stat().st_mode) == 0o600 and key.stat().st_uid == os.getuid()
            and parent.resolve() == parent and stat.S_IMODE(parent.stat().st_mode) == 0o700, "Existing private receiver permissions required")
    # Never read key bytes here; only the bounded original Node receiver reads
    # the actual existing key, locally, during the two synthetic receiver cases.
    return {"executable": executable, "executableSHA256": row["sha256"], "nodeVersion": observed["nodeVersion"],
            "opensslVersion": observed["opensslVersion"], "platform": "darwin", "machine": observed["machine"],
            "macOS": observed["macOS"], "images": images}


def run(args):
    require(sys.platform == "darwin" and os.uname().machine == "arm64", "Actual matching Mac required")
    source_index = qualify_source(args)
    node = receiver_identity(args)
    require(args.output.is_absolute() and args.output.parent.resolve() == args.output.parent
            and not args.output.exists() and not args.output.is_symlink(), "Exclusive new owned control output required")
    require(shutil.disk_usage(args.output.parent).free >= 2 * 1024**3 + 512 * 1024**2 + 64 * 1024**2,
            "Original resource floor plus bounded synthetic-control reserve required")
    args.output.mkdir(mode=0o700)
    for name in ("fixtures", "restored"):
        (args.output / name).mkdir(mode=0o700)
    shared = load_declarations(args.original_root, "shared", ("require", "sha", "digest", "raw", "decode", "write_bytes", "write", "error", "Commands"))
    lifetime = load_declarations(args.original_root, "lifetime", ("CommandAdmission",), {"require": shared.require})
    observer = load_declarations(args.original_root, "t5", ("observe_owned_groups",), {"shared": shared})
    commands = lifetime.CommandAdmission(shared.Commands(args.output / "commands", args.source), shared.error)
    commands.environment.update(TMPDIR=str(args.output / "fixtures"), PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN", "NODE_OPTIONS", "NODE_PATH", "OPENSSL_CONF", "OPENSSL_MODULES"):
        commands.environment.pop(key, None)
    receiver_plan = publication.private_json(args.output / "receiver-control-plan.json",
        {"privateKey": str(args.receiver_private_key), "parent": str(args.output / "restored"), "nodeIdentity": node})
    commands.environment["PINKHA_T5_LOCAL_RECEIVER_CONTROL_PLAN"] = receiver_plan["path"]
    result = {"schema": "pinkha-t5-eleven-mac-controls-v1", "status": "FAIL", "startedAt": time.time(),
        "sourceIndexSHA256": args.source_index_sha256, "receiverClosureSHA256": RECEIVER_CLOSURE_SHA,
        "expectedUniqueControls": 11, "pythonMethods": list(PYTHON_METHODS), "nodeMethods": list(NODE_METHODS),
        "series": {}, "testsFromOriginalT5Executed": 0, "nativeAccountsOpened": 0, "simulatorsCreated": 0,
        "XcodeCommandsExecuted": 0, "networkCalls": 0, "privateKeyTransferred": False, "firstFailure": None}
    first = None
    def fail(error, phase):
        nonlocal first
        if first is None:
            first = {"phase": phase, **shared.error(error)}
    try:
        for name, argv, timeout in (("python-six", [sys.executable, "-B", str(args.source / "test_control.py"), "-v"], 60),
            ("node-five", [node["executable"], "--test", "--test-reporter=tap", str(args.source / "custody_crypto.test.mjs")], 120)):
            require(commands.is_open, "Original unresolved group forbids the next control process")
            command = None
            try:
                log, command = commands.run(argv, name, timeout, checked=False)
                interruption = command.get("interruption")
                if isinstance(interruption, dict):
                    if first is None:
                        first = {"phase": name, **interruption}
                    if interruption.get("type") in {"CommandCancelled", "KeyboardInterrupt"}:
                        commands.original.cancelled = True
                text = shared.raw(log).decode()
                if name == "python-six":
                    require(re.search(r"\bRan 6 tests in [0-9.]+s", text) and re.search(r"^OK$", text, re.MULTILINE)
                            and all(text.count(method + " (") == 1 for method in PYTHON_METHODS), "Every original six Python control must execute once and pass")
                else:
                    require(re.search(r"^# tests 5$", text, re.MULTILINE) and re.search(r"^# pass 5$", text, re.MULTILINE)
                            and all(re.search(r"^# " + key + r" 0$", text, re.MULTILINE) for key in ("fail", "cancelled", "skipped", "todo"))
                            and all(len(re.findall(r"^ok [0-9]+ - " + re.escape(method) + r"$", text, re.MULTILINE)) == 1 for method in NODE_METHODS),
                            "All five actual Node controls including receiver/authentication must pass without skip")
                require(command["status"] == "PASS_COMMAND" and command["exitCode"] == 0, "Actual control command failed")
                result["series"][name] = {"status": "PASS", "originalCommand": command,
                    "logSHA256": sha(log), "logBytes": log.stat().st_size}
            except BaseException as error:
                fail(error, name)
                result["series"][name] = {"status": "FAIL", "error": shared.error(error), "originalCommand": command}
                if isinstance(error, KeyboardInterrupt):
                    commands.original.cancelled = True
                if not commands.is_open or commands.original.cancelled:
                    break
        if len(result["series"]) == 2 and all(row["status"] == "PASS" for row in result["series"].values()):
            result["status"] = "PASS_ELEVEN_SYNTHETIC_MAC_CONTROLS_NOT_APP_OR_T5_ACCEPTANCE"
    except BaseException as error:
        fail(error, "control-supervisor")
    finally:
        result["ownedProcessClosure"] = observer.observe_owned_groups(commands)
        if commands.blocked is not None or result["ownedProcessClosure"]["status"] != "PASS":
            result["status"] = "FAIL"
            if first is None:
                first = commands.blocked or result["ownedProcessClosure"]
        try:
            require(qualify_source(args) == source_index, "Control source changed during the actual control run")
            require(receiver_identity(args) == node, "Original complete Node image custody changed")
        except BaseException as error:
            fail(error, "file-only-final-inputs"); result["status"] = "FAIL"
        result["firstFailure"] = first
        result["finishedAt"] = time.time()
        try:
            publication.private_json(args.output / "result.json", result)
        except BaseException as error:
            fail(error, "final-receipt"); result["firstFailure"] = first; result["status"] = "FAIL"
            result["terminalReceiptFailure"] = shared.error(error)
    # All case payloads are synthetic. Keep only safe metadata on stdout; the
    # original command logs and complete receipt remain in the owned directory.
    print(json.dumps({"status": result["status"], "expectedUniqueControls": 11,
        "series": {key: row["status"] for key, row in result["series"].items()},
        "firstFailureType": (first or {}).get("type"), "originalT5Replayed": False, "privateKeyTransferred": False}, sort_keys=True))
    return 0 if result["status"] == "PASS_ELEVEN_SYNTHETIC_MAC_CONTROLS_NOT_APP_OR_T5_ACCEPTANCE" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "source-index", "original-root", "receiver-node-closure", "receiver-private-key", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-index-sha256", required=True)
    args = parser.parse_args()
    original_signals = load_declarations(args.original_root, "signals", ("CommandCancelled", "cancellation_signals"))
    with original_signals.cancellation_signals():
        return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
