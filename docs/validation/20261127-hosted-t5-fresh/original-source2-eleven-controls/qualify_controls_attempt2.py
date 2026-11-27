#!/usr/bin/env python3
"""Read-only qualification of the one corrected Mac source2/run1 attempt.

No imports of staged code, process probes, subprocesses, writes, retries, account
or simulator operations. Missing originals remain explicit gaps. This report is
a review of original evidence, never a replacement native or control receipt.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path("/Users/m1/development/anytype-root-active-20261125/t5-custody-controls-20261127-source2")
SOURCE_INDEX = "d011bb85ac64a9d21ffd55767cc8346105ac8ae7cf156761d81ca0b56f24f6c0"
BUNDLE = "5beff2d03880c7e7db72d9d627f645026ae9b46fde7246d24cc63f6d40d3f10f"
INVENTORY = "2371c7cc9e809ff1b651985dcfaa7ed31e5d2e89bb146d01e0959e900edcdf0c"
RECEIVER = "7f7e5dce6a6c5f82c8573126d4892f01a93440d7531f2d452f0b29ca1fd2d2e7"
FILES = {'input/hosted_t5/README.md': {'bytes': 10782, 'sha256': 'f617d7200e8589c316ae7c2767efd893974a04a292b70b4646ef0cae64253af4'}, 'input/hosted_t5/activation.json': {'bytes': 690, 'sha256': 'b3fcfed369598b852580a680544244467b72daea5e73bef88b8878caefbf1f29'}, 'input/hosted_t5/custody_crypto.mjs': {'bytes': 26407, 'sha256': '469ec4884cb377972265b2b58bc6fd1ef7db757a050b5204019ae00b64f3af0a'}, 'input/hosted_t5/custody_crypto.test.mjs': {'bytes': 4970, 'sha256': '18600324a3daff1cfa4ec5bb26b5823b1e6b7c8370b54caf615439513c7acf3a'}, 'input/hosted_t5/job_binding.py': {'bytes': 2046, 'sha256': '781356dcbe8f607dd45a898d514aa54a471c1e110605e8bb1055926ec7b3e78e'}, 'input/hosted_t5/original_sources.json': {'bytes': 3855, 'sha256': '1807a0aab8d76b53691a9e97a58339c251263a8f42377ef6d5f7166ed855df77'}, 'input/hosted_t5/profile.py': {'bytes': 8915, 'sha256': 'aea717fe620b6ad5791a8e529ed0736dde0d3cd68c28cc6bfaa8eadd65530d08'}, 'input/hosted_t5/promote_identity.py': {'bytes': 6569, 'sha256': 'fda2e5231503030813ecc38cca6923e0d693d07150cc810d625fe6f586fb7c3a'}, 'input/hosted_t5/publication.py': {'bytes': 12175, 'sha256': 'bbdcb6cd24ea4f0a1629692cd86f74df0dacd47d078efe4d7dbcd1de77e00d5b'}, 'input/hosted_t5/recipient-public.pem': {'bytes': 625, 'sha256': '47a137c28c8564ba8c913b00db9a9e47e5669092b7112e10adfec59949cf6853'}, 'input/hosted_t5/run.py': {'bytes': 23922, 'sha256': 'b95a9c72d1a9b048df36216ea81d49966462e04f7c2887473b1ed11f84698d47'}, 'input/hosted_t5/run_controls.py': {'bytes': 14578, 'sha256': 'de021b657c1f91e630204fd58eed6e1364c113c3b57d2d8915f0e2cb9cb5e2f4'}, 'input/hosted_t5/t5_originals.py': {'bytes': 6756, 'sha256': '6f57f5d4d012f98affd8335312eeff0fea2a71d561f6ea3ba1b160ae1e36a9ac'}, 'input/hosted_t5/test_control.py': {'bytes': 6145, 'sha256': '4604583436f26338f7751fe2699800ea560e807cd5faedfde881c1045b7d6314'}, 'input/original/Tools/CurrentAppleValidation/combined_heart_semantics/build15/combined_heart_semantics_current.py': {'bytes': 82071, 'sha256': '1dcd02a4413b26c201e8a38772484eff48e448ae4398af2fd4ee1fc6a5675736'}, 'input/original/Tools/CurrentAppleValidation/combined_heart_semantics/build15/combined_host_acceptance_app15.py': {'bytes': 50267, 'sha256': 'e574f30bd123e6645f093951744a924bf2e9190be6c7474480eb6ec8f58d8eed'}, 'input/original/Tools/Hanlin/host_command.py': {'bytes': 4236, 'sha256': '5f09813c5719f5ea3920c003e58ac6b2b5633f276686bf6c5ef8bc6f9f39a807'}, 'input/original/Tools/PinkhaDualEngineRuntime/hosted_core13/run.py': {'bytes': 28729, 'sha256': 'cf16f08fefcc0d639e1f924a230c2fefb8bcc7af4f311e9e03191165908a29c8'}, 'input/receiver-node-closure.json': {'bytes': 5322, 'sha256': '7f7e5dce6a6c5f82c8573126d4892f01a93440d7531f2d452f0b29ca1fd2d2e7'}, 'input/source-index.json': {'bytes': 2059, 'sha256': 'd011bb85ac64a9d21ffd55767cc8346105ac8ae7cf156761d81ca0b56f24f6c0'}}
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


def read_original(relative, limit=2 * 1024**2):
    path = ROOT / relative
    if not os.path.lexists(path):
        return {"path": str(path), "status": "MISSING_ORIGINAL"}, None
    try:
        if path.resolve() != path:
            raise ValueError("Original path is not physical")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise ValueError("Original file type or bounded size differs")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                data = stream.read(limit + 1)
            after = os.fstat(descriptor)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("Original file changed while read")
            if len(data) != before.st_size:
                raise ValueError("Original bounded read incomplete")
            return {"path": str(path), "status": "READ_ORIGINAL", "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest()}, data
        finally:
            os.close(descriptor)
    except Exception as error:
        return {"path": str(path), "status": "READ_FAILED", "type": type(error).__name__}, None


def main():
    report = {"schema": "pinkha-t5-attempt2-readonly-qualification-v1", "status": "NOT_QUALIFIED",
        "sourceIndexSHA256": SOURCE_INDEX, "bundleSHA256": BUNDLE, "inventorySHA256": INVENTORY,
        "originals": {}, "checks": [], "actualFirstFailure": None, "nativeAcceptance": False,
        "commandsExecuted": 0, "historicalGroupsReprobed": False, "privateKeyRead": False}
    originals = report["originals"]
    checks = report["checks"]

    def check(name, condition):
        checks.append({"name": name, "status": "PASS" if condition else "FAIL"})

    def original(relative, decode=True):
        evidence, data = read_original(relative)
        originals[relative] = evidence
        if data is None:
            return None
        if not decode:
            return data
        try:
            return json.loads(data)
        except Exception as error:
            evidence["decodeFailureType"] = type(error).__name__
            return None

    staging = original("staging-receipt.json")
    result = original("run1/result.json")
    source_index = original("input/source-index.json")
    receiver = original("input/receiver-node-closure.json")
    check("original source index bytes", originals["input/source-index.json"].get("sha256") == SOURCE_INDEX)
    check("original receiver closure bytes", originals["input/receiver-node-closure.json"].get("sha256") == RECEIVER)
    check("exact twenty original inputs", staging is not None
        and staging.get("sourceBefore") == FILES and staging.get("sourceAfter") == FILES
        and staging.get("sourceUnchanged") is True and staging.get("files") == 20
        and staging.get("unpackedBytes") == 301119 and staging.get("bundleSHA256") == BUNDLE
        and staging.get("inventorySHA256") == INVENTORY and staging.get("sourceIndexSHA256") == SOURCE_INDEX
        and staging.get("status") == "PASS_STAGED_NOT_CONTROL_EXECUTION")
    for relative, expected in FILES.items():
        data = original(relative, decode=False)
        row = originals[relative]
        check("retained input: " + relative, data is not None and row.get("bytes") == expected["bytes"]
              and row.get("sha256") == expected["sha256"])
    check("closed final product source", source_index is not None and source_index.get("readyForRuntime") is False
          and source_index.get("finalProducerTuple") is None and source_index.get("testsExecuted") == 0
          and len(source_index.get("files", {})) == 14)
    check("original full eighteen-image Node closure", receiver is not None and len(receiver.get("images", [])) == 18
          and sum(row["bytes"] for row in receiver["images"]) == 89563424
          and receiver.get("macOS") == "27.0" and receiver.get("machine") == "arm64")
    # The actual supervisor's exact source qualifies these same eighteen files
    # before and after its commands. Do not fabricate historical per-image
    # observations or substitute a fresh receiver process for that witness.
    report["receiverCustodyScope"] = "original pinned closure plus exact supervisor preflight/final checks; no new Node invocation or image rehash"
    if result is not None:
        report["actualFirstFailure"] = result.get("firstFailure")
        report["originalResult"] = result
    check("original terminal eleven-control pass", result is not None
          and result.get("status") == "PASS_ELEVEN_SYNTHETIC_MAC_CONTROLS_NOT_APP_OR_T5_ACCEPTANCE"
          and result.get("firstFailure") is None and result.get("sourceIndexSHA256") == SOURCE_INDEX
          and result.get("receiverClosureSHA256") == RECEIVER and result.get("expectedUniqueControls") == 11)
    check("original exact method inventory", result is not None
          and result.get("pythonMethods") == list(PYTHON_METHODS) and result.get("nodeMethods") == list(NODE_METHODS))
    check("original zero native scope", result is not None and all(result.get(key) == 0 for key in (
        "testsFromOriginalT5Executed", "nativeAccountsOpened", "simulatorsCreated", "XcodeCommandsExecuted", "networkCalls"))
        and result.get("privateKeyTransferred") is False)
    groups = []
    for label, timeout in (("python-six", 60), ("node-five", 120)):
        directory = "run1/commands/" + label + "/"
        log = original(directory + "original.log", decode=False)
        command = original(directory + "result.json")
        exit_receipt = original(directory + "process-exit.json")
        # These are read if present even when an earlier receipt failed. No
        # missing file is manufactured, and no later series is dispatched.
        started = original(directory + "started.json")
        interruption = original(directory + "interruption.json")
        if command is None and interruption is not None:
            report.setdefault("originalInterruptionEvidence", {})[label] = interruption
        series = (result or {}).get("series", {}).get(label)
        check(label + " original series receipt", isinstance(series, dict) and series.get("status") == "PASS"
              and isinstance(command, dict) and series.get("originalCommand") == command)
        log_row = originals[directory + "original.log"]
        check(label + " original log binding", isinstance(command, dict)
              and command.get("logSHA256") == log_row.get("sha256") and command.get("logBytes") == log_row.get("bytes")
              and isinstance(series, dict) and series.get("logSHA256") == log_row.get("sha256")
              and series.get("logBytes") == log_row.get("bytes"))
        check(label + " original exit/cleanup", isinstance(command, dict) and command.get("status") == "PASS_COMMAND"
              and command.get("commandStatus") == "PASS_COMMAND" and command.get("exitCode") == 0
              and command.get("timeoutSeconds") == timeout and command.get("cleanupErrors") == []
              and command.get("termination") == [] and "interruption" not in command)
        check(label + " original positive absence", isinstance(command, dict)
              and command.get("ownedGroupObservationStatus") == "ABSENT_ESRCH"
              and command.get("ownedGroupPresentAfterExit") is False
              and command.get("ownedGroupObservations", [{}])[-1].get("status") == "ABSENT_ESRCH")
        exit_row = originals[directory + "process-exit.json"]
        check(label + " original pre-probe exit receipt", isinstance(command, dict) and isinstance(exit_receipt, dict)
              and command.get("processExitReceipt") == {key: exit_row.get(key) for key in ("path", "sha256", "bytes")}
              and exit_receipt.get("status") == "EXIT_RECORDED_PENDING_GROUP_OBSERVATION"
              and exit_receipt.get("commandStatus") == "PASS_COMMAND" and exit_receipt.get("exitCode") == 0)
        if isinstance(command, dict) and type(command.get("pgid")) is int:
            groups.append(command["pgid"])
        text = "" if log is None else log.decode("utf-8", "replace")
        if label == "python-six":
            actual = re.findall(r"^(test_[A-Za-z0-9_]+) \([^\n]+\) \.\.\. ok$", text, re.MULTILINE)
            check("all six Python methods actually passed once", len(actual) == len(PYTHON_METHODS) and set(actual) == set(PYTHON_METHODS)
                  and re.search(r"\bRan 6 tests in [0-9.]+s", text) is not None
                  and re.search(r"^OK$", text, re.MULTILINE) is not None)
        else:
            actual = re.findall(r"^ok [0-9]+ - ([^\n]+)$", text, re.MULTILINE)
            check("all five Node methods actually passed once with zero skips", tuple(actual) == NODE_METHODS
                  and re.search(r"^# tests 5$", text, re.MULTILINE) is not None
                  and re.search(r"^# pass 5$", text, re.MULTILINE) is not None
                  and all(re.search(r"^# " + name + r" 0$", text, re.MULTILINE) is not None
                          for name in ("fail", "cancelled", "skipped", "todo")))
        report.setdefault("observedMethodPasses", {})[label] = actual
    closure = (result or {}).get("ownedProcessClosure")
    check("original two groups positively closed without historical reprobe", isinstance(closure, dict)
          and closure.get("status") == "PASS" and closure.get("errors") == [] and len(groups) == 2
          and closure.get("groups") == [{"pgid": group, "absentAtOriginalExit": True,
                                         "historicalGroupReprobed": False} for group in groups])
    if all(row["status"] == "PASS" for row in checks):
        report["status"] = "PASS_ORIGINAL_ELEVEN_SYNTHETIC_CONTROLS_EVIDENCE_NOT_T5_OR_APP_ACCEPTANCE"
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
