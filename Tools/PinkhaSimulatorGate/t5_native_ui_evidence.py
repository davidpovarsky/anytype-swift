"""Strict evidence gates for the optional real T5 post-pair UI selection.

These controls validate receipts, identities and original XCTest attachments.
They do not create Native or UI acceptance from simulated test data.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil

PREPARATION = "TorahT5UIAcceptancePreparationTests/prepareFreshNativeUIFixture"
METHODS = {
    "related-targets": "PinkhaT5NativeAcceptanceUITests/testCurrentSpaceRowsAndExactBlockNavigation",
    "note-lifecycle": "PinkhaT5NativeAcceptanceUITests/testAddNoteEditOpenUnlinkAndRetainAfterRelaunch",
}
ROW_PREFIX = "torah-inspector-related-row-"
TARGET_ROLES = ["page", "note", "writing", "block", "quote"]
RELATED_STAGES = ["current-space-from-page", "current-space-from-note", "current-space-from-writing",
                  "block-control-offscreen", "block-opened-from-inspector",
                  "quote-control-offscreen", "quote-opened-from-inspector"]
NOTE_STAGES = ["note-created-and-edited", "note-visible-in-current-space", "note-opened-from-inspector",
               "note-unlinked", "unlinked-list-after-relaunch", "note-retained-after-relaunch"]
SCREENSHOTS = {
    "related-targets": ["t5-related-from-page", "t5-related-from-note", "t5-related-from-writing",
                        "t5-block-ordinary-entry-control", "t5-block-exact-native-target",
                        "t5-quote-ordinary-entry-control", "t5-quote-exact-native-target"],
    "note-lifecycle": ["t5-created-note-native-editor", "t5-note-opened-from-related-result", "t5-note-unlink-menu",
                       "t5-note-unlinked-current-results", "t5-source-results-after-relaunch",
                       "t5-unlinked-note-retained-and-editable"],
}
UUID = r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}"


def presentation_title(role, token):
    if role not in {"page", "writing"}:
        return "T5 UI " + role
    return ("כותרת עברית ארוכה למסמך " + role + " — "
            + "מקור קנוני והערות עם טקסט מעורב T5. " * 5 + token[:8])


def presentation_probe_text(token):
    return "פסקה עברית לקריאה בלבד עם טקסט מעורב T5 — " + token


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(128 * 1024), b""):
            value.update(data)
    return value.hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def is_hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_fixture(value, *, source, run_id, token, runtime, pair_report):
    keys = {"protocolVersion", "token", "appSourceSHA", "runID", "runtimeVersion", "preparationProcessID",
            "accountID", "spaceID", "foreignSpaceID", "accountRootPathSHA256", "providerID", "canonicalReference",
            "coverage", "limitations", "targets", "excluded", "presentationProbe", "productLookupFlag"}
    require(set(value) == keys and type(value.get("protocolVersion")) is int
            and value.get("protocolVersion") == 1, "Unexpected native UI fixture schema")
    require(value["appSourceSHA"] == source and value["runID"] == run_id and value["token"] == token,
            "Native UI fixture source/run/attempt differs")
    require(re.fullmatch(r"[0-9a-f]{40}", source) is not None and run_id.isdigit()
            and re.fullmatch(r"[0-9a-f]{32}", token) is not None, "Invalid source/run/attempt identity")
    require(value["runtimeVersion"] == runtime, "Preparation did not observe the exact actual r15 runtime")
    require(type(value["preparationProcessID"]) is int and value["preparationProcessID"] > 0,
            "Native preparation process identity is absent")
    for key, paired in [("accountID", "accountID"), ("spaceID", "spaceID"),
                        ("accountRootPathSHA256", "rootPathSHA256")]:
        require(nonempty(value[key]) and value[key] != pair_report[paired], "UI preparation reused the paired account or storage")
    require(is_hash(value["accountRootPathSHA256"]) and nonempty(value["foreignSpaceID"])
            and value["spaceID"] != value["foreignSpaceID"], "Fresh UI Space/root identity differs")
    require(value["providerID"] == "sefaria" and value["canonicalReference"] == "Genesis 1:1", "Canonical UI source differs")
    require(value["coverage"] == "indexedTargetsOnly" and value["limitations"] == ["indexFreshnessUnverified"]
            and value["productLookupFlag"] == "OFF", "UI fixture expanded its coverage or enabled product lookup")
    targets = value["targets"]
    require(isinstance(targets, list) and [item.get("role") for item in targets] == TARGET_ROLES,
            "Five ordered real native target roles are required")
    require(len({item.get("objectID") for item in targets}) == 5 and len({item.get("resultID") for item in targets}) == 5,
            "Native UI target identities are duplicated")
    for item in targets:
        for key in ["objectID", "typeKey", "associationID", "resultID"]:
            require(nonempty(item.get(key)), "Native UI target identity is missing")
        require(is_hash(item.get("canonicalSHA256")), "Canonical readback hash is absent")
        require(item.get("title") == presentation_title(item["role"], token), "Actual native presentation title differs")
        if item["role"] in {"block", "quote"}:
            require(all(nonempty(item.get(key)) for key in ["blockID", "blockText", "firstBlockID", "firstBlockText"]),
                    "Actual distant block/negative-control content is missing")
            require(len({item["objectID"], item["blockID"], item["firstBlockID"]}) == 3,
                    "Distant block identity is not distinct")
            require(item["blockText"] == "T5 native " + item["role"] + " target " + token,
                    "Native block fixture content differs")
        else:
            require(all(item.get(key) is None for key in ["blockID", "blockText", "firstBlockID", "firstBlockText"]),
                    "A document-level row unexpectedly uses a block target")
        identity = [value["spaceID"], item["objectID"], item.get("blockID") or ""]
        require(item["resultID"] == "|".join(str(len(part.encode("utf8"))) + ":" + part for part in identity),
                "Native result does not identify the exact Space/object/block")
    by_role = {item["role"]: item for item in targets}
    probe = value["presentationProbe"]
    require(isinstance(probe, dict) and set(probe) == {"objectID", "blockID", "text"}
            and probe["objectID"] == by_role["page"]["objectID"] and nonempty(probe["blockID"])
            and probe["blockID"] != probe["objectID"] and probe["text"] == presentation_probe_text(token),
            "Native Hebrew presentation probe identity/content differs")
    require(by_role["page"]["typeKey"] == by_role["block"]["typeKey"] == by_role["quote"]["typeKey"]
            and len({by_role[role]["typeKey"] for role in ["page", "note", "writing"]}) == 3,
            "Page, Note and writing type identity is ambiguous")
    excluded = value["excluded"]
    require(isinstance(excluded, list) and [item.get("reason") for item in excluded]
            == ["differentVerse", "differentProvider", "differentSpace"], "Three independent negative fixtures are required")
    require(len({item.get("objectID") for item in excluded}) == 3
            and not {item["objectID"] for item in targets}.intersection(item.get("objectID") for item in excluded),
            "Positive and excluded objects overlap")
    for item in excluded:
        require(nonempty(item.get("objectID")) and item.get("spaceID") ==
                (value["foreignSpaceID"] if item["reason"] == "differentSpace" else value["spaceID"]),
                "Negative fixture Space identity differs")
    return by_role


def validate_selection(summary, methods, expected, udid):
    normalized = {name.removesuffix("()"): result for name, result in methods.items()}
    require(len(methods) == len(expected) and normalized == {name: "Passed" for name in expected},
            "Actual named XCTest selection differs")
    require(all(type(summary.get(key)) is int for key in ["totalTestCount", "passedTests", "failedTests", "skippedTests"])
            and summary["totalTestCount"] == summary["passedTests"] == len(expected)
            and summary["failedTests"] == 0 and summary["skippedTests"] == 0,
            "Exact nonzero XCTest counts are required")
    devices = [entry.get("device", {}) for entry in summary.get("devicesAndConfigurations", [])]
    require(devices and all(entry.get("deviceId", "").lower() == udid.lower()
            and entry.get("architecture") == "arm64" and entry.get("osVersion", "").split(".")[0] == "27"
            for entry in devices), "Actual XCTest simulator/runtime/architecture differs")
    return {"passed": len(expected), "failed": 0, "skipped": 0, "methods": normalized, "devices": devices}


def validate_receipt(value, scope, fixture):
    require(scope in METHODS and type(value.get("protocolVersion")) is int and value.get("protocolVersion") == 1
            and value.get("status") == "PASS" and value.get("scope") == scope,
            "Selected UI method did not emit its successful actual receipt")
    for key in ["token", "appSourceSHA", "runID", "spaceID"]:
        require(value.get(key) == fixture[key], "UI receipt uses a different native fixture")
    require(value.get("coverage") == "indexedTargetsOnly" and value.get("productLookupFlag") == "OFF"
            and value.get("physicalDeviceAccepted") is False, "UI receipt expanded its acceptance scope")
    observations = value.get("observations", [])
    expected_stages = RELATED_STAGES if scope == "related-targets" else NOTE_STAGES
    require([item.get("stage") for item in observations] == expected_stages, "Actual UI observation order is incomplete")
    targets = {item["role"]: item for item in fixture["targets"]}
    rows = sorted(ROW_PREFIX + item["resultID"] for item in fixture["targets"])
    if scope == "related-targets":
        for index, role in enumerate(["page", "note", "writing"]):
            require(observations[index].get("originObjectID") == targets[role]["objectID"]
                    and observations[index].get("actualRows") == rows, "Current-Space UI results differ by origin document")
        for index, role in [(3, "block"), (5, "quote")]:
            before, after = observations[index:index + 2]
            target = targets[role]
            require(before.get("objectID") == after.get("objectID") == target["objectID"]
                    and before.get("blockID") == after.get("blockID") == target["blockID"], "UI reached a different block/object")
            require(before.get("firstBlockID") == target["firstBlockID"] and before.get("targetHittable") is False,
                    "A real offscreen negative control is required")
            require(after.get("targetHittable") is True and after.get("actualText") == target["blockText"]
                    and after.get("resultID") == target["resultID"], "Inspector result did not expose its exact native block")
    else:
        created, linked, opened, unlinked, reopened, retained = observations
        note = created.get("objectID")
        block = created.get("blockID")
        require(nonempty(note) and nonempty(block) and note != block
                and note not in {item["objectID"] for item in fixture["targets"] + fixture["excluded"]},
                "The UI must create a distinct native Note")
        require(all(item.get("objectID") == note for item in [linked, opened, unlinked, retained])
                and opened.get("blockID") == retained.get("blockID") == block, "Note identity changed during the UI lifecycle")
        expected_text = "T5 Note edited through native UI " + fixture["token"]
        require(created.get("actualText") == retained.get("actualText") == expected_text,
                "Actual user-typed Note content was not preserved")
        result_id = linked.get("resultID")
        require(nonempty(result_id) and opened.get("resultID") == result_id
                and linked.get("actualRows") == sorted(rows + [ROW_PREFIX + result_id]), "New Note did not appear exactly once")
        identity = [fixture["spaceID"], note, ""]
        require(result_id == "|".join(str(len(part.encode("utf8"))) + ":" + part for part in identity),
                "The observed Note result identifies another object")
        require(unlinked.get("actualRows") == reopened.get("actualRows") == rows,
                "Unlink or relaunch retained a stale related row")
        require(retained.get("sourceChipExists") is False and retained.get("editable") is True,
                "The retained Note is linked again, missing or not editable")
    return value


def attachment_path(directory, name):
    require(isinstance(name, str) and name and Path(name).name == name and name not in {".", ".."}
            and "/" not in name and "\\" not in name, "Attachment path is not a single safe basename")
    path = directory / name
    require(path.is_file() and not path.is_symlink() and path.resolve().parent == directory.resolve(),
            "Original attachment escaped its owned export directory")
    return path


def named_attachment(case, directory, label, extension):
    exported = re.compile(re.escape(label) + r"_\d+_" + UUID + re.escape(extension))
    matches = [item for item in case.get("attachments", []) if item.get("suggestedHumanReadableName") == label
               or exported.fullmatch(item.get("suggestedHumanReadableName", ""))]
    require(len(matches) == 1, "Exactly one original named UI attachment is required")
    return attachment_path(directory, matches[0].get("exportedFileName"))


def read_ui_receipts(directory, fixture):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8-sig"))
    require(isinstance(manifest, list), "Unexpected XCTest attachment manifest")
    cases = {}
    files = [directory / "manifest.json"]
    for case in manifest:
        method = case.get("testIdentifier", "").removesuffix("()")
        if method not in METHODS.values():
            continue
        require(method not in cases, "Duplicate selected UI method attachment entry")
        cases[method] = case
        files.extend(attachment_path(directory, item.get("exportedFileName")) for item in case.get("attachments", []))
    require(set(cases) == set(METHODS.values()), "Selected UI methods are absent from original attachments")
    receipts, processes, records = {}, {}, []
    for scope, method in METHODS.items():
        case = cases[method]
        path = named_attachment(case, directory, "t5-native-ui-" + scope + "-receipt", ".json")
        require(path.stat().st_size <= 64 * 1024, "UI receipt exceeds its bounded schema")
        receipts[scope] = validate_receipt(json.loads(path.read_text(encoding="utf-8-sig")), scope, fixture)
        pids = []
        for label in SCREENSHOTS[scope]:
            screenshot = named_attachment(case, directory, label, ".png")
            with screenshot.open("rb") as stream:
                signature = stream.read(8)
            require(1024 < screenshot.stat().st_size <= 25 * 1024 * 1024 and signature == b"\x89PNG\r\n\x1a\n",
                    "Named actual UI screenshot is missing or invalid")
            tree = named_attachment(case, directory, label + "-accessibility", ".txt")
            require(tree.stat().st_size <= 16 * 1024 * 1024, "Accessibility evidence exceeds its bound")
            header = tree.read_text(encoding="utf-8-sig").lstrip().splitlines()[0]
            match = re.match(r"(?:Attributes:\s*)?Application,\s*(?:0x[0-9a-fA-F]+,\s*)?pid:\s*(\d+)", header)
            require(match is not None and int(match.group(1)) > 0, "Actual UI target process identity is missing")
            pids.append(int(match.group(1)))
            records.append({"label": label, "image": screenshot.name, "image_sha256": digest(screenshot),
                            "accessibility": tree.name, "accessibility_sha256": digest(tree), "process_id": pids[-1]})
        if scope == "related-targets":
            require(len(set(pids)) == 1, "Related-result UI unexpectedly changed processes")
        else:
            require(len(set(pids[:4])) == 1 and len(set(pids[4:])) == 1 and pids[0] != pids[4],
                    "The Note UI must prove a real separate relaunch process")
        processes[scope] = pids
    require(len(set(processes["related-targets"] + processes["note-lifecycle"] + [fixture["preparationProcessID"]])) == 4,
            "Preparation and three observed UI lifetimes must be distinct")
    return {"receipts": receipts, "screenshot_records": records, "actual_processes": processes}, sorted(set(files))


def publish_evidence(private, public, allowed, *, secret_record, token, contains_secret):
    require(secret_record.get("token") == token and all(nonempty(secret_record.get(key)) for key in ["mnemonic", "accountKey"]),
            "Full fresh-account credential inventory is required before publication")
    require(not public.exists(), "Refuse stale public UI evidence")
    needles = [secret_record[key].encode(encoding) for key in ["mnemonic", "accountKey"]
               for encoding in ["utf8", "utf-16-le", "utf-16-be"]]
    candidates = []
    for path in sorted(set(allowed)):
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(private.resolve()),
                "UI evidence escaped its owned private directory")
        relative = path.relative_to(private)
        require(not any(part == "secrets.json" or part.endswith(".xcresult") or part.endswith(".app")
                        for part in relative.parts), "Account data or raw test bundle is not publishable")
        require(path.stat().st_size <= 200 * 1024 * 1024, "Original evidence file exceeds its bound")
        require(not contains_secret(path, needles), "Fresh disposable credentials found; all UI evidence withheld")
        candidates.append((path, public / relative))
    require(sum(source.stat().st_size for source, _ in candidates) <= 512 * 1024 * 1024,
            "Original UI evidence exceeds the upload bound")
    # Validate the entire allowlist before creating the first public directory.
    for source, target in candidates:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return {"status": "PASS", "scanned_complete_credential_encodings": 3,
            "files": [{"path": str(target.relative_to(public)), "sha256": digest(target), "bytes": target.stat().st_size}
                      for _, target in candidates],
            "raw_xcresult_uploaded": False, "account_data_uploaded": False, "secrets_uploaded": False}
