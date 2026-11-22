"""New rejection controls for exact Swift Testing event and source admission."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import run_packages as subject


def event(kind, identity=None, symbol=None, text=""):
    payload = {"kind": kind, "instant": {"absolute": 1, "since1970": 1}, "messages": []}
    if identity is not None:
        payload["testID"] = identity
    if symbol is not None:
        payload["messages"] = [{"symbol": symbol, "text": text}]
    return {"version": 0, "kind": "event", "payload": payload}


def original_stream(methods):
    """Synthetic ABI-v0 controls, never represented as executed Swift tests."""
    records, suites, ids = [], {}, {}
    for index, method in enumerate(methods):
        if method.suite not in suites:
            identity = "opaque-suite-" + str(index)
            suites[method.suite] = identity
            records.append({"version": 0, "kind": "test", "payload": {
                "id": identity, "kind": "suite", "name": method.suite,
                "sourceLocation": {"fileID": method.file_id, "line": 1, "column": 1}}})
        identity = "opaque-function-" + str(index)
        ids[method.key] = identity
        records.append({"version": 0, "kind": "test", "payload": {
            "id": identity, "kind": "function", "name": method.name + "()",
            "sourceLocation": {"fileID": method.file_id, "line": 4, "column": 1},
            "isParameterized": bool(method.arguments)}})
    records.append(event("runStarted", symbol="default", text="Test run started."))
    for suite, suite_id in suites.items():
        records.append(event("testStarted", suite_id))
        for method in (m for m in methods if m.suite == suite):
            identity = ids[method.key]
            records.append(event("testStarted", identity))
            if method.arguments:
                for value in method.argument_cases:
                    label = method.arguments[0][0]
                    text = "Test case passing 1 argument " + label + " → " + value + " (Fixture.Value) to " + method.name
                    records.append(event("testCaseStarted", identity, "default", text + " started."))
                    records.append(event("testCaseEnded", identity, "pass", text + " passed after 0.1 seconds."))
            records.append(event("testEnded", identity, "pass", "Test passed."))
        records.append(event("testEnded", suite_id, "pass", "Suite passed."))
    records.append(event("runEnded", symbol="pass", text="Test run passed."))
    return records


class RelatedReadPackageControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.method = subject.Method("BoundaryTests", "BoundarySuite", "readAuthority", (("reason",("denied","invalidated")),))
        self.methods = [self.method, subject.Method("BoundaryTests", "BoundarySuite", "ordinaryFailure")]

    def qualify(self, records, methods=None):
        path = self.root / "original.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")
        return subject.qualify_stream(path, methods or self.methods)

    def testExactNamedEnumAndBooleanArgumentClosuresAreAccepted(self):
        enum = self.qualify(original_stream(self.methods))
        self.assertEqual(enum[0]["actualArguments"], ["denied","invalidated"])
        method = subject.Method("AnyTests","AnySuite","owner",(("ownerIsActive",("false","true")),))
        result = self.qualify(original_stream([method]),[method])
        self.assertEqual(result[0]["actualArguments"],["false","true"])

    def testSourceProfilesRequireTheirSeparateExactCounts(self):
        app = Path(__file__).resolve().parents[2]
        kit = self.root / "Kit"
        target = kit / "docs/validation/20261121-related-read-authority/test-profile.json"
        target.parent.mkdir(parents=True)
        target.write_bytes((Path(__file__).parent / "Fixtures/kit-test-profile.json").read_bytes())
        for profile, counts in subject.PROFILES.items():
            with self.subTest(profile=profile):
                _, methods = subject.load_profile(app, profile, kit)
                cases = self.qualify(original_stream(methods), methods)
                self.assertEqual((len(cases),sum(c["actualCases"] for c in cases)),counts)

    def testMissingMethodOrMissingNamedCaseIsRejected(self):
        for kind, identity in [("testEnded","opaque-function-1"),("testCaseEnded","opaque-function-0")]:
            records=original_stream(self.methods)
            index=next(i for i,r in enumerate(records) if r["kind"]=="event" and r["payload"]["kind"]==kind and r["payload"].get("testID")==identity)
            del records[index]
            with self.subTest(kind=kind), self.assertRaises(ValueError): self.qualify(records)

    def testDuplicateOrWrongActualArgumentCannotSatisfyCount(self):
        for replacement in ["denied","unknown"]:
            records=original_stream(self.methods)
            for row in records:
                for message in row["payload"].get("messages",[]):
                    message["text"]=message["text"].replace("→ invalidated", "→ "+replacement)
            with self.subTest(replacement=replacement), self.assertRaises(ValueError): self.qualify(records)

    def testFailureKnownIssueSkipAndCancellationRejectWholeRun(self):
        for kind in ["issueRecorded","testSkipped","testCancelled","testCaseCancelled"]:
            records=original_stream(self.methods)
            index=next(i for i,r in enumerate(records) if r["kind"]=="event" and r["payload"]["kind"]=="testCaseEnded")
            issue=event(kind,"opaque-function-0","passWithKnownIssue" if kind=="issueRecorded" else "skip")
            if kind=="issueRecorded": issue["payload"]["issue"]={"isKnown":True,"isFailure":False}
            records.insert(index,issue)
            with self.subTest(kind=kind),self.assertRaises(ValueError): self.qualify(records)

    def testAggregatePassCannotReplaceActualPassingTerminal(self):
        records=original_stream(self.methods)
        row=next(r for r in records if r["kind"]=="event" and r["payload"]["kind"]=="testCaseEnded")
        row["payload"]["messages"]=[{"symbol":"default","text":"finished"}]
        with self.assertRaises(ValueError): self.qualify(records)

    def testUnselectedExecutionOrForeignSourceCannotQualify(self):
        records=original_stream(self.methods+[subject.Method("OtherTests","BoundarySuite","unselected")])
        with self.assertRaises(ValueError): self.qualify(records)
        records=original_stream(self.methods)
        records[1]["payload"]["sourceLocation"]["fileID"]="OtherTests/BoundarySuite.swift"
        with self.assertRaises(ValueError): self.qualify(records)

    def testDuplicateTerminalOrMissingRunEndCannotQualify(self):
        records=original_stream(self.methods)
        terminal=next(r for r in records if r["kind"]=="event" and r["payload"]["kind"]=="testEnded" and r["payload"].get("testID")=="opaque-function-0")
        records.insert(records.index(terminal)+1,deepcopy(terminal))
        with self.assertRaises(ValueError): self.qualify(records)
        with self.assertRaises(ValueError): self.qualify(original_stream(self.methods)[:-1])

    def testAmbiguousJSONOrUnreviewedSchemaIsRejected(self):
        records=original_stream(self.methods)
        records[0]["version"]="6.3"
        with self.assertRaises(ValueError): self.qualify(records)
        path=self.root/'ambiguous.jsonl'
        path.write_text('{"version":0,"version":0,"kind":"test","payload":{}}\n')
        with self.assertRaises(ValueError):subject.qualify_stream(path,self.methods)

    def testActualDeclarationAndArgumentDriftIsRejected(self):
        source=self.root/'Tests/BoundaryTests/BoundarySuite.swift'
        source.parent.mkdir(parents=True)
        template='struct BoundarySuite {\n@Test(arguments: [.denied, .invalidated])\nfunc readAuthority(reason: Reason) {}\n@Test\nfunc ordinaryFailure() {}\n}'
        source.write_text(template)
        self.assertEqual(len(subject.inspect_sources(self.root,self.methods)),1)
        source.write_text(template.replace('.invalidated','.denied'))
        with self.assertRaises(ValueError):subject.inspect_sources(self.root,self.methods)

    def testWrongDestinationOrXcodeDoesNotCountAsAppleProof(self):
        subject.validate_host('Darwin','arm64','Xcode 27.0\nBuild version 27A266a')
        for system,arch,xcode in [('Linux','arm64','Xcode 27.0\nBuild version 27A266a'),
                                  ('Darwin','x86_64','Xcode 27.0\nBuild version 27A266a'),
                                  ('Darwin','arm64','Xcode 26.0\nBuild version 17A1')]:
            with self.subTest(system=system,arch=arch,xcode=xcode),self.assertRaises(ValueError):
                subject.validate_host(system,arch,xcode)


if __name__ == '__main__':
    unittest.main()
