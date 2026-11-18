"""Negative controls only; synthetic metadata never constitutes Apple acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_t5_native_ui as runner
import t5_native_ui_evidence as gates

SOURCE = "a" * 40
TOKEN = "b" * 32
RUN = "123456"
RUNTIME = "actual-reviewed-r15-version"
FLAGS = ["test-only-reviewed-flags"]
UDID = "11111111-1111-1111-1111-111111111111"


def result_id(space, obj, block=None):
    return "|".join(str(len(value.encode("utf8"))) + ":" + value for value in [space, obj, block or ""])


def paired():
    reports = [{"phase": phase, "processID": index + 1, "nonce": f"{index:032x}", "accountID": "pair-account",
                "spaceID": "pair-space", "rootPathSHA256": "d" * 64, "token": "e" * 32, "appSourceSHA": SOURCE}
               for index, phase in enumerate(["old-create", "new-upgrade", "old-edit", "new-recover", "new-freshness"])]
    reports[-1].update(readbackBoundary="BEFORE_FRESHNESS_MUTATIONS", freshness={
        "status": "PASS_ACTUAL_SWIFT_NATIVE_LOOKUP", "observations": [{} for _ in range(11)]})
    return {"status": runner.PAIR_PASS, "include_freshness": True, "app_source_sha": SOURCE,
            "actual_counts": {"app_builds": 2, "actual_native_processes": 5, "named_swift_tests_passed": 5,
                              "failed": 0, "skipped": 0, "host_freshness_observations": 11},
            "phase_reports": reports[:4], "freshness_report": reports[-1]}


def build():
    return {"role": "new", "app_source_sha": SOURCE, "flags": FLAGS, "runtime_version": RUNTIME,
            "code_sha256": "1" * 64, "hanlin_snapshot_sha256": "2" * 64, "kit_sha": "3" * 40}


def fixture():
    value = {"protocolVersion": 1, "token": TOKEN, "appSourceSHA": SOURCE, "runID": RUN,
             "runtimeVersion": RUNTIME, "preparationProcessID": 100, "accountID": "fresh-account", "spaceID": "fresh-space",
             "foreignSpaceID": "other-space", "accountRootPathSHA256": "c" * 64, "providerID": "sefaria",
             "canonicalReference": "Genesis 1:1", "coverage": "indexedTargetsOnly", "limitations": ["indexFreshnessUnverified"],
             "productLookupFlag": "OFF", "targets": [], "excluded": [],
             "presentationProbe": {"objectID": "object-page", "blockID": "presentation-block", "text": gates.presentation_probe_text(TOKEN)}}
    for role in gates.TARGET_ROLES:
        block = "block-" + role if role in {"block", "quote"} else None
        value["targets"].append({"role": role, "objectID": "object-" + role, "title": gates.presentation_title(role, TOKEN),
            "typeKey": "note" if role == "note" else "writing" if role == "writing" else "page", "blockID": block,
            "blockText": "T5 native " + role + " target " + TOKEN if block else None,
            "firstBlockID": "first-" + role if block else None, "firstBlockText": "First actual paragraph" if block else None,
            "associationID": "association-" + role, "canonicalSHA256": "f" * 64,
            "resultID": result_id(value["spaceID"], "object-" + role, block)})
    for reason in ["differentVerse", "differentProvider", "differentSpace"]:
        value["excluded"].append({"objectID": "excluded-" + reason, "reason": reason,
            "spaceID": value["foreignSpaceID"] if reason == "differentSpace" else value["spaceID"]})
    return value


def receipts(value):
    targets = {item["role"]: item for item in value["targets"]}
    rows = sorted(gates.ROW_PREFIX + item["resultID"] for item in value["targets"])
    base = {"protocolVersion": 1, "status": "PASS", "token": value["token"], "appSourceSHA": value["appSourceSHA"],
            "runID": value["runID"], "spaceID": value["spaceID"], "coverage": "indexedTargetsOnly",
            "productLookupFlag": "OFF", "physicalDeviceAccepted": False}
    related = [dict(stage="current-space-from-" + role, originObjectID=targets[role]["objectID"], actualRows=rows)
               for role in ["page", "note", "writing"]]
    for role in ["block", "quote"]:
        target = targets[role]
        related += [dict(stage=role + "-control-offscreen", objectID=target["objectID"], blockID=target["blockID"],
                         firstBlockID=target["firstBlockID"], targetHittable=False),
                    dict(stage=role + "-opened-from-inspector", objectID=target["objectID"], blockID=target["blockID"],
                         resultID=target["resultID"], targetHittable=True, actualText=target["blockText"])]
    note = "ui-created-note"
    block = "ui-typed-block"
    note_result = result_id(value["spaceID"], note)
    text = "T5 Note edited through native UI " + value["token"]
    notes = [dict(stage="note-created-and-edited", objectID=note, blockID=block, actualText=text),
             dict(stage="note-visible-in-current-space", objectID=note, resultID=note_result,
                  actualRows=sorted(rows + [gates.ROW_PREFIX + note_result])),
             dict(stage="note-opened-from-inspector", objectID=note, blockID=block, resultID=note_result),
             dict(stage="note-unlinked", objectID=note, actualRows=rows),
             dict(stage="unlinked-list-after-relaunch", actualRows=rows),
             dict(stage="note-retained-after-relaunch", objectID=note, blockID=block, actualText=text,
                  sourceChipExists=False, editable=True)]
    return {"related-targets": dict(base, scope="related-targets", observations=related),
            "note-lifecycle": dict(base, scope="note-lifecycle", observations=notes)}


def write_attachments(directory, value):
    output = receipts(value)
    cases = []
    number = 0
    for scope, method in gates.METHODS.items():
        entries = []
        def add(label, extension, data):
            nonlocal number
            number += 1
            name = str(number) + extension
            (directory / name).write_bytes(data)
            entries.append({"suggestedHumanReadableName": label, "exportedFileName": name})
        add("t5-native-ui-" + scope + "-receipt", ".json", json.dumps(output[scope]).encode())
        for index, label in enumerate(gates.SCREENSHOTS[scope]):
            add(label, ".png", b"\x89PNG\r\n\x1a\n" + b"fixture-parser-only" * 100)
            pid = 101 if scope == "related-targets" else 102 if index < 4 else 103
            add(label + "-accessibility", ".txt", f"Application, 0x123, pid: {pid}\nSynthetic parser control only".encode())
        cases.append({"testIdentifier": method + "()", "attachments": entries})
    (directory / "manifest.json").write_text(json.dumps(cases))
    return cases


class NativeUIEvidenceControls(unittest.TestCase):
    def test_selected_configuration_keeps_testroot_and_replaces_old_suite_in_both_formats(self):
        for version in [1, 2]:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temp:
                products = Path(temp) / "Products"; products.mkdir()
                bundle = products / "Release/AnytypeTests.xctest"; bundle.mkdir(parents=True)
                host = products / "Release/Anytype.app"; host.mkdir()
                target = {"BlueprintName": "AnytypeTests", "TestBundlePath": "__TESTROOT__/Release/AnytypeTests.xctest",
                          "TestHostPath": "__TESTROOT__/Release/Anytype.app", "OnlyTestIdentifiers": ["TorahT5RuntimePairTests"],
                          "SkipTestIdentifiers": ["TorahT5UIAcceptancePreparationTests"]}
                data = {"AnytypeTests": target} if version == 1 else {"TestConfigurations": [{"TestTargets": [target]}]}
                original = products / "Original.xctestrun"; original.write_bytes(plistlib.dumps(data)); before = original.read_bytes()
                selected, filters = runner.selected_configuration(original, "AnytypeTests", [gates.PREPARATION], {},
                    SimpleNamespace(inject=lambda *args: None))
                self.assertEqual(selected.parent, original.parent)
                self.assertEqual(original.read_bytes(), before)
                actual = plistlib.loads(selected.read_bytes())
                actual = actual["AnytypeTests"] if version == 1 else actual["TestConfigurations"][0]["TestTargets"][0]
                self.assertEqual(filters, ["TorahT5UIAcceptancePreparationTests"])
                self.assertEqual(actual["OnlyTestIdentifiers"], filters)
                self.assertEqual(actual["SkipTestIdentifiers"], [])
                for key, expected in [("TestBundlePath", bundle), ("TestHostPath", host)]:
                    self.assertEqual(Path(actual[key].replace("__TESTROOT__", str(selected.parent))), expected)
                    self.assertTrue(expected.exists())
                with self.assertRaises(ValueError):
                    runner.selected_configuration(original, "OtherTests", [gates.PREPARATION], {}, SimpleNamespace(inject=lambda *args: None))

    def test_post_pair_hook_freezes_pair_before_ui_and_preserves_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); result = paired(); counts = copy.deepcopy(result["actual_counts"])
            def write(path, value):
                path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value))
            pair = SimpleNamespace(FLAGS=FLAGS, runtime_version=lambda role: RUNTIME, write=write)
            def observed(**kwargs):
                self.assertEqual(json.loads((root / "pair-result.json").read_text())["status"], runner.PAIR_PASS)
                self.assertEqual(kwargs["pair_result"]["actual_counts"], counts)
                return {"status": runner.PASS, "actual_observation_counts": {"related_targets": 7, "note_lifecycle": 6}}
            with patch.object(runner, "run_after_pair", side_effect=observed):
                runner.continue_with_native_ui(app=root, work=root, proof=root, result=result, build=build(),
                    pair_container=root, selection={}, pair=pair, ui=None, method_results=None)
            self.assertEqual(result["status"], runner.COMBINED_PASS)
            self.assertEqual(result["pair_status"], runner.PAIR_PASS)
            self.assertEqual(result["actual_counts"], counts)
            self.assertEqual(json.loads((root / "pair-result.json").read_text())["native_ui_status"], "NOT_RUN")
            self.assertEqual(gates.digest(root / "pair-result.json"), result["pair_result_sha256"])

    def test_post_pair_hook_retains_independent_pass_on_ui_failure_and_cancel(self):
        for error in [ValueError("bounded UI failure"), KeyboardInterrupt()]:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); result = paired()
                def write(path, value):
                    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value))
                pair = SimpleNamespace(FLAGS=FLAGS, runtime_version=lambda role: RUNTIME, write=write)
                with patch.object(runner, "run_after_pair", side_effect=error), self.assertRaises(type(error)):
                    runner.continue_with_native_ui(app=root, work=root, proof=root, result=result, build=build(),
                        pair_container=root, selection={}, pair=pair, ui=None, method_results=None)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(result["pair_status"], runner.PAIR_PASS)
                self.assertEqual(result["native_ui_status"], "CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL")
                self.assertEqual(json.loads((root / "pair-result.json").read_text())["status"], runner.PAIR_PASS)
                self.assertEqual(gates.digest(root / "pair-result.json"), result["pair_result_sha256"])

    def test_cancellation_during_cleanup_or_publication_is_recorded_and_propagated(self):
        for interrupt_at in ["cleanup", "publication"]:
            with self.subTest(interrupt_at=interrupt_at), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); work = root / "work"; work.mkdir(); proof = root / "proof"
                pair_container = root / "paired"; ui_container = root / "ui-container"; ui_container.mkdir()
                ledger = pair_container / "Library/Application Support/pinkha-t5-runtime-pair/ledger.json"
                ledger.parent.mkdir(parents=True)
                result = paired(); result["run_id"] = RUN
                fresh = result["freshness_report"]
                ledger.write_text(json.dumps({key: fresh[key] for key in ["accountID", "spaceID", "token", "appSourceSHA"]}))
                fresh["nextLedgerSHA256"] = gates.digest(ledger)
                built = build(); built.update(app=str(work / "new/Products/App.app"), configuration=str(work / "new/Products/original.xctestrun"))
                selection = {"udid": "22222222-2222-2222-2222-222222222222", "runtime": {"identifier": "ios27"}, "device": {"identifier": "ipad-type"}}
                paired_device = {"udid": selection["udid"], "state": "Shutdown"}
                owned = {"udid": UDID, "name": "", "deviceTypeIdentifier": "ipad-type", "state": "Shutdown", "isAvailable": True}
                def write(path, value):
                    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value))
                def command(argv, cwd, directory, name, timeout, check=True, output=None):
                    directory.mkdir(parents=True, exist_ok=True); log = directory / (name + ".log"); log.write_text("")
                    if name == "create-ui-simulator": owned["name"] = argv[3]; log.write_text(UDID)
                    if output is not None:
                        write(output, {"devices": {"ios27": [paired_device] + ([] if name == "simulators-before" else [owned])}})
                    if name == "shutdown-owned-ui" and interrupt_at == "cleanup": raise KeyboardInterrupt()
                    return {"return_code": 0, "timed_out": False}, log
                pair = SimpleNamespace(FLAGS=FLAGS, runtime_version=lambda role: RUNTIME, write=write, run_logged=command,
                    git=lambda app, *args: SOURCE if args[0] == "rev-parse" else "", sha_bytes=lambda data: hashlib.sha256(data).hexdigest(),
                    app_container=lambda udid, kind, required=True: ui_container if required else None,
                    contains_secret=lambda path, needles: any(n in path.read_bytes() for n in needles))
                def preparation(**kwargs):
                    if interrupt_at == "publication":
                        secrets = ui_container / "Library/Application Support/pinkha-t5-native-ui-private/secrets.json"
                        write(secrets, {"token": kwargs["environment"]["PINKHA_T5_UI_TOKEN"], "mnemonic": "disposable-phrase", "accountKey": "disposable-key"})
                    raise ValueError("Controlled preparation failure to exercise cleanup only")
                publication = KeyboardInterrupt() if interrupt_at == "publication" else None
                with patch.object(runner.shutil, "disk_usage", return_value=SimpleNamespace(free=4 * 1024**3)), \
                     patch.object(runner, "select_tests", side_effect=preparation), \
                     patch.object(gates, "publish_evidence", side_effect=publication), self.assertRaises(KeyboardInterrupt):
                    runner.run_after_pair(app=root, work=work, proof=proof, pair_result=result, build=built,
                        pair_container=pair_container, selection=selection, pair=pair,
                        ui=SimpleNamespace(code_carriers=lambda path: {"sha256": built["code_sha256"]}), method_results=None)
                report = json.loads((proof / "native-ui/result.json").read_text())
                self.assertEqual(report["status"], "CANCELLED")
                self.assertEqual(report[interrupt_at + "_error_type"], "KeyboardInterrupt")
                self.assertEqual(gates.digest(ledger), fresh["nextLedgerSHA256"])

    def check_fixture(self, value):
        return gates.validate_fixture(value, source=SOURCE, run_id=RUN, token=TOKEN, runtime=RUNTIME,
                                      pair_report=paired()["freshness_report"])

    def test_requires_actual_five_phase_prerequisite_and_same_build(self):
        self.assertEqual(runner.require_ready(paired(), build(), SOURCE, FLAGS, RUNTIME)["phase"], "new-freshness")
        for key, bad in [("status", "RUNNING"), ("include_freshness", False), ("app_source_sha", "b" * 40)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                value = paired(); value[key] = bad
                runner.require_ready(value, build(), SOURCE, FLAGS, RUNTIME)
        for key, bad in [("role", "old"), ("flags", []), ("runtime_version", "old-r14"), ("kit_sha", "")]:
            with self.subTest(build_key=key), self.assertRaises(ValueError):
                value = build(); value[key] = bad
                runner.require_ready(paired(), value, SOURCE, FLAGS, RUNTIME)

    def test_rejects_labeled_counts_missing_freshness_or_reused_process(self):
        mutations = [lambda p: p["actual_counts"].update(app_builds=3),
                     lambda p: p["actual_counts"].update(failed=False),
                     lambda p: p["freshness_report"].update(processID=1),
                     lambda p: p["freshness_report"].update(nonce="0" * 32),
                     lambda p: p["freshness_report"]["freshness"].update(status="NOT_RUN"),
                     lambda p: p["freshness_report"]["freshness"].update(observations=[]),
                     lambda p: p["phase_reports"].pop(),
                     lambda p: p["phase_reports"][1].update(accountID="other-account")]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index), self.assertRaises(ValueError):
                value = paired(); mutate(value)
                runner.require_ready(value, build(), SOURCE, FLAGS, RUNTIME)

    def test_requires_fresh_account_source_and_real_runtime(self):
        self.assertEqual(set(self.check_fixture(fixture())), set(gates.TARGET_ROLES))
        for key, bad in [("accountID", "pair-account"), ("spaceID", "pair-space"), ("accountRootPathSHA256", "d" * 64),
                         ("token", "0" * 32), ("runtimeVersion", "r14"), ("coverage", "spaceWide"),
                         ("productLookupFlag", "ON"), ("preparationProcessID", True), ("protocolVersion", True)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                value = fixture(); value[key] = bad
                self.check_fixture(value)

    def test_rejects_duplicate_wrong_block_and_incomplete_negative_fixtures(self):
        mutations = [lambda v: v["targets"][4].update(objectID="object-block"),
                     lambda v: v["targets"][3].update(blockID=None),
                     lambda v: v["targets"][3].update(firstBlockID="block-block"),
                     lambda v: v["targets"][3].update(resultID="document-only"),
                     lambda v: v["targets"][0].update(canonicalSHA256="not-a-hash"),
                     lambda v: v["targets"][1].update(typeKey="page"),
                     lambda v: v["excluded"][2].update(spaceID="fresh-space"),
                     lambda v: v["excluded"][0].update(objectID="object-page"),
                     lambda v: v["excluded"].pop(), lambda v: v.update(mnemonic="must-not-be-public")]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index), self.assertRaises(ValueError):
                value = fixture(); mutate(value)
                self.check_fixture(value)

    def test_exact_named_xctest_counts_and_device(self):
        methods = {name + "()": "Passed" for name in gates.METHODS.values()}
        summary = {"totalTestCount": 2, "passedTests": 2, "failedTests": 0, "skippedTests": 0,
                   "devicesAndConfigurations": [{"device": {"deviceId": UDID, "architecture": "arm64", "osVersion": "27.0"}}]}
        self.assertEqual(gates.validate_selection(summary, methods, list(gates.METHODS.values()), UDID)["passed"], 2)
        for key, bad in [("passedTests", 0), ("failedTests", 1), ("skippedTests", 1), ("passedTests", True),
                         ("totalTestCount", 999), ("totalTestCount", 3), ("totalTestCount", None), ("totalTestCount", True)]:
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                value = dict(summary); value[key] = bad
                gates.validate_selection(value, methods, list(gates.METHODS.values()), UDID)
        with self.assertRaises(ValueError):
            gates.validate_selection(summary, methods, list(gates.METHODS.values()), "other-device")
        with self.assertRaises(ValueError):
            gates.validate_selection(summary, {"unselectedTest": "Passed"}, list(gates.METHODS.values()), UDID)

    def test_related_receipt_requires_true_offscreen_to_exact_visible_block(self):
        value = fixture(); observed = receipts(value)["related-targets"]
        gates.validate_receipt(observed, "related-targets", value)
        for index, key, bad in [(0, "actualRows", []), (3, "targetHittable", True), (3, "blockID", "wrong-block"),
                                (4, "targetHittable", False), (4, "actualText", "wrong text"), (6, "resultID", "wrong-result")]:
            with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                broken = copy.deepcopy(observed); broken["observations"][index][key] = bad
                gates.validate_receipt(broken, "related-targets", value)

    def test_note_receipt_requires_ui_created_identity_edit_unlink_and_retention(self):
        value = fixture(); observed = receipts(value)["note-lifecycle"]
        gates.validate_receipt(observed, "note-lifecycle", value)
        for index, key, bad in [(0, "objectID", "object-note"), (1, "actualRows", []), (2, "blockID", "changed-block"),
                                (3, "actualRows", ["stale-note"]), (4, "actualRows", []), (5, "actualText", "lost edit"),
                                (5, "sourceChipExists", True), (5, "editable", False)]:
            with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                broken = copy.deepcopy(observed); broken["observations"][index][key] = bad
                gates.validate_receipt(broken, "note-lifecycle", value)

    def test_receipt_rejects_wrong_attempt_and_expanded_acceptance_claim(self):
        value = fixture(); observed = receipts(value)["note-lifecycle"]
        for key, bad in [("status", "FAIL"), ("token", "c" * 32), ("scope", "unknown"), ("spaceID", "other-space"),
                         ("physicalDeviceAccepted", True), ("productLookupFlag", "ON"), ("protocolVersion", True)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                broken = copy.deepcopy(observed); broken[key] = bad
                gates.validate_receipt(broken, "note-lifecycle", value)

    def test_original_attachments_bind_receipts_screenshots_and_distinct_ui_lifetimes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); value = fixture(); write_attachments(directory, value)
            actual, files = gates.read_ui_receipts(directory, value)
            self.assertEqual(len(actual["screenshot_records"]), 13)
            self.assertEqual(len(files), 29)
            self.assertEqual(set(actual["actual_processes"]["note-lifecycle"]), {102, 103})

    def test_rejects_reused_relaunch_pid_and_duplicate_test_attachment_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); value = fixture(); manifest = write_attachments(directory, value)
            for path in directory.glob("*.txt"):
                path.write_text(path.read_text().replace("pid: 103", "pid: 102"))
            with self.assertRaises(ValueError): gates.read_ui_receipts(directory, value)
            (directory / "manifest.json").write_text(json.dumps(manifest + [manifest[0]]))
            with self.assertRaises(ValueError): gates.read_ui_receipts(directory, value)

    def test_attachment_names_accept_observed_export_suffix_but_not_ambiguous_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); (directory / "one.json").write_text("{}")
            name = "receipt_12_" + UDID + ".json"
            case = {"attachments": [{"suggestedHumanReadableName": name, "exportedFileName": "one.json"}]}
            self.assertEqual(gates.named_attachment(case, directory, "receipt", ".json").name, "one.json")
            case["attachments"].append({"suggestedHumanReadableName": "receipt", "exportedFileName": "one.json"})
            with self.assertRaises(ValueError): gates.named_attachment(case, directory, "receipt", ".json")

    def test_attachment_path_escape_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); directory = root / "export"; directory.mkdir()
            outside = root / "outside.json"; outside.write_text("{}")
            for name in ["../outside.json", "..\\outside.json", str(outside), ".", ""]:
                with self.subTest(name=name), self.assertRaises(ValueError): gates.attachment_path(directory, name)
            (directory / "link.json").symlink_to(outside)
            with self.assertRaises(ValueError): gates.attachment_path(directory, "link.json")

    def test_publication_scans_every_candidate_before_any_copy_and_all_credential_encodings(self):
        for key in ["mnemonic", "accountKey"]:
            for encoding in ["utf8", "utf-16-le", "utf-16-be"]:
                with self.subTest(key=key, encoding=encoding), tempfile.TemporaryDirectory() as temp:
                    root = Path(temp); private = root / "private"; private.mkdir(); public = root / "public"
                    first = private / "a.json"; first.write_text("{\"safe\":true}")
                    last = private / "z.log"
                    secrets = {"token": TOKEN, "mnemonic": "disposable-sensitive-phrase", "accountKey": "disposable-sensitive-key"}
                    last.write_bytes(b"prefix" + secrets[key].encode(encoding) + b"suffix")
                    with self.assertRaises(ValueError):
                        gates.publish_evidence(private, public, [first, last], secret_record=secrets, token=TOKEN,
                                               contains_secret=lambda path, needles: any(n in path.read_bytes() for n in needles))
                    self.assertFalse(public.exists())

    def test_publication_preserves_exact_allowed_bytes_and_excludes_secrets_or_raw_xcresult(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); private = root / "private"; private.mkdir(); source = private / "original.log"
            source.write_bytes(b"exact original bytes\r\nwith whitespace  \n")
            secrets = {"token": TOKEN, "mnemonic": "sensitive-disposable-phrase", "accountKey": "sensitive-disposable-key"}
            result = gates.publish_evidence(private, root / "public", [source], secret_record=secrets, token=TOKEN,
                                            contains_secret=lambda path, needles: any(n in path.read_bytes() for n in needles))
            self.assertEqual((root / "public/original.log").read_bytes(), source.read_bytes())
            self.assertFalse(result["account_data_uploaded"])
            for relative in ["secrets.json", "result.xcresult/data"]:
                path = private / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("safe bytes")
                with self.assertRaises(ValueError):
                    gates.publish_evidence(private, root / "bad-public", [path], secret_record=secrets, token=TOKEN,
                                           contains_secret=lambda path, needles: False)

    def test_rejects_preexisting_or_wrong_type_simulator(self):
        selection = {"runtime": {"identifier": "ios27"}, "device": {"identifier": "ipad-type"}}
        name = "job-owned"
        item = {"udid": UDID, "name": name, "deviceTypeIdentifier": "ipad-type", "state": "Shutdown", "isAvailable": True}
        before = {"devices": {"ios27": []}}; after = {"devices": {"ios27": [item]}}
        self.assertEqual(runner.validate_owned_simulator(before, after, UDID, name, selection), item)
        with self.assertRaises(ValueError): runner.validate_owned_simulator(after, after, UDID, name, selection)
        for key, bad in [("name", "another-job"), ("deviceTypeIdentifier", "iphone"), ("state", "Booted"), ("isAvailable", False)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                altered = copy.deepcopy(after); altered["devices"]["ios27"][0][key] = bad
                runner.validate_owned_simulator(before, altered, UDID, name, selection)

    def test_original_pair_ledger_is_hash_bound_and_never_rewritten(self):
        with tempfile.TemporaryDirectory() as temp:
            container = Path(temp); path = container / "Library/Application Support/pinkha-t5-runtime-pair/ledger.json"
            path.parent.mkdir(parents=True)
            original = {"accountID": "a", "spaceID": "s", "token": TOKEN, "appSourceSHA": SOURCE}
            raw = json.dumps(original).encode(); path.write_bytes(raw)
            report = dict(original, nextLedgerSHA256=hashlib.sha256(raw).hexdigest())
            self.assertEqual(runner.original_pair_ledger(container, report), (path, report["nextLedgerSHA256"]))
            self.assertEqual(path.read_bytes(), raw)
            path.write_bytes(raw + b"\n")
            with self.assertRaises(ValueError): runner.original_pair_ledger(container, report)


if __name__ == "__main__":
    unittest.main()
