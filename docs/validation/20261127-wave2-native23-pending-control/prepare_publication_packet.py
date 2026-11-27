"""Package the exact reviewed closed successor and retained source-only evidence."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = "Tools/CurrentAppleValidation/native23_pending_closed/"
DOCS = "docs/validation/20261127-wave2-native23-pending-control/"
BASE = "1f8a19ab4ec87490d6a17ae8470224f39bc48596"
BRANCH = "codex/chatgpt-wave15-wave2-native23-pending-20261127"
PINS = {
    "native23_profile_closed.py": "54ec0671be6bd88eadc795ae25ff24d8b46e968e8c61b8da23934536f3e2275f",
    "prepare_native23_controllers_closed.py": "d54988593a1191b5e255b6a0961723a2d7d7aaeb23e9880cbe8cc5ab0399c09b",
    "native_styled_runtime.py": "c249ab9d04b4f8014475cf1eb8b81cf0371cab40a3f98a77b2938a2a0f2b6714",
    "native_styled_observations.py": "71c376659d34b7065d152f22c41f2ded731d4527d0231375a3e688a31e7f4f02",
    "native_rtl_matrix.py": "58c240a703a757291822073f82d84627ac5e3fedd9a0a8daf60c961a33c384ae",
    "native_library_search.py": "7f2af4c63464ae3ce9e088cf923d314b0bbb58b94bdc94ff871190a8b205d8f0",
}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def pin(value):
    return {"bytes": len(value), "sha256": sha(value)}


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-review", type=Path, required=True)
parser.add_argument("--source-review-sha256", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
require(not args.output.exists(), "Existing publication material must remain retained")
files, reviews = {}, []
for path, expected in ((args.source_review, args.source_review_sha256),):
    raw = path.read_bytes()
    require(sha(raw) == expected and str(json.loads(raw).get("status", "")).startswith("PASS"),
            "The exact final independent source review is required")
    require("3aff24c73606a2b071c00616866a606aa0f92c0433f3eec8e019c868fd85ef4f" in raw.decode(),
            "Review must bind the frozen actual generated Native23 runner")
    require(DOCS + path.name not in files, "Independent review filenames collide")
    files[DOCS + path.name] = raw
    reviews.append({"path": path.name, **pin(raw)})
for name, expected in PINS.items():
    raw = (HERE / name).read_bytes()
    require(sha(raw) == expected, "Frozen reviewed source changed: " + name)
    files[TOOLS + name] = raw
files[TOOLS + "README.md"] = (HERE / "README.md").read_bytes()
for path in sorted((HERE / "materialized-closed1").iterdir()):
    require(path.is_file() and not path.is_symlink(), "Unexpected materialized member")
    files[TOOLS + "materialized/" + path.name] = path.read_bytes()
evidence = ["source-derivative.json", "pending-controls1.json", "pending-controls1-tool-output.json",
            "validate_native23_pending.py", "closed-entrypoints.json", "prepare_publication_packet.py",
            "publish_native23_pending.py", "root-review-attempt1.json"]
for label in ("builder", "pending-sharing", "accepted-hierarchy-drag-rejected"):
    evidence.extend(label + suffix for suffix in (".stdout", ".stderr"))
for name in evidence:
    files[DOCS + name] = (HERE / name).read_bytes()
for path in sorted((HERE / "retained-preparation-attempt1").iterdir()):
    require(path.is_file() and not path.is_symlink(), "Unexpected retained original input")
    files[DOCS + "retained-preparation-attempt1/" + path.name] = path.read_bytes()
queue = HERE.parent / "d-acceptance-queue"
for path in sorted(queue.rglob("*")):
    if path.is_file():
        require(not path.is_symlink(), "Queue evidence must be a physical retained file")
        files[DOCS + "queue/" + str(path.relative_to(queue))] = path.read_bytes()
materialized = json.loads((HERE / "materialized-closed1/nativeui16-materialization.json").read_bytes())
handoff = {
    "schema": "pinkha.wave2.native23-pending-closed-control-handoff/1",
    "createdAtUTC": datetime.now(timezone.utc).isoformat(),
    "status": "SOURCE_REVIEWED_RUNTIME_CLOSED", "branch": BRANCH, "sourceDependency": BASE,
    "readyForExecution": False, "futureSourceCommit": None,
    "futureSharedControllerSHA256": None, "futureCanonicalAdmissionSHA256": None,
    "nativeManifest": "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b",
    "currentFiles": {name: pin(files[TOOLS + name]) for name in PINS},
    "materialized": {name: pin(raw) for name, raw in files.items() if name.startswith(TOOLS + "materialized/")},
    "reviews": reviews,
    "allowedStages": materialized["allowedExecutionStages"],
    "pendingOriginalPlans": materialized["pendingOriginalMethods"],
    "sourceMethods": 23, "nativeHistoryMethodSeparate": True,
    "sourceInverseAuthority": "Unchanged71c exact23→21→19, then unchanged Library/RTL/title inverse chain",
    "originalEnumerationSeconds": 360, "originalAttachmentExportSeconds": 180,
    "originalCommandGraceSeconds": 300,
    "originalControllerDefinitionCounts": {"builder": 5, "runner": 16},
    "ownedRegistry": "Unchanged c249, extended at the new five original lane call sites; original73bb lifecycle and first-error/positive-absence guarantees retained",
    "onlyRTLOriginalLaneAcceptsDeviceCell": True,
    "historicalAcceptedStagesSelectable": False,
    "passedHierarchyDragSelected": False, "historicalT5Replayed": False,
    "accessibilityMethodsSelectable": False,
    "accessibilityNextStep": "Separate additive source-reviewed helper/plan integration behind the same closed common admission and sole registry",
    "sourceClosure": "All27 prior source path pins unchanged; no actual future App source or product admitted",
    "commonAPI": "admit_and_clone_products(admission, root, evidence, commands)",
    "sourceOnlyVerification": {
        "portableMethods": 2, "portableFailures": 0, "portableErrors": 0,
        "scope": "Synthetic Popen with actual generated five-lane branch dispatch and original cell validation",
        "oldRegistryAndCollectorControlSuitesRerun": 0,
        "closedEntrypoints": "Builder and pending-sharing expected refusal before external input/output; accepted hierarchy drag parser rejection",
        "firstMaterializationFailurePreserved": True, "interruptedLocalEvidenceGenerationPreserved": True},
    "queue": "Retained D snapshot with original accepted, pending and explicitly unmapped obligations; not a current-product acceptance report",
    "evidenceRelocation": "Executed local harnesses and paths retained exactly; packaging is not a relocated execution",
    "classification": {TOOLS: "DOWNSTREAM_OWNED tools only", DOCS: "DOWNSTREAM_OWNED evidence only"},
    "AppleBuilds": 0, "XCTestRuns": 0, "nativeCalls": 0, "simulatorOperations": 0,
    "visualAcceptance": "NOT_RUN", "physicalAcceptance": "NOT_RUN",
    "applicationFilesChanged": 0, "nativeContractChanges": 0,
    "files": {name: pin(raw) for name, raw in files.items()},
}
files[DOCS + "handoff.json"] = encoded(handoff)
payload = sum(map(len, files.values()))
require(payload <= 1024 * 1024, "Publication exceeds the authorized bounded source envelope")
packet = {"schema": "native23-pending-closed-publication-packet/v1", "base": BASE, "branch": BRANCH,
          "files": {name: dict(pin(raw), base64=base64.b64encode(raw).decode()) for name, raw in files.items()}}
compressed = gzip.compress(encoded(packet), mtime=0)
assembly = {"schema": "native23-pending-closed-packet-assembly/v1", "status": "PACKAGED_NOT_COMMITTED",
            "payloadBytes": payload, "fileCount": len(files), "packet": pin(compressed),
            "handoffSHA256": sha(files[DOCS + "handoff.json"]), "base": BASE, "branch": BRANCH}
args.output.mkdir(mode=0o700)
(args.output / "packet.json.gz").write_bytes(compressed)
(args.output / "handoff.json").write_bytes(files[DOCS + "handoff.json"])
(args.output / "assembly.json").write_bytes(encoded(assembly))
print(json.dumps(assembly, sort_keys=True))
