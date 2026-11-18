"""Bounded Hebrew/light/dark evidence after independently accepted T5 core UI.

This checks actual command readbacks, XCTest receipts and original attachments.
Screenshots remain subject to visual review; AX inspection is not VoiceOver.
"""
import json
import math
import re

import t5_native_ui_evidence as core

METHOD = "PinkhaT5NativeAcceptanceUITests/testHebrewRelatedRowsLongTitlesAndReadOnlyNavigation"
APPEARANCES = ("light", "dark")
STAGES = ("r08-related-rows", "r08-native-rtl-navigation", "r08-retained-unlinked-note", "r08-related-rows-after-return")
PASS = "R08_HEBREW_UI_PASS_VISUAL_REVIEW_PENDING"


def screenshot_labels(appearance):
    prefix = "t5-r08-he-" + appearance
    return [prefix + "-long-title-page", prefix + "-long-title-writing",
            prefix + "-native-rtl-navigation", prefix + "-retained-unlinked-note"]


def actual_setting(raw, expected, label):
    core.require(isinstance(raw, str) and raw.strip().lower() == expected,
                 "Actual simulator " + label + " differs or has an unreviewed representation")
    return raw.strip().lower()


def rectangle(value):
    core.require(isinstance(value, dict) and set(value) == {"x", "y", "width", "height"}
                 and all(type(v) in {int, float} and math.isfinite(v) for v in value.values())
                 and value["width"] > 0 and value["height"] > 0, "Invalid actual UI frame")
    return value


def validate_receipt(value, appearance, fixture, retained):
    core.require(appearance in APPEARANCES and type(value.get("protocolVersion")) is int
                 and value["protocolVersion"] == 1 and value.get("status") == "PASS"
                 and value.get("scope") == "r08-he-" + appearance, "Missing actual R08 method receipt")
    for key in ("token", "appSourceSHA", "runID", "spaceID"):
        core.require(value.get(key) == fixture[key], "R08 source/run/account fixture differs")
    core.require(value.get("requestedAppLanguage") == "he" and value.get("requestedAppearance") == appearance
                 and value.get("coverage") == "indexedTargetsOnly" and value.get("productLookupFlag") == "OFF"
                 and value.get("physicalDeviceAccepted") is False and value.get("voiceOverStatus") == "NOT_RUN"
                 and value.get("visualReviewStatus") == "PENDING" and value.get("dynamicTypeScope") == "fixed-large-only",
                 "R08 expanded its acceptance scope or requested another presentation")
    observations = value.get("observations", [])
    core.require(isinstance(observations, list) and [x.get("stage") for x in observations] == list(STAGES),
                 "R08 actual observation sequence is incomplete")
    before, opened, note, after = observations
    targets = {item["role"]: item for item in fixture["targets"]}
    rows = sorted(core.ROW_PREFIX + item["resultID"] for item in fixture["targets"])
    core.require(before.get("actualRows") == after.get("actualRows") == rows
                 and before.get("originObjectID") == after.get("originObjectID") == targets["writing"]["objectID"],
                 "R08 changed the current-Space baseline or used another origin")
    core.require(before.get("addNoteLabel") == "הוסף הערה למקור", "Actual source action is not Hebrew")
    actual = before.get("rows", [])
    core.require(isinstance(actual, list) and [x.get("role") for x in actual] == core.TARGET_ROLES,
                 "Missing/duplicate actual accessible related row")
    app = rectangle(before.get("appFrame"))
    for row in actual:
        target = targets[row["role"]]
        core.require(row.get("resultID") == target["resultID"] and core.nonempty(row.get("actualLabel"))
                     and target["title"] in row["actualLabel"] and row.get("hittable") is True
                     and row.get("enabled") is True, "R08 lost the complete title or reachable native row")
        frame = rectangle(row.get("frame"))
        core.require(frame["width"] >= 160 and 44 <= frame["height"] <= 160
                     and frame["x"] >= app["x"] - 1 and frame["y"] >= app["y"] - 1
                     and frame["x"] + frame["width"] <= app["x"] + app["width"] + 1
                     and frame["y"] + frame["height"] <= app["y"] + app["height"] + 1,
                     "Actual R08 row is clipped, unreachable or not compact at fixed Large size")
        if row["role"] in {"page", "writing"}:
            core.require(len(target["title"]) >= 160 and re.search("[א-ת]", target["title"])
                         and "T5" in target["title"], "The native long title does not exercise mixed Hebrew text")
    probe = fixture["presentationProbe"]
    core.require(opened.get("objectID") == probe["objectID"] == targets["page"]["objectID"]
                 and opened.get("blockID") == probe["blockID"] and opened.get("actualText") == probe["text"]
                 and opened.get("resultID") == targets["page"]["resultID"], "R08 did not navigate to the exact native Page/probe")
    direction = opened.get("actualDirectionLabel", "")
    core.require(isinstance(direction, str) and {"app-language-he", "swiftui-rtl", "navigation-rtl", "uikit-rtl", "content-rtl"}
                 <= set(direction.split(";")), "Actual App/editor language and direction differ")
    core.require(all(note.get(key) == retained[key] for key in ("objectID", "blockID", "actualText"))
                 and note.get("sourceChipExists") is False and type(note.get("sourceChipCount")) is int
                 and note["sourceChipCount"] == 0, "R08 changed/lost the fully unlinked core Note")
    return value


def read_receipt(directory, appearance, fixture, retained, forbidden_processes):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8-sig"))
    core.require(isinstance(manifest, list), "Unexpected R08 attachment manifest")
    selected = [x for x in manifest if x.get("testIdentifier", "").removesuffix("()") == METHOD]
    core.require(len(selected) == 1, "Exactly one original R08 method attachment entry required")
    case = selected[0]
    files = [directory / "manifest.json"] + [core.attachment_path(directory, x.get("exportedFileName"))
                                              for x in case.get("attachments", [])]
    path = core.named_attachment(case, directory, "t5-native-ui-r08-he-" + appearance + "-receipt", ".json")
    core.require(path.stat().st_size <= 64 * 1024, "R08 receipt exceeds its bound")
    receipt = validate_receipt(json.loads(path.read_text(encoding="utf-8-sig")), appearance, fixture, retained)
    records, pids = [], []
    for label in screenshot_labels(appearance):
        image = core.named_attachment(case, directory, label, ".png")
        with image.open("rb") as stream:
            signature = stream.read(8)
        core.require(1024 < image.stat().st_size <= 25 * 1024 * 1024 and signature == b"\x89PNG\r\n\x1a\n",
                     "Original R08 screenshot is absent/invalid")
        tree = core.named_attachment(case, directory, label + "-accessibility", ".txt")
        core.require(tree.stat().st_size <= 16 * 1024 * 1024, "R08 AX evidence exceeds its bound")
        text = tree.read_text(encoding="utf-8-sig")
        first = text.lstrip().splitlines()[0]
        pid = re.match(r"(?:Attributes:\s*)?Application,\s*(?:0x[0-9a-fA-F]+,\s*)?pid:\s*(\d+)", first)
        core.require(pid is not None and int(pid.group(1)) > 0, "Original R08 App process is absent")
        pids.append(int(pid.group(1)))
        if "-long-title-" in label:
            role = label.rsplit("-", 1)[-1]
            target = next(x for x in fixture["targets"] if x["role"] == role)
            core.require(core.ROW_PREFIX + target["resultID"] in text and target["title"] in text,
                         "Full native title/row identity is absent from original AX evidence")
        elif label.endswith("-native-rtl-navigation"):
            core.require("pinkha.stage1.body." + fixture["presentationProbe"]["blockID"] in text
                         and receipt["observations"][1]["actualDirectionLabel"] in text,
                         "Actual RTL body observations are absent from original AX evidence")
        else:
            core.require("pinkha.stage1.body." + retained["blockID"] in text and retained["actualText"] in text
                         and "torah-document-source-chip-" not in text,
                         "Retained core Note is absent or still has a source chip in original AX evidence")
        records.append(dict(label=label, image=image.name, image_sha256=core.digest(image),
                            accessibility=tree.name, accessibility_sha256=core.digest(tree), process_id=pids[-1]))
    core.require(len(set(pids)) == 1 and pids[0] not in forbidden_processes,
                 "R08 reused a prior App lifetime or changed processes within its single selection")
    return dict(receipt=receipt, process_id=pids[0], screenshot_records=records), sorted(set(files))
