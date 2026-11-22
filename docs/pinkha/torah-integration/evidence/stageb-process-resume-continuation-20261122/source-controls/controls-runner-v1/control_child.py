#!/usr/bin/env python3
"""Execute only the explicitly frozen new/affected portable controls."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback
import unittest
import xml.etree.ElementTree as ET

PUBLIC = [
    "HostFrameworkContractControls.test_all_reviewed_public_and_spi_paths_are_required_without_ui_credit",
    "HostFrameworkContractControls.test_qualification_declarations_require_actual_spi_scope",
    "HostFrameworkContractControls.test_new_resume_context_fields_and_operations_cannot_be_missing",
    "HostFrameworkContractControls.test_returned_process_receipt_cannot_be_publicly_constructed",
]
COLLECTOR = [
    "ProcessReceiptControls.test_valid_distinct_processes_remain_observation_without_body_ack",
    "ProcessReceiptControls.test_same_pid_cannot_claim_process_restart",
    "ProcessReceiptControls.test_boolean_pid_is_not_an_integer_process",
    "ProcessReceiptControls.test_wrong_workspace_request_is_refused",
    "ProcessReceiptControls.test_changed_saved_body_cannot_reuse_checkpoint",
    "ProcessReceiptControls.test_foreign_annotation_cannot_reuse_native_object",
    "ProcessReceiptControls.test_unconsumed_credential_is_not_success",
    "ProcessReceiptControls.test_never_owned_query_is_not_an_absence_receipt",
    "ProcessReceiptControls.test_checkpoint_unknown_fields_are_refused",
    "ProcessReceiptControls.test_duplicate_json_key_is_refused",
    "ProcessReceiptControls.test_missing_original_show_cannot_claim_native_resume",
    "ProcessReceiptControls.test_extra_presentation_is_refused",
    "ProcessReceiptControls.test_real_symlink_report_is_refused",
    "ProcessReceiptControls.test_changed_export_bytes_cannot_reuse_archive_digest",
    "ProcessReceiptControls.test_cleanup_for_another_process_is_refused",
    "ProcessReceiptControls.test_wrong_one_shot_attempt_nonce_is_refused",
    "ProcessReceiptControls.test_duplicate_native_response_is_refused",
    "ProcessReceiptControls.test_callback_retains_primary_failure_before_witness_rejection",
    "ProcessReceiptControls.test_callback_excludes_private_native_repository",
    "ProcessReceiptControls.test_unknown_capture_file_is_refused_before_account_copy"
]

def utc():
    return datetime.now(timezone.utc).isoformat()

def atomic(path, value):
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

parser = argparse.ArgumentParser()
parser.add_argument("--packet", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--group", choices=("public", "collector"), required=True)
args = parser.parse_args()
packet, out = Path(args.packet).resolve(strict=True), Path(args.out).resolve(strict=True)
sys.dont_write_bytecode = True
sys.path.insert(0, str(packet / "python-closure/Tools/OriginalEditor"))
os.environ["STAGEB_COLLECTOR_SOURCE"] = str(packet / "python-closure/Scripts/CI/runtime27-original-editor-native.py")
source = (packet / "python-closure/Tools/OriginalEditor/test_host_framework_contract.py"
          if args.group == "public" else packet / "test_process_receipts.py")
names = PUBLIC if args.group == "public" else COLLECTOR
module_name = "stageb_frozen_" + args.group
spec = importlib.util.spec_from_file_location(module_name, source)
module = importlib.util.module_from_spec(spec)
sys.modules[module_name] = module
spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromNames(names, module)
selected = [test.id() for test in flatten(suite)]
expected = [module_name + "." + name for name in names]
if selected != expected or len(selected) != len(set(selected)):
    raise RuntimeError("Actual selected test IDs differ from the frozen list")
rows = []
began = {}
class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        began[test.id()] = time.monotonic()
        rows.append({"id": test.id(), "status": "RUNNING", "started": utc()})
        atomic(out / "CASES.json", rows)
    def record(self, test, status, detail=None):
        row = next(row for row in rows if row["id"] == test.id())
        row.update(status=status, finished=utc(), seconds=time.monotonic()-began[test.id()])
        if detail is not None:
            row["detail"] = detail
        atomic(out / "CASES.json", rows)
    def addSuccess(self, test):
        super().addSuccess(test); self.record(test, "PASS")
    def addFailure(self, test, err):
        super().addFailure(test, err); self.record(test, "FAIL", self._exc_info_to_string(err, test))
    def addError(self, test, err):
        super().addError(test, err); self.record(test, "ERROR", self._exc_info_to_string(err, test))
    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.record(test, "SKIP", reason)
    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err); self.record(test, "EXPECTED_FAILURE", self._exc_info_to_string(err, test))
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.record(test, "UNEXPECTED_SUCCESS")
atomic(out / "SELECTED.json", {"group": args.group, "expected": expected, "actual": selected,
                             "pid": os.getpid(), "started": utc()})
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=RecordedResult).run(suite)
loaded = {}
for value in tuple(sys.modules.values()):
    path = getattr(value, "__file__", None)
    if not path:
        continue
    path = Path(path).resolve()
    if path.is_file() and (path.is_relative_to(packet / "python-closure") or path == packet / "test_process_receipts.py"):
        raw = path.read_bytes()
        loaded[path.relative_to(packet).as_posix()] = {"bytes":len(raw), "sha256":hashlib.sha256(raw).hexdigest()}
required_loaded = ({"python-closure/Tools/OriginalEditor/" + name for name in
                    ("test_host_framework_contract.py", "framework_products.py", "framework_profile.py", "pbx_source.py")}
                   if args.group == "public" else
                   {"test_process_receipts.py", "python-closure/Scripts/CI/runtime27-original-editor-native.py"})
if set(loaded) != required_loaded:
    raise RuntimeError("Observed imported source closure differs from this group's declaration")
passed = (result.wasSuccessful() and result.testsRun == len(expected) and len(rows) == len(expected)
          and [row["id"] for row in rows] == expected and all(row["status"] == "PASS" for row in rows))
xml = ET.Element("testsuite", name=args.group, tests=str(len(rows)),
                 failures=str(len(result.failures)), errors=str(len(result.errors)), skipped=str(len(result.skipped)))
for row in rows:
    case = ET.SubElement(xml, "testcase", name=row["id"], time=str(row["seconds"]))
    if row["status"] != "PASS":
        ET.SubElement(case, "failure", type=row["status"]).text = row.get("detail", row["status"])
ET.ElementTree(xml).write(out / "xunit.xml", encoding="utf-8", xml_declaration=True)
atomic(out / "RESULT.json", {"status":"PASS" if passed else "FAIL", "group":args.group,
    "pid":os.getpid(), "caseCount":result.testsRun, "expectedCaseCount":len(expected),
    "caseIDs":expected, "loadedSources":loaded, "finished":utc(),
    "nativeExecution":False, "scope":"real Python assertions; synthetic public graph/native reports and explicit native-container probe"})
sys.exit(0 if passed else 1)
