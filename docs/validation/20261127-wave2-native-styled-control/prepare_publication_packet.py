"""Assemble exact reviewed source and retained local evidence; do not execute it."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
COLLECTOR = WORKSPACE / "torah-acceptance-prep/styled-collector-control"
TOOLS = "Tools/CurrentAppleValidation/native_styled_closed/"
DOCS = "docs/validation/20261127-wave2-native-styled-control/"
BASE = "7380a797d13b279b6d19e43ade7af1929089b8ef"
BRANCH = "codex/chatgpt-wave15-wave2-native-styled-control-20261127"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def record(raw):
    return {"bytes": len(raw), "sha256": sha(raw)}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--runtime-review", required=True, type=Path)
parser.add_argument("--runtime-review-sha256", required=True)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
require(not args.output.exists(), "Existing publication assembly must be preserved")
review_raw = args.runtime_review.read_bytes()
require(sha(review_raw) == args.runtime_review_sha256, "Independent runtime review changed")
review = json.loads(review_raw)
require(str(review.get("status", "")).startswith("PASS"), "Final runtime source review is not PASS")
require("c249ab9d04b4f8014475cf1eb8b81cf0371cab40a3f98a77b2938a2a0f2b6714" in review_raw.decode(),
        "Review does not bind exact frozen runtime")

files = {}
sources = ["native16_profile_closed.py", "prepare_native_styled_controllers_closed.py",
           "native_styled_runtime.py", "native_styled_observations.py",
           "native_rtl_matrix.py", "native_library_search.py"]
for name in sources:
    files[TOOLS + name] = (HERE / name).read_bytes()
files[TOOLS + "README.md"] = (HERE / "README.md").read_bytes()
for path in sorted((HERE / "materialized-closed3").iterdir()):
    require(path.is_file() and not path.is_symlink(), "Unexpected materialized member")
    files[TOOLS + "materialized/" + path.name] = path.read_bytes()

evidence_names = [
    "closed-entrypoints1.json", "closed-entrypoints3.json", "control1-input-retention.json",
    "editor-collector-review-71c.json", "editor-runtime-review-2d87.json",
    "editor-runtime-review-342a.json", "root-crosswire-review-a499.json",
    "portable-controls1.json", "lifecycle-controls2.json", "lifecycle-controls3.json",
    "registry-controls4.json", "post-popen-cleanup-correction.json",
    "owned-registry-correction.json",
    "validate_styled_preparation.py", "validate_styled_lifecycle.py", "validate_styled_registry.py",
    "publish_styled_control.py", "resume_styled_control_publication.py",
    "prepare_publication_packet.py", "source-publication-preflight.json",
]
for name in evidence_names:
    files[DOCS + name] = (HERE / name).read_bytes()
files[DOCS + args.runtime_review.name] = review_raw
diff_members = {}
for name in ["runtime-post-popen-cleanup.diff", "runtime-owned-registry.diff", "generated-owned-registry-runner.diff"]:
    raw = (HERE / name).read_bytes()
    diff_members[name] = {**record(raw), "utf8": raw.decode()}
files[DOCS + "retained-exact-diffs.json"] = encode({
    "schema": "native-styled-exact-reviewed-diff-retention/v1", "members": diff_members,
    "reason": "Git's ordinary whitespace gate rejects the valid single-space blank context lines in an added .diff file. Exact original diff bytes are retained as JSON string data; no reviewed controller/source bytes or Git gates are changed.",
    "failedPublicationReceiptSHA256": "abbfa0b717bc200fd88ffc09022492e8f0c8ac2a88ad8f902f8104c0b0ce2008",
})
for name in ["dispatch-attempt1.json", "actual-source-failure.json"]:
    files[DOCS + "publication/" + name] = (HERE / "publication1" / name).read_bytes()

members = {}
retained_names = ["materialized-closed1", "materialized-closed2", "retained-control1-input",
                  "retained-runtime-review1", "retained-runtime-review2"]
for name in retained_names:
    for path in sorted((HERE / name).rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        raw = path.read_bytes()
        key = str(path.relative_to(WORKSPACE))
        members[key] = {**record(raw), "utf8": raw.decode()}
prior_packager = HERE / "publication1/prepare_publication_packet_before_diff_encoding.py"
prior_raw = prior_packager.read_bytes()
members[str(prior_packager.relative_to(WORKSPACE))] = {**record(prior_raw), "utf8": prior_raw.decode()}
for name, expected in {
    "build_prebuilt_native_ui8ac.py": "e6c4c506cf893b2dc495fdc4b76c686f09a108c9980e05d19590d92acab804f9",
    "run_prebuilt_native_ui8ac.py": "18c7cc5722a856782d454a11db11ea172c9d718cecd17cd6dc54ffcc2a256d2b",
}.items():
    path = HERE.parent / "nativeui" / name
    raw = path.read_bytes()
    require(sha(raw) == expected, "Original controller bytes changed")
    members[str(path.relative_to(WORKSPACE))] = {**record(raw), "utf8": raw.decode()}
for path in sorted(COLLECTOR.rglob("*")):
    if not path.is_file() or "__pycache__" in path.parts:
        continue
    raw = path.read_bytes()
    if "review-v1" in path.parts:
        members[str(path.relative_to(WORKSPACE))] = {**record(raw), "utf8": raw.decode()}
    else:
        files[DOCS + "collector/" + str(path.relative_to(COLLECTOR))] = raw
member_records = {name: {"bytes": item["bytes"], "sha256": item["sha256"]}
                  for name, item in members.items()}
content_by_sha = {item["sha256"]: item["utf8"] for item in members.values()}
for name, item in member_records.items():
    retained = content_by_sha[item["sha256"]].encode()
    require(record(retained) == item, "Retained member reconstruction changed: " + name)
archive_raw = encode({"schema": "native-styled-exact-prior-source-members/v1",
                      "sourceRootAtExecution": str(WORKSPACE), "members": member_records,
                      "contentUTF8BySHA256": content_by_sha})
compressed = gzip.compress(archive_raw, mtime=0)
files[DOCS + "retained-prior-inputs.json"] = encode({
    "schema": "native-styled-exact-retained-input-archive/v1",
    "format": "base64(gzip(UTF-8 JSON))", "gzipMtime": 0,
    "decodedJSON": record(archive_raw), "compressed": record(compressed),
    "members": member_records,
    "payloadBase64": base64.b64encode(compressed).decode(),
    "scope": "Exact previously reviewed/executed local sources; no relocated execution claim",
})

reviews = []
for name in ["root-crosswire-review-a499.json", "editor-collector-review-71c.json", args.runtime_review.name]:
    reviews.append({"path": name, **record(files[DOCS + name])})
handoff = {
    "schema": "pinkha.wave2.native-styled-closed-control-handoff/1",
    "createdAtUTC": datetime.now(timezone.utc).isoformat(),
    "status": "SOURCE_REVIEWED_RUNTIME_CLOSED", "branch": BRANCH,
    "sourceDependency": BASE, "nativeManifest": "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b",
    "freshUpstreamDevelopReference": "d857b23ea540be33d6faab4f7a7a1a260ab578c1",
    "upstreamReferenceMeaning": "Read-only current lineage reference; source basis remains exact7380, no upstream merge or original-source mutation",
    "readyForExecution": False, "futureSourceCommit": None,
    "futureSharedControllerSHA256": None, "futureCanonicalAdmissionSHA256": None,
    "currentFiles": {name: record(files[TOOLS + name]) for name in sources},
    "materialized": {name: record(raw) for name, raw in files.items() if name.startswith(TOOLS + "materialized/")},
    "reviews": reviews,
    "plans": {
        "styled-blocks": {"selector": "PinkhaAnyNativeUITests/NativeLaunchTests/testTypedBlockMenusPersistAllNineKindsAndColdReopen",
                          "allowanceSeconds": 1800, "typedPhaseGroups": 29},
        "styled-live-type": {"selector": "PinkhaAnyNativeUITests/NativeLaunchTests/testNativeStyledTypographyRefreshesLiveAtAccessibilitySize",
                             "allowanceSeconds": 900, "typedPhaseGroups": 6},
    },
    "originalEnumerationSeconds": 360, "originalExportSeconds": 180,
    "commonAPI": "admit_and_clone_products(admission, root, evidence, commands)",
    "runtimeAdapter": "One isolated-globals registry captures every owned Popen in both new stages; unchanged original run code and lifecycle73bb do not imply unchanged executed behavior",
    "ownedClosure": "All commands aggregate custody; latch actual ABSENT_ESRCH, never re-probe a historical absent PGID, preserve first failure, retain device and withhold setting/shutdown if unresolved",
    "originalRunDeclarationSHA256": "5ea092b2a4d7159e8dec45b264224811e24e64265493a1e4958e4937b5fecaad",
    "originalLifecycleSHA256": "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a",
    "collectorSchemaChangedForClosure": False,
    "previousFailuresPreserved": ["editor-runtime-review-2d87.json", "editor-runtime-review-342a.json", "lifecycle-controls2.json"],
    "portableControls": {
        "initialPreparation": "5 PASS on individually pinned earlier inputs",
        "collector": "9 PASS on earlier exact collector, then 1 affected literal-negative PASS on current71c",
        "firstLifecycleAttempt": "2 PASS / 1 harness module-identity ERROR; original FAIL retained",
        "affectedHarnessRetry": "1 PASS, same342a runtime; no repetition of the other two methods",
        "finalRegistry": "4 PASS on c249; synthetic Popen, actual original run body/generated guards",
        "finalClosedEntrypoints": "2 expected CLOSED refusals before external I/O or subprocess creation",
    },
    "evidenceRelocation": "Retained local harnesses keep their actual original paths; copying is not a new execution and no path repair is silently applied",
    "sourceClosure": "27 exact paths declared; no future integrated App has yet been compared or admitted",
    "AppleBuilds": 0, "XCTestRuns": 0, "nativeCalls": 0, "simulatorOperations": 0,
    "visualAcceptance": "NOT_RUN", "physicalAcceptance": "NOT_RUN",
    "passedHierarchyDragSelected": False, "historicalT5Replayed": False,
    "classification": {TOOLS: "DOWNSTREAM_OWNED tools only", DOCS: "DOWNSTREAM_OWNED evidence only"},
    "applicationFilesChanged": 0, "nativeContractChanges": 0,
    "rollback": "Do not integrate this additive closed control commit; no published App/source runtime is mutated",
    "sourcePublicationBudget": "After all old-source retirements became terminal, parent qualified this distinct source-only phase using measured materialized source + uploaded packet + 16 MiB Git allowance + 64 MiB operating margin; all compiler/native/runtime gates unchanged. Earlier generic512MiB preflight hold remains retained.",
    "next": "Wave3 integrates exact source dependencies, supplies successful shared producer and reviewed fixed common admission; separately review executable successor, then compile one NativeUI runner with actual swiftc/two-file witness and run only the necessary selected journeys with retained visual/native evidence",
    "files": {name: record(raw) for name, raw in sorted(files.items())},
}
files[DOCS + "handoff.json"] = encode(handoff)
payload_bytes = sum(map(len, files.values()))
require(payload_bytes <= 1024 * 1024, "Publication payload exceeds the declared 1 MiB source-only envelope")
packet = encode({"schema": "native-styled-closed-publication-packet/v1", "base": BASE,
                 "branch": BRANCH, "files": {name: {**record(raw), "base64": base64.b64encode(raw).decode()}
                 for name, raw in sorted(files.items())}})
packed = gzip.compress(packet, mtime=0)
args.output.mkdir(mode=0o700)
(args.output / "packet.json.gz").write_bytes(packed)
(args.output / "handoff.json").write_bytes(files[DOCS + "handoff.json"])
(args.output / "retained-prior-inputs.json").write_bytes(files[DOCS + "retained-prior-inputs.json"])
summary = {"schema": "native-styled-local-publication-assembly/v1", "status": "PACKAGED_NOT_PUBLISHED",
           "files": len(files), "payloadBytes": payload_bytes, "packet": record(packed),
           "handoff": record(files[DOCS + "handoff.json"]), "retainedMembers": len(members),
           "runtimeReview": {"path": str(args.runtime_review), "sha256": args.runtime_review_sha256},
           "builds": 0, "tests": 0, "nativeCalls": 0}
(args.output / "assembly.json").write_bytes(encode(summary))
print(json.dumps(summary, sort_keys=True))
