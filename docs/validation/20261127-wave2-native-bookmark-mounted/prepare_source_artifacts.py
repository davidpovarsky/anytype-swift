from pathlib import Path
import difflib
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
BASE = "5a45fe4af2c4601faad181f81d391057c1237654"
REPO = "davidpovarsky/anytype-swift"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def row(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": sha(raw), "gitBlob": blob(raw)}

def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

changes = []
patch = []
for relative, suffix in [
    ("NativeApp/Sources/NativeCustomTypeFixture.swift", "bookmark_fixture_suffix.swift"),
    ("NativeApp/UITests/NativeLaunchTests.swift", "bookmark_ui_suffix.swift"),
]:
    before = ROOT / "originals" / relative
    after = ROOT / "candidate" / relative
    first, second, append = before.read_bytes(), after.read_bytes(), (ROOT / suffix).read_bytes()
    assert second == first + append
    assert second[:-len(append)] == first
    changes.append({"repositoryPath": relative, "original": row(before), "candidate": row(after),
                    "operation": "append-exact-suffix", "suffix": row(ROOT / suffix),
                    "prefixBytesUnchanged": len(first), "fullInverseVerified": True})
    patch.extend(difflib.unified_diff(first.decode().splitlines(True), second.decode().splitlines(True),
                                    fromfile="a/" + relative, tofile="b/" + relative))

relative = "NativeApp/Sources/AnyNativeApp.swift"
before, after = ROOT / "originals" / relative, ROOT / "candidate" / relative
first, second = before.read_text(), after.read_text()
rules = [
    ("    private let customTypeFixture: NativeCustomTypeFixture?\n",
     "    private let customTypeFixture: NativeCustomTypeFixture?\n    private let bookmarkFixture: NativeBookmarkFixture?\n"),
    ("            customTypeFixture = fixture\n",
     "            let bookmark = try NativeBookmarkFixture.configured(arguments: ProcessInfo.processInfo.arguments,\n                dataDirectory: directory, credentialService: service)\n            customTypeFixture = fixture\n            bookmarkFixture = bookmark\n"),
    ("            customTypeFixture = nil\n", "            customTypeFixture = nil\n            bookmarkFixture = nil\n"),
    ("                    .task { await customTypeFixture?.run(application: application) }\n",
     "                    .task { await customTypeFixture?.run(application: application) }\n"
     "                    .overlay(alignment: .bottomTrailing) {\n"
     "                        if let bookmarkFixture {\n"
     "                            VStack(alignment: .trailing, spacing: 4) {\n"
     "                                Text(\"Native Bookmark fixture\").font(.caption2)\n"
     "                                    .accessibilityIdentifier(\"any-native-ui-bookmark-fixture\")\n"
     "                                    .accessibilityValue(bookmarkFixture.accessibilityValue)\n"
     "                                    .allowsHitTesting(false)\n"
     "                                if bookmarkFixture.canReadNext {\n"
     "                                    Button(\"Read Bookmark checkpoint\") {\n"
     "                                        Task { await bookmarkFixture.readNext(application: application) }\n"
     "                                    }\n"
     "                                    .font(.caption2)\n"
     "                                    .accessibilityIdentifier(\"any-native-ui-bookmark-read-checkpoint\")\n"
     "                                }\n"
     "                            }.padding(8)\n"
     "                        }\n"
     "                    }\n"
     "                    .task { await bookmarkFixture?.run(application: application) }\n"),
]
actual = first
for old, new in rules:
    assert actual.count(old) == 1
    actual = actual.replace(old, new, 1)
assert actual == second
restored = second
for old, new in reversed(rules):
    assert restored.count(new) == 1
    restored = restored.replace(new, old, 1)
assert restored == first
changes.append({"repositoryPath": relative, "original": row(before), "candidate": row(after),
                "operation": "four-additive-hook-replacements", "rules": [{"old": a, "new": b, "count": 1} for a, b in rules],
                "fullInverseVerified": True})
patch.extend(difflib.unified_diff(first.splitlines(True), second.splitlines(True), fromfile="a/" + relative, tofile="b/" + relative))
(ROOT / "source.patch").write_text("".join(patch))
save("source-inverse.json", {"schema": "native-bookmark-three-file-full-inverse-v1", "baseCommit": BASE,
    "sourceOnly": True, "changes": changes, "allOriginalBytesRestored": True})

intake = ROOT.parent / "torah-acceptance-prep/bookmark-c13-fixture-intake"
original_bindings = json.loads((intake / "source-bindings.json").read_text())
originals = {}
for relative in ["NativeApp/Sources/NativeCustomTypeFixture.swift", "NativeApp/Sources/AnyNativeApp.swift"]:
    matching = next(x for x in original_bindings["files"] if x["path"] == relative and x["commit"] == BASE)
    observed = row(ROOT / "originals" / relative)
    for key in ["bytes", "sha256", "gitBlob"]:
        assert matching[key] == observed[key]
    originals[relative] = {"primary": matching, "observed": observed}
ui_meta = json.loads((ROOT / "primary/NativeLaunchTests.swift.json").read_text())
ui_row = row(ROOT / "originals/NativeApp/UITests/NativeLaunchTests.swift")
assert ui_row["sha256"] == "e2979e777dd61f7eb8be06bd38028b15cc6f7e2d944fe6adce9603a3f7817358"
assert ui_row["gitBlob"] == "83fd25121f27f789dcce4cde088dd29e3df738a2"
originals["NativeApp/UITests/NativeLaunchTests.swift"] = {"primary": ui_meta, "observed": ui_row}
dependencies = []
for path in sorted((ROOT / "source").rglob("*")):
    if not path.is_file():
        continue
    meta_path = ROOT / "primary" / (path.name + ".json")
    meta = json.loads(meta_path.read_text())
    observed = row(path)
    assert observed["gitBlob"] == meta["gitBlob"]
    dependencies.append({"primary": meta, "primaryMetadata": row(meta_path), "observed": observed})
save("source-bindings.json", {"schema": "native-bookmark-mounted-source-bindings-v1", "repository": REPO,
    "baseCommit": BASE, "originals": originals, "freshCurrentDependencies": dependencies,
    "retainedIntakeBindings": {"path": str(intake / "source-bindings.json"), "sha256": sha((intake / "source-bindings.json").read_bytes()),
                              "files": original_bindings["files"]},
    "sourceReadOnly": True, "nativeHTTPRequests": 0, "swiftInvocations": 0})

old_ui = (ROOT / "originals/NativeApp/UITests/NativeLaunchTests.swift").read_text()
new_ui = (ROOT / "candidate/NativeApp/UITests/NativeLaunchTests.swift").read_text()
names = lambda text: re.findall(r"\bfunc\s+(test[A-Za-z0-9_]+)\s*\(", text)
old_names, new_names = names(old_ui), names(new_ui)
new_method = "testNativeBookmarkCancelCreateEditOpenAndColdReopen"
assert len(old_names) == 26 and new_names == old_names + [new_method]
fixture = (ROOT / "bookmark_fixture_suffix.swift").read_text()
assert fixture.count('requestJSONResponse(method: "POST"') == 4
assert fixture.count('requestJSONResponse(method: "PATCH"') == 1
assert '"bookmark-create-frame"' not in fixture and '"pinkha", "objects"' not in fixture
assert 'executionTimeAllowance' not in (ROOT / "bookmark_ui_suffix.swift").read_text()
project = (ROOT / "source/NativeApp/AnyNative.xcodeproj/project.pbxproj").read_text()
for token in ["Sources/AnyNativeApp.swift", "Sources/NativeCustomTypeFixture.swift", "UITests/NativeLaunchTests.swift"]:
    assert token in project
save("candidate-manifest.json", {"schema": "native-bookmark-mounted-source-candidate-v1", "status": "SOURCE_ONLY_NOT_RUN",
    "repository": REPO, "baseCommit": BASE, "changedExistingFiles": [x["candidate"] for x in changes],
    "sourceInverse": row(ROOT / "source-inverse.json"), "sourceBindings": row(ROOT / "source-bindings.json"),
    "declarations": {"originalMethods": old_names, "originalMethodCount": 26, "candidateMethodCount": 27,
        "newSelector": "NativeLaunchTests/" + new_method, "newXCTestMethods": 1, "newUnparameterizedCases": 1,
        "original26SelectionUnchanged": True, "compiledEnumeration": None, "newExecutionTimeAllowanceOverride": None},
    "fixture": {"definitions": "SYNTHETIC_INSTALLED", "publicDefinitionWritesOnSuccessfulPrepare": 5,
        "acknowledgedHTTPStatuses": [201, 201, 201, 201, 204], "fixtureObjectWrites": 0, "fixtureBodyWrites": 0,
        "fixtureMembershipWrites": 0, "fixtureFrameRequests": 0, "warmReadCheckpoints": ["baseline", "cancelled", "created", "edited", "returned"],
        "coldReadOnly": True, "coldRequiresSameActualSeedAccountSpaceObject": True, "coldRequiresDistinctPIDAndOwnerGeneration": True,
        "census": {"maximumRecords": 128, "queryLimit": 129, "requiresTotalEqualsUniqueCount": True, "requiresHasNextFalse": True,
            "acceptsPartialPage": False, "paginationClaim": False, "cancellationClaim": "No additional or changed native census records; no HTTP-count claim"},
        "observationMaximumBytes": 32768, "nativeQueryMaximumResponseBytes": 1048576},
    "predecessors": [row(ROOT / "review-v1-app-init/AnyNativeApp.swift"), row(ROOT / "review-v1-ui-evidence/NativeLaunchTests.swift")],
    "corrections": [row(ROOT / "app-initialization-correction.json"), row(ROOT / "external-evidence-order-correction.json")],
    "compilation": {"existingNativeAppProject": row(ROOT / "source/NativeApp/AnyNative.xcodeproj/project.pbxproj"),
        "newInputPaths": [], "PBXChanges": 0, "PackageChanges": 0, "compilerFileListProof": None,
        "standaloneHookSourceOnly": True, "combinedHookQualified": False},
    "runtimeReady": False, "matchingProducerAdmission": None, "swiftOrAppleCompilation": "NOT_RUN", "uiExecution": "NOT_RUN",
    "externalBrowserExactAddress": "NOT_RUN", "coldNativeReadback": "NOT_RUN", "visualOrPhysicalAcceptance": "NOT_RUN",
    "originalNineteenTypeMigration": "NOT_QUALIFIED_BY_SYNTHETIC_FIXTURE", "controllersChanged": 0,
    "firstAppleOrderUnchanged": ["original22methods34cases", "originalRealApplicationPreparation", "original4UIselectors"]})
print(json.dumps({"candidateManifest": row(ROOT / "candidate-manifest.json"), "sourceInverse": row(ROOT / "source-inverse.json"),
                  "sourceBindings": row(ROOT / "source-bindings.json"), "sourcePatch": row(ROOT / "source.patch")}, indent=2))
