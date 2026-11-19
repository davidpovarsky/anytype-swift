"""Negative parser/controller controls only; no synthetic Apple/visual acceptance."""
import copy
import json
from pathlib import Path
import plistlib
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_t5_native_ui as runner
import t5_native_ui_evidence as core
import t5_native_ui_r08 as r08
import test_t5_native_ui as baseline


def retained_note(fixture):
    return {key: baseline.receipts(fixture)["note-lifecycle"]["observations"][-1][key]
            for key in ("objectID", "blockID", "actualText")}


def receipt(fixture, appearance):
    target = {x["role"]: x for x in fixture["targets"]}
    rows = sorted(core.ROW_PREFIX + x["resultID"] for x in fixture["targets"])
    probe = fixture["presentationProbe"]
    return {"protocolVersion": 1, "status": "PASS", "scope": "r08-he-" + appearance,
        **{key: fixture[key] for key in ("token", "appSourceSHA", "runID", "spaceID")},
        "requestedAppLanguage": "he", "requestedAppearance": appearance, "coverage": "indexedTargetsOnly",
        "productLookupFlag": "OFF", "physicalDeviceAccepted": False, "voiceOverStatus": "NOT_RUN",
        "visualReviewStatus": "PENDING", "dynamicTypeScope": "fixed-large-only", "observations": [
            {"stage": r08.STAGES[0], "originObjectID": target["writing"]["objectID"], "actualRows": rows,
             "addNoteLabel": "הוסף הערה למקור", "appFrame": {"x": 0, "y": 0, "width": 1024, "height": 1366},
             "rows": [{"role": x["role"], "resultID": x["resultID"], "actualLabel": x["title"],
                       "hittable": True, "enabled": True,
                       "frame": {"x": 200, "y": 300, "width": 500, "height": 100}} for x in fixture["targets"]]},
            {"stage": r08.STAGES[1], "objectID": probe["objectID"], "blockID": probe["blockID"],
             "actualText": probe["text"], "resultID": target["page"]["resultID"],
             "actualDirectionLabel": "app-language-he;swiftui-rtl;navigation-rtl;uikit-rtl;content-rtl"},
            {"stage": r08.STAGES[2], **retained_note(fixture), "sourceChipExists": False, "sourceChipCount": 0},
            {"stage": r08.STAGES[3], "originObjectID": target["writing"]["objectID"], "actualRows": rows}]}


def attachments(directory, fixture, appearance, pid):
    directory.mkdir(parents=True)
    value = receipt(fixture, appearance)
    entries = []
    def add(label, suffix, data):
        path = directory / (str(len(entries)) + suffix)
        path.write_bytes(data)
        entries.append(dict(suggestedHumanReadableName=label, exportedFileName=path.name))
    add("t5-native-ui-r08-he-" + appearance + "-receipt", ".json", json.dumps(value).encode())
    for index, label in enumerate(r08.screenshot_labels(appearance)):
        add(label, ".png", b"\x89PNG\r\n\x1a\n" + b"PARSER_CONTROL_NOT_A_SCREENSHOT" * 100)
        text = f"Application, 0x123, pid: {pid}\nSynthetic parser control only\n"
        if index < 2:
            role = "page" if index == 0 else "writing"
            target = next(x for x in fixture["targets"] if x["role"] == role)
            text += core.ROW_PREFIX + target["resultID"] + "\n" + target["title"]
        elif index == 2:
            text += "pinkha.stage1.body." + fixture["presentationProbe"]["blockID"] + "\n" + value["observations"][1]["actualDirectionLabel"]
        else:
            note = retained_note(fixture)
            text += "pinkha.stage1.body." + note["blockID"] + "\n" + note["actualText"]
        add(label + "-accessibility", ".txt", text.encode())
    manifest = [dict(testIdentifier=r08.METHOD + "()", attachments=entries)]
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return manifest


class R08EvidenceControls(unittest.TestCase):
    def test_separate_hebrew_receipts_keep_actual_identity_and_acceptance_boundaries(self):
        fixture = baseline.fixture()
        for appearance in r08.APPEARANCES:
            with self.subTest(appearance=appearance):
                value = receipt(fixture, appearance)
                self.assertIs(r08.validate_receipt(value, appearance, fixture, retained_note(fixture)), value)

    def test_requested_language_is_insufficient_without_every_actual_direction(self):
        fixture = baseline.fixture()
        for field in ["app-language-he", "swiftui-rtl", "navigation-rtl", "uikit-rtl", "content-rtl"]:
            with self.subTest(field=field):
                value = receipt(fixture, "light")
                value["observations"][1]["actualDirectionLabel"] = value["observations"][1]["actualDirectionLabel"].replace(field, "unrecorded")
                with self.assertRaises(ValueError): r08.validate_receipt(value, "light", fixture, retained_note(fixture))

    def test_visual_voiceover_physical_and_dynamic_type_claims_cannot_expand(self):
        fixture = baseline.fixture()
        for key, bad in [("voiceOverStatus", "PASS"), ("visualReviewStatus", "PASS"), ("physicalDeviceAccepted", True),
                         ("dynamicTypeScope", "all-sizes"), ("coverage", "spaceWide"), ("requestedAppearance", "dark")]:
            with self.subTest(key=key):
                value = receipt(fixture, "light"); value[key] = bad
                with self.assertRaises(ValueError): r08.validate_receipt(value, "light", fixture, retained_note(fixture))

    def test_complete_titles_compact_frames_and_hit_targets_are_required(self):
        fixture = baseline.fixture()
        mutations = [lambda row: row.update(actualLabel=row["actualLabel"][:30]),
                     lambda row: row.update(enabled=False), lambda row: row.update(hittable=False),
                     lambda row: row["frame"].update(height=161), lambda row: row["frame"].update(height=43),
                     lambda row: row["frame"].update(width=159), lambda row: row["frame"].update(x=-10),
                     lambda row: row["frame"].update(y=1300), lambda row: row["frame"].update(height=float("nan")),
                     lambda row: row["frame"].update(width=True)]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                value = receipt(fixture, "dark"); mutate(value["observations"][0]["rows"][0])
                with self.assertRaises(ValueError): r08.validate_receipt(value, "dark", fixture, retained_note(fixture))

    def test_read_only_baseline_note_and_navigation_identity_cannot_change(self):
        fixture = baseline.fixture()
        mutations = [lambda v: v["observations"][0]["actualRows"].pop(),
                     lambda v: v["observations"][3].update(originObjectID="other-object"),
                     lambda v: v["observations"][1].update(blockID="other-block"),
                     lambda v: v["observations"][1].update(actualText="rewritten"),
                     lambda v: v["observations"][2].update(sourceChipExists=True),
                     lambda v: v["observations"][2].update(sourceChipCount=1),
                     lambda v: v["observations"][2].update(sourceChipCount=True),
                     lambda v: v["observations"][2].pop("sourceChipCount"),
                     lambda v: v["observations"][2].update(actualText="changed core Note"),
                     lambda v: v["observations"][2].update(objectID="another Note")]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                value = receipt(fixture, "light"); mutate(value)
                with self.assertRaises(ValueError): r08.validate_receipt(value, "light", fixture, retained_note(fixture))

    def test_original_attachments_require_complete_ax_content_and_new_same_process(self):
        fixture = baseline.fixture()
        for mutation in ("none", "old-pid", "different-pid", "title", "direction", "note", "missing-image", "localized-chip"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp) / "attachments"; manifest = attachments(directory, fixture, "light", 104)
                entries = manifest[0]["attachments"]
                if mutation == "different-pid":
                    p = directory / entries[2]["exportedFileName"]; p.write_text(p.read_text().replace("pid: 104", "pid: 105"))
                elif mutation in {"title", "direction", "note"}:
                    index = {"title": 2, "direction": 6, "note": 8}[mutation]
                    p = directory / entries[index]["exportedFileName"]
                    p.write_text("Application, 0x123, pid: 104\nmissing actual target content")
                elif mutation == "missing-image": (directory / entries[1]["exportedFileName"]).unlink()
                elif mutation == "localized-chip":
                    # A receipt saying false cannot hide an actual Hebrew chip.
                    p = directory / entries[8]["exportedFileName"]
                    p.write_text(p.read_text() + "\nButton, identifier: torah-document-source-chip-revived, label: בראשית א:א\n")
                forbidden = {100, 101, 102, 103} | ({104} if mutation == "old-pid" else set())
                if mutation == "none":
                    report, files = r08.read_receipt(directory, "light", fixture, retained_note(fixture), forbidden)
                    self.assertEqual(report["process_id"], 104); self.assertEqual(len(report["screenshot_records"]), 4)
                    self.assertEqual(len(files), 10)
                else:
                    with self.assertRaises(ValueError): r08.read_receipt(directory, "light", fixture, retained_note(fixture), forbidden)

    def test_simulator_readback_must_be_exact_actual_setting(self):
        self.assertEqual(r08.actual_setting(" Dark\n", "dark", "appearance"), "dark")
        for raw in ["light", "requested dark", "", "dark\nlight", None]:
            with self.subTest(raw=raw), self.assertRaises(ValueError): r08.actual_setting(raw, "dark", "appearance")

    def test_ui_selection_cannot_inherit_or_expand_the_two_core_methods(self):
        for version in (1, 2):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp); target = {"BlueprintName": "PinkhaStage1AcceptanceUITests",
                    "TestBundlePath": "__TESTROOT__/Runner.xctest", "OnlyTestIdentifiers": list(core.METHODS.values())}
                value = {"UITests": target} if version == 1 else {"TestConfigurations": [{"TestTargets": [target]}]}
                original = directory / "original.xctestrun"; original.write_bytes(plistlib.dumps(value)); before = original.read_bytes()
                selected, filters = runner.selected_configuration(original, "PinkhaStage1AcceptanceUITests", [r08.METHOD], {},
                    SimpleNamespace(inject=lambda *args: None))
                self.assertEqual(filters, [r08.METHOD]); self.assertEqual(original.read_bytes(), before)
                data = plistlib.loads(selected.read_bytes())
                target = data["UITests"] if version == 1 else data["TestConfigurations"][0]["TestTargets"][0]
                self.assertEqual(target["OnlyTestIdentifiers"], [r08.METHOD]); self.assertEqual(target["SkipTestIdentifiers"], [])

    def test_two_selections_keep_core_receipt_and_propagate_failure_cancel_and_readback_mismatch(self):
        for mode in ("pass", "relocate", "readback", "cancel", "ui-fail", "reused-pid", "fixture-change", "credentials-change", "missing-store", "carrier-change"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                private = Path(temp) / "private"; private.mkdir(); container = Path(temp) / "container"
                fixture = baseline.fixture(); fixture_path = container / "Library/Application Support/pinkha-t5-native-ui-fixture.json"
                fixture_path.parent.mkdir(parents=True); fixture_path.write_text(json.dumps(fixture)); calls = []
                (container / runner.NATIVE_ROOT).mkdir(parents=True)
                secret_path = container / runner.UI_SECRETS; secret_path.parent.mkdir()
                secret_path.write_text(json.dumps(dict(token=baseline.TOKEN, mnemonic="synthetic-phrase", accountKey="synthetic-key")))
                core_path = private / "core-result.json"; core_path.write_text('{"status":"CORE_PASS"}'); core_hash = core.digest(core_path)
                observed = {"receipts": baseline.receipts(fixture), "actual_processes": {"related-targets": [101], "note-lifecycle": [102, 103]}}
                built = baseline.build(); built["app"] = str(Path(temp) / "App.app")
                def write(path, value): path.write_text(json.dumps(value))
                def command(argv, name):
                    path = private / (name + ".log")
                    value = "large" if argv[-1] == "content_size" else "dark" if name.startswith("r08-he-dark") else "light"
                    if mode == "readback" and name.endswith("appearance-after"): value = "dark"
                    path.write_text(value); calls.append(("command", argv)); return {}, path
                def select(**kwargs):
                    nonlocal container
                    self.assertEqual(kwargs["selections"], [r08.METHOD]); self.assertEqual(core.digest(core_path), core_hash)
                    env = kwargs["environment"]; self.assertEqual(env["PINKHA_UI27_APP_LANGUAGE"], "he")
                    self.assertEqual(json.loads(env["PINKHA_T5_R08_RETAINED_NOTE_JSON"]), retained_note(fixture))
                    if mode == "cancel": raise KeyboardInterrupt()
                    if mode == "ui-fail": raise ValueError("Actual selected XCTest failed")
                    appearance = env["PINKHA_T5_UI_APPEARANCE"]
                    pid = 101 if mode == "reused-pid" else 104 if appearance == "light" else 105
                    attachments(kwargs["directory"] / "attachments", fixture, appearance, pid)
                    if mode == "fixture-change": fixture_path.write_text("{}")
                    if mode == "credentials-change": secret_path.write_text('{"token":"other","mnemonic":"other","accountKey":"other"}')
                    if mode == "missing-store": (container / runner.NATIVE_ROOT).rmdir()
                    if mode == "relocate":
                        relocated = container.with_name("container-" + appearance)
                        container.rename(relocated); container = relocated
                    calls.append(("selection", appearance)); return {"passed": 1, "failed": 0, "skipped": 0}
                pair = SimpleNamespace(write=write, app_container=lambda udid, kind: container)
                ui = SimpleNamespace(code_carriers=lambda path: {"sha256": "wrong" if mode == "carrier-change" else built["code_sha256"]})
                with patch.object(runner, "select_tests", side_effect=select):
                    args = dict(private=private, app=Path(temp), build=built, container=container, ui_udid=baseline.UDID,
                        configuration=Path(temp) / "original.xctestrun", environment={}, fixture=fixture,
                        observed=observed, pair=pair, ui=ui, method_results=None, command=command)
                    if mode in ("pass", "relocate"):
                        result = runner.run_r08(**args); self.assertEqual(result["status"], r08.PASS)
                        self.assertEqual([x[1] for x in calls if x[0] == "selection"], ["light", "dark"])
                        self.assertEqual(result["actual_counts"]["ui_method_executions"], 2)
                    else:
                        with self.assertRaises(KeyboardInterrupt if mode == "cancel" else ValueError): runner.run_r08(**args)
                self.assertEqual(core.digest(core_path), core_hash)
                result = json.loads((private / "r08-result.json").read_text())
                self.assertEqual(result["status"], r08.PASS if mode in ("pass", "relocate") else "CANCELLED" if mode == "cancel" else "FAIL")


if __name__ == "__main__":
    unittest.main()
