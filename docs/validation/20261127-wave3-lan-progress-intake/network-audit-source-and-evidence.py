#!/usr/bin/env python3
"""Review retained source/evidence only; never import or execute its controllers."""
import ast
import datetime
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = "Tools/AnyEngineValidation/native_file_peer_comparison"
FIRST = "8c4953a01c3b6c8025b2f6c78edd491e8be7ea08"
SECOND = "988d057848087410dc6363b21fadea94ee759b52"
THIRD = "4a381db674fa1f011bff5d02d1a1e9badf253c1e"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def j(path):
    return json.loads(Path(path).read_bytes())


def entry(path):
    p = Path(path)
    data = p.read_bytes()
    return {"path": str(p), "bytes": len(data), "sha256": sha(data)}


def source(ref, name):
    return ROOT / ref / REPO / name


intake = j(ROOT / "intake.json")
assert [c["sha"] for c in intake["commits"]] == [FIRST, SECOND, THIRD]
assert [c["parents"][0]["sha"] for c in intake["commits"]] == [
    "f2b40968bd9347438b8fed432912f41944b43828", FIRST, SECOND]
rows = []
for row in intake["files"]:
    data = row["content"].encode()
    assert blob(data) == row["expectedBlob"] == row["sha"]
    assert (ROOT / row["ref"] / row["path"]).read_bytes() == data
    rows.append({"commit": row["ref"], "path": row["path"], "bytes": len(data),
                 "gitBlob": blob(data), "sha256": sha(data)})
assert len(rows) == 23
assert all(f["status"] == "added" for c in intake["commits"] for f in c["files"])

manifest = j(source(FIRST, "lan_progress/manifest.json"))
patch = source(FIRST, "lan_progress/sdk-lan-progress.patch").read_bytes()
assert sha(patch) == manifest["patchSHA256"]
root_closure = j(ROOT / "root-predecessor-closure.json")
assert root_closure["exactEquality"] and len(root_closure["rootEntries"]) == 17
extra = j(ROOT / "additional-prerequisites.json")
acl_patch = next(x for x in extra if x["key"] == "networkRootACLPatch")["content"].encode()
assert sha(acl_patch) == manifest["requiresPatchSHA256"]


def sections(raw):
    lines = raw.decode().splitlines(keepends=True)
    out = []
    i = 0
    while i < len(lines):
        assert lines[i].startswith("--- ") and lines[i+1].startswith("+++ ")
        old, new = lines[i][4:].rstrip("\n"), lines[i+1][4:].rstrip("\n")
        i += 2
        hunks = []
        while i < len(lines) and not lines[i].startswith("--- "):
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
            assert match, lines[i]
            start_old, count_old, start_new, count_new = (
                int(match[1]), int(match[2] or 1), int(match[3]), int(match[4] or 1))
            i += 1
            body = []
            while i < len(lines) and not lines[i].startswith(("@@ ", "--- ")):
                assert lines[i][0] in " +-", lines[i]
                body.append(lines[i])
                i += 1
            hunks.append((start_old, count_old, start_new, count_new, body))
        out.append((old, new, hunks))
    return out


def apply(original, hunks, reverse=False):
    original = original.decode().splitlines(keepends=True)
    output, cursor = [], 0
    for old_start, old_count, new_start, new_count, body in hunks:
        if reverse:
            old_start, old_count, new_start, new_count = new_start, new_count, old_start, old_count
            body = [("-" if x[0] == "+" else "+" if x[0] == "-" else " ")+x[1:] for x in body]
        start = max(0, old_start-1)
        assert start >= cursor
        output += original[cursor:start]
        consumed = [x[1:] for x in body if x[0] in " -"]
        produced = [x[1:] for x in body if x[0] in " +"]
        assert len(consumed) == old_count and len(produced) == new_count
        assert original[start:start+old_count] == consumed
        output += produced
        cursor = start + old_count
    return "".join(output + original[cursor:]).encode()


source_inverse = []
for old, new, hunks in sections(patch):
    name = new.removeprefix("b/")
    row = next(x for x in manifest["changes"] if x["path"] == name)
    before = (ROOT / "oracle-originals/acl-refresh-overlay1/sdk-source" / name).read_bytes() if old != "/dev/null" else b""
    after = apply(before, hunks)
    assert (sha(before) if old != "/dev/null" else None) == row["beforeSHA256"]
    assert sha(after) == row["afterSHA256"]
    assert apply(after, hunks, True) == before
    if name.endswith("peermanager.go"):
        assert after == (ROOT / "oracle-originals/lan-progress-unit2/sdk-source" / name).read_bytes()
        # The published qualification input predates gofmt and has one extra LF.
        assert (ROOT / "sdk-inputs-before-gofmt" / name).read_bytes() == after+b"\n"
    else:
        assert after == (ROOT / "sdk-inputs-before-gofmt" / name).read_bytes()
    source_inverse.append({**row, "beforeBytes": len(before), "afterBytes": len(after),
                           "hunks": len(hunks), "exactForward": True, "exactReverse": True})
assert len(source_inverse) == 3

u1 = j(source(FIRST, "lan_progress/lan-progress-unit1-result.json"))
u2 = j(source(FIRST, "lan_progress/lan-progress-unit2-result.json"))
original_tests = j(ROOT / "original-files2.json")["files"]
for receipt, path, label in (
    (u1, "lan-progress-unit1/baseline.log", "baseline"),
    (u2, "lan-progress-unit2/baseline.log", "baseline"),
    (u2, "lan-progress-unit2/corrected.log", "corrected"),
):
    log = next(x for x in original_tests if x["path"].endswith(path))
    process = next(x for x in receipt["processes"] if x["label"] == label)
    assert log["sha256"] == process["logSHA256"]
    terminal = [{"name": x["Test"], "action": x["Action"], "seconds": x["Elapsed"]}
                for x in log["terminalEvents"] if x.get("Test")]
    assert terminal == receipt[label]
assert sum(x["action"] == "fail" for x in u2["baseline"]) == 5
assert sum(x["action"] == "pass" for x in u2["baseline"]) == 2
assert len(u2["corrected"]) == 17 and all(x["action"] == "pass" for x in u2["corrected"])
assert not any(x["action"] == "skip" for x in u2["corrected"])
assert u2["allOwnedGroupsPositivelyAbsent"] and u2["baselineTestSourcesUnchanged"]
old_test = next(x for x in extra if x["key"] == "networkUnit1TestRead")["content"]
new_test = (ROOT / "sdk-inputs-before-gofmt/internal/anysyncx/peerprogress_test.go").read_text()
assert old_test.count("newTestManager(") == new_test.count("newTestManager(") == 7
old_lines, new_lines = old_test.splitlines(), new_test.splitlines()
assert len(old_lines) == len(new_lines)
fixture_changes = [(i+1, a, b) for i, (a, b) in enumerate(zip(old_lines,new_lines)) if a != b]
assert len(fixture_changes) == 5
for _, a, b in fixture_changes:
    assert "newTestManager(" in a and "newTestManager(" in b
    assert a.replace(", nil,", ", &fakeLocalPeers{},", 1) == b

native = j(source(SECOND, "lan_progress/native-build-result.json"))
accepted = j(source(SECOND, "lan_progress/original-files-lan-progress1-result.json"))
failed = j(source(SECOND, "lan_progress/original-files-after-join2-result.json"))
assert accepted["status"] == "PASS_ORIGINAL_RETAINED_ACCOUNTS_LAN_PROGRESS_FIVE_FILES_CRASH_COLD_BYTES"
assert accepted["actualFilesV2Acceptance"] and not accepted["cloudCustodyAccepted"] and not accepted["wholeSpaceMigrationAccepted"]
assert not accepted["errors"] and accepted["confirmedAttachmentsReissued"] == 0
assert all(accepted[key] == 0 for key in ("accountInitCalls","joinCalls","grantCalls","inviteCreateCalls","appBuilds","goBuilds"))
assert len(accepted["existingAttachmentLedger"]) == 4
assert accepted["attachmentCalls"] == len(accepted["attachmentLedger"]) == 2
assert [x["name"] for x in accepted["attachmentLedger"]] == ["thumb.png","acl-revocation-canary.bin"]
assert accepted["accounts"] == failed["accounts"]
assert accepted["spaceId"] == failed["spaceId"] and accepted["objectId"] == failed["objectId"]
assert accepted["existingAttachmentLedger"] == failed["existingAttachmentLedger"]+failed["attachmentLedger"]
assert accepted["nativeBefore"] == accepted["nativeAfter"] == accepted["finalNativeAdmission"]
assert accepted["nativeBefore"]["binarySHA256"] == native["binary"]["sha256"]
assert len(accepted["processes"]) == 7 and len({x["pid"] for x in accepted["processes"]}) == 7
assert sum(x["intentionalCrash"] for x in accepted["processes"]) == 1
assert all(x["groupPositivelyAbsent"] and not x["forcedKill"] and x["exitCode"] == (-9 if x["intentionalCrash"] else 0) for x in accepted["processes"])
assert len(accepted["files"]) == len(accepted["coldFiles"]) == 5
for row, cold in zip(accepted["files"], accepted["coldFiles"]):
    assert row["fileId"] == cold["fileId"]
    assert row["plaintextBytes"] == cold["bytes"]
    assert row["plaintextSHA256"] == row["destinationSHA256"] == cold["sha256"]
    assert row["recipientComplete"] and not row["recipientInitiallyCached"]
assert accepted["partialCrash"]["actualOwnedCrash"]
assert accepted["partialCrash"]["partialEncryptedCAR"]["hasSparseAllocation"]
assert all(accepted["partialColdSync"][k] == accepted["fullColdSync"][k] == 0 for k in ("networkPeers","localPeers","globalPeers"))
assert accepted["revocationCanary"]["recipientContentReadCalls"] == 0
assert accepted["revocationCanary"]["recipientStillUncachedAfterColdReopen"]
assert accepted["offlineReaderWriteDenial"]["status"] == 403

old_control = source(SECOND, "lan_progress/continue_original_files_with_sync_diagnostics.py").read_text()
new_control = source(SECOND, "lan_progress/qualify_original_lan_progress.py").read_text()
def functions(text):
    return {n.name: ast.get_source_segment(text,n) for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef)}
old_functions, new_functions = functions(old_control), functions(new_control)
same_functions = sorted(k for k in old_functions.keys() & new_functions.keys() if old_functions[k] == new_functions[k])
changed_functions = sorted(k for k in old_functions.keys() & new_functions.keys() if old_functions[k] != new_functions[k])
assert len(same_functions) == 34 and changed_functions == ["attach","main"]
assert 'return until(90,row_arrived,"recipient complete native file metadata")' in new_functions["await_metadata"]

audit = j(ROOT / "original-files4.json")
assert audit["status"] == "PASS_READ_ONLY_ORIGINAL_SOURCE_LOG_AND_CUSTODY_AUDIT"
assert not audit["errors"] and len(audit["files"]) == 37
assert audit["nativeSourceComparison"]["actual"]["files"] == 1599
assert audit["nativeSourceComparison"]["actual"]["exactManifestMatch"]
assert audit["SDKComparison"]["actualQualifiedSDKUnchanged"]
assert audit["SDKComparison"]["sameExactNewTestsBaselineAndCorrected"]
stacks = audit["observedBlockedWorkerStacks"]
assert all(x["matchingWorkerStacks"] == 4 for x in stacks if "9DSkw6W3eqv" in x["name"])
assert not audit["native792Custody"]["formerPathExists"] and not audit["native792Custody"]["restoreExecuted"]
assert audit["native792Custody"]["rawCopyExact"] and audit["native792Custody"]["metadataExact"]
assert audit["native792Custody"]["originalPartialXZRemainsFailed"]
assert not audit["accountDirectoriesOpened"] and audit["nativeOrTestCommandsExecuted"] == 0

for ref,name,receipt,key in (
    (FIRST,"lan_progress/qualify_lan_progress2.py",u2,"controllerSHA256"),
    (SECOND,"lan_progress/build_lan_progress_native.py",native,"controllerSHA256"),
    (SECOND,"lan_progress/qualify_original_lan_progress.py",accepted,"controllerSHA256"),
    (SECOND,"lan_progress/continue_original_files_with_sync_diagnostics.py",failed,"controllerSHA256"),
):
    assert sha(source(ref,name).read_bytes()) == receipt[key]

receipts = [
    source(FIRST,"lan_progress/lan-progress-unit1-result.json"),
    source(FIRST,"lan_progress/lan-progress-unit2-result.json"),
    source(FIRST,"lan_progress/source-replay-result.json"),
    source(SECOND,"lan_progress/native-build-result.json"),
    source(SECOND,"lan_progress/native-source-manifest.json"),
    source(SECOND,"lan_progress/original-files-after-join2-result.json"),
    source(SECOND,"lan_progress/original-files-lan-progress1-result.json"),
    source(THIRD,"native_product_custody/receipt.json"),
    source(THIRD,"native_product_custody/failed-xz-result.json"),
]
report = {
    "schema": "pinkha-wave3-independent-network-lan-progress-intake-v1",
    "reviewer": "/root/miniapps_otzaria",
    "reviewedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "READY_SOURCE_AND_SCOPED_ORIGINAL_LINUX_EVIDENCE_APPLE_INTEGRATION_NOT_ACCEPTED",
    "concreteSourceBlockers": [],
    "requestedHQStory": intake["story"],
    "mergeOrder": [FIRST, SECOND, THIRD],
    "parentSource": "f2b40968bd9347438b8fed432912f41944b43828",
    "reviewedRootSnapshot": root_closure["rootRef"],
    "rootPrerequisites": {"originalNetworkDirectoryExactDonorEquality": True, "entries": 17,
                          "closure": entry(ROOT/"root-predecessor-closure.json"),
                          "requiredACLOverlaySHA256": manifest["requiresPatchSHA256"],
                          "rootACLOverlayMatches": True},
    "gitFiles": rows,
    "productionOverlay": {"manifest": manifest, "exactPatchForwardAndReverse": source_inverse,
                          "originalQualificationInputDifference": "peermanager.go input has one extra trailing LF before the recorded gofmt; published patch, actual qualified source and native manifest use the exact canonical f4fafe bytes. No hash normalization is used for source admission."},
    "sourceReview": [
        {"area": "Per-Space coalescing", "finding": "atomic.Bool admits one queued/resolving subscription per original spacePeerManager. sync.OnceFunc releases on getter completion or Send rejection. The original node-state notification still runs on a coalesced call. The same manager is not promised reusable after shutdown discards its queued getter."},
        {"area": "Cancellation and dispatch ownership", "finding": "Original KeepAlive already dispatched with m.runCtx rather than caller ctx. New code retains that original Space lifetime and refuses a cancelled owner. Discovery creates its10s context only inside the actual worker; cancellation still reaches the original pool.Get. Original Close/runCancel and unchanged StreamPool.Send remain authoritative. Original eachOf joins all at-most3 workers before publishing the ordered result slice."},
        {"area": "Fallback and ACL boundary", "finding": "Only the node leg gets1s when the original Space has known LAN/global candidate IDs. The LAN/global leg retains original caller ctx, preserving cancellation and dial-strike behavior. No-candidate GetResponsiblePeers retains original caller budget and node error. Public GetNodePeers stays unchanged/nodes-only. The overlay does not modify identity, membership, signed ACL/tree, cipher, content or file-storage code."},
        {"area": "Scope of concurrency fix", "finding": "This bounds one manager's discovery and coalesces its subscriptions; it is not a claim that every multi-Space scheduling or WAN topology is now exhaustively accepted."},
        {"area": "Apply boundary", "finding": "The overlay applies only to an isolated canonical SDK directory after exact ACL prerequisite pins, patch SHA and before hashes, then verifies exactly3 changed files and after hashes. Retained qualified exports are refused. Applying or checking the overlay is source-only, not native/app acceptance."},
    ],
    "originalFocusedTests": {
        "baseline": u2["baseline"], "corrected": u2["corrected"],
        "rawLogReads": original_tests,
        "fiveBaselineFailuresTwoPasses": True,
        "correctedPassCount": 17, "correctedFailCount": 0, "correctedSkipCount": 0,
        "baselineProcessSeconds": 24.040, "correctedProcessSeconds": 12.029,
        "firstFixturePanicPreserved": True,
        "priorFixtureSourceChanges": [{"line": n,"before": a,"after": b} for n,a,b in fixture_changes],
        "fixtureAssertionsChanged": False,
        "baselineAndCorrectedUseSameNewTestBytes": True,
        "reviewerTestReruns": 0,
    },
    "observedOriginalStall": {"originalFailures": audit["originalFailureRetention"],
                              "matchingOriginalWorkerStacks": stacks,
                              "finding": "The PNG15s and60s captures each contain four real KeepAlive/GetNodePeers/streampool worker stacks in both retained peers. These are hashes/readbacks of original captures, not new native observations."},
    "nativeIdentity": {"binary": native["binary"], "sourceFiles": 1599,
                       "nativeManifestSHA256": native["sourceManifestSHA256"],
                       "sdkFiles": 718, "sdkManifestSHA256": native["sdkManifestSHA256"],
                       "baseAnyCommit": manifest["baseNativeAnyCommit"],
                       "baseAnySyncSDKCommit": manifest["baseNativeSDKCommit"],
                       "buildReceipt": entry(source(SECOND,"lan_progress/native-build-result.json")),
                       "sourceAndDeltaAudit": audit["nativeSourceComparison"],
                       "actualSDKClosureAudit": audit["SDKComparison"],
                       "compilerProcessSeconds": 80.470, "wholeProducerSeconds": 100.129,
                       "compilerLogBytes": 0, "compilerOutcome": "Original process exit0, exact binary and complete source manifest; not inferred merely from an empty log."},
    "originalRetainedNativeAcceptance": {
        "status": accepted["status"], "receipt": entry(source(SECOND,"lan_progress/original-files-lan-progress1-result.json")),
        "seconds": accepted["seconds"], "sameOriginalAccountsSpaceObject": True,
        "accountInitCalls": 0,"joinCalls": 0,"grantCalls": 0,"inviteCreateCalls": 0,
        "confirmedAttachmentsReissued": 0,"existingConfirmedAttachments": 4,
        "newAttachments": [x["name"] for x in accepted["attachmentLedger"]],
        "unchangedMetadataDeadlineSeconds": 90,
        "fiveFiles": accepted["files"], "fiveColdReadbacks": accepted["coldFiles"],
        "partialCrash": accepted["partialCrash"], "partialColdSync": accepted["partialColdSync"],
        "fullColdSync": accepted["fullColdSync"], "nativeVariantReadback": accepted["variantResolution"],
        "originalOSDenialProbe": audit["offlineProbe"],
        "readerWriteDenial": accepted["offlineReaderWriteDenial"],
        "canaryRemainsUncached": True,
        "processOutcome": {"distinctOwnedPIDs": 7,"normalExits": 6,"intentionalSIGKILL": 1,"allOriginalGroupsPositivelyAbsent": True},
        "controllerUnchangedSharedFunctions": same_functions,
        "controllerChangedFunctions": changed_functions,
        "controllerReview": "34 original functions including request/start/member/metadata/until90/range/OS probe/CAR and cleanup are byte-identical to the failed predecessor. New main admits exactly4 confirmed IDs and old custody; attach permits only the missing thumbnail and unique canary. It persists dispatch before native POST, forbids duplicate confirmed attachments, then performs real range/crash/new-PID offline/LAN-resume/full-cold checks.",
        "currentAccountDataReadByReviewer": False,
    },
    "native792Custody": {
        "receipt": entry(source(THIRD,"native_product_custody/receipt.json")),
        "restoreSource": entry(source(THIRD,"native_product_custody/restore.py")),
        "rawPath": "/mnt/development/projects/evidence/pinkha-w1-network-native792-raw-20261127/any-79248a63132a0146",
        "originalPath": "/var/lib/pinkha-c-filesv2-20261126/acl-refresh-native1/any",
        "sha256": "79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857",
        "bytes": 78074642,
        "actualOriginalReadAudit": audit["native792Custody"],
        "review": "Actual raw bytes, size,0700 mode, uid/gid and originalmtime match. Relocation fsynced the copy, restore mapping and receipt before duplicate-only retirement after source identity/no-live-use checks. The separate partialxz failed at the unchanged2GiB floor and remains intact/failed. No restore, retirement or copy was executed by this reviewer.",
        "restorePrerequisite": "Only a specific historical replay in the sole owner's exclusive slot should use the retained restore mapping. It checks source hash/size, destination absence and original resource floors, writes an exclusive temporary copy, verifies bytes/metadata, fsyncs and installs the historical path. It is not needed for current0796; old receipts keep their original content/source identity rather than being relabeled to0796.",
    },
    "scopeNotAccepted": [
        "Original-role revoked-read/removal/restoration; only Reader write refusal is proved and its canary remains uncached.",
        "Production cloud quota/custody or a FilesV2 cloud fleet; durable=false is explicit.",
        "Whole-Space migration, broad12-network/WAN or all multi-Space scheduling scenarios.",
        "Apple native slice build/packaging, final consumer ABI and application execution, physical devices or TestFlight.",
        "The frozen Apple8ac/Hanlin385 app is not this original Linux native0796. Any-sync SDKc1fd/718 and Hanlin SDK pins are separate source identities.",
    ],
    "mergeAndBuildPrerequisites": [
        "Root alone integrates8c4953 then988d057 then4a381 (23 added Tools/evidence files); the existing17-entry network directory at reviewed e320 exactly equals donorf2 and already includes the required1d421 ACL overlay.",
        "Retain the first unit panic, five-failure baseline, both native-transfer failures, failed partialxz and explicit raw792 restore mapping with their original SHA scopes.",
        "These commits publish an isolated Any-sync SDK overlay and Linux evidence; they do not modify the live Apple native framework or final product pins. Root/Wave1 must assemble the intended native union with the exact reviewed peer overlay and other ready changes, then qualify Apple slices/ABI/source manifests and bind the actual consumers.",
        "Do not rerun already-qualified original17 or the retained native file journey merely to merge source. Additional execution must resolve an actual changed dependency or remaining acceptance gate.",
    ],
    "retainedReceiptFiles": [entry(p) for p in receipts],
    "originalReadEvidence": [entry(ROOT/name) for name in (
        "original-read1.json","original-read2.json","original-files2.json",
        "original-read3.json","original-files3.json","original-read4.json","original-files4.json",
        "original-send-pool.json","additional-prerequisites.json")],
    "originalReadTransport": "First large readonly call returned MCP Internal error; exact failure preserved. Narrower readonly calls used the same authorized Sentinel artifact-reader identity. No permission/group/credential change or denied-read circumvention occurred.",
    "reviewerExecution": {"sourceAndEvidenceMechanicalAudit": "PASS", "testsRerun": 0,
                          "compilersStarted": 0,"nativeProcessesStarted": 0,"accountDirectoriesOpened": 0,
                          "networkOrACLMutations": 0,"signalsSent": 0,"restoreExecuted": False,
                          "MacOperations": 0,"finalBranchWrites": 0},
}
out = ROOT / "independent-review.json"
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"status": report["status"],"report": entry(out),"sourceFiles": len(rows),
                  "exactPatchFiles": len(source_inverse),"originalArtifactReadCount": 37,
                  "unchangedControllerFunctions": len(same_functions),"originalNativeSourceFiles": 1599,
                  "originalSDKSourceFiles": 718,"originalCorrectedTests": 17},indent=2))
