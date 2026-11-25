#!/usr/bin/env python3
"""Qualify the retained SDK9565 run without another compiler or test invocation."""
import hashlib, importlib.util, json, pathlib, re, sys
sys.dont_write_bytecode = True
ROOT = pathlib.Path("/Users/m1/development/anytype-d-active-20261125/sdk9565-notification")
OUT = ROOT / "original-suite-attempt1"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(v, r):
    if not v: raise RuntimeError(r)
receipt = OUT / "result.json"
require(sha(receipt) == "ca5d2276967975854794279844efd3604da622613358e0da89bdac0ac002079f", "exact_failed_collector_receipt")
original = json.loads(receipt.read_bytes())
require(original["status"] == "FAIL" and original["errors"] == [
    {"message": "exact_original_twelve_case_instances", "type": "RuntimeError"}],
    "only_observed_summary_count_mismatch")
require(original["exitCode"] == 0 and original["sourceBeforeVerified"] is True
        and original["sourceAfterVerified"] is True and original["ownedGroupRemaining"] is False
        and original["groupCensusExit"] == 0 and not original.get("stopReason"), "actual_successful_execution_and_cleanup")
controller = ROOT / "run_composed_notification_tests.py"
require(sha(controller) == "a7dd95a6c10d494af0c70a6db791fc579bd4347f871060a4c07a7437ecadd776", "original_controller")
spec = importlib.util.spec_from_file_location("original_notification_controller", controller)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
expected = module.verify(ROOT / "source")
log = OUT / "original-test.log"
require(sha(log) == original["logSHA256"] == "bc782f3205ab74c7126bee07afd5abda5f0ab6c8d47ab54c782546918b8b8840", "original_log")
text = log.read_text(errors="strict")
matches = re.findall(r"^✔ Test (\w+)\([^\n]*?\)(?: with (\d+) test cases)? passed after [0-9.]+ seconds\.$", text, re.M)
require(len(matches) == 11 and {name for name, _ in matches} == set(expected),
        "each_original_method_exactly_once")
parameterized = "typedEventExecutesOnceAndKeepsItsActualResultAfterReopen"
require([(name, int(count)) for name, count in matches if count] == [(parameterized, 2)],
        "exact_original_parameterized_method")
for runtime in ["hanlinExpo", "hanlinNativeScript"]:
    line = "◇ Test case passing 1 argument runtime → ." + runtime + " to " + parameterized + "(_:) started."
    require(text.count(line) == 1, "both_original_runtime_cases:" + runtime)
require(re.findall(r"^✔ Test run with (\d+) tests in (\d+) suite passed after [0-9.]+ seconds\.$", text, re.M) == [("11", "1")],
        "original_method_summary")
require(not re.search(r"^✘|^↷.*(?:Test|test)", text, re.M), "no_failed_or_skipped_original_case")
cases = sum(int(count) if count else 1 for _, count in matches)
require(cases == 12, "eleven_methods_twelve_actual_case_invocations")
require(not (OUT / "qualified-original-result.json").exists(), "new_independent_qualification_only")
result = {
    "status": "PASS_QUALIFIED_ORIGINAL_NOTIFICATION_SUITE_NOT_APP_ACCEPTANCE",
    "sourceCommit": module.SOURCE, "sourceFilesVerified": 959,
    "originalCollectorStatus": original["status"], "originalCollectorReceiptSHA256": sha(receipt),
    "originalLogSHA256": sha(log), "originalControllerSHA256": sha(controller),
    "qualifierSHA256": sha(pathlib.Path(__file__)),
    "actualMethodsPassed": 11, "actualCaseInvocationsPassed": 12, "failed": 0, "skipped": 0,
    "originalMethodResults": [{"method": name, "caseInvocations": int(count) if count else 1} for name, count in matches],
    "originalParameterCases": ["hanlinExpo", "hanlinNativeScript"],
    "originalSwiftTestingSummaryCountsMethods": True, "xUnitWasEmitted": False,
    "sourceUnchanged": module.verify(ROOT / "source") == expected,
    "newTestInvocations": 0, "newCompilerInvocations": 0,
    "originalElapsedSeconds": original["elapsedSeconds"],
    "fullAppAcceptance": False, "osNotificationDeliveryAccepted": False,
    "warnings": "Original full package compiler warnings retained; no zero-warning claim."
}
require(sha(receipt) == result["originalCollectorReceiptSHA256"] and sha(log) == result["originalLogSHA256"], "originals_unchanged")
p = OUT / "qualified-original-result.json";p.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({"path": str(p), "sha256": sha(p), **result}, ensure_ascii=False))
