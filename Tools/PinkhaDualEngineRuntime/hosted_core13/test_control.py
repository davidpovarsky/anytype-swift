#!/usr/bin/env python3
"""Portable boundary controls only; never invoke Apple, simulators or accounts."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True

import admission
from originals import Originals
import run


class HostedCore13ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ["PINKHA_CORE13_ORIGINAL_SOURCE"]).resolve(strict=True)
        cls.originals = Originals(cls.source)
        try:
            cls.originals.install()
        except BaseException:
            cls.originals.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.originals.unchanged()
        cls.originals.close()

    def test_exact_original_declarations_and_thirteen_method_scope(self):
        self.assertEqual(len(self.originals.sources), 15)
        self.assertEqual(len(self.originals.proof["declarations"]), 45)
        methods = []
        for lane, count in zip(run.LANES, (9, 2, 2)):
            contract = self.originals.native_core.fixed_contract(lane)
            self.assertEqual(contract["expected_methods"], count)
            self.assertEqual(contract["declared_cases"], count)
            self.assertEqual(len(contract["compiled_identifiers"]), count)
            self.assertEqual(contract["original_target"], "PinkhaAnyUITests")
            self.assertEqual(contract["selected_target"], "AnytypeTests")
            methods.extend(contract["compiled_identifiers"])
        self.assertEqual(len(methods), 13)
        self.assertEqual(len(set(methods)), 13)
        self.assertFalse(self.originals.proof["swiftTestBodiesCopied"])
        self.assertEqual(self.originals.shared.Commands._termination_waits,
                         ((self.originals.shared.signal.SIGTERM, 15),
                          (self.originals.shared.signal.SIGKILL, 5)))

    def test_one_changed_original_byte_is_rejected_before_loading(self):
        with tempfile.TemporaryDirectory(prefix="pinkha-core13-portable-originals-") as temporary:
            root = Path(temporary).resolve()
            for path, data in self.originals.sources.items():
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
            changed = root / "Tools/MiniApps/receipt_admission.py"
            changed.write_bytes(changed.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Original control bytes changed"):
                Originals(root)

    def test_same_job_paths_and_root_authority_are_required(self):
        with tempfile.TemporaryDirectory(prefix="pinkha-core13-portable-job-") as temporary:
            root = Path(temporary).resolve()
            workspace, runtime = root / "workspace", root / "temporary"
            workspace.mkdir(); runtime.mkdir()
            (workspace / "control").mkdir()
            (workspace / "app/source").mkdir(parents=True)
            args = SimpleNamespace(control=workspace / "control", source=workspace / "app/source",
                                   build_root=runtime / "pinkha-hosted-shared-42-3",
                                   plan=runtime / "pinkha-root-plan.json", output=runtime / "pinkha-hosted-core13-42-3")
            plan = {"controlCommit": "1" * 40, "repository": admission.REPOSITORY, "readyForBuild": True,
                    "schema": "pinkha-hosted-original-shared-build-plan-v1",
                    "toolchain": {"developerDir": "/portable-fixture/Developer"}}
            env = {"GITHUB_REPOSITORY": admission.REPOSITORY, "GITHUB_ACTIONS": "true",
                   "RUNNER_ENVIRONMENT": "github-hosted", "RUNNER_ARCH": "ARM64", "GITHUB_RUN_ID": "42",
                   "GITHUB_RUN_ATTEMPT": "3", "GITHUB_JOB": "portable-control-fixture",
                   "GITHUB_WORKSPACE": str(workspace), "RUNNER_TEMP": str(runtime),
                   "GITHUB_SHA": "1" * 40, "DEVELOPER_DIR": "/portable-fixture/Developer"}
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(admission.bind_job(args, plan)["runAttempt"], "3")
                for key, value in (("GITHUB_RUN_ATTEMPT", "4"), ("RUNNER_ENVIRONMENT", "self-hosted"),
                                   ("DEVELOPER_DIR", "/different/Developer"), ("GITHUB_SHA", "2" * 40)):
                    with self.subTest(key=key), patch.dict(os.environ, {key: value}):
                        with self.assertRaises(ValueError):
                            admission.bind_job(args, plan)
                relocated = copy.copy(args)
                relocated.source = workspace / "imported-source"
                with self.assertRaisesRegex(ValueError, "relocated"):
                    admission.bind_job(relocated, plan)
                closed = copy.deepcopy(plan)
                closed["readyForBuild"] = False
                with self.assertRaisesRegex(ValueError, "root-reviewed"):
                    admission.bind_job(args, closed)

    @staticmethod
    def runtime_inventory():
        return {"runtimes": [{"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0",
                              "isAvailable": True, "version": "27.0", "buildversion": "PORTABLE-FIXTURE-ONLY"}],
                "devicetypes": [{"identifier": run.DEVICE_TYPE, "name": "iPad Pro portable fixture"}]}

    def test_actual_runtime_discovery_rejects_missing_or_ambiguous_scope(self):
        value = self.runtime_inventory()
        runtime, device = run.select_runtime(value)
        self.assertEqual(runtime["identifier"], value["runtimes"][0]["identifier"])
        self.assertEqual(device["identifier"], run.DEVICE_TYPE)
        invalid = []
        duplicate = copy.deepcopy(value)
        duplicate["runtimes"].append(dict(duplicate["runtimes"][0], identifier="com.apple.CoreSimulator.SimRuntime.iOS-27-1"))
        invalid.append(duplicate)
        for key, replacement in (("isAvailable", False), ("version", "26.0"), ("buildversion", ""),
                                 ("supportedDeviceTypes", [{"identifier": "foreign-device"}])):
            current = copy.deepcopy(value)
            current["runtimes"][0][key] = replacement
            invalid.append(current)
        missing = copy.deepcopy(value); missing["devicetypes"] = []; invalid.append(missing)
        for current in invalid:
            with self.subTest(inventory=current), self.assertRaises(ValueError):
                run.select_runtime(current)

    def test_only_actual_owned_device_and_shutdown_state_are_accepted(self):
        with tempfile.TemporaryDirectory(prefix="pinkha-core13-portable-device-") as temporary:
            path = Path(temporary).resolve() / "fixture.json"
            runtime, device = run.select_runtime(self.runtime_inventory())
            udid, lane = "00000000-0000-0000-0000-000000000042", run.LANES[0]
            row = {"udid": udid, "state": "Booted", "isAvailable": True,
                   "deviceTypeIdentifier": device["identifier"], "name": "F-Combined-fixture-" + lane}
            commands = []
            def command(argv, label, timeout, **kwargs):
                commands.append((argv, label, timeout, kwargs))
                return path, {"portableFixture": True}
            consumer = SimpleNamespace(command=command, shared_module=self.originals.shared,
                                       binding={"nonce": "fixture"})
            def write(value):
                path.write_text(json.dumps({"devices": {runtime["identifier"]: [value]}}))
            write(row)
            self.assertEqual(run.verify_created_device(consumer, lane, udid, runtime, device)["device"], row)
            with self.assertRaises(ValueError):
                run.verify_created_device(consumer, lane, udid, runtime, device, state="Shutdown")
            row["state"] = "Shutdown"; write(row)
            self.assertEqual(run.verify_created_device(consumer, lane, udid, runtime, device,
                                                       state="Shutdown")["device"]["state"], "Shutdown")
            row["name"] = "another-owner"; write(row)
            with self.assertRaises(ValueError):
                run.verify_created_device(consumer, lane, udid, runtime, device, state="Shutdown")
            self.assertTrue(all(item[0] == ["xcrun", "simctl", "list", "devices", "--json"] for item in commands))

    def test_failed_suite_receipts_and_cleanup_cannot_be_reported_as_pass_or_not_run(self):
        with tempfile.TemporaryDirectory(prefix="pinkha-core13-portable-results-") as temporary:
            directory = Path(temporary).resolve()
            (directory / "native").mkdir()
            fixture = {"status": "FAIL", "errors": [{"phase": "owned-shutdown", "error": "portable failure fixture"}]}
            (directory / "execution.json").write_text(json.dumps(fixture))
            (directory / "native/result.json").write_text(json.dumps({"status": "FAIL", "testInvoked": True}))
            row = run.lane_summary(directory, self.originals)
            self.assertEqual(row["status"], "FAIL")
            self.assertTrue(row["testInvoked"])
            self.assertEqual(row["qualifiedMethods"], 0)
            cleanup = run.include_lane_cleanup({"status": "PASS", "errors": [], "groups": []}, {run.LANES[0]: row})
            self.assertEqual(cleanup["status"], "FAIL")
            self.assertEqual(cleanup["errors"][0]["phase"], "owned-shutdown")
            # Original validator success does not override a failed owned
            # shutdown, and a started lane without a terminal receipt fails.
            (directory / "native/result.json").write_text(json.dumps({"status": "PASS", "testInvoked": True,
                "actualHostCases": {"actual_method_count": 9, "declared_case_count": 9}}))
            row = run.lane_summary(directory, self.originals)
            self.assertEqual(row["originalValidatorCounts"], {"methods": 9, "cases": 9})
            self.assertEqual(row["qualifiedMethods"], 0)
            for status in ("STARTED", "FAIL_NO_TERMINAL_LANE_RECEIPT"):
                cleanup = run.include_lane_cleanup({"status": "PASS", "errors": [], "groups": []},
                                                    {run.LANES[0]: {"status": status}})
                self.assertEqual(cleanup["status"], "FAIL")
            fixture.update(status="PASS_ORIGINAL_CORE13_SUITE", errors=[])
            (directory / "execution.json").write_text(json.dumps(fixture))
            row = run.lane_summary(directory, self.originals)
            self.assertEqual((row["qualifiedMethods"], row["qualifiedCases"]), (9, 9))

    @staticmethod
    def unresolved_original(root):
        """No process is spawned; this is an explicit portable custody fixture."""
        class OriginalFixture:
            def __init__(self):
                self.root, self.cwd, self.environment = root, root, {}
                self.groups, self.absent_groups, self.spawns, self.probes = [], set(), [], []

            def run(self, argv, label, timeout, **kwargs):
                self.spawns.append((argv, label))
                self.groups.append(42)
                raise RuntimeError("portable original owned group lacks absence proof")

            def present(self, group):
                self.probes.append(group)
                return False
        return OriginalFixture()

    def test_unresolved_original_group_closes_every_later_spawn_even_after_final_absence(self):
        with tempfile.TemporaryDirectory(prefix="pinkha-core13-portable-group-") as temporary:
            original = self.unresolved_original(Path(temporary).resolve())
            commands = run.CommandAdmission(original, self.originals.shared.error)
            with self.assertRaisesRegex(RuntimeError, "lacks absence proof"):
                commands.run(["portable-fixture-no-executable"], "first", 1)
            self.assertFalse(commands.is_open)
            for name in ("xcresult", "preserve", "shutdown", "next-suite"):
                with self.assertRaisesRegex(ValueError, "admission is closed"):
                    commands.run(["portable-fixture-no-executable"], name, 1)
            self.assertEqual(len(original.spawns), 1)
            # Use the unchanged final original read-only observer. Its new
            # positive absence cannot reopen admission or erase first failure.
            observed = self.originals.host_functions.observe_owned_groups(commands)
            self.assertEqual(observed["status"], "PASS")
            self.assertEqual(original.probes, [42])
            self.assertIn(42, original.absent_groups)
            self.originals.host_functions.observe_owned_groups(commands)
            self.assertEqual(original.probes, [42])
            with self.assertRaisesRegex(ValueError, "admission is closed"):
                commands.run(["portable-fixture-no-executable"], "after-final-observation", 1)
            self.assertEqual(len(original.spawns), 1)
            self.assertEqual(commands.blocked["firstFailure"]["type"], "RuntimeError")

    def test_group_failure_skips_device_cleanup_and_receipt_errors_preserve_first_failure(self):
        lane = run.LANES[0]
        runtime, device = run.select_runtime(self.runtime_inventory())
        for fail_receipt in (False, True):
            with self.subTest(fail_receipt=fail_receipt), tempfile.TemporaryDirectory(prefix="pinkha-core13-portable-lane-") as temporary:
                root = Path(temporary).resolve()
                original = self.unresolved_original(root / "commands")
                commands = run.CommandAdmission(original, self.originals.shared.error)
                devices, invoked, cleanup_calls = [], set(), []
                udid = "00000000-0000-0000-0000-000000000042"
                def create(*args, **kwargs):
                    devices.append(udid)
                    return udid, None
                def stage(*args, **kwargs):
                    invoked.add(udid)
                    commands.run(["portable-fixture-no-executable"], "original-test", 1)
                def preserve(*args, **kwargs):
                    cleanup_calls.append("preserve")
                    raise AssertionError("Unresolved owned process must prevent preserve invocation")
                def command(*args, **kwargs):
                    cleanup_calls.append("simctl")
                    raise AssertionError("Unresolved owned process must prevent device operations")
                consumer = SimpleNamespace(root=root, source=self.source, commands=commands, devices=devices,
                    invoked_devices=invoked, binding={"sourceSHA": "1" * 40}, built={}, create=create,
                    stage=stage, preserve=preserve, command=command)
                original_contract = self.originals.native_core.fixed_contract(lane)
                fixture_originals = SimpleNamespace(shared=self.originals.shared, source=self.source,
                    native_core=SimpleNamespace(source_contract=lambda *a, **k: original_contract), unchanged=lambda: None)
                context = {"build": {"nativeCompilationProof": {"portableFixtureOnly": True}}}
                with patch.object(run, "verify_created_device", return_value={"portableFixtureOnly": True}):
                    if fail_receipt:
                        with patch.object(self.originals.shared, "write", side_effect=OSError("portable receipt failure")):
                            outcome = run.execute_lane(consumer, lane, fixture_originals, context, runtime, device)
                    else:
                        outcome = run.execute_lane(consumer, lane, fixture_originals, context, runtime, device)
                self.assertEqual(outcome["status"], "FAIL")
                self.assertEqual(outcome["firstFailure"], {"type": "RuntimeError",
                    "message": "portable original owned group lacks absence proof"})
                self.assertEqual(cleanup_calls, [])
                self.assertEqual(len(original.spawns), 1)
                self.assertTrue(outcome["testInvoked"])
                self.assertEqual(outcome["ownedSimulator"]["status"], "UNRESOLVED_NO_FURTHER_DEVICE_OPERATION")
                row = run.lane_summary(root / "evidence/lanes" / lane, self.originals, execution=outcome)
                self.assertEqual(row["firstFailure"], outcome["firstFailure"])
                self.assertEqual(row["qualifiedMethods"], 0)
                self.assertTrue(row["testInvoked"])
                if fail_receipt:
                    self.assertEqual(outcome["receiptFailures"][0]["phase"], "lane-terminal-receipt")
                for phase in ("lane-checkpoint-receipt", "final-runtime-receipt"):
                    retained = {"status": "FAIL", "firstFailure": outcome["firstFailure"]}
                    with patch.object(self.originals.shared, "write", side_effect=OSError("portable later receipt failure")):
                        self.assertFalse(run.retain_receipt(self.originals.shared, root / (phase + ".json"), retained, phase))
                    self.assertEqual(retained["firstFailure"], outcome["firstFailure"])
                    self.assertEqual(retained["receiptFailures"][0]["phase"], phase)


if __name__ == "__main__":
    unittest.main(verbosity=2)
