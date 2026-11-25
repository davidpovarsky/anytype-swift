"""Independently compare original semantic UI attachments; perform no app work."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

SOURCE = "6f1194f9b8c9540dea1187826dda6a256777dbbf"
CONTROLLER = "aa7a081dac474724f8ae799ccb5e7124c951696c801aafaa6c207a209e08e458"
MAIN = "f6054279384d731c17014d78b0aa09c1f244130f2295119197a8bd9c50930983"
RUNNER = "0bbf74af14ca71000bc1179ea106dae37d6a8ea5dbee9642091b52344f09ce69"
NATIVE = "70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72"
METHODS = {
    "semantic-anchor": "NativeLaunchTests/testActualSemanticSelectionCancelCreateEditAndColdReopen",
    "semantic-sources": "NativeLaunchTests/testSemanticSourceLinkSurvivesEditAndColdReopen",
}
PHASES = {
    "semantic-anchor": ["initial-saved", "cancel-without-native-mutation",
        "native-and-rendered-anchor-created", "ordinary-ui-edit-preserved-identity",
        "fresh-process-native-and-ui-reopen"],
    "semantic-sources": ["source-target-native-anchor-created", "source-link-canonical-native-readback",
        "source-link-follows-real-text-edit", "source-link-fresh-process-native-reopen",
        "source-unlink-keeps-native-text-and-marker", "source-unlink-fresh-process-readback"],
}


def require(value, name):
    if not value:
        raise ValueError(name)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def textsha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def load(path):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))


def anchor(by_phase):
    initial, cancelled, created, edited, cold = [by_phase[p] for p in PHASES["semantic-anchor"]]
    require(initial["nativeMarkCount"] == cancelled["nativeMarkCount"] == 0, "cancel_created_marker")
    require(initial["nativeVersionSHA256"] == cancelled["nativeVersionSHA256"]
        and initial["blocks"][0]["sourceSHA256"] == cancelled["blocks"][0]["sourceSHA256"],
        "cancel_changed_native_revision_or_source")
    require(initial["blocks"][0]["textSHA256"] == textsha("Anchor"), "initial_text_differs")
    marker = created["blocks"][0]["nativeMarks"]
    require(len(marker) == 1 and marker[0]["location"] == 0 and marker[0]["length"] == 6
        and marker[0]["textSHA256"] == textsha("Anchor"), "created_native_marker_differs")
    require(created["nativeVersionSHA256"] != cancelled["nativeVersionSHA256"], "capture_did_not_change_revision")
    for value in (edited, cold):
        block = value["blocks"][0]
        require(block["textSHA256"] == textsha("Changed") and len(block["nativeMarks"]) == 1,
            "edited_native_text_or_marker_count")
        mark = block["nativeMarks"][0]
        require(mark["identitySHA256"] == marker[0]["identitySHA256"] and mark["location"] == 0
            and mark["length"] == 7 and mark["textSHA256"] == textsha("Changed"), "edited_native_marker_extent")
    require(edited["nativeVersionSHA256"] != created["nativeVersionSHA256"]
        and edited["nativeVersionSHA256"] == cold["nativeVersionSHA256"], "edited_revision_not_persistent")
    require(edited["blocks"][0]["sourceSHA256"] == cold["blocks"][0]["sourceSHA256"]
        and edited["blocks"][0]["nativeMarks"] == cold["blocks"][0]["nativeMarks"], "cold_native_source_changed")
    require(edited["pid"] != cold["pid"] and edited["generation"] != cold["generation"], "cold_owner_not_distinct")
    require(all(value["semanticSources"] == [] for value in by_phase.values()), "unrequested_source_association")
    return {"cancelPreservesOriginalNativeBytesAndRevision": True, "anchorIdentitySurvivesEdit": True,
        "savedNativeBytesAndRevisionSurviveDistinctColdProcess": True}


def sources(by_phase):
    created, linked, edited, cold, unlinked, removed = [by_phase[p] for p in PHASES["semantic-sources"]]
    # These native/canonical equality predicates preserve the independently
    # audited original source-link qualification at accepted 78d6eb2a.
    require(created['nativeVersionSHA256']==linked['nativeVersionSHA256'],'unrequested_text_revision_before_edit')
    require(edited['nativeVersionSHA256']!=linked['nativeVersionSHA256'],'text_edit_did_not_change_native_document_revision')
    require(edited['nativeVersionSHA256']==cold['nativeVersionSHA256']==unlinked['nativeVersionSHA256']==removed['nativeVersionSHA256'],'saved_native_text_revision_changed_after_reopen_or_unlink')
    mark=created['blocks'][0]['nativeMarks'][0]
    require(mark['location']==0 and mark['length']==6 and mark['textSHA256']==textsha('Anchor'),'original_selected_marker')
    require(created['semanticSources']==[] and len(linked['semanticSources'])==1,'canonical_link_count')
    association=linked['semanticSources'][0]
    require(association['identitySHA256']==mark['identitySHA256'] and association['canonicalSHA256']==textsha('Genesis 1:1') and association['resolution']=='resolved','canonical_source_identity')
    require(linked['sourceReadOrigin']=='TorahEditorSession.associationRecords','canonical_read_origin')
    require(edited['semanticSources']==cold['semanticSources']==[association],'canonical_source_changed_after_edit_or_reopen')
    for value in [edited,cold,unlinked,removed]:
        block=value['blocks'][0]
        require(block['textSHA256']==textsha('Changed') and len(block['nativeMarks'])==1,'edited_native_text_or_mark_count')
        current=block['nativeMarks'][0]
        require(current['identitySHA256']==mark['identitySHA256'] and current['location']==0 and current['length']==7,'edited_native_marker_identity_or_extent')
    require(edited['blocks'][0]['sourceSHA256']==cold['blocks'][0]['sourceSHA256']==unlinked['blocks'][0]['sourceSHA256']==removed['blocks'][0]['sourceSHA256'],'unlink_changed_native_source_bytes')
    require(unlinked['semanticSources']==removed['semanticSources']==[],'unlink_not_persisted')
    require(len({edited['pid'],cold['pid'],removed['pid']})==3 and len({edited['generation'],cold['generation'],removed['generation']})==3,'cold_process_not_distinct')
    return {"canonicalSourceRecordUnchangedAfterEditAndColdReopen": True,
        "unlinkSourceAbsentAfterSecondColdProcess": True, "textAndMarkerUnchangedByUnlink": True,
        "nativeDocumentRevisionChangesWithTextEditAndPersistsAfterward": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--stage", choices=tuple(METHODS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    require(root.is_absolute() and root.resolve() == root, "canonical_original_root_required")
    receipt = root / "receipt.json"
    require(re.fullmatch(r"[a-f0-9]{64}", args.receipt_sha256) and sha(receipt) == args.receipt_sha256,
        "exact_original_receipt_required")
    actual = load(receipt); summary = load(root / "summary.json")
    require(actual["status"] == "PASS" and actual["sourceCommit"] == SOURCE
        and actual["controllerSHA256"] == CONTROLLER and actual["stage"] == args.stage
        and actual["mainReceiptSHA256"] == MAIN and actual["runnerReceiptSHA256"] == RUNNER
        and actual["nativeManifestSHA256"] == NATIVE, "qualified_current_source_or_result_differs")
    counts = {"failedTests": 0, "passedTests": 1, "skippedTests": 0, "totalTestCount": 1}
    require(actual["counts"] == counts and {key: summary[key] for key in counts} == counts
        and summary["result"] == "Passed" and summary["expectedFailures"] == 0
        and actual["actualCases"] == {METHODS[args.stage] + "()": "Passed"}, "exact_original_method_not_passed")
    command = actual["testCommand"]
    require(command["status"] == "PASS" and command["exitCode"] == 0
        and command["ownedProcessGroup"] == "ABSENT_ESRCH"
        and sha(root / "execute.log") == command["logSHA256"]
        and actual["diagnosticFailures"] == [] and actual["firstFailure"] is None,
        "original_command_or_cleanup_failure")
    require(actual["applicationBuilds"] == actual["nativeLibraryBuilds"] == actual["uiRunnerBuilds"] == 0
        and actual["ownedSimulatorDeleted"] is False
        and actual["ownedShutdownSimulatorRetainedForRecovery"] == actual["ownedSimulator"],
        "original_no_build_or_retention_scope_differs")
    devices = summary["devicesAndConfigurations"]
    require(len(devices) == 1 and devices[0]["device"]["deviceId"].upper() == actual["ownedSimulator"],
        "original_device_differs")
    private = root / "private-original-attachment-audit/attachments"
    manifest = load(private / "manifest.json")
    require(len(manifest) == 1 and manifest[0]["testIdentifier"] == METHODS[args.stage] + "()",
        "original_attachment_method_differs")
    by_phase = {}; observations = []; seen = set(); selected = []; before = []
    for attachment in manifest[0]["attachments"]:
        name = attachment["suggestedHumanReadableName"]; path = private / attachment["exportedFileName"]
        require(path.parent == private and path.resolve() == path, "attachment_path_alias")
        if path.suffix != ".json" or not name.startswith("native-semantic-anchor-"):
            continue
        require(path.name not in seen, "duplicate_attachment_file"); seen.add(path.name)
        value = load(path)
        require(value["schema"] == "any-semantic-anchor-native-rendered/v1"
            and value["state"] == "MATCHED" and value["mode"] == "read-only", "observation_shape")
        require(value["engineCalls"] == value["mutations"] == value["selectionChanges"] == 0,
            "observer_performed_actions")
        require(len(value["blocks"]) == 1 and value["nativeMarkCount"] == value["renderedMarkCount"]
            == len(value["blocks"][0]["nativeMarks"])
            and value["blocks"][0]["nativeMarks"] == value["blocks"][0]["renderedMarks"],
            "native_rendered_markers_differ")
        observations.append({"name": name, "file": path.name, "bytes": path.stat().st_size, "sha256": sha(path)})
        for phase in PHASES[args.stage]:
            if name.startswith("native-semantic-anchor-" + phase + "_"):
                require(phase not in by_phase, "duplicate_phase"); by_phase[phase] = value
        if name.startswith("native-semantic-anchor-actual-uikit-selected-range_"):
            selected.append(value)
        if name.startswith("native-semantic-anchor-actual-uikit-selection-before-reselection_"):
            before.append(value)
    require(set(by_phase) == set(PHASES[args.stage]), "original_required_phase_missing")
    expected_selections = 3 if args.stage == "semantic-anchor" else 4
    require(len(selected) == len(before) == expected_selections, "original_real_selection_witness_missing")
    for value in selected:
        block = value["blocks"][0]
        require(block["isFirstResponder"] is True and block["selectionLocation"] == 0
            and block["selectionLength"] == block["utf16Length"] and block["utf16Length"] in (6, 7),
            "actual_complete_uikit_selection_not_proven")
    first = next(iter(by_phase.values()))
    for value in by_phase.values():
        require((value["spaceSHA256"], value["objectSHA256"], value["blocks"][0]["blockSHA256"])
            == (first["spaceSHA256"], first["objectSHA256"], first["blocks"][0]["blockSHA256"]),
            "document_or_block_identity_changed")
    boundaries = anchor(by_phase) if args.stage == "semantic-anchor" else sources(by_phase)
    result = {"status": "PASS_INDEPENDENT_ORIGINAL_UI_ATTACHMENT_COMPARISON", "stage": args.stage,
        "sourceCommit": SOURCE, "nativeManifestSHA256": NATIVE, "method": METHODS[args.stage],
        "originalReceiptSHA256": args.receipt_sha256, "qualifierSHA256": sha(Path(__file__)),
        "privateAttachmentManifestSHA256": sha(private / "manifest.json"),
        "nativeRenderedComparisons": len(observations), "actualCompleteSelectionWitnesses": len(selected),
        "verifiedBoundaries": PHASES[args.stage], "boundaryResults": boundaries,
        "originalAttachments": observations, "testsExecutedByAudit": 0, "engineCallsByAudit": 0,
        "rawAccountDataPublished": False, "fullEAcceptance": False, "physicalDevice": "NOT_RUN"}
    with args.output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2); stream.write("\n")
    args.output.chmod(0o600)
    print(json.dumps({"status": result["status"], "observations": len(observations),
        "receiptSHA256": sha(args.output), "output": str(args.output)}))


if __name__ == "__main__":
    main()
