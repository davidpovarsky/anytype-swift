"""Finite portable source/receipt boundaries; all observations are synthetic.

No App, compiler, simulator, native model or XCTest is executed by this file.
The original selected XCTest result remains an independent runtime prerequisite.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import prepare_future_torah_control as materializer
import torah_future_control as future
import torah_overflow_observations as observations
import torah_ui_profile as profile

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
UDID = "11111111-2222-3333-4444-555555555555"
TOKEN = "12345678" * 4
BINDING = {"sourceSHA": "a" * 40, "runID": "123", "runAttempt": "1", "nonce": TOKEN}


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")


class Common:
    @staticmethod
    def require(value, reason):
        if not value:
            raise ValueError(reason)

    @staticmethod
    def sha(value):
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def decode(value):
        return json.loads(value)

    @staticmethod
    def raw(path, maximum=64 * 1024**2):
        value = Path(path).read_bytes()
        Common.require(len(value) <= maximum, "Oversized synthetic fixture")
        return value

    @staticmethod
    def write(path, value):
        Path(path).write_bytes(encode(value))

    @staticmethod
    def error(exc):
        return {"type": type(exc).__name__, "message": str(exc)}


C = Common()


def bound(fixture=None):
    fixture = fixture or {"spaceId": "synthetic-space", "manySourcesDocument": "synthetic-many-source-document",
        "sourceHeaderCases": [{"count": 12, "objectId": "synthetic-many-source-document",
                               "labels": ["Genesis 2:" + str(n) for n in range(1, 13)]}]}
    raw = json.dumps(fixture, indent=2).encode() + b"\n"
    preparation = profile.LANES["properties"]["preparation"]
    admission = {"schema": "pinkha-combined-host-acceptance-admission-v1", "executionEnvironment": "SentinelX-owned-Mac",
                 "sourceCommit": BINDING["sourceSHA"], "appLanguage": "en", "deviceType": "synthetic-ipad", "deviceFamily": "ipad"}
    invocation = {"binding": BINDING, "argv": ["platform=iOS Simulator,id=" + UDID,
                  "-only-testing:AnytypeTests/" + preparation + "()"]}
    prepared = {"status": "PASS", "testInvoked": True, "selected": [preparation], "command_exit_code": 0,
                "passed": 1, "failed": 0, "skipped": 0, "actual_devices": [{"deviceId": UDID, "platform": "iOS Simulator"}],
                "installedOriginalCode": {"codeCarriersSHA256": "b" * 64}}
    owned = {"udid": UDID, "name": "F-Combined-" + TOKEN + "-properties", "deviceType": "synthetic-ipad", "deviceFamily": "ipad"}
    environment = {"PINKHA_NATIVE_UI_DISPOSABLE": "1", "PINKHA_NATIVE_UI_FIXTURE_JSON": json.dumps(fixture),
                   "PINKHA_UI27_APP_LANGUAGE": "en", "PINKHA_UI27_SELECTION_SCOPE": "WAVE15_ACCEPTANCE"}
    startup = profile.startup_environment(lane="properties", fixture_raw=raw, ui_environment=environment,
        preparation_raw=encode(prepared), invocation_raw=encode(invocation), admission_raw=encode(admission),
        owned_simulator_raw=encode(owned), binding=BINDING, udid=UDID, token=TOKEN, code_carriers_sha256="b" * 64)
    actual, controller = observations.fixture_binding(C, raw, startup, UDID)
    return actual, controller, raw, startup


def records(fixture, controller):
    before = {"torah-document-source-chip-source-1": "Genesis 2:1",
              "torah-document-source-chip-source-2": "Genesis 2:2"}
    hidden = sorted(set(fixture["sourceHeaderCases"][0]["labels"]) - set(before.values()))
    selected = hidden[0]
    result = {}
    for phase in observations.PHASES:
        result[phase] = {"schema": "pinkha-source-overflow-ui-observation-v1", "phase": phase,
            "spaceID": fixture["spaceId"], "objectID": fixture["manySourcesDocument"],
            "controllerProvenance": "CONTROLLER_OWNED_SIMULATOR_AFTER_ORIGINAL_NATIVE_PREPARATION",
            "controller": controller, "selectedReference": selected, "visibleBefore": before,
            "hiddenReferences": hidden, "observedMenu": hidden,
            "observedSelectedHeading": "" if phase == "menu-choice" else selected,
            "readerIdentifier": "torah-reader-segment-" + selected if phase == "reader-content" else "",
            "readerText": "Synthetic selected verse body" if phase == "reader-content" else "",
            "visibleAfter": before if phase == "returned-document" else {},
            "associationMutationRequestedByThisCase": False, "evidenceScope": "OBSERVED_UI_ONLY"}
    return result


def exports(directory, values):
    # Synthetic PNG header only. These controls do not render or inspect pixels.
    png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 10, 20) + b"\x08\x06\0\0\0\0\0\0\0"
    items = []
    for phase in (*observations.PHASES, "final"):
        kinds = (".txt", ".png") if phase == "final" else (".json", ".txt", ".png")
        for kind in kinds:
            stem = "source-overflow-" + phase + {".txt": "-ax", ".png": "-visual"}.get(kind, "")
            name = str(len(items)) + kind
            raw = encode(values[phase]) if kind == ".json" else png if kind == ".png" else b"Synthetic AX text\n"
            (directory / name).write_bytes(raw)
            items.append({"suggestedHumanReadableName": stem + kind, "exportedFileName": name,
                          "deviceId": UDID, "isAssociatedWithFailure": False})
    manifest = [{"testIdentifier": observations.TARGET + "/" + observations.METHOD + "()", "attachments": items}]
    (directory / "manifest.json").write_bytes(encode(manifest))
    return manifest


class PortableControls(unittest.TestCase):
    def test_exact_actual_source_appends_and_g02_literal_inverse(self):
        comprehensive = (HERE.parent / "word-unlink-ui/AnytypeComprehensiveAcceptanceUITests.swift").read_bytes()
        stage1 = (WORKSPACE / "wave2-editor-rtl/coverage-audit/PinkhaStage1AcceptanceUITests.swift").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary).resolve()
            ui = source / "PinkhaStage1Acceptance/Tests"; ui.mkdir(parents=True)
            cp, st = ui / "AnytypeComprehensiveAcceptanceUITests.swift", ui / "PinkhaStage1AcceptanceUITests.swift"
            cp.write_bytes(comprehensive); st.write_bytes(stage1)
            self.assertTrue(profile.reviewed_original_ui_inverse(source)["originalThirteenUISelectorsUnchanged"])
            self.assertEqual(observations.qualify_source(C, comprehensive)["declaredMethods"], 1)
            for target, bad in ((st, stage1[:86201]), (st, stage1+b"\n"),
                                (cp, comprehensive[:43356]), (cp, comprehensive+b"\n")):
                target.write_bytes(bad)
                with self.assertRaises(ValueError): profile.reviewed_original_ui_inverse(source)
                cp.write_bytes(comprehensive); st.write_bytes(stage1)
        proof = materializer.profile_inverse((HERE / "originals/torah_ui_profile.py").read_bytes(),
            (HERE / "torah_ui_profile.py").read_bytes(), (HERE / "source-profile-inverse.json").read_bytes())
        self.assertTrue(proof["exactProfileInverse"])
        _, g02 = materializer.g02_literal_successor((HERE / "originals/g02_word_consumer.py").read_bytes())
        self.assertTrue(g02["exactSingleLiteralInverse"] and g02["allFunctionBodiesUnchanged"])

    def test_exact_host_inverse_finite480_delegation_and_closed_gates(self):
        original = (HERE / "originals/combined_host_acceptance_app15.py").read_bytes()
        candidate, inverse = materializer.compose(original)
        self.assertTrue(inverse["exactFullInverse"] and inverse["originalMainAndOwnedLaneFinallyUnchanged"])
        def plans(raw):
            node = next(n for n in ast.parse(raw).body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "PLANS" for t in n.targets))
            return ast.literal_eval(node.value)
        self.assertEqual(plans(candidate), {**plans(original), future.PLAN: (future.LANE,)})
        calls, sentinel = [], {"original-unchanged-budget": True}
        def old(target, methods):
            calls.append((target, methods)); return sentinel
        consumer = SimpleNamespace(admission={"plan": future.PLAN}, shared_module=C,
                                   helpers={"run_ui27": SimpleNamespace(selection_time_budget=old)})
        existing = ["PinkhaNativeDerivedAcceptanceUITests/testSourceHeaderSelectionAndOverflow"]
        self.assertIs(future.ui_budget(consumer, observations.TARGET, existing), sentinel)
        self.assertEqual(calls, [(observations.TARGET, existing)])
        result = future.ui_budget(consumer, observations.TARGET, [observations.METHOD])
        self.assertEqual((result["default_seconds"], result["maximum_seconds"], result["total_method_seconds"]), (480,480,480))
        for target, methods, plan in (("AnytypeTests", [observations.METHOD], future.PLAN),
                                     (observations.TARGET, [observations.METHOD, existing[0]], future.PLAN),
                                     (observations.TARGET, [observations.METHOD], "properties-only")):
            consumer.admission["plan"] = plan
            with self.assertRaises(ValueError): future.ui_budget(consumer, target, methods)
        self.assertEqual(len(calls), 1)
        for admission in ({"plan": future.PLAN}, {"plan": "properties-only", "runtimeReady": True,
                          "sourceCommit": "f" * 40, "commonSHA256": "d" * 64}):
            with patch("builtins.open", side_effect=AssertionError("Closed gate must not read or write")):
                with self.assertRaisesRegex(ValueError, "FUTURE_TORAH_RUNTIME_CLOSED"):
                    future.require_runtime_ready(admission, Path("/synthetic-unqualified-product"))
        a = materializer.declarations(candidate.decode())
        lane = next(n for n in a["Consumer"].body if isinstance(n, ast.FunctionDef) and n.name == "execute_lane")
        self.assertIn("require_runtime_ready", ast.unparse(lane.body[0]))
        main = materializer.segment(candidate.decode(), a["main"])
        self.assertLess(main.index("future_torah.require_runtime_ready"), main.index("args.root.mkdir"))
        self.assertLess(main.index("future_torah.require_runtime_ready"), main.index("shared.admit_and_clone_products"))

    def test_original_raw_fixture_and_ten_key_controller_scope(self):
        fixture, controller, raw, startup = bound()
        self.assertEqual(set(controller), set(observations.CONTROLLER_KEYS)); self.assertEqual(len(controller),10)
        self.assertNotEqual(C.sha(raw), C.sha(startup["PINKHA_NATIVE_UI_FIXTURE_JSON"].encode()))
        self.assertEqual(observations.fixture_binding(C, raw, startup, UDID)[0], fixture)
        with self.assertRaises(ValueError): observations.fixture_binding(C, raw, startup, "66666666-2222-3333-4444-555555555555")
        wrong = dict(startup, PINKHA_NATIVE_UI_FIXTURE_JSON=startup["PINKHA_NATIVE_UI_FIXTURE_JSON"].replace("synthetic-space", "foreign-space"))
        with self.assertRaises(ValueError): observations.fixture_binding(C, raw, wrong, UDID)
        duplicate = copy.deepcopy(fixture); duplicate["sourceHeaderCases"].append(duplicate["sourceHeaderCases"][0])
        with self.assertRaises(ValueError): bound(duplicate)

    def test_hidden_selection_reader_return_and_all14_manifest_artifacts(self):
        fixture, controller, _, _ = bound(); values = records(fixture, controller)
        metadata = observations.validate_metadata(C, values, fixture, controller)
        self.assertFalse(metadata["nativePersistenceAccepted"])
        for mutate in (lambda x: x["selected-reference"].update(observedSelectedHeading="Genesis 2:1"),
                       lambda x: x["menu-choice"].update(selectedReference="Genesis 2:1"),
                       lambda x: x["reader-content"].update(spaceID="foreign-space"),
                       lambda x: x["reader-content"].update(readerText=x["reader-content"]["selectedReference"]),
                       lambda x: x["returned-document"].update(visibleAfter={})):
            wrong = copy.deepcopy(values); mutate(wrong)
            with self.assertRaises(ValueError): observations.validate_metadata(C, wrong, fixture, controller)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve(); manifest = exports(directory, values)
            actual = observations.attachments(C, directory, UDID, fixture, controller)
            self.assertEqual(sum(len(v) for v in actual["artifacts"].values()),14)
            self.assertEqual(actual["visualReview"], "PENDING")
            for mutate in (lambda m: m[0]["attachments"].pop(),
                           lambda m: m[0]["attachments"].append(m[0]["attachments"][0]),
                           lambda m: m[0]["attachments"][0].update(deviceId="foreign-device"),
                           lambda m: m[0]["attachments"][0].update(isAssociatedWithFailure=True),
                           lambda m: m[0].update(testIdentifier="OtherSuite/OtherMethod")):
                wrong = copy.deepcopy(manifest); mutate(wrong)
                (directory / "manifest.json").write_bytes(encode(wrong))
                with self.assertRaises(ValueError): observations.attachments(C, directory, UDID, fixture, controller)

    def test_actual_stage_descriptor_command_and_first_failure_boundaries(self):
        fixture, controller, raw, startup = bound(); values = records(fixture, controller)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); stage = root / "torah-source-overflow/ui"; stage.mkdir(parents=True)
            attachments = stage / "private-attachments"; attachments.mkdir(); exports(attachments, values)
            fixture_path = root / "fixture.json"; fixture_path.write_bytes(raw)
            descriptor = plistlib.dumps({observations.TARGET:{"OnlyTestIdentifiers":[observations.METHOD],"EnvironmentVariables":startup}})
            (stage / "bound.xctestrun").write_bytes(descriptor); (stage / "enumeration.json").write_bytes(b"{}")
            argv = ["xcodebuild", "test-without-building", "-destination", "platform=iOS Simulator,id="+UDID,
                    "-only-testing:"+observations.TARGET+"/"+observations.METHOD,
                    "-default-test-execution-time-allowance", "480", "-maximum-test-execution-time-allowance", "480"]
            command = {"status":"PASS_COMMAND","exitCode":0,"argv":argv}
            result = {"status":"PASS","selected":[observations.METHOD],"testInvoked":True,"command_exit_code":0,
                      "passed":1,"failed":0,"skipped":0,"command":command,
                      "actual_devices":[{"deviceId":UDID,"platform":"iOS Simulator"}]}
            invocation = {"argv":argv,"binding":BINDING,"descriptorSHA256":C.sha(descriptor),"enumerationSHA256":C.sha(b"{}")}
            C.write(stage / "result.json", result); C.write(stage / "invocation.json", invocation)
            commands = root / "commands"; actual_command = commands / "torah-source-overflow-ui-test"; actual_command.mkdir(parents=True)
            C.write(actual_command / "result.json",command);(actual_command / "original.log").write_bytes(b"** TEST EXECUTE SUCCEEDED **\n")
            consumer = SimpleNamespace(shared_module=C,binding=BINDING,commands=SimpleNamespace(root=commands))
            actual = observations.collect(consumer,stage,UDID,startup,fixture_ref=observations.reference(C,fixture_path))
            self.assertFalse(actual["nativePersistenceAccepted"])
            self.assertNotEqual(actual["originalPreparationInvocationSHA256"],actual["actualPhaseInvocationSHA256"])
            bad=copy.deepcopy(invocation); bad["argv"][bad["argv"].index("-maximum-test-execution-time-allowance")+1]="300"
            wrong=copy.deepcopy(result);wrong["command"]["argv"]=bad["argv"]
            C.write(stage / "invocation.json",bad);C.write(stage / "result.json",wrong);C.write(actual_command / "result.json",wrong["command"])
            with self.assertRaises(ValueError): observations.collect(consumer,stage,UDID,startup,fixture_ref=observations.reference(C,fixture_path))
            first=ValueError("original-stage-failure")
            def fail_save(*args):raise OSError("later evidence save failure")
            with self.assertRaises(ValueError) as caught:
                future.save_result(SimpleNamespace(write=fail_save,error=C.error),root / "failed.json",{"status":"FAIL"},first)
            self.assertIs(caught.exception,first);self.assertIsInstance(caught.exception.__cause__,OSError)


if __name__ == "__main__":
    unittest.main(verbosity=2)
