#!/usr/bin/env python3
"""Qualify the original Swift Testing report; never launch or repeat a test."""
import hashlib,json,pathlib,sys,xml.etree.ElementTree as ET
def sha(b): return hashlib.sha256(b).hexdigest()
root=pathlib.Path(sys.argv[1])
producer=root/"original-controller.py"
assert sha(producer.read_bytes())=="6c9dde2574bcd61a8ddfbca2e3671012d5c323a14e79c4f8e0979a7697543387"
original_bytes=(root/"result.json").read_bytes(); original=json.loads(original_bytes)
assert original["status"]=="FAIL" and original["exitCode"]==0 and original["ownedGroupAbsent"] is True
assert original["cleanup"]==[] and original["error"]=="FileNotFoundError(2, 'No such file or directory')"
assert "tree=ET.parse" in original["traceback"] and str(root/"original.xml") in original["traceback"]
assert not (root/"original.xml").exists()
before=json.loads((root/"source-before.json").read_bytes())
assert before==json.loads((root/"source-after.json").read_bytes())
actual=[]
for p in sorted((root/"package").rglob("*")):
    assert not p.is_symlink()
    if p.is_file():
        b=p.read_bytes(); actual.append({"path":p.relative_to(root/"package").as_posix(),"bytes":len(b),"sha256":sha(b)})
assert actual==before
expected={
"equivalentDecimalSpellingsPreserveExactValues","changedPrecisionKeepsExactJSONPointer",
"escapedDuplicateKeysRefuseEitherInput","canonicalUnknownNumbersCannotLosePrecision",
"canonicalNumbersRemainSafeAcrossCodecAndGuard","malformedJSONNeverBecomesAValidEmptyComparison",
"exactDecimalGuardAcceptsEquivalentNotationAndIgnoresNumericStrings","ambiguousDuplicateJSONKeysCannotBeImported"}
xml=(root/"original-swift-testing.xml").read_bytes()
assert sha(xml)=="bce90fda2594f07bced94ace3f3bcc3cd2e52adeaee2ad318c931aa240b89425"
tree=ET.fromstring(xml); suites=tree.findall("./testsuite")
assert len(suites)==1
assert {k:suites[0].attrib[k] for k in ("tests","errors","failures","skipped")}=={"tests":"8","errors":"0","failures":"0","skipped":"0"}
cases=tree.findall(".//testcase")
assert len(cases)==8 and {x.attrib["name"].removesuffix("()") for x in cases}==expected
assert all(not list(x) for x in cases)
log=(root/"original.log").read_text()
assert "Test run with 8 tests in 2 suites passed" in log
assert all("Test "+name+"() passed" in log for name in expected)
out={"protocol":"pinkha-shared-json-guard-original-report-qualification-v1",
"status":"PASS_8_ORIGINAL_COMPONENT_METHODS_COLLECTOR_FILENAME_CORRECTED",
"producerResultSHA256":sha(original_bytes),"producerOriginalFailurePreserved":True,
"collectorOnlyFailure":"Swift Testing wrote original-swift-testing.xml for --xunit-output original.xml",
"sourceManifestSHA256":sha((root/"source-before.json").read_bytes()),
"originalXMLSHA256":sha(xml),"originalLogSHA256":sha((root/"original.log").read_bytes()),
"originalControllerSHA256":sha(producer.read_bytes()),"qualifierSHA256":sha(pathlib.Path(__file__).read_bytes()),
"actualMethods":sorted(expected),"tests":8,"failures":0,"skips":0,
"newTestInvocations":0,"newBuilds":0,"nativeCalls":0,"appAcceptance":False}
dst=root/"collector-correction.json"
assert not dst.exists()
dst.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":out["status"],"receiptSHA256":sha(dst.read_bytes()),"tests":8,"newTestInvocations":0}))
