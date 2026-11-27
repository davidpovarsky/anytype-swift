"""Focused portable source/receipt controls, with synthetic UI observations.

No UIKit, App, native store, compiler, simulator or XCTest method is executed.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
TORAH = HERE.parent / "torah-acceptance-prep/future-torah-control"
sys.path.insert(0, str(TORAH))
import torah_ui_profile as startup_profile
import heart_editor_observations as observed
import heart_editor_control as control
import prepare_heart_editor_control as materializer

UDID = "11111111-2222-3333-4444-555555555555"
NONCE = "01234567" * 4
BINDING = {"sourceSHA": "a" * 40, "runID": "123", "runAttempt": "1", "nonce": NONCE}


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


class Common:
    @staticmethod
    def require(value, reason):
        if not value:
            raise ValueError(reason)

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def decode(raw):
        return json.loads(raw)

    @staticmethod
    def raw(path, maximum=64*1024**2):
        value = Path(path).read_bytes()
        Common.require(len(value) <= maximum, "Oversized synthetic artifact")
        return value

    @staticmethod
    def write(path, value):
        Path(path).write_bytes(encode(value))

    @staticmethod
    def error(error):
        return {"type": type(error).__name__, "message": str(error)}


C = Common()


def bound(language="he"):
    native = {"spaceId": "synthetic-space", "pinkhaObjectId": "synthetic-pinkha",
              "noteObjectId": "synthetic-note", "pageObjectId": "synthetic-page"}
    raw = json.dumps(native, indent=2).encode() + b"\n"
    preparation = startup_profile.EDITOR_SPEC["preparation"]
    admission = {"schema":"pinkha-combined-host-acceptance-admission-v1","executionEnvironment":"SentinelX-owned-Mac",
                 "sourceCommit":BINDING["sourceSHA"],"appLanguage":language,"deviceType":"synthetic-ipad","deviceFamily":"ipad"}
    invocation = {"binding":BINDING,"argv":["platform=iOS Simulator,id="+UDID,"-only-testing:AnytypeTests/"+preparation+"()"]}
    prepared = {"status":"PASS","testInvoked":True,"selected":[preparation],"command_exit_code":0,
                "passed":1,"failed":0,"skipped":0,"actual_devices":[{"deviceId":UDID,"platform":"iOS Simulator"}],
                "installedOriginalCode":{"codeCarriersSHA256":"b"*64}}
    owned = {"udid":UDID,"name":"F-Combined-"+NONCE+"-editor","deviceType":"synthetic-ipad","deviceFamily":"ipad"}
    environment = {"PINKHA_ACCEPTANCE_SPACE_ID":native["spaceId"],"PINKHA_ACCEPTANCE_PINKHA_ID":native["pinkhaObjectId"],
        "PINKHA_ACCEPTANCE_NOTE_ID":native["noteObjectId"],"PINKHA_ACCEPTANCE_PAGE_ID":native["pageObjectId"],
        "PINKHA_ACCEPTANCE_DIRECTION":"rtl" if language=="he" else "ltr",
        "PINKHA_ACCEPTANCE_DEVICE_LANGUAGE":"en" if language=="he" else "he",
        "PINKHA_UI27_APP_LANGUAGE":language,"PINKHA_UI27_SELECTION_SCOPE":"WAVE15_ACCEPTANCE"}
    startup = startup_profile.startup_environment(lane="editor",fixture_raw=raw,ui_environment=environment,
        preparation_raw=encode(prepared),invocation_raw=encode(invocation),admission_raw=encode(admission),
        owned_simulator_raw=encode(owned),binding=BINDING,udid=UDID,token=NONCE,code_carriers_sha256="b"*64)
    return observed.fixture_binding(C,raw,startup,UDID),raw,startup


def records(selection, fixture):
    result = {}
    for index, kind in enumerate(observed.KINDS):
        token = "ABCDEF"+str(index).zfill(2)
        guard_id = observed.BODY_PREFIX+kind+"-guard"
        target_id = observed.BODY_PREFIX+kind+"-target"
        second_id = observed.BODY_PREFIX+kind+"-second"
        guard, left, right = "Guard_"+token,"Left_"+token,"Right_"+token
        if selection=="split-merge":
            split={guard_id:guard,target_id:left,second_id:right};joined={guard_id:guard,target_id:left+right}
            maps={phase:split if phase in ("split","split-redo","merge-undo") else joined for phase in observed.PHASES[selection]}
            ranges={"split":"INFERRED_FROM_EXACT_PREFIX_SUFFIX_AFTER_REAL_RETURN",
                    "merge":"INFERRED_FROM_EXACT_MERGE_AFTER_REAL_COMMAND_A_LEFT_BACKSPACE"}
        else:
            before={guard_id:guard,target_id:left+"MIDDLE"+right};after={guard_id:guard,target_id:left+"Z"+right}
            maps={phase:before if phase=="replacement-undo" else after for phase in observed.PHASES[selection]}
            ranges={"partial-replacement":"INFERRED_FROM_EXACT_UNCHANGED_PREFIX_SUFFIX_AFTER_REAL_SHIFT_RANGE"}
        result[kind]={}
        for phase in observed.PHASES[selection]:
            cold=phase==observed.PHASES[selection][-1]
            row={"schema":"pinkha-heart-editor-mutation-observation-v1","phase":phase,"documentKind":kind,
                 "spaceID":fixture["spaceID"],"objectID":fixture["documents"][kind],"token":token,
                 "appLanguage":fixture["appLanguage"],"requestedDeviceLanguage":fixture["deviceLanguage"],
                 "appPID":2000+index if cold else 1000+index,"expectedBlocks":copy.deepcopy(maps[phase]),
                 "observedBlocks":copy.deepcopy(maps[phase]),"startupBindingSHA256":fixture["startupBindingSHA256"],
                 "rangeEvidence":ranges.get(phase,"NO_PRE_EDIT_RANGE_CLAIM"),"directNativeRangeObservation":False,
                 "programmaticSelectionChanges":0,"persistedColdReadback":cold,
                 "saveEvidence":"DISTINCT_COLD_PROCESS_EXACT_ID_AND_TEXT_READBACK" if cold else "UI_STATE_ONLY"}
            if cold:row["previousPID"]=1000+index
            result[kind][phase]=row
    return result


def exports(directory, selections, fixture):
    png=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"+struct.pack(">II",10,20)+b"\x08\x06\0\0\0\0\0\0\0"
    manifest=[]
    for selection in selections:
        values=records(selection,fixture);items=[]
        def add(label,ext,body=None):
            name=str(len(manifest))+"-"+str(len(items))+ext
            raw=encode(body) if ext==".json" else png if ext==".png" else b"Synthetic AX\n"
            (directory/name).write_bytes(raw)
            items.append({"suggestedHumanReadableName":label+ext,"exportedFileName":name,"deviceId":UDID,"isAssociatedWithFailure":False})
        for kind in observed.KINDS:
            for phase in observed.PHASES[selection]:
                label=observed.PREFIX+kind+"-"+phase
                add(label,".json",values[kind][phase]);add(label+"-ax",".txt");add(label+"-visual",".png")
            if selection=="range-replacement":
                label=observed.PREFIX+kind+"-real-shift-selection"
                add(label+"-ax",".txt");add(label+"-visual",".png")
        final=observed.PREFIX+observed.FINALS[selection]
        add(final+"-ax",".txt");add(final+"-visual",".png")
        manifest.append({"testIdentifier":observed.TARGET+"/"+observed.METHODS[selection]+"()","attachments":items})
    (directory/"manifest.json").write_bytes(encode(manifest));return manifest


class PortableControls(unittest.TestCase):
    def test_actual_source_inverse_original_host_and_finite_budget_gate(self):
        original=(TORAH/"originals/combined_host_acceptance_app15.py").read_bytes()
        candidate,inverse=materializer.compose(original)
        self.assertTrue(inverse["fullInverse"] and inverse["originalMainAndOwnedLaneFinallyUnchanged"])
        source=HERE.parent/"wave2-editor-rtl/coverage-audit"
        raw=(source/"PinkhaStage1AcceptanceUITests.swift").read_bytes();proof=(source/"mutation-source-proof.json").read_bytes()
        self.assertEqual(observed.qualify_source(C,raw,proof)["declaredCases"],2)
        for bad in (raw[:observed.ORIGINAL_BYTES],raw+b"\n"):
            with self.assertRaises(ValueError):observed.qualify_source(C,bad,proof)
        with self.assertRaises(ValueError):observed.qualify_source(C,raw,proof+b"\n")
        calls=[];sentinel={"oldBudget":True}
        def old(target,methods):calls.append((target,methods));return sentinel
        consumer=SimpleNamespace(admission={},shared_module=C,helpers={"run_ui27":SimpleNamespace(selection_time_budget=old)})
        for plan,lanes in control.PLANS.items():
            consumer.admission["plan"]=plan;methods=control.LANES[lanes[0]]
            budget=control.ui_budget(consumer,observed.TARGET,methods)
            self.assertEqual(budget["default_seconds"],1200);self.assertEqual(budget["maximum_seconds"],1200)
            self.assertEqual(budget["total_method_seconds"]+300,1500 if len(methods)==1 else 2700)
            with patch("builtins.open",side_effect=AssertionError("Closed before IO")):
                with self.assertRaisesRegex(ValueError,"HEART_EDITOR_RUNTIME_CLOSED"):
                    control.require_runtime_ready({"plan":plan,"runtimeReady":True,"sourceCommit":"f"*40},Path("/synthetic"))
        existing=["PinkhaStage1AcceptanceUITests/testMultiBlockEnterCreationAndTypingLifecycle"]
        self.assertIs(control.ui_budget(consumer,observed.TARGET,existing),sentinel);self.assertEqual(len(calls),1)
        consumer.admission["plan"]="heart-mutations-only"
        for target,methods in (("AnytypeTests",list(observed.METHODS.values())),
                               (observed.TARGET,list(reversed(observed.METHODS.values()))),
                               (observed.TARGET,[observed.METHODS["split-merge"],existing[0]])):
            with self.assertRaises(ValueError):control.ui_budget(consumer,target,methods)
        nodes=materializer.declarations(candidate.decode())
        main=materializer.segment(candidate.decode(),nodes["main"])
        self.assertLess(main.index("heart_editor.require_runtime_ready"),main.index("args.root.mkdir"))
        lane=next(n for n in nodes["Consumer"].body if isinstance(n,ast.FunctionDef) and n.name=="execute_lane")
        self.assertIn("require_runtime_ready",ast.unparse(lane.body[0]))

    def test_original_fixture_both_languages_and_exact_controller_binding(self):
        for language in ("he","en"):
            fixture,raw,startup=bound(language)
            self.assertNotEqual(fixture["appLanguage"],fixture["deviceLanguage"])
            self.assertEqual(len(set(fixture["documents"].values())),3)
            self.assertEqual(fixture["startupBindingSHA256"],C.sha(startup["PINKHA_UI27_STARTUP_BINDING_JSON"].encode()))
            with self.assertRaises(ValueError):observed.fixture_binding(C,raw,startup,"66666666-2222-3333-4444-555555555555")
            wrong=dict(startup,PINKHA_ACCEPTANCE_NOTE_ID="foreign-note")
            with self.assertRaises(ValueError):observed.fixture_binding(C,raw,wrong,UDID)
            wrong=dict(startup,PINKHA_ACCEPTANCE_DEVICE_LANGUAGE=language)
            with self.assertRaises(ValueError):observed.fixture_binding(C,raw,wrong,UDID)

    def test_exact_all_phase_maps_and_cold_not_optimistic_or_wrong_range(self):
        fixture,_,_=bound()
        for selection in observed.METHODS:
            values=records(selection,fixture)
            accepted=observed.validate_metadata(C,values,selection,fixture)
            self.assertEqual(set(accepted),set(observed.KINDS))
            warm=observed.PHASES[selection][0];cold=observed.PHASES[selection][-1]
            for mutate in (
                lambda x:x["pinkha"][warm].update(persistedColdReadback=True),
                lambda x:x["note"][warm].update(directNativeRangeObservation=True),
                lambda x:x["page"][cold].update(appPID=x["page"][cold]["previousPID"]),
                lambda x:x["pinkha"][cold].update(previousPID=999),
                lambda x:x["note"][cold].update(objectID="other-object"),
                lambda x:x["pinkha"][warm].update(rangeEvidence="DIRECT_NATIVE_RANGE"),
                lambda x:x["page"][warm]["observedBlocks"].update({observed.BODY_PREFIX+"extra":"unexpected"}),
                lambda x:x["note"][cold].update(startupBindingSHA256="f"*64),
            ):
                wrong=copy.deepcopy(values);mutate(wrong)
                with self.assertRaises(ValueError):observed.validate_metadata(C,wrong,selection,fixture)

    def test_exact109_groups_with_selection_final_method_and_device_boundaries(self):
        fixture,_,_=bound()
        for selections,total in ((["split-merge"],65),(["range-replacement"],44),(list(observed.METHODS),109)):
            with tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary).resolve();manifest=exports(directory,selections,fixture)
                methods=[observed.METHODS[x] for x in selections]
                accepted=observed.attachments(C,directory,UDID,methods,fixture)
                self.assertEqual(accepted["artifactCount"],total);self.assertEqual(accepted["visualReview"],"PENDING")
                for mutate in (
                    lambda m:m[-1]["attachments"].pop(),
                    lambda m:m[0]["attachments"].append(m[0]["attachments"][0]),
                    lambda m:m[0]["attachments"][0].update(deviceId="foreign-device"),
                    lambda m:m[0]["attachments"][0].update(isAssociatedWithFailure=True),
                    lambda m:m[0].update(testIdentifier="OtherSuite/OtherMethod"),
                ):
                    wrong=copy.deepcopy(manifest);mutate(wrong);(directory/"manifest.json").write_bytes(encode(wrong))
                    with self.assertRaises(ValueError):observed.attachments(C,directory,UDID,methods,fixture)
                if "range-replacement" in selections:
                    wrong=copy.deepcopy(manifest)
                    for row in wrong:
                        row["attachments"]=[x for x in row["attachments"] if "page-real-shift-selection-visual" not in x["suggestedHumanReadableName"]]
                    (directory/"manifest.json").write_bytes(encode(wrong))
                    with self.assertRaises(ValueError):observed.attachments(C,directory,UDID,methods,fixture)

    def test_original_stage_binding_exact_counts_allowance_and_first_failure(self):
        fixture,raw,startup=bound();methods=list(observed.METHODS.values())
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();stage=root/"heart-editor-mutations/ui";stage.mkdir(parents=True)
            directory=stage/"private-attachments";directory.mkdir();exports(directory,list(observed.METHODS),fixture)
            fixture_path=root/"fixture.json";fixture_path.write_bytes(raw)
            descriptor=plistlib.dumps({observed.TARGET:{"OnlyTestIdentifiers":methods,"EnvironmentVariables":startup}})
            (stage/"bound.xctestrun").write_bytes(descriptor);(stage/"enumeration.json").write_bytes(b"{}")
            argv=["xcodebuild","test-without-building","-destination","platform=iOS Simulator,id="+UDID,
                  *["-only-testing:"+observed.TARGET+"/"+m for m in methods],
                  "-default-test-execution-time-allowance","1200","-maximum-test-execution-time-allowance","1200"]
            command={"argv":argv,"status":"PASS_COMMAND","exitCode":0}
            result={"status":"PASS","selected":methods,"testInvoked":True,"command_exit_code":0,"passed":2,"failed":0,"skipped":0,
                    "originalTimeBudget":observed.time_budget(C,observed.TARGET,methods),"command":command,
                    "actual_devices":[{"deviceId":UDID,"platform":"iOS Simulator"}]}
            invocation={"argv":argv,"binding":BINDING,"descriptorSHA256":C.sha(descriptor),"enumerationSHA256":C.sha(b"{}")}
            C.write(stage/"result.json",result);C.write(stage/"invocation.json",invocation)
            commands=root/"commands";actual=commands/"heart-editor-mutations-ui-test";actual.mkdir(parents=True)
            C.write(actual/"result.json",command);(actual/"original.log").write_bytes(b"** TEST EXECUTE SUCCEEDED **\n")
            consumer=SimpleNamespace(shared_module=C,binding=BINDING,commands=SimpleNamespace(root=commands))
            accepted=observed.collect(consumer,stage,UDID,startup,methods,fixture_ref=observed.reference(C,fixture_path))
            self.assertEqual(accepted["artifactCount"],109);self.assertEqual(accepted["selectedMethodCount"],2)
            self.assertNotEqual(accepted["originalPreparationInvocationSHA256"],accepted["actualUIInvocationSHA256"])
            for change in ({"passed":1},{"skipped":1},{"selected":[methods[0]]},{"originalTimeBudget":{"maximum_seconds":300}}):
                wrong=copy.deepcopy(result);wrong.update(change);C.write(stage/"result.json",wrong)
                with self.assertRaises(ValueError):observed.collect(consumer,stage,UDID,startup,methods,fixture_ref=observed.reference(C,fixture_path))
            first=ValueError("original-ui-failure")
            def fail(*args):raise OSError("later-save-failure")
            with self.assertRaises(ValueError) as caught:control.save_result(SimpleNamespace(write=fail,error=C.error),root/"failed.json",{},first)
            self.assertIs(caught.exception,first);self.assertIsInstance(caught.exception.__cause__,OSError)


if __name__ == "__main__":
    unittest.main(verbosity=2)
