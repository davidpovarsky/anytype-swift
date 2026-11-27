"""Package only the exact source-reviewed CLOSED Native23 accessibility successor."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
HELPER = HERE.parents[1] / "wave2-native-accessibility-control"
TOOLS = "Tools/CurrentAppleValidation/native23_accessibility_closed/"
DOCS = "docs/validation/20261127-wave2-native23-accessibility-control/"
BASE = "c7111ad400e9737ac3d35c54d9dcd6454e9a63b6"
BRANCH = "codex/chatgpt-wave15-wave2-native23-accessibility-20261127"
PINS = {
    "native23_profile_closed.py": "3fd3049737f4be72f4257a04e5ca94085e6d9e11cd3916257ced4bf2e8943aa6",
    "prepare_native23_controllers_closed.py": "a7d8fbe1a47266ef07381972fbae7190b4bc97c3f4633c5460e41dae54a143ef",
    "native_accessibility_runtime.py": "8001c3efc0003ce659a7d5b9e97656b801e6d59a45972589904652f7de55f9d2",
    "native_accessibility_observations.py": "a0e4a67a21594023537e830124272be23312afd9b3b5158fe7f0e6e5df543336",
    "native_styled_runtime.py": "c249ab9d04b4f8014475cf1eb8b81cf0371cab40a3f98a77b2938a2a0f2b6714",
    "native_styled_observations.py": "71c376659d34b7065d152f22c41f2ded731d4527d0231375a3e688a31e7f4f02",
    "native_rtl_matrix.py": "58c240a703a757291822073f82d84627ac5e3fedd9a0a8daf60c961a33c384ae",
    "native_library_search.py": "7f2af4c63464ae3ce9e088cf923d314b0bbb58b94bdc94ff871190a8b205d8f0",
}
REVIEW_PINS = {
    "root-independent-review.json": "b333bd4c64cdf7233741b91a994e6042fd50e8e69441bb277035b5a4345e2e1c",
    "torah-runtime-compatibility-review.json": "783ea3f9179efa3735b008ea96ea8d9170599409a6f6be77c65af04f2142c954",
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
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
require(not args.output.exists(), "Existing publication material must remain retained")
files, reviews = {}, []
for name, expected in REVIEW_PINS.items():
    raw = (HERE / name).read_bytes()
    require(sha(raw) == expected, "Frozen independent source review changed: " + name)
    files[DOCS + name] = raw
    reviews.append({"path": name, **pin(raw)})
root_review = json.loads(files[DOCS + "root-independent-review.json"])
require(root_review["status"] == "PASS_SOURCE_WIRING_REVIEW_NOT_RUNTIME_ACCEPTANCE"
        and root_review["proof"]["runner"]["candidateSHA256"] ==
        "e4515cc6cd36424c607ee1e986ea9f0cfdcb0db516bf6e91276eef685ba29a22",
        "Final review must bind the actual frozen generated runner")
for name, expected in PINS.items():
    raw = (HERE / name).read_bytes()
    require(sha(raw) == expected, "Frozen reviewed source changed: " + name)
    files[TOOLS + name] = raw
files[TOOLS + "README.md"] = (HERE / "README.md").read_bytes()
for path in sorted((HERE / "materialized-closed1").iterdir()):
    require(path.is_file() and not path.is_symlink(), "Unexpected materialized member")
    files[TOOLS + "materialized/" + path.name] = path.read_bytes()
for name in ("source-derivative.json", "choreography-controls1.json", "choreography-controls1.log",
             "validate_accessibility_choreography.py", "closed-accessibility-entry.json",
             "closed-accessibility-entry.stdout", "closed-accessibility-entry.stderr",
             "d-queue-addendum.json", "prepare_publication_packet.py", "publish_native23_accessibility.py"):
    files[DOCS + name] = (HERE / name).read_bytes()
# The helper's earlier custody record and missing-interpreter failure are
# retained verbatim. The later independent review is appended, not rewritten.
custody = json.loads((HELPER / "file-custody.json").read_bytes())
for name, expected in custody["files"].items():
    raw = (HELPER / name).read_bytes()
    require(pin(raw) == expected, "Original helper custody member changed: " + name)
    files[DOCS + "helper-originals/" + name] = raw
for name in ("file-custody.json", "torah-independent-review.json"):
    files[DOCS + "helper-originals/" + name] = (HELPER / name).read_bytes()
require(sha(files[DOCS + "helper-originals/torah-independent-review.json"]) ==
        "0f81e86965add59a9173c5582eea9ffe804a79840b889d910cba65d2b827cbd0",
        "Exact later helper source review is required")
reviews.append({"path": "helper-originals/torah-independent-review.json",
                **pin(files[DOCS + "helper-originals/torah-independent-review.json"])})
materialized = json.loads((HERE / "materialized-closed1/nativeui16-materialization.json").read_bytes())
require(sha((HERE / "materialized-closed1/nativeui16-materialization.json").read_bytes()) ==
        "f64e2ae359237a0b5c4ede43a49ae04bbce12cd97c4ccaaa8004c54149eca5b1",
        "Frozen materialization changed")
handoff = {
    "schema": "pinkha.wave2.native23-accessibility-closed-control-handoff/1",
    "createdAtUTC": datetime.now(timezone.utc).isoformat(),
    "status": "SOURCE_REVIEWED_RUNTIME_CLOSED", "branch": BRANCH, "sourceDependency": BASE,
    "readyForExecution": False, "futureSourceCommit": None,
    "futureSharedControllerSHA256": None, "futureCanonicalAdmissionSHA256": None,
    "nativeManifest": "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b",
    "newNativeTupleAdmitted": False,
    "currentFiles": {name: pin(files[TOOLS + name]) for name in PINS},
    "materialized": {name: pin(raw) for name, raw in files.items() if name.startswith(TOOLS + "materialized/")},
    "reviews": reviews, "allowedStages": materialized["allowedExecutionStages"],
    "accessibilityMethods": materialized["accessibilityMethods"],
    "sourceMethods": 23, "accessibilityUniqueMethods": 2, "additionalAccessibilityPlans": 3,
    "sourceInverseAuthority": "Unchanged71c exact23→21→19, then unchanged Library/RTL/title inverse chain",
    "previousSevenPlansUnchanged": True, "sourcePathPinsUnchanged": 27,
    "originalEnumerationSeconds": 360, "originalAttachmentExportSeconds": 180,
    "methodAllowanceSeconds": 900, "originalCommandGraceSeconds": 300,
    "originalControllerDefinitionCounts": {"builder": 5, "runner": 16},
    "ownedRegistry": "One unchanged c249 registry for all10 plans; original73bb lifecycle, first error and positive absence retained",
    "settings": "Original explicit baseline RTL cell; expanded audit changes size and restores large only after positive aggregate process closure",
    "context": "Exact13 original string fields; two descriptor variables with complete inverse; actual selected before-record SHA",
    "historicalAcceptedStagesSelectable": False, "passedHierarchyDragSelected": False,
    "historicalT5Replayed": False, "sourceClosure": "No actual future App/UI/source or new Native tuple admitted",
    "commonAPI": "admit_and_clone_products(admission, root, evidence, commands)",
    "sourceOnlyVerification": {
        "newChoreographyPortableMethods": 4, "newHelperPortableMethods": 4,
        "portableFailures": 0, "portableErrors": 0,
        "scope": "Synthetic commands, settings and source-observation boundaries only; no runtime admission",
        "oldRegistryCollectorOrUIControlsRerun": 0,
        "closedExpandedEntrypoint": "Expected refusal before external input reads/output creation",
        "originalMissingInterpreterFailurePreserved": True,
        "earlierHelperCustodyPendingStatusPreserved": True},
    "publicVoiceOverAPIProbe": "Prior compile-only bbc7a3 retained by its original owner; not rerun and not UI/VoiceOver runtime acceptance",
    "queue": "Addendum changes references to the three prepared plans only; prior D accepted/pending/unmapped obligations remain",
    "evidenceRelocation": "Original executed local harness paths retained exactly; packaging is not relocated execution",
    "classification": {TOOLS: "DOWNSTREAM_OWNED tools only", DOCS: "DOWNSTREAM_OWNED evidence only"},
    "AppleBuilds": 0, "XCTestRuns": 0, "nativeCalls": 0, "simulatorOperations": 0,
    "visualAcceptance": "NOT_RUN", "physicalAcceptance": "NOT_RUN",
    "applicationFilesChanged": 0, "nativeContractChanges": 0,
    "files": {name: pin(raw) for name, raw in files.items()},
}
files[DOCS + "handoff.json"] = encoded(handoff)
payload = sum(map(len, files.values()))
require(payload <= 1024 * 1024, "Publication exceeds the authorized bounded source envelope")
packet = {"schema": "native23-accessibility-closed-publication-packet/v1", "base": BASE, "branch": BRANCH,
          "files": {name: dict(pin(raw), base64=base64.b64encode(raw).decode()) for name, raw in files.items()}}
compressed = gzip.compress(encoded(packet), mtime=0)
assembly = {"schema": "native23-accessibility-closed-packet-assembly/v1", "status": "PACKAGED_NOT_COMMITTED",
            "payloadBytes": payload, "fileCount": len(files), "packet": pin(compressed),
            "handoffSHA256": sha(files[DOCS + "handoff.json"]), "base": BASE, "branch": BRANCH}
args.output.mkdir(mode=0o700)
(args.output / "packet.json.gz").write_bytes(compressed)
(args.output / "handoff.json").write_bytes(files[DOCS + "handoff.json"])
(args.output / "assembly.json").write_bytes(encoded(assembly))
print(json.dumps(assembly, sort_keys=True))
