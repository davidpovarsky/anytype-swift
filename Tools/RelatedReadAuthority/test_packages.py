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
    """Synthetic observed ABI-v0 controls, never executed Swift test evidence."""
    targets = list(dict.fromkeys(m.target for m in methods))
    if len(targets) > 1:
        return [r for target in targets for r in original_stream([m for m in methods if m.target == target])]
    records, suites, ids = [], {}, {}
    for index, method in enumerate(methods):
        if not method.top_level and method.suite not in suites:
            identity = "opaque-suite-" + str(index)
            suites[method.suite] = identity
            records.append({"version": 0, "kind": "test", "payload": {
                "id": identity, "kind": "suite", "name": method.suite,
                "sourceLocation": {"fileID": method.file_id, "line": 1, "column": 1}}})
        identity = "opaque-function-" + str(index)
        ids[method.key] = identity
        payload = {
            "id": identity, "kind": "function", "name": method.name + "()",
            "sourceLocation": {"fileID": method.file_id, "line": 4, "column": 1},
            "isParameterized": bool(method.arguments)}
        if method.arguments:
            payload["_parameters"] = [{"name": method.arguments[0][0], "typeName": "Fixture.Value"}]
            payload["_testCases"] = [{"id": identity + ":" + value, "displayName": value}
                                    for value in method.argument_cases]
        records.append({"version": 0, "kind": "test", "payload": payload})
    records.append(event("runStarted", symbol="default", text="Test run started."))
    for suite in list(suites) + ([None] if any(m.top_level for m in methods) else []):
        suite_id = suites.get(suite)
        if suite_id is not None:
            records.append(event("testStarted", suite_id))
        for method in (m for m in methods if (m.top_level and suite is None) or (not m.top_level and m.suite == suite)):
            identity = ids[method.key]
            records.append(event("testStarted", identity))
            if method.arguments:
                for value in method.argument_cases:
                    label = method.arguments[0][0]
                    text = "Test case passing 1 argument " + label + " → " + value + " (Fixture.Value) to " + method.name
                    start = event("testCaseStarted", identity, "default", text + " started.")
                    end = event("testCaseEnded", identity)
                    for row in (start, end):
                        row["payload"]["_testCase"] = {"id": identity + ":" + value, "displayName": value}
                    records.extend([start, end])
            records.append(event("testEnded", identity, "pass", "Test passed."))
        if suite_id is not None:
            records.append(event("testEnded", suite_id, "pass", "Suite passed."))
    records.append(event("runEnded", symbol="pass", text=f"Test run with {len(methods)} tests passed."))
    # Real test IDs are target-qualified; keep simple IDs for single-target
    # rejection fixtures and namespace them when composing target streams.
    for row in records:
        payload = row["payload"]
        for key in ("id", "testID"):
            if key in payload and methods[0].target != "BoundaryTests":
                payload[key] = methods[0].target + ":" + payload[key]
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
        row=next(r for r in records if r["kind"]=="event" and r["payload"]["kind"]=="testEnded"
                 and r["payload"].get("testID")=="opaque-function-0")
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

    def testActualOriginalTenMethodsQualifyWithoutRerunningSwift(self):
        root = Path(__file__).resolve().parents[2]
        kit = self.root / "Kit"
        profile = kit / "docs/validation/20261121-related-read-authority/test-profile.json"
        profile.parent.mkdir(parents=True)
        profile.write_bytes((Path(__file__).parent / "Fixtures/kit-test-profile.json").read_bytes())
        _, all_methods = subject.load_profile(root, "kit-related-current-access", kit)
        methods = [m for m in all_methods if not m.top_level]
        path = root / "docs/validation/20261122-related-read-mac-observed/original/related-read-authority/kit-related-current-access/original-events.jsonl"
        rows = subject.qualify_stream(path, methods, path.with_name("original-test.log"))
        self.assertEqual((len(rows), sum(x["actualCases"] for x in rows)), (10, 12))

    def testEmptyCaseTerminalRequiresItsExactDeclaredAndStartedIdentity(self):
        for mutation in ("missing", "foreign", "changed-display", "duplicated"):
            records = original_stream(self.methods)
            row = next(r for r in records if r["kind"] == "event" and r["payload"]["kind"] == "testCaseEnded")
            if mutation == "missing": del row["payload"]["_testCase"]
            elif mutation == "foreign": row["payload"]["_testCase"]["id"] = "foreign"
            elif mutation == "changed-display": row["payload"]["_testCase"]["displayName"] = "invalidated"
            else: records.insert(records.index(row) + 1, deepcopy(row))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.qualify(records)

    def testSequentialTargetsRequireIndependentCompleteClosure(self):
        second = subject.Method("SecondTests", "SecondSuite", "second")
        methods = self.methods + [second]
        records = original_stream(methods)
        self.assertEqual(len(self.qualify(records, methods)), 3)
        for kind in ("runEnded", "testEnded"):
            damaged = deepcopy(records)
            index = next(i for i, r in enumerate(damaged) if r["kind"] == "event" and r["payload"]["kind"] == kind)
            del damaged[index]
            with self.subTest(kind=kind), self.assertRaises(ValueError): self.qualify(damaged, methods)
        with self.assertRaises(ValueError): self.qualify(records + records, methods)

    def testTopLevelSelectionUsesMethodsAndRequiresNoInventedSuite(self):
        methods = [subject.Method("RefreshTests", "SourceFile", "refreshOne", top_level=True),
                   subject.Method("RefreshTests", "SourceFile", "refreshTwo", top_level=True)]
        import re
        pattern = subject.selection_filter(methods)
        self.assertTrue(re.search(pattern, "RefreshTests.refreshOne()/SourceFile.swift:3:6"))
        self.assertFalse(re.search(pattern, "RefreshTests.SourceFile/unrelated()"))
        self.assertEqual(len(self.qualify(original_stream(methods), methods)), 2)

    def testEmptyTargetRunCannotSubstituteForAnyMethod(self):
        empty = [event("runStarted", symbol="default"), event("runEnded", symbol="pass", text="Test run with 0 tests passed.")]
        self.assertEqual(len(self.qualify(empty + original_stream(self.methods))), 2)
        with self.assertRaises(ValueError): self.qualify(empty)
        empty[1]["payload"]["messages"][0]["text"] = "Test run with 1 test passed."
        with self.assertRaises(ValueError): self.qualify(empty + original_stream(self.methods))

    def testEmptySimpleTerminalRequiresItsExactOriginalNamedLog(self):
        methods = [subject.Method("BoundaryTests", "BoundarySuite", "ordinaryFailure")]
        records = original_stream(methods)
        row = next(r for r in records if r["kind"] == "event" and r["payload"]["kind"] == "testEnded"
                   and r["payload"].get("testID") == "opaque-function-0")
        row["payload"]["messages"] = []
        path = self.root / "original.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        log = self.root / "original-test.log"
        terminal = "✔ Test ordinaryFailure() passed after 0.001 seconds.\n"
        log.write_text(terminal)
        self.assertEqual(len(subject.qualify_stream(path, methods, log)), 1)
        for text in ("", terminal.replace("ordinaryFailure", "other"), terminal + terminal, "Test run passed.\n"):
            log.write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError): subject.qualify_stream(path, methods, log)
        with self.assertRaises(ValueError): subject.qualify_stream(path, methods)


if __name__ == '__main__':
    unittest.main()
