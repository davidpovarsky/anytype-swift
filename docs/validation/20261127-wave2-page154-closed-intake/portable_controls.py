#!/usr/bin/env python3
"""Closed-state controls only; no canonical admission or product is fabricated."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "prepare_wave2_page154_shared_profile_closed.py"
ORIGINAL_SHA = "a9a8ee451d4ae5acd8b207c90404ca97ee2f184134dd648d16038103a64ead08"
CANDIDATE_SHA = "0893c414fb7bacde191679df7cde048235463413832b3937d43553d20c786789"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    receipt = ROOT / "portable-controls1.json"
    assert not receipt.exists()
    before = SOURCE.read_bytes()
    assert sha(before) == CANDIDATE_SHA
    spec = importlib.util.spec_from_file_location("closed_page154", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    results = []
    began = time.monotonic()
    inverse = json.loads((ROOT / "source-inverse.json").read_bytes())
    restored = before.decode()
    for row in reversed(inverse["edits"]):
        assert restored.count(row["after"]) == 1
        restored = restored.replace(row["after"], row["before"], 1)
    assert sha(restored.encode()) == ORIGINAL_SHA
    old, new = module.definitions(restored.encode()), module.definitions(before)
    assert set(old) == set(new)
    assert {name for name in old if old[name] != new[name]} == {"prepare"}
    results.append({"boundary": "exact_original4005_inverse_and_unchanged_helpers_main", "status": "PASS"})

    assert inverse["currentSharedCommandsByteIdentical"] is True
    assert all(inverse["currentSharedAPIsPresent"].values())
    assert module.SOURCE is module.FUTURE_SHARED_CONTROLLER_SHA256 is module.FUTURE_CANONICAL_ADMISSION_SHA256 is None
    assert module.READY_FOR_MATERIALIZATION is False
    assert ast.get_source_segment(restored, next(n for n in ast.parse(restored).body if isinstance(n, ast.FunctionDef) and n.name == "main")) == new["main"]
    results.append({"boundary": "fixed_missing_pins_and_no_new_cli_source_override", "status": "PASS"})

    output = ROOT / "control-output-must-not-exist"
    assert not output.exists()
    reads = []
    def forbidden_read(*args):
        reads.append(args)
        raise AssertionError("Closed preparer touched an input")
    module.read = forbidden_read
    def rejected():
        try:
            module.prepare(ROOT, ROOT / "unadmitted-shared.py", "a" * 64,
                           ROOT / "unadmitted-canonical.json", "b" * 64,
                           ROOT / "unadmitted-typed.py", output)
        except ValueError as error:
            assert "future shared profile is closed" in str(error)
        else:
            raise AssertionError("Unknown producer admitted")
        assert reads == [] and not output.exists()
    rejected()
    results.append({"boundary": "closed_preparer_rejects_before_reads_or_output", "status": "PASS"})

    try:
        module.READY_FOR_MATERIALIZATION = True
        for source in (None, "a089ff29a5c0a7e415aac800844505f099a5561d", "8f2c11713fb8a40ae13444104723666ffef68afe"):
            module.SOURCE = source
            rejected()
    finally:
        module.READY_FOR_MATERIALIZATION = False
        module.SOURCE = None
    results.append({"boundary": "ready_flag_or_historical_source_alone_cannot_bypass_missing_exact_pins", "status": "PASS"})
    assert SOURCE.read_bytes() == before
    result = {
        "schema": "pinkha-page154-closed-preparer-portable-controls-v1",
        "status": "PASS_CLOSED_PREPARER_CONTROLS_NOT_APPLE_EXECUTION",
        "controllerSHA256": sha(Path(__file__).read_bytes()),
        "candidateSHA256": CANDIDATE_SHA,
        "inverseSHA256": sha((ROOT / "source-inverse.json").read_bytes()),
        "controls": results, "controlsPassed": len(results),
        "durationSeconds": time.monotonic() - began,
        "inputReadsFromRejectedPrepare": len(reads),
        "controllerDirectoriesMaterialized": 0,
        "canonicalAdmissionsFabricated": 0,
        "AppleInvocations": 0, "nativeCalls": 0, "XCTestMethodsExecuted": 0,
    }
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
