"""One new composition control; no Mac, XCTest, App or native invocation."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import tempfile
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

import warning_profile as profile
import warning_runner

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs/validation/20261123-semantic-page-startup-warning"
HERE = Path(__file__).resolve().parent


class PageStartupWarningControls(unittest.TestCase):
    def testWarningUiOnlyCompositionPreservesNativeOriginAndSetupAccounting(self):
        plan = profile.read_plan()
        original_plan = json.loads((HERE / "source-plan.json").read_bytes())
        original_ui = (DOCS / "control-data/original-mounted-ui.swift").read_bytes()
        original_descriptor = (DOCS / "control-data/original-ui.xctestrun").read_bytes()
        self.assertEqual(profile.sha(original_ui), profile.ORIGINAL_UI_SHA256)
        current = {name: row["sha256"] for name, row in original_plan["files"].items()}
        app = dict(current)
        for name, row in plan["files"].items():
            current[name] = row["sha256"]
            app[name] = row["original_sha256"]
        current[plan["generator_path"]] = plan["generator_sha256"]
        current["Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json"] = (
            plan["original_mounted_source_plan_sha256"])
        binding = dict(sourceSHA=profile.APP_COMMIT, runID="999991", runAttempt="1", nonce="a" * 32)
        with self.subTest("one_ui_delta_only"):
            admitted = profile.source_admission(original_plan, current, app, plan)
            self.assertEqual(admitted["changed_ui_path"], profile.UI_PATH)
            for owner in ("current", "app"):
                invalid = dict(current if owner == "current" else app)
                name = next(n for n in original_plan["files"] if n != profile.UI_PATH)
                invalid[name] = "0" * 64
                with self.assertRaises(ValueError):
                    profile.source_admission(original_plan, invalid if owner == "current" else current,
                                             invalid if owner == "app" else app, plan)

        with tempfile.TemporaryDirectory(prefix="page-warning-control-") as temporary:
            directory = Path(temporary)
            owner = directory / "immutable-app"; owner.mkdir()
            for name, row in plan["files"].items():
                raw = original_ui if name == profile.UI_PATH else (ROOT / name).read_bytes()
                self.assertEqual(profile.sha(raw), row["original_sha256"])
                path = owner / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
            before = {n: profile.sha((owner / n).read_bytes()) for n in plan["files"]}
            copied = directory / "ui-source"
            with self.subTest("actual_qualified_projection_of_nine_declared_inputs"):
                profile.copy_sources(copied, ROOT, owner, plan)
                generator_path = ROOT / plan["generator_path"]
                raw_generator = generator_path.read_bytes()
                self.assertEqual(profile.sha(raw_generator), plan["generator_sha256"])
                tree = ast.parse(raw_generator, filename=str(generator_path))
                functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "ui_only_project"]
                self.assertEqual(len(functions), 1)
                scope = dict(shutil=shutil, re=re, ET=ET)
                # Executes only the exact qualified project projection function,
                # with current fixed source data. No module main or process call.
                exec(compile(ast.Module(body=functions, type_ignores=[]), str(generator_path), "exec"), scope)
                generated = scope["ui_only_project"](copied)
                observed = profile.generated_project(copied, generated, plan)
                self.assertEqual(len(observed), 11)
                self.assertEqual(before, {n: profile.sha((owner / n).read_bytes()) for n in plan["files"]})
                self.assertEqual(profile.sha((copied / profile.UI_PATH).read_bytes()), profile.UI_SHA256)
                project = generated / "project.pbxproj"; original_project = project.read_bytes()
                project.write_bytes(original_project + b"\n/* PBXTargetDependency */\n")
                with self.assertRaises(ValueError):
                    profile.generated_project(copied, generated, plan)
                project.write_bytes(original_project)

            with self.subTest("single_ui_build_selector_and_owned_destination"):
                udid = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
                command = profile.build_command(generated, directory / "derived-ui", udid, ("ENABLE_TESTABILITY=YES",))
                self.assertEqual(command[0:2], ["xcodebuild", "build-for-testing"])
                self.assertEqual([x for x in command if x.startswith("-only-testing")],
                                 ["-only-testing:" + profile.SELECTOR])
                self.assertIn("platform=iOS Simulator,id=" + udid, command)
                self.assertNotIn(profile.PREPARATION, command)
                self.assertNotIn("Anytype.xcodeproj", " ".join(command))
                with self.assertRaises(ValueError):
                    profile.build_command(generated, directory / "derived-ui", "../foreign", ())

            with self.subTest("same_job_descriptor_keeps_proven_page_target_mode"):
                admitted_descriptor = profile.same_job_descriptor(original_descriptor)
                self.assertEqual(admitted_descriptor["sha256"], profile.sha(original_descriptor))
                invalid = plistlib.loads(original_descriptor)
                invalid[profile.TARGET]["UseUITargetAppProvidedByTests"] = False
                with self.assertRaises(ValueError):
                    profile.same_job_descriptor(plistlib.dumps(invalid))
                invalid = plistlib.loads(original_descriptor)
                invalid["ForeignUITests"] = copy.deepcopy(invalid[profile.TARGET])
                with self.assertRaises(ValueError):
                    profile.same_job_descriptor(plistlib.dumps(invalid))

            with self.subTest("real_adapter_counts_fresh_setup_without_new_acceptance_credit"):
                evidence = directory / "evidence"; evidence.mkdir()
                def save(path, value):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(value, sort_keys=True) + "\n")
                caller_receipt = {}
                args = SimpleNamespace(work=directory / "work", evidence=evidence,
                                       controller=ROOT, app=owner)
                context = warning_runner.WarningContinuation(args, binding, "b" * 40, plan,
                    SimpleNamespace(save=save), SimpleNamespace(BUILD_FLAGS=("ENABLE_TESTABILITY=YES",)),
                    caller_receipt)
                execution = dict(selector=profile.PREPARATION,
                    counts=dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0))
                context.setup(execution, dict(binding))
                actual = caller_receipt["startup_warning_continuation"]["fresh_fixture_setup"]
                self.assertEqual(actual["new_preparation_acceptance_credit"], 0)
                self.assertEqual(actual["actual_setup_method_invocations"], 1)
                self.assertFalse(actual["original_simulator_state_reused"])
                self.assertEqual(actual["retained_preparation_acceptance"], plan["retained_preparation"])
                self.assertEqual(context.detail["ui_builds_started"], 0)
                self.assertEqual(context.detail["native_builds"], 0)
                self.assertEqual(context.detail["app_builds"], 0)
                with self.assertRaises(ValueError):
                    context.setup(dict(execution, selector=profile.SELECTOR), dict(binding))
                with self.assertRaises(ValueError):
                    context.setup(execution, dict(binding, nonce="c" * 32))

        for phase, taps in (("capture", 1), ("reopen", 0)):
            with self.subTest("startup_budget_and_real_action_" + phase):
                value = dict(binding, protocol="pinkha-page154-native-startup-warning-v1", phase=phase,
                    budgetSeconds=60, continueTaps=taps, status="HOME_READY",
                    admittedElapsedSeconds=5.5, elapsedSeconds=5.6)
                if phase == "capture":
                    value["exactWarningObserved"] = True
                self.assertEqual(profile.startup_observation(value, binding, phase), value)
                for invalid in (dict(value, admittedElapsedSeconds=60),
                                dict(value, continueTaps=1 - taps),
                                dict(value, nonce="d" * 32),
                                dict(value, status="FAIL")):
                    with self.assertRaises(ValueError):
                        profile.startup_observation(invalid, binding, phase)
