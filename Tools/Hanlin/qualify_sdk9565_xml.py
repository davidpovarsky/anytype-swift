#!/usr/bin/env python3
"""Supplement the original SDK9565 receipt with Swift Testing's actual xUnit output."""
import hashlib, importlib.util, json, pathlib, re, sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True
ROOT = pathlib.Path("/Users/m1/development/anytype-d-active-20261125/sdk9565-notification")
OUT = ROOT / "original-suite-attempt1"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(v, why):
    if not v: raise RuntimeError(why)
prior = OUT / "qualified-original-result.json"
require(sha(prior) == "93f9dc565b5ee19378efce7525c5ead039a35ed23ba25de08729cafb7da4d97f", "original_qualification")
qualified = json.loads(prior.read_bytes())
require(qualified["actualMethodsPassed"] == 11 and qualified["actualCaseInvocationsPassed"] == 12
        and qualified["failed"] == qualified["skipped"] == 0, "original_counts")
receipt = OUT / "result.json"
require(sha(receipt) == qualified["originalCollectorReceiptSHA256"], "failed_collector_unchanged")
require(sha(OUT / "original-test.log") == qualified["originalLogSHA256"], "original_log_unchanged")
controller = ROOT / "run_composed_notification_tests.py"
require(sha(controller) == qualified["originalControllerSHA256"], "original_controller")
spec = importlib.util.spec_from_file_location("sdk9565_original", controller)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
expected = module.verify(ROOT / "source")
xml = OUT / "original-tests-swift-testing.xml"
tree = ET.fromstring(xml.read_bytes())
require(tree.tag == "testsuites", "actual_xml_root")
suites = list(tree)
require(all(s.tag == "testsuite" and int(s.get("errors", "-1")) == 0
            and int(s.get("failures", "-1")) == 0 and int(s.get("skipped", "-1")) == 0
            for s in suites), "all_actual_suites_without_failures_or_skips")
cases = tree.findall("./testsuite/testcase")
require(len(cases) == 11 and sum(int(s.get("tests", "-1")) for s in suites) == 11, "actual_xml_method_count")
require(all(c.get("classname") == "HanlinScriptExtensionsTests.HanlinNotificationInvocationTests"
            and len(c) == 0 and float(c.get("time", "-1")) >= 0 for c in cases), "original_class_and_outcomes")
names = [c.get("name", "").split("(")[0] for c in cases]
require(len(set(names)) == 11 and set(names) == set(expected), "exact_original_xml_methods")
out = OUT / "qualified-original-with-xml.json"
require(not out.exists(), "independent_supplement_not_overwrite")
result = dict(qualified)
result.update({
    "priorQualificationSHA256": sha(prior),
    "priorQualificationRetained": True,
    "xUnitWasEmitted": True,
    "xUnitFile": xml.name,
    "xUnitSHA256": sha(xml),
    "requestedXUnitFilenameExists": (OUT / "original-tests.xml").exists(),
    "xUnitMethodsPassed": 11,
    "xUnitCountsMethodsNotParameterInstances": True,
    "qualificationNote": "The original log qualification remains valid. Its xUnitWasEmitted=false described only the requested filename too broadly. Swift Testing emitted original-tests-swift-testing.xml, independently qualified here; neither original receipt was rewritten.",
    "supplementSHA256": sha(pathlib.Path(__file__)),
    "sourceUnchanged": module.verify(ROOT / "source") == expected,
})
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({"path": str(out), "sha256": sha(out), "xmlSHA256": sha(xml),
                  "methods": 11, "caseInvocations": 12, "testsRerun": 0}))
