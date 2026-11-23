"""Verify exact historical native prestart evidence and its unaffected execution path."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

BASE_PACKET = "docs/pinkha/torah-integration/native-heart-rpc-runtime-20261123"
BASE_SOURCE = "54169c763c2178fc1e796dfbe92a675d9c21a0b3"
BASE_MANIFEST = "4fc15e8112172752f85e9e67e6eace8cf6a0c0f473f71a4817ac01b2853f243b"
PRIOR_ZIP = "9358c6636a4b175d56596b09f56c3e4a898b30252dd5548d55fd9f89f057586d"
PRIOR_FIXTURE = "857e7f6b421542a51c597a9332050374cfde9035760b949e30a8b981142a376d"
PRIOR_RECEIPT = "b73d2dfe4934d06d3573c790e131e78a7eccde4389c56bdaa13b47b37e0e816b"
NOOP_SHA = "e58d6d6dd8d68adf8e830bea83a239bb4304f805c3f1ffd3704a63b14a962a8e"
CASE = "TestOtzariaOwnedImportNativeLifetime/RegisteredPreStartCancellationRequiresActualReturn"
FAILED_CASE = "TestOtzariaOwnedImportNativeLifetime/OriginalProtobufImportAndReentrantRetirement"
MAPPING_PATH = "core/block/import/mapping_observation.go"
MAPPING_BEFORE = '\tif !eligible || traceID == "" || processID == "" || targetSpaceID == "" {\n'
MAPPING_AFTER = (
    "\t// Original process.NewNoOp has no progress process ID. Keep that copied\n"
    "\t// observation empty; the actual Execute-generated trace remains required.\n"
    "\t// A progress ID is neither an assignment prerequisite nor authority.\n"
    '\tif !eligible || traceID == "" || targetSpaceID == "" {\n'
)

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def committed(control, relative):
    path = control / relative
    require(path.resolve().is_relative_to(control.resolve()), "Reuse source escapes checkout")
    data = path.read_bytes()
    original = subprocess.check_output(
        ["git", "-C", str(control), "show", "HEAD:" + str(relative)], timeout=60)
    require(data == original, "Dirty reused native source/evidence")
    return data

def verify(control, packet, manifest):
    control, packet = Path(control), Path(packet)
    baseline_bytes = committed(control, BASE_PACKET + "/EXECUTION_INPUTS.json")
    require(sha(baseline_bytes) == BASE_MANIFEST, "Original native manifest differs")
    baseline = json.loads(baseline_bytes)
    require(manifest["source_inputs"] == baseline["source_inputs"], "Retained 42 original inputs changed")
    require(manifest["baseline_product_hashes"] == baseline["unchanged_product_hashes"],
            "Original 28-product baseline differs")
    require(manifest["base"] == BASE_SOURCE and manifest["prestart_reuse"]["run_id"] == 45105771388,
            "Wrong native reuse lineage")
    require(manifest["selector"] ==
            "^TestOtzariaOwnedImportNativeLifetime$/^OriginalProtobufImportAndReentrantRetirement$"
            and manifest["expected_cases"] == [FAILED_CASE], "Passed native leaf would be replayed")

    old_fixture = committed(control, BASE_PACKET + "/" + baseline["test_file"])
    new_fixture = (packet / manifest["test_file"]).read_bytes()
    require(sha(old_fixture) == PRIOR_FIXTURE, "Historical native fixture differs")
    first = b'\tt.Run("OriginalProtobufImportAndReentrantRetirement", func(t *testing.T) {'
    second = b'\tt.Run("RegisteredPreStartCancellationRequiresActualReturn", func(t *testing.T) {'
    require(old_fixture.count(first) == new_fixture.count(first) == 1
            and old_fixture.count(second) == new_fixture.count(second) == 1, "Unexpected native fixture shape")
    require(old_fixture[:old_fixture.index(first)] == new_fixture[:new_fixture.index(first)]
            and old_fixture[old_fixture.index(second):] == new_fixture[new_fixture.index(second):],
            "Passed prestart case or shared fixture helper changed")
    passed_suffix = old_fixture[old_fixture.index(second):]

    repairs = manifest["product_repairs"]
    require(len(repairs) == 1 and repairs[0]["native_path"] == MAPPING_PATH,
            "Reuse excludes only the reviewed mapping-finish correction")
    repair = repairs[0]
    mapping_before = committed(control, BASE_PACKET + "/retained-inputs/" + repair["baseline_destination"])
    mapping_after = (packet / repair["path"]).read_bytes()
    require(sha(mapping_before) == repair["before_sha256"]
            and sha(mapping_after) == repair["after_sha256"], "Mapping correction source differs")
    before_text = mapping_before.decode()
    require(before_text.count(MAPPING_BEFORE) == 1
            and mapping_after.decode() == before_text.replace(MAPPING_BEFORE, MAPPING_AFTER),
            "Correction changes more than original no-progress observation admission")

    retained = control / BASE_PACKET / "retained-inputs"
    processor = (retained / "owned/composition/native/core/block/import/processor.go").read_text()
    files = (retained / "owned/composition/native/core/block/import/owned_import_files.go").read_text()
    begin = processor.index("func (p *importProcessor) Execute(ctx context.Context)")
    reset = processor.index("p.resetNativeMappingObservation()", begin)
    early = processor[begin:reset]
    require("if err := p.owned.beginRun(); err != nil {" in early
            and "return &ImportResponse{Err: err}" in early, "Original canceled Execute early return differs")
    start = files.index("func (o *ownedImportExecution) beginRun() error {")
    stop = files.index("func newOwnedImportExecution(", start)
    begin_run = files[start:stop]
    require('if err := o.ctx.Err(); err != nil {\n\t\treturn err\n\t}' in begin_run
            and begin_run.index("o.ctx.Err()") < begin_run.index("o.started = true"),
            "Original pre-canceled native admission differs")
    require(reset < processor.index("defer func() {", begin)
            and processor.index("defer func() {", begin) < processor.index("p.retainNativeMappingObservation(ctx)", begin),
            "Original mapping retain ordering differs")

    evidence = packet / "retained-run-45105771388"
    archive = evidence / "original-heart-native-lifetime.zip"
    require(sha(archive.read_bytes()) == PRIOR_ZIP, "Authentic prior native archive changed")
    run = json.loads((evidence / "RUN.json").read_bytes())
    require(run["id"] == 45105771388 and run["head_sha"] == BASE_SOURCE
            and run["head_branch"] == "codex/otzaria-heart-native-20261123"
            and run["run_attempt"] == 1 and run["event"] == "push"
            and run["status"] == "completed" and run["conclusion"] == "failure",
            "Prior run must remain the authentic partial failure")
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None and len(z.namelist()) == 37
                and len(set(z.namelist())) == 37, "Prior ZIP framing/CRC differs")
        rows = json.loads(z.read("EVIDENCE_INDEX.json"))["files"]
        require(len(rows) == 36 and {r["path"] for r in rows} ==
                set(z.namelist()) - {"EVIDENCE_INDEX.json"}, "Prior indexed evidence is incomplete")
        for row in rows:
            data = z.read(row["path"])
            require(len(data) == row["bytes"] and sha(data) == row["sha256"], "Prior evidence byte mismatch")
        result = json.loads(z.read("RESULT.json"))
        require(result["control_head"] == BASE_SOURCE and result["heart_base"] == manifest["heart_base"]
                and result["status"] == "FAIL" and result["historical_controls_replayed"] is False
                and result["owned_native_temporary_removed"] is True, "Prior native scope/cleanup differs")
        commands = json.loads(z.read("COMMANDS.json"))
        require(len(commands) == 14 and all(c["status"] == "TERMINAL" and not c["timed_out"]
                and c["cleanup"] and all(e["drained"] for e in c["cleanup"]) for c in commands),
                "Prior owned native commands did not drain")
        require(all(c["effective_returncode"] == 0 for c in commands[:-1])
                and commands[-1]["label"] == "execute-new-native-cases"
                and commands[-1]["effective_returncode"] == 1, "Prior native execution differs")
        events = [json.loads(line) for line in z.read("14-execute-new-native-cases.stdout").splitlines()]
        passes = [e for e in events if e.get("Test") == CASE and e.get("Action") == "pass"]
        require(len(passes) == 1 and sum(e.get("Test") == CASE and e.get("Action") == "run" for e in events) == 1
                and not any(e.get("Test") == CASE and e.get("Action") in ("fail", "skip") for e in events),
                "Prior prestart case was not actually executed and passed once")
        require(sum(e.get("Test") == FAILED_CASE and e.get("Action") == "fail" for e in events) == 1,
                "Original failed first leaf must not be relabeled")
        receipt_bytes = z.read("registered-prestart-cancellation.json")
        require(sha(receipt_bytes) == PRIOR_RECEIPT, "Prior actual native receipt differs")
        receipt = json.loads(receipt_bytes)
        require(receipt["ack_authority"] is False and
                all(v is True for k, v in receipt.items() if k != "ack_authority"),
                "Prior actual prestart/return/retirement facts differ")
        declared = json.loads(z.read("DECLARED_NATIVE_INPUTS.json"))["files"]
        for path, digest in baseline["unchanged_product_hashes"].items():
            actual = [r for r in declared if r["path"].endswith("/Heart-Native-Runtime/" + path)]
            require(len(actual) == 1 and actual[0]["sha256"] == digest, "Prior compiled native product differs")
        actual_noop = [r for r in declared if r["path"].endswith("/Heart-Native-Runtime/core/block/process/noop.go")]
        require(len(actual_noop) == 1 and actual_noop[0]["sha256"] == NOOP_SHA,
                "Prior compile did not use original no-progress identity")
    return {
        "status": "AUTHENTIC_PRESTART_NATIVE_PASS_REUSED",
        "run_id": 45105771388, "run_attempt": 1, "source": BASE_SOURCE,
        "artifact_id": 14790861121, "archive_sha256": PRIOR_ZIP,
        "case": CASE, "actual_prior_passes": 1, "reexecuted_here": False,
        "prior_overall_result": "FAIL", "receipt_sha256": PRIOR_RECEIPT,
        "actual_prior_native_receipt": receipt,
        "passed_case_and_shared_helpers_sha256": sha(passed_suffix),
        "passed_case_and_shared_helpers_byte_identical": True,
        "changed_product_path": MAPPING_PATH,
        "whole_product_tree_unchanged": False,
        "changed_finish_reachable_in_reused_precanceled_path": False,
        "path_reason": "Actual prior context.Canceled outcome; unchanged beginRun returns before mapping reset, defer registration and mapping finish.",
        "path_reason_kind": "source-path proof tied to authentic prior native case",
        "new_native_selector": manifest["selector"], "ack_authority": False,
        "mapping_body_or_cold_reopen_qualified_by_reuse": False,
    }
