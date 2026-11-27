#!/usr/bin/env python3
"""Read-only byte/inverse review of the published typography source tranche.

This is a source audit, not Swift compilation, UIKit execution or app acceptance.
"""
import base64
import datetime
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHA = "33e31c64ca9e35e258a4d64cfe8690b08a6cbc39"
BASE = "dc582ba3239d6dcb66dbe1f7098b95349e4289f9"
ORIGINAL = "8f2c11713fb8a40ae13444104723666ffef68afe"
DOC = "docs/validation/20261127-wave2-native-typography"
EDITOR = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift"
PACKAGE = "Modules/PinkhaAnyUI/Package.swift"
TEST = "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextTypographyTests.swift"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def entry(data, **metadata):
    return dict(metadata, bytes=len(data), sha256=digest(data), gitBlob=blob(data))


def read_json(path):
    return json.loads(path.read_bytes())


commit = read_json(ROOT / "commit.json")
assert commit["sha"] == SHA
assert [p["sha"] for p in commit["parents"]] == [BASE]
assert len(commit["files"]) == 14
assert len([f for f in commit["files"] if f["filename"].endswith(".swift")]) == 4
files = {f["filename"]: f for f in commit["files"]}
source_rows = read_json(ROOT / "sources.json")
reference_rows = read_json(ROOT / "original-references.json")
binary_rows = read_json(ROOT / "binary-evidence.json")
verified = []
for row in source_rows + reference_rows:
    data = row["content"].encode("utf-8")
    assert blob(data) == row["blob"]
    if "expectedBlob" in row:
        assert blob(data) == row["expectedBlob"]
        assert digest(data) == row["expectedSHA256"]
    assert (ROOT / row["ref"] / row["path"]).read_bytes() == data
    if row["ref"] == SHA:
        assert files[row["path"]]["sha"] == blob(data)
    verified.append(entry(data, ref=row["ref"], path=row["path"]))

proof = read_json(ROOT / SHA / DOC / "source-proof.json")
for row in proof["files"]:
    data = (ROOT / SHA / row["path"]).read_bytes()
    assert entry(data, path=row["path"]) == row
for field, name in (
    ("editorInverseSHA256", "editor-source-inverse.json"),
    ("sourceRefactorEntriesSHA256", "source-refactor-entries.json"),
    ("sourceReferencesSHA256", "source-references.json"),
    ("sourceReviewSHA256", "root-source-review.json"),
):
    assert digest((ROOT / SHA / DOC / name).read_bytes()) == proof[field]

binary_index = read_json(ROOT / SHA / DOC / "binary-evidence-index.json")
binary_verified = []
for row in binary_rows:
    data = base64.b64decode("".join(row["content"].split()), validate=True)
    assert blob(data) == row["blob"]
    assert files[f"{DOC}/{row['path']}"]["sha"] == blob(data)
    assert (ROOT / "binary" / row["path"]).read_bytes() == data
    decoded = gzip.decompress(data)
    index = next(r for r in binary_index["files"] if r["encodedName"] == row["path"])
    assert len(data) == index["encodedBytes"] and digest(data) == index["encodedSHA256"]
    assert len(decoded) == index["originalBytes"] and digest(decoded) == index["originalSHA256"]
    assert (ROOT / "binary" / index["originalName"]).read_bytes() == decoded
    binary_verified.append(dict(encoded=entry(data, path=f"{DOC}/{row['path']}"),
                                decoded=entry(decoded, path=index["originalName"])))

before = (ROOT.parent / "miniapps-independent-w2-dc582-review" / "after" / EDITOR).read_bytes()
after = (ROOT / SHA / EDITOR).read_bytes()
assert blob(before) == proof["editorDonor"]["gitBlob"]
assert digest(before) == proof["editorDonor"]["sha256"]
inverse = read_json(ROOT / SHA / DOC / "editor-source-inverse.json")
operations = sum((inverse[group] for group in
                 ("exactChanges", "reviewCorrectionChanges", "bodyWeightCorrectionChanges")), [])
assert len(operations) == 15
forward = before
for operation in operations:
    old, new = operation["old"].encode(), operation["new"].encode()
    assert forward.count(old) == 1
    forward = forward.replace(old, new, 1)
assert forward == after
reverse = after
for operation in reversed(operations):
    old, new = operation["old"].encode(), operation["new"].encode()
    assert reverse.count(new) == 1
    reverse = reverse.replace(new, old, 1)
assert reverse == before

before_package = (ROOT / BASE / PACKAGE).read_bytes()
after_package = (ROOT / SHA / PACKAGE).read_bytes()
assert digest(before_package) == proof["originalPackageSHA256"]
assert blob(before_package) == proof["originalPackageBlob"]
package_ops = [
    (b'        .package(path: "../Loc"),\n',
     b'        .package(path: "../Loc"),\n        .package(path: "../DesignKit"),\n'),
    (b'            .product(name: "Loc", package: "Loc", condition: .when(platforms: [.iOS, .macOS])),\n',
     b'            .product(name: "Loc", package: "Loc", condition: .when(platforms: [.iOS, .macOS])),\n'
     b'            .product(name: "DesignKit", package: "DesignKit", condition: .when(platforms: [.iOS])),\n'),
    (b'            "PinkhaAnyUI", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration"\n',
     b'            "PinkhaAnyUI", "PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration",\n'
     b'            .product(name: "DesignKit", package: "DesignKit", condition: .when(platforms: [.iOS]))\n'),
]
forward = before_package
for old, new in package_ops:
    assert forward.count(old) == 1
    forward = forward.replace(old, new, 1)
assert forward == after_package
reverse = after_package
for old, new in reversed(package_ops):
    assert reverse.count(new) == 1
    reverse = reverse.replace(new, old, 1)
assert reverse == before_package

hanlin = read_json(ROOT / SHA / DOC / "hanlin-present-preimage.json")
function = hanlin["function"].encode("utf-8")
assert len(function) == hanlin["functionBytes"] == 1262
assert digest(function) == hanlin["functionSHA256"]
assert before.count(function) == after.count(function) == 1
methods = re.findall(r"^    func (test\w+)\(", (ROOT / SHA / TEST).read_text(), re.MULTILINE)
assert [f"AnyNativeTextTypographyTests/{method}" for method in methods] == proof["preparedUIKitMethods"]
assert len(methods) == 2

report = {
    "schema": "pinkha-wave3-independent-typography-source-review-v1",
    "reviewer": "/root/miniapps_otzaria",
    "reviewedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "NO_CONCRETE_SOURCE_BLOCKER_APPLE_AND_VISUAL_ACCEPTANCE_NOT_RUN",
    "sourceCommit": SHA,
    "sourceTree": commit["commit"]["tree"]["sha"],
    "parentCommit": BASE,
    "sourceProofSHA256": digest((ROOT / SHA / DOC / "source-proof.json").read_bytes()),
    "reusedWave2IndependentReviewSHA256": digest((ROOT / SHA / DOC / "root-source-review.json").read_bytes()),
    "changedFiles": [{"path": f["filename"], "status": f["status"], "gitBlob": f["sha"]}
                     for f in commit["files"]],
    "sourceAndOriginalReferenceFiles": verified,
    "retainedBinaryDiffs": binary_verified,
    "literalInverses": {
        "editor": {"operations": 15, "forwardExactCandidate": True, "reverseExactOriginal": True,
                   "before": entry(before, ref=BASE, path=EDITOR), "after": entry(after, ref=SHA, path=EDITOR)},
        "package": {"operations": 3, "forwardExactCandidate": True, "reverseExactOriginal": True,
                    "before": entry(before_package, ref=BASE, path=PACKAGE),
                    "after": entry(after_package, ref=SHA, path=PACKAGE)},
    },
    "hanlinPresentation": {
        "unchangedExactFunction": entry(function, path=EDITOR, function="presentHanlin"),
        "futureHookOwner": "Wave2 editor owner coordinated with /root/sdk_hanlin",
        "futureHookPreimage": entry(after, ref=SHA, path=EDITOR),
        "hookImplementedInReviewedCommit": False,
    },
    "semanticReview": [
        {"area": "Original font policy", "result": "Original TextContent+Font maps header/header2/header3/code/default text to title/heading/subheading/codeBlock/bodyRegular. The actual DesignKit configurations are Inter Bold28/22/17, IBM Plex Mono15 and Inter Regular17. The stale prose typography table is not used as authority."},
        {"area": "Scaling", "result": "Each render calls original nominal UIKitFontBuilder then UIFontMetrics.scaledFont for the current trait collection. No already-scaled font is passed to the scaling API. Inline overrides retain the already-scaled base point size."},
        {"area": "Body emphasis and inline code", "result": "The original nominal UIFont.bold/italic policy is applied before restoring scaled size, preserving body semibold and heading bold. The exact original four IBM Plex Mono faces are explicitly registered by FontConvertible before font creation. An unmarked run returns its original base font."},
        {"area": "Live refresh", "result": "An iOS17+ trait registration on the controller rerenders on preferred content size change; current package minimum iOS27 covers availability. The cache includes source, native style, native block type and content-size category; type/category clear on cell reuse and advance only after original renderer success."},
        {"area": "Composition and input preservation", "result": "Original controller render/configure marked-composition guards, attribute-only renderer, paragraph direction/alignment, source ranges, link/strike, selection, focus, undo and native mutation flows survive the exact inverse. Original normal composition completion rerenders after marked state clears. New font refresh does not write native data."},
        {"area": "Dependency and source boundary", "result": "Only downstream PinkhaAnyUI source/tests/manifest and evidence change. DesignKit is an explicit local iOS-conditional target/test dependency. No engine, Host, native, SDK pin or lock changes occur in this tranche; final root must retain the reviewed original font sources for matching acceptance."},
    ],
    "fontPolicy": [
        {"native": "heading level 1", "original": "AnytypeFont.title / Inter Bold28", "metrics": "title1"},
        {"native": "heading level 2, legacy or unknown level", "original": "AnytypeFont.heading / Inter Bold22", "metrics": "title2"},
        {"native": "heading level 3", "original": "AnytypeFont.subheading / Inter Bold17", "metrics": "headline"},
        {"native": "code", "original": "AnytypeFont.codeBlock / IBM Plex Mono Regular15", "metrics": "body"},
        {"native": "other rendered text", "original": "AnytypeFont.bodyRegular / Inter Regular17", "metrics": "body"},
    ],
    "applePrimaryReferences": [
        {"url": "https://developer.apple.com/documentation/uikit/uifontmetrics/scaledfont(for:compatiblewith:).md", "scope": "API signature, nominal input requirement, trait-specific scaling; not actual execution."},
        {"url": "https://developer.apple.com/documentation/uikit/uitraitchangeobservable-67e94/registerfortraitchanges(_:handler:).md", "scope": "iOS17 availability, observed object closure, registration lifetime; not actual execution."},
    ],
    "testSources": {
        "originalPath": TEST,
        "authoredMethods": [f"AnyNativeTextTypographyTests/{m}" for m in methods],
        "status": "NOT_RUN",
        "scope": "Two authored UIKit methods inspect actual bundled faces/sizes and original body-emphasis descriptors; the renderer check observes attribute-only update, UTF16 Hebrew/emoji selection, link/strike/direction/alignment and refusal while composing.",
        "hostBinding": "PinkhaAnyUI package test source. It is not included merely by the existing AnytypeTests 43-source proof or the old shared8f2 product. A future actual package/hosted source reference, compiler FileList and compiled enumeration must bind this exact source before claiming execution.",
    },
    "sourceRefactorClassification": "The supplied editor entry is an 8f2-relative downstream review mapping; it is not automatically a member of the original586c/upstream129 source map. Root owns map intake.",
    "remainingAcceptance": [
        "Actual matching Apple compiler and compiled enumeration of both authored UIKit methods.",
        "Execute these two methods with the reviewed bundled font resources and source closure.",
        "Actual controller trait-change notification while mounted, including retained marked composition and refresh on completion.",
        "Real iPhone/iPad, RTL/LTR, light/dark and accessibility-category visual acceptance.",
        "Physical-device acceptance remains NOT_RUN.",
    ],
    "execution": {"sourceMechanicalAudit": "PASS", "swiftCompilerRuns": 0, "UIKitRuns": 0,
                  "nativeServiceCalls": 0, "MacOperations": 0, "testsReplayed": 0,
                  "productionSourceEdits": 0, "finalBranchWrites": 0},
}
out = ROOT / "independent-review.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"status": report["status"], "path": str(out), "bytes": out.stat().st_size,
                  "sha256": digest(out.read_bytes()), "sourceProofSHA256": report["sourceProofSHA256"],
                  "verifiedSourceAndOriginalReferences": len(verified), "retainedDiffs": len(binary_verified),
                  "inverseOperations": 18, "authoredMethodsNotRun": len(methods)}, indent=2))
