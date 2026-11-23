#!/usr/bin/env python3
"""Exact source review for retaining the original Any native acceptance subset."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = "07c3568f9f9cf4044dd81163cd374d4ad35330cb"
REVIEW = "Tools/AnyEnginePort/reviews/native-ui-continuation-450382-sources.json"
TEST = "NativeApp/UITests/NativeLaunchTests.swift"
PROJECT = "NativeApp/AnyNative.xcodeproj/project.pbxproj"
PROVIDER = "Tools/AnyEngineValidation/HanlinProviderFixture/fixture.py"
PROVIDER_SHA = "afe281d0dca77d47d672d182c156d9ce5ec5a7c9a7644819515c546473d3c714"
PROTECTED = ("Modules", "NativeApp", "Package.resolved", "Tools/Hanlin")
FAILED_NAMES = (
    "testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType",
    "testExplicitHebrewDirectionAndAlignmentSurviveColdReopen",
    "testHierarchyDragIntoFolderPersistsAfterColdReopen",
    "testSourceDragIntoNativeEditorPreservesTargetAndColdReopens",
    "testTopicAndWordLinksDriveDerivedRelatedDocumentsAfterColdReopen",
    "testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen",
)
FILES_NAME = "testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies"
HISTORY_NAME = "testSavedHebrewVersionsRemainReadOnlyAcrossCloseBackgroundAndColdReopen"
HANLIN_HELPER = "configureHanlinThroughNormalFields"
HANLIN_INPUT_HELPER = "hanlinComposerInput"
HANLIN_SEND_HELPER = "sendHanlinPrompt"
LIBRARY_VIEW = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryView.swift"
HISTORY_PATHS = frozenset({
    "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeHistoryReader.swift",
    "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/NativeHistoryReaderTests.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeHistoryPresentation.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeHistoryView.swift",
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeHistoryPresentationTests.swift",
    "NativeApp/UITests/NativeHistoryTests.swift",
})
SCOPES = {
    TEST: "failed_journey_controllers_only",
    LIBRARY_VIEW: "inactive_hierarchy_drag_label_owner",
    PROJECT: "new_history_ui_test_target_registration",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift": "alignment_picker_and_inactive_history_presentation",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativePropertiesView.swift": "related_result_accessibility_only",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeArchiveTransfer.swift": "inactive_archive_directory_and_separate_presenters",
    "Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/PinkhaHanlinChatView.swift": "connection_field_accessibility_only",
    **{path: "unexecuted_readonly_history" for path in HISTORY_PATHS},
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def git(*args, root=ROOT):
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE)


def source(commit, path, root=ROOT):
    return git("show", commit + ":" + path, root=root)


def source_tree(commit, root=ROOT):
    result = {}
    for row in git("ls-tree", "-rz", commit, "--", *PROTECTED, root=root).split(b"\0"):
        if not row:
            continue
        header, name = row.split(b"\t", 1)
        mode, kind, identity = header.decode("ascii").split()
        require(kind == "blob" and mode in {"100644", "100755"}, "nonregular_protected_source")
        result[name.decode("utf-8")] = identity
    require(TEST in result and len(result) > 100, "incomplete_native_product_source_closure")
    return result


def declaration(raw, name):
    # The reviewed file uses four-space class members and four-space closing
    # braces. Exact full-file hashes below freeze this bounded source grammar.
    matches = list(re.finditer(rb"^    (?:private )?func " + name.encode() + rb"\(", raw, re.M))
    require(len(matches) == 1, "one_reviewed_declaration_required_" + name)
    start = matches[0].start()
    end = raw.find(b"\n    }\n", matches[0].end())
    require(end >= 0, "unterminated_reviewed_declaration_" + name)
    return start, end + len(b"\n    }\n")


def verify_test_declarations(before, after):
    masks = (*FAILED_NAMES, FILES_NAME, HANLIN_HELPER, HANLIN_INPUT_HELPER)
    facts = []
    ownership = {
        HANLIN_HELPER: (FAILED_NAMES[-1],),
        HANLIN_INPUT_HELPER: (HANLIN_HELPER, HANLIN_SEND_HELPER),
        HANLIN_SEND_HELPER: (FAILED_NAMES[-1],),
    }
    for raw in (before, after):
        for helper, callers in ownership.items():
            own = declaration(raw, helper)
            spans = [declaration(raw, name) for name in callers]
            occurrences = [m.start() for m in re.finditer(helper.encode() + rb"\s*\(", raw)]
            require(sum(own[0] <= point < own[1] for point in occurrences) == 1
                    and all(any(a <= point < b for a, b in [own, *spans]) for point in occurrences)
                    and all(any(a <= point < b for point in occurrences) for a, b in spans),
                    "hanlin_helper_is_not_exclusive_to_failed_method_" + helper)
    def masked(raw):
        for name in masks:
            start, end = declaration(raw, name)
            raw = raw[:start] + ("    // REVIEWED " + name + "\n").encode() + raw[end:]
        return raw
    require(masked(before) == masked(after), "retained_methods_or_common_helpers_changed")
    for name in masks:
        bstart, bend = declaration(before, name)
        astart, aend = declaration(after, name)
        facts.append({"declaration": name, "beforeSHA256": sha(before[bstart:bend]),
                      "afterSHA256": sha(after[astart:aend])})
    return {"unchangedRemainderSHA256": sha(masked(before)), "reviewedDeclarations": facts,
            "retainedEntryQuoteAndCommonHelpersByteIdentical": True,
            "changedPrivateHelperUniqueCaller": FAILED_NAMES[-1]}


def verify_hierarchy_drag_scope(before, after):
    """Reverse only the exact label/owner relocation; preserve the complete row."""
    label = b'            // Keep the drag source on the label, independently of the Button\'s\n            // context-menu interaction. Include the row\'s open spacer area.\n            .contentShape(Rectangle())\n            .draggable("pinkha-any-node|\\(model.session.workspace.spaceID)|\\(item.objectID)")\n'
    drop = b'        .dropDestination(for: String.self) { payloads, _ in\n'
    draggable = b'        .draggable("pinkha-any-node|\\(model.session.workspace.spaceID)|\\(item.objectID)")\n'
    require(after.count(label) == 1 and after.count(drop) == 1,
            "hierarchy_drag_label_scope_not_exact")
    restored = after.replace(label, b"").replace(drop, draggable + drop)
    require(restored == before, "hierarchy_drag_changed_context_drop_or_other_source")
    return {"scope": "hierarchyRow drag owner only", "exactReversalMatchesOriginalFile": True,
            "contextMenuDropAdmissionNavigationAndNativeWritesByteIdentical": True,
            "retainedJourneysDoNotPerformThisDrag": True}


def verify_history_registration(before, after):
    edits = (
        (b"", b"  A10000000000000000000005 = {isa = PBXBuildFile; fileRef = A20000000000000000000006; };\n"),
        (b"", b'  A20000000000000000000006 = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = UITests/NativeHistoryTests.swift; sourceTree = "<group>"; };\n'),
        (b"A20000000000000000000003, B30000000000000000000001",
         b"A20000000000000000000003, A20000000000000000000006, B30000000000000000000001"),
        (b"A40000000000000000000004 = {isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = (A10000000000000000000003);",
         b"A40000000000000000000004 = {isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = (A10000000000000000000003, A10000000000000000000005);"),
    )
    restored = after
    for old, new in edits:
        require(restored.count(new) == 1, "history_ui_registration_not_exact")
        restored = restored.replace(new, old)
    require(restored == before, "production_target_or_unrelated_project_setting_changed")
    return {"exactRegistrationEdits": 4, "productionTargetsAndSettingsByteIdentical": True}


def verify_maps(before, after, review, read_before, read_after):
    require(set(review) == {"schemaVersion", "producerCommit", "historyIncluded", "reviewedChanges"} and
            type(review["schemaVersion"]) is int and review["schemaVersion"] == 1 and
            review["producerCommit"] == PRODUCER and review["historyIncluded"] is True,
            "source_review_contract")
    entries = review["reviewedChanges"]
    require(isinstance(entries, list) and len(entries) == len(SCOPES), "complete_fixed_source_review_required")
    paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
    require(len(paths) == len(entries) == len(set(paths)) and set(paths) == set(SCOPES),
            "unreviewable_or_duplicate_source_change")
    changed = {path for path in before.keys() | after.keys() if before.get(path) != after.get(path)}
    require(changed == set(paths), "unexpected_source_or_dependency_change")
    for entry in entries:
        path = entry["path"]
        require(set(entry) == {"path", "beforeSHA256", "afterSHA256", "beforeGitBlob", "afterGitBlob", "scope", "declarations", "reason"} and
                entry["scope"] == SCOPES[path] and isinstance(entry["reason"], str) and len(entry["reason"]) >= 80 and
                isinstance(entry["declarations"], list) and entry["declarations"] and
                all(isinstance(value, str) and value.strip() for value in entry["declarations"]),
                "incomplete_bounded_source_review_" + path)
        old = read_before(path) if path in before else None
        new = read_after(path)
        require((old is None) == (path in HISTORY_PATHS), "history_addition_or_existing_source_changed")
        require(entry["beforeSHA256"] == (sha(old) if old is not None else None) and
                entry["beforeGitBlob"] == before.get(path) == (blob(old) if old is not None else None) and
                entry["afterSHA256"] == sha(new) and entry["afterGitBlob"] == after[path] == blob(new),
                "reviewed_source_bytes_changed_" + path)
    tests = verify_test_declarations(read_before(TEST), read_after(TEST))
    registration = verify_history_registration(read_before(PROJECT), read_after(PROJECT))
    drag = verify_hierarchy_drag_scope(read_before(LIBRARY_VIEW), read_after(LIBRARY_VIEW))
    return {"producerClosureSHA256": canonical(before), "consumerClosureSHA256": canonical(after),
            "unchangedProtectedFileCount": len(set(before) & set(after)) - len(changed - HISTORY_PATHS),
            "reviewedSourceChanges": entries, "testDeclarationProof": tests,
            "historyTargetRegistration": registration, "inactiveHierarchyDragProof": drag,
            "claim": "Original execution remains at its original sources; exact reviewed presentation additions are not described as executed or byte-identical."}


def verify_worktree(root=ROOT):
    paths = (*PROTECTED, PROVIDER, "Tools/AnyEnginePort", ".github/workflows/pinkha-any-engine-port.yml")
    tracked = [name.decode("utf-8") for name in
               git("diff", "--name-only", "-z", "HEAD", "--", *paths, root=root).split(b"\0") if name]
    untracked = [name.decode("utf-8") for name in
                 git("ls-files", "--others", "--exclude-standard", "-z", "--", *paths, root=root).split(b"\0") if name]
    # Bytecode is not exempt. The workflow prevents its creation; an existing
    # cache or any other unreviewed source still fails this admission fence.
    if tracked or untracked:
        raise ValueError("consumer_source_worktree_not_clean " + json.dumps({
            "trackedCount": len(tracked), "untrackedCount": len(untracked),
            "tracked": tracked[:64], "untracked": untracked[:64]}, sort_keys=True))


def verify_sources(consumer, root=ROOT):
    require(git("rev-parse", "HEAD", root=root).decode().strip() == consumer, "consumer_checkout_mismatch")
    raw = (root / REVIEW).read_bytes()
    review = json.loads(raw)
    before, after = source_tree(PRODUCER, root), source_tree(consumer, root)
    require(len(before) == 3594 and canonical(before) ==
            "c7975db2eeea07096998e835da0132af873a4ed693cc9d474492943a00e96b41",
            "original_product_dependency_closure_changed")
    proof = verify_maps(before, after, review,
                        lambda path: source(PRODUCER, path, root), lambda path: source(consumer, path, root))
    require(sha(source(PRODUCER, PROVIDER, root)) == PROVIDER_SHA and
            sha(source(consumer, PROVIDER, root)) == PROVIDER_SHA, "finite_provider_fixture_changed")
    verify_worktree(root)
    return {**proof, "reviewSHA256": sha(raw), "unchangedProviderFixtureSHA256": PROVIDER_SHA}
