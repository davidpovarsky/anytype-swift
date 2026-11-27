"""Independent comparison of saved originals; does not run product code or tests."""
from pathlib import Path
import ast
import base64
import difflib
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
COMMIT = "0925ff79df8f70be288f96ea117dbd7059e24219"
PARENT = "5235bf902f8820fdc41fe802265ff5444407b363"
GIT = ROOT / "git" / COMMIT
ORIGINALS = ROOT / "originals"
DOC = "docs/validation/20261127-wave1-functional-migration/canonical-definition-supplement"
CONTROLS = "Tools/AnyEngineValidation/native_canonical_definition"
DIRECTORY = "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeImportedDefinitionDirectory.swift"
TEST = "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/NativeCanonicalDefinitionSupplementTests.swift"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def file_row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


def apply_exact_patch(source, patch):
    """Consume a preserved unified diff with exact old-line/context checks."""
    original = source.splitlines(keepends=True)
    lines = patch.splitlines(keepends=True)
    cursor = 0
    output = []
    i = 0
    hunks = 0
    while i < len(lines):
        if not lines[i].startswith("@@ "):
            i += 1
            continue
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
        assert match
        old_start = int(match[1]) - 1
        assert old_start >= cursor
        output.extend(original[cursor:old_start])
        cursor = old_start
        old_count = new_count = 0
        i += 1
        while i < len(lines) and not lines[i].startswith("@@ "):
            line = lines[i]
            assert line[:1] in (" ", "+", "-")
            if line[0] in " -":
                assert original[cursor] == line[1:]
                cursor += 1
                old_count += 1
            if line[0] in " +":
                output.append(line[1:])
                new_count += 1
            i += 1
        assert old_count == int(match[2] or 1)
        assert new_count == int(match[4] or 1)
        hunks += 1
    output.extend(original[cursor:])
    assert hunks
    return "".join(output)


def function_text(source, names):
    parsed = ast.parse(source)
    found = {}
    for node in ast.walk(parsed):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            assert node.name not in found
            found[node.name] = ast.get_source_segment(source, node)
    assert set(found) == set(names)
    return found


qualification = read(GIT / DOC / "qualification.json")
assert sha((GIT / DOC / "qualification.json").read_bytes()) == "85ddbc0f95ddb1e790fb6db4b8b473580538e0811d73c16207f875c0d4df91bb"
published = {r["path"]: r for r in qualification["files"]}
original_observations = []
for bundle in sorted(ROOT.glob("original-read-bundle*.json")):
    content = read(bundle)
    rows = content.get("rows", [content])
    for row in rows:
        if "base64" in row:
            data = base64.b64decode(row["base64"], validate=True)
            assert len(data) == row["bytes"] and sha(data) == row["sha256"]
        if row["path"] in published:
            assert all(row[k] == published[row["path"]][k] for k in ("bytes", "sha256"))
        original_observations.append({k: v for k, v in row.items() if k != "base64"})

closure = read(ROOT / "recorded-source-closure-vs-commit.json")
assert closure["commit"] == COMMIT and closure["tree"] == "79a0ba671dc5b02a6f65b05b2c9add17440f5a47"
assert closure["count"] == len(closure["rows"]) == 308
assert not closure["missingInGit"] and not closure["additionalInGit"] and not closure["mismatches"]
assert all(row["matchesRecordedInput"] for row in closure["rows"])
before = read(ORIGINALS / "native/swift-sources-before.json")
prior = read(ORIGINALS / "failed-attempts/components-attempt1/source-before.json")
assert set(before) == set(prior)
assert [key for key in before if before[key] != prior[key]] == [TEST]
assert {r["path"]: r["sha256"] for r in closure["rows"]} == before

compare = read(ROOT / "commit-compare.json")
assert compare["base"] == PARENT and compare["head"] == COMMIT
assert compare["ahead_by"] == compare["total_commits"] == 1 and compare["behind_by"] == 0
code_changes = [r for r in compare["files"] if r["filename"].startswith("Modules/")]
assert len(code_changes) == 3
production = [r for r in code_changes if "/Sources/" in r["filename"]]
assert len(production) == 1 and production[0]["filename"] == DIRECTORY
assert (production[0]["additions"], production[0]["deletions"]) == (44, 2)
old_directory = (ROOT / "git" / PARENT / DIRECTORY).read_text()
current_directory = (GIT / DIRECTORY).read_text()
assert apply_exact_patch(old_directory, (ROOT / "production.diff").read_text()) == current_directory

old_fixture = (GIT / DOC / "failed-attempts/components-attempt1/NativeCanonicalDefinitionSupplementTests.swift").read_text()
current_fixture = (GIT / TEST).read_text()
assert apply_exact_patch(old_fixture, (ROOT / "positive-expectation.diff").read_text()) == current_fixture
negative_boundary = "    func testSupplementRefusesDuplicateExistingAndCallerChosenAliases() throws {"
assert old_fixture.count(negative_boundary) == current_fixture.count(negative_boundary) == 1
assert old_fixture.split(negative_boundary, 1)[1] == current_fixture.split(negative_boundary, 1)[1]
old_expectation = "            XCTAssertEqual(entry.originalDescriptor, try canonical.expectedNativeDescriptor)"
new_expectation = '''            // The directory keeps the established complete content projection;
            // the native HTTP declaration omits empty optional fields. Compare
            // every field after adding only those documented empty defaults.
            var expected = try XCTUnwrap(canonical.expectedNativeDescriptor.object)
            for (key, value) in ["xKey": AnyJSON.string(""), "meta": .object([:]),
                                 "properties": .array([]), "required": .array([]), "xFormat": .object([:])] {
                if expected[key] == nil { expected[key] = value }
            }
            XCTAssertEqual(entry.originalDescriptor, .object(expected))'''
assert old_fixture.count(old_expectation) == 1
assert old_fixture.replace(old_expectation, new_expectation, 1) == current_fixture

component = read(ORIGINALS / "components/result.json")
component_prior = read(ORIGINALS / "failed-attempts/components-attempt1/result.json")
assert component["status"] == "PASS" and component_prior["status"] == "FAIL"
assert component["exitCode"] == 0 and component_prior["exitCode"] == 1
assert component["compiled"] and component_prior["compiled"]
assert component["sourceUnchanged"] and component_prior["sourceUnchanged"]
assert component["dependencies"] == component_prior["dependencies"]
assert component["sourceDefinitionsBefore"] == component["sourceDefinitionsAfter"] == component_prior["sourceDefinitionsBefore"] == component_prior["sourceDefinitionsAfter"]
positive = "testEightOriginalCanonicalDefinitionsRetainEvidenceAndDistinctValueSemantics"
negative = ["testSupplementRefusesDuplicateExistingAndCallerChosenAliases", "testSupplementRefusesSelfConsistentChangedWireAndForeignSourceSpace"]
old_log = (ORIGINALS / "failed-attempts/components-attempt1/test.log").read_text()
new_log = (ORIGINALS / "components/test.log").read_text()
assert "skipped" not in old_log.lower() and "skipped" not in new_log.lower()
assert sum("XCTAssertEqual failed" in line for line in old_log.splitlines()) == 8
assert len(component_prior["passLines"]) == 2 and len(component_prior["failLines"]) == 1
assert positive in component_prior["failLines"][0]
assert len(component["passLines"]) == len(component["startLines"]) == 1 and not component["failLines"]
assert positive in component["passLines"][0]
for method in negative:
    assert sum(method in line for line in component_prior["passLines"]) == 1
    assert method not in new_log
assert component["qualification"] == {"newlyExecutedMethods": 1, "retainedUnchangedMethods": 2, "totalQualifiedMethods": 3, "qualifiedMethods": [positive] + negative, "priorOverallFailurePreserved": True}

native = read(ORIGINALS / "native-attempt3-result.json")
assert native["status"] == "PASS" and not native["errors"]
assert native["sourceCommit"] == component["sourceCommit"] == PARENT
assert native["swiftBuildReceiptSHA256"] == sha((ORIGINALS / "components/result.json").read_bytes())
assert native["nativeBefore"] == native["nativeAfter"]
assert native["nativeBefore"]["binarySHA256"] == "1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"
assert native["uniqueTestMethods"] == 1 and native["testInvocations"] == 2
assert len(native["processes"]) == len(native["phases"]) == len(native["testLaunches"]) == 2
assert len({row["pid"] for row in native["processes"] + native["testLaunches"]}) == 4
assert native["allOwnedGroupsPositivelyAbsent"]
for process in native["processes"]:
    assert process["exitCode"] == 0 and process["groupPositivelyAbsent"]
    assert process["actualInheritedNoNewPrivileges"] and process["actualInheritedSeccompFilter"]
    assert process["actualExecutableSHA256"] == native["nativeBefore"]["binarySHA256"]
for phase in native["phases"]:
    name = phase["phase"]
    log_path = ORIGINALS / "native" / (name + "-test.log")
    log = log_path.read_text()
    assert phase["logSHA256"] == sha(log_path.read_bytes())
    assert phase["result"] == "PASS" and phase["exitCode"] == 0 and phase["testGroupPositivelyAbsent"]
    assert phase["compiledProducts"] == component["compiledProducts"]
    assert "PINKHA_NATIVE_CANONICAL_DEFINITION_PHASE_PASS " + name in log
    assert "Executed 1 test, with 0 failures" in log and "skipped" not in log.lower()
    assert sum("Test Case " in line and " started" in line for line in log.splitlines()) == 1
    assert sum("Test Case " in line and " passed " in line for line in log.splitlines()) == 1
    receipt = read(ORIGINALS / "native" / (name + "-result.json"))
    assert receipt["foreignSpaceRefused"] and receipt["revokedLeaseRefused"]
    assert receipt["domainWrites"] == receipt["preparedOperations"] == 0
    assert receipt["newCanonicalDefinitions"] == 8 and receipt["allDirectoryEntries"] == 21
    assert receipt["unresolvedSourceDefinitions"] == 129
    assert not any(receipt[key] for key in ["literalNativeIdentityEquivalenceClaim", "originalHistoryValuesRestamped", "sourceAdmissionPromoted", "wholeSpaceMigration"])
assert native["sourceDefinitionsUnchanged"] and native["swiftSourcesUnchanged"]
assert native["originalAccountAndAcceptedReceiptsUnchanged"]
assert native["actualDomainWrites"] == native["actualPreparedOperations"] == 0
assert not any(native[key] for key in ["sourceAdmissionPromoted", "wholeSpaceMigration", "historicalPreservationReexecuted", "appleUIPresentationAccepted", "literalNativeIdentityEquivalenceClaim"])

descriptor_read = read(ROOT / "descriptor-cold-and-dependency-original-read.json")
assert descriptor_read["warmColdBytesIdentical"]
assert len(descriptor_read["descriptorObservations"]) == 2
assert all(r["bytes"] == 4310 and r["sha256"] == native["comparisonSHA256"] for r in descriptor_read["descriptorObservations"])
meanings = {"description": "ordinaryProperty", "id": "translatedIdentity", "spaceId": "translatedIdentity", "type": "translatedIdentity", "author": "destinationDerived", "createdAt": "destinationDerived", "modifiedAt": "destinationDerived", "modifiedBy": "destinationDerived"}
for observation in descriptor_read["descriptorObservations"]:
    assert {r["nativePropertyID"]: r["valueSemantics"] for r in observation["definitions"]} == meanings
    assert all(r["nativeOwnerID"] == "any" for r in observation["definitions"])

dependency_join = read(ROOT / "retained-dependency-custody-join.json")
assert dependency_join["exactSourceFilesAndModesEqual"] and dependency_join["sourceBeforeAfterEqual"]
assert dependency_join["recordedDependencySourceFiles"] == dependency_join["postBuildCustodyDependencyFiles"] == 1265
assert not dependency_join["missingInPostBuildCustody"] and not dependency_join["extraInPostBuildCustody"] and not dependency_join["differentBytesModeHash"]
repair = read(ORIGINALS / "dependency-locator-repair-result.json")
clean_all = [r for r in repair["checks"] if "--untracked-files=all" in r["command"] and r["exitCode"] == 0 and r["stdout"] == r["stderr"] == ""]
assert len(clean_all) == 3
custody = read(ORIGINALS / "native/cache-custody-result.json")
assert custody["qualifiedProducts"] == component["compiledProducts"]
assert custody["dependencyPinsAtStablePath"] == component["dependencies"]

native_current = (GIT / CONTROLS / "run_native_canonical_definition_linux.py").read_text()
native_failed = (ORIGINALS / "failed-attempts/native-attempt2/controller.py").read_text()
assert native_failed.replace("for base, folders, files in os.walk(original_account, followlinks=False):", "for copy_walk_dir, folders, files in os.walk(original_account, followlinks=False):", 1).replace("info = (Path(base) / name).lstat()", "info = (Path(copy_walk_dir) / name).lstat()", 1) == native_current
native_cache_base = (ORIGINALS / "cache-placement/prior-controller.py").read_text()
native_unexecuted = (ORIGINALS / "allocation-measurement/previous-unexecuted-controller.py").read_text()
assert apply_exact_patch(native_unexecuted, (ORIGINALS / "allocation-measurement/controller.diff").read_text()) == native_cache_base
assert apply_exact_patch(native_cache_base, (ORIGINALS / "cache-placement/controller.diff").read_text()) == native_failed
unchanged_functions = ["source_members", "absent", "finish", "stop_native", "request", "offline_controls", "start_native", "run_test"]
assert function_text(native_unexecuted, unchanged_functions) == function_text(native_current, unchanged_functions)
component_current = (GIT / CONTROLS / "run_canonical_definition_components.py").read_text()
component_failed = (ORIGINALS / "failed-attempts/components-attempt2/controller.py").read_text()
assert apply_exact_patch(component_failed, (ROOT / "component-controller.diff").read_text()) == component_current
assert component_failed.replace("canonical-definition-components-attempt2\")", "canonical-definition-components-attempt3\")", 1).replace("controller_sha=sha(Path(__file__))\n", "controller_sha=sha(Path(__file__))\n(OUT/\"controller.py\").write_bytes(Path(__file__).read_bytes())\n(OUT/\"NativeCanonicalDefinitionSupplementTests.swift\").write_bytes((ROOT/FIXTURE).read_bytes())\n", 1) == component_current

failure1 = read(ORIGINALS / "failed-attempts/native-attempt1/result.json")
failure2 = read(ORIGINALS / "failed-attempts/native-attempt2/result.json")
assert failure1["status"] == failure2["status"] == "FAIL"
assert failure1["processes"] == failure1["testLaunches"] == []
assert failure2["testLaunches"] == [] and [p["exitCode"] for p in failure2["processes"]] == [-15]
assert failure1["allOwnedGroupsPositivelyAbsent"] and failure2["allOwnedGroupsPositivelyAbsent"]
interrupted = read(ORIGINALS / "failed-attempts/components-attempt2/result.json")
termination = read(ORIGINALS / "failed-attempts/components-attempt2/dispatch-termination.json")
assert interrupted["status"] == "RUNNING" and termination["status"] == "FAIL_SENTINEL_DISPATCH_TIMEOUT_BEFORE_TEST_METHODS"
assert termination["actualPasses"] == termination["actualTestMethodsStarted"] == 0

review = {
    "protocol": "independent-canonical-definition-supplement-review-v1",
    "status": "READY_FOR_SOURCE_MERGE_WITH_EXACT_RETAINED_LINUX_SCOPE",
    "reviewer": "/root/apple_release",
    "commit": COMMIT, "parent": PARENT, "tree": closure["tree"],
    "asanaStory": "1220944031127606",
    "productTestsExecutedByReviewer": 0, "nativeProcessesStartedByReviewer": 0,
    "macCallsByReviewerForThisReview": 0, "sourceOrAccountOrCacheChangesByReviewer": False,
    "productionChange": {"path": DIRECTORY, "additions": 44, "deletions": 2, "fullByteDeltaVerified": True,
        "otherProductionPathsChanged": [], "oldInitializerCallCompatibilityPreserved": True,
        "supplementCountMaximum": 9, "sourceAndNativeAuthorityUnchanged": True},
    "sourceClosure": {"recordedHEADBeforeChanges": PARENT, "compiledInputCommitByByteEquality": COMMIT,
        "completeSelectedSwiftAndPackageInputs": 308, "missingOrAdditionalOrChanged": 0,
        "originalManifestSHA256": closure["originalRecordedManifestSHA256"]},
    "dependencyEvidence": {"pins": component["dependencies"], "preparationCleanAllUntrackedChecks": 3,
        "retainedSourceFilesJoinedAcrossOriginalPreparationAndPostBuildCustody": 1265,
        "allBytesModesPathsEqual": True,
        "interpretation": "Use the original clean-all preparation and exact retained 1,265-file source join; the component controller's --untracked-files=no predicate alone does not establish this stronger closure."},
    "componentEvidence": {"newlyExecutedMethods": 1, "retainedUnchangedNegativeMethods": 2,
        "retainedOverallFailureStillFAIL": True, "negativeMethodBodiesAndHelpersByteIdentical": True,
        "onlyFixtureCorrection": "Normalize documented empty projection fields in one positive expectation; compare every schema field.",
        "resultSHA256": sha((ORIGINALS / "components/result.json").read_bytes())},
    "nativeEvidence": {"uniqueMethodCount": 1, "invocations": 2, "actualPasses": 2,
        "nativePIDs": [p["pid"] for p in native["processes"]], "testPIDs": [p["pid"] for p in native["testLaunches"]],
        "normalNativeExitCodes": [p["exitCode"] for p in native["processes"]],
        "allFourProcessGroupsPositivelyAbsent": True, "outboundDeniedAndNoPeers": True,
        "seconds": native["seconds"], "nativeIdentity": native["nativeBefore"],
        "compiledProducts": component["compiledProducts"], "descriptors": meanings,
        "warmColdBytes": 4310, "warmColdSHA256": native["comparisonSHA256"],
        "foreignSpaceAndRevokedLeaseReadsRefused": True,
        "resultSHA256": sha((ORIGINALS / "native-attempt3-result.json").read_bytes())},
    "controllerLineage": {"allPreservedUnifiedDeltasReconstructExactSuccessorBytes": True,
        "unchangedSemanticAndLifecycleFunctions": unchanged_functions,
        "failedNativeAttempt2Correction": "Only copy-loop variable and its Path reference renamed, preventing overwrite of HTTP base URL.",
        "failedComponentAttempt2SuccessorChanges": "Fresh evidence directory and two source-retention writes only; original timeout/guards unchanged.",
        "allocationAndCacheChanges": "Measured 128 MiB initialization reserve, original 2 GiB live floor retained, bounded output caps and 512 MiB relocated-cache floor added."},
    "authorityAndScope": {"eightNewDefinitions": 8, "totalDirectoryEntries": 21, "unresolvedDefinitions": 129,
        "preparedOperations": 0, "domainWrites": 0, "wholeSpaceMigration": False,
        "sourceAdmission": False, "sourceHistoricalValuesRestamped": False,
        "literalCrossEngineIdentityEquivalence": False, "currentValueMigrationAccepted": False,
        "old182OperationMigrationRerun": False, "peerSyncAccepted": False,
        "appleOrFrozen8acAcceptance": False,
        "reason": "Ordinary source-bound canonical schema reads and normal offline process reopen only. Destination-derived clocks/signers remain destination facts; historical source values and identity translation remain separately governed."},
    "remainingRequirements": ["129 unresolved source definitions and 17 Type families remain outside this supplement.",
        "Whole-source admission, current-value migration, peer synchronization and Apple UI acceptance require their separately bound original evidence.",
        "No transfer of Linux native 1dc evidence to frozen Mac native 8ac or a later consumer/SDK source."],
    "originalReadObservationCount": len(original_observations),
    "reviewArtifacts": [file_row(ROOT / name) for name in ["recorded-source-closure-vs-commit.json", "retained-dependency-custody-join.json", "descriptor-cold-and-dependency-original-read.json", "production.diff", "positive-expectation.diff", "native-copy-variable.diff", "component-controller.diff"]],
}
target = ROOT / "independent-review.json"
target.write_text(json.dumps(review, sort_keys=True, indent=2) + "\n")
print(json.dumps({"status": review["status"], **file_row(target), "reviewerExecutedProductTests": 0}, sort_keys=True))
