"""New partial-creation and cleanup ownership controls; no simulator commands."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import coherent_original_preflight as owned
import coherent_original_products as original

BINDING = dict(source_sha="c" * 40, run_id="45100000123", run_attempt="2")
BASE = "10000000-0000-4000-8000-000000000001"
PHONE = "20000000-0000-4000-8000-000000000002"
PAD = "30000000-0000-4000-8000-000000000003"
RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"


def inventory():
    devices = [{"name": "iPhone Control", "identifier": "phone-type"},
               {"name": "iPad Control", "identifier": "pad-type"}]
    return dict(runtimes=[dict(name="iOS 27.0", version="27.0", identifier=RUNTIME,
        isAvailable=True, supportedDeviceTypes=devices)], devicetypes=devices,
        devices={RUNTIME: [dict(udid=BASE, name="Existing unrelated simulator",
            deviceTypeIdentifier="phone-type", isAvailable=True, state="Shutdown")]})


class Machine:
    def __init__(self, root, *, mode=None):
        self.root, self.mode = root, mode
        self.time = 0.0; self.calls = []; self.group_calls = []
        self.baseline = inventory(); self.second_saw_first_owner = False
        self.group_saw_owner = False

    def factory(self, control, directory, receipt, checkpoint, *, clock):
        if self.mode == "factory-failure": raise RuntimeError("original worker setup failure")
        return owned.Commands(control, directory, receipt, checkpoint, clock=clock,
                              execute=self.execute, stopped=self.stopped)

    def execute(self, argv, control, path, timeout):
        self.calls.append((argv, timeout))
        self.time += .1
        text = ""; error = None
        if argv[:1] == ["git"]: text = BINDING["source_sha"] + "\n" if "rev-parse" in argv else ""
        elif argv == ["xcodebuild", "-version"]: text = "Xcode 27.0\nBuild version control\n"
        elif argv == ["swift", "--version"]: text = "Synthetic Swift toolchain control\n"
        elif argv == ["xcodebuild", "-showsdks"]: text = "Synthetic iOS27 SDK control\n"
        elif argv == ["xcrun", "simctl", "list", "--json"]:
            text = json.dumps(self.baseline)
            if self.mode == "precreate-deadline": self.time += owned.PREPARE_SECONDS
        elif argv[:3] == ["xcrun", "simctl", "create"]:
            kind = "iphone" if argv[3].endswith("-iphone") else "ipad"
            lifecycle = self.root / "preflight/lifecycle"
            intent = owned.read(lifecycle / "intent.json")
            assert len(intent["lane_devices"]) == 2 and intent["baseline_udids"] == [BASE]
            assert (lifecycle / "lanes" / ("preflight-" + kind) / "create-started.json").is_file()
            if kind == "ipad":
                self.second_saw_first_owner = (
                    owned.read(self.root / "preflight/preflight.json")["selected"]["iphone"]["udid"] == PHONE
                    and (lifecycle / "lanes/preflight-iphone/owned-simulator.json").is_file())
            text = (PHONE if kind == "iphone" else PAD) + "\n"
            if self.mode == "baseline-uuid": text = BASE + "\n"
            if self.mode == "second-failure" and kind == "ipad":
                text = ""; error = subprocess.CalledProcessError(1, argv)
            if self.mode == "unknown-first" and kind == "iphone":
                text = ""; error = subprocess.CalledProcessError(1, argv)
            if self.mode == "timeout-then-group" and kind == "iphone":
                error = subprocess.TimeoutExpired(argv, timeout)
        else: raise AssertionError("Unexpected command: " + repr(argv))
        path.write_text(text)
        record = dict(argv=argv, return_code=0 if error is None else -9, worker_pid=601,
                      owned_group_cleanup="TERM_THEN_KILL", status="COMPLETE" if error is None else "FAIL")
        if error: record["error_type"] = type(error).__name__
        owned.save(path.with_suffix(".command.json"), record, original=True)
        if error: raise error
        return record

    def stopped(self, path, *, cleanup_profile):
        self.group_calls.append(path)
        assert cleanup_profile == owned.batch.COHERENT_HEART_PROFILE
        if self.mode == "timeout-then-group" and path.name == "create-iphone.command.json":
            self.group_saw_owner = (self.root / "preflight/lifecycle/lanes/preflight-iphone/owned-simulator.json").is_file()
            raise RuntimeError("later owned-group finalization failure")
        return dict(status="PASS", live_members=0, pgid=601)


def prepare_case(root, machine, *, host=lambda: None):
    with mock.patch.dict(os.environ, {"GITHUB_ENV": str(root / "job.env")}):
        return owned.prepare(root, root, BINDING, factory=machine.factory,
                             host=host, clock=lambda: machine.time)


def present(device, *, udid=None, device_type=None):
    return {"devices": {RUNTIME: [dict(udid=udid or device["udid"], name=device["name"],
        deviceTypeIdentifier=device_type or device["device"]["identifier"],
        isAvailable=True, state="Shutdown")]}}


class CoherentOriginalPreflightControls(unittest.TestCase):
    def test_success_persists_original_pair_and_first_uuid_before_second_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); machine = Machine(root)
            result = prepare_case(root, machine)
            self.assertEqual(result["status"], "PREFLIGHT_PASS_UI_NOT_RUN")
            self.assertEqual(result["source_sha"], BINDING["source_sha"])
            self.assertNotEqual(result["source_sha"], original.SOURCE)
            self.assertTrue(machine.second_saw_first_owner)
            intent, known, attempted = owned.admitted_journal(root / "preflight", BINDING)
            self.assertEqual(attempted, 2); self.assertEqual([row["udid"] for row in known], [PHONE, PAD])
            self.assertEqual(intent["baseline_udids"], [BASE])
            self.assertEqual(owned.read(root / "preflight/simulator-inventory.json"), machine.baseline)
            self.assertEqual((root / "job.env").read_text(),
                "PINKHA_UI27_IPHONE_UDID=" + PHONE + "\nPINKHA_UI27_IPAD_UDID=" + PAD + "\n")
            self.assertTrue(all(0 < timeout <= 60 for _, timeout in machine.calls))

    def test_second_create_failure_keeps_first_owner_and_cleans_only_exact_owned_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); machine = Machine(root, mode="second-failure")
            result = prepare_case(root, machine)
            self.assertEqual(result["error_type"], "CalledProcessError")
            self.assertEqual(result["selected"]["iphone"]["udid"], PHONE)
            self.assertNotIn("ipad", result["selected"]); self.assertFalse((root / "job.env").exists())
            before = (root / "preflight/preflight.json").read_bytes(); signals = []; queries = []
            def query(device, *, timeout, observation):
                queries.append(copy.deepcopy(device))
                observation.update(status="RETURNED_VALID_SCOPED_INVENTORY",
                    selector=device.get("udid", device["name"]), selector_kind="OWNED_UDID" if "udid" in device else "EXACT_PLANNED_NAME")
                return present(device) if device.get("udid") == PHONE else {"devices": {RUNTIME: []}}
            def signal(argv, **kwargs):
                signals.append(argv); return SimpleNamespace(returncode=0)
            with mock.patch.object(owned.subprocess, "check_output", return_value=BINDING["source_sha"] + "\n"), \
                 mock.patch.object(owned.batch, "scoped_device_inventory", side_effect=query), \
                 mock.patch.object(owned.batch.subprocess, "run", side_effect=signal):
                cleaned = owned.cleanup(root, root, BINDING, host=lambda: None)
            self.assertEqual(cleaned["status"], "PASS")
            self.assertEqual(signals, [["xcrun", "simctl", "delete", PHONE]])
            self.assertEqual(len(queries), 2)
            self.assertEqual(queries[1]["name"], "Pinkha-UI27-" + BINDING["run_id"] + "-ipad")
            self.assertEqual((root / "preflight/preflight.json").read_bytes(), before)

    def test_original_create_timeout_survives_later_group_failure_with_uuid_already_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); machine = Machine(root, mode="timeout-then-group")
            result = prepare_case(root, machine)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["error_type"], "TimeoutExpired")
            self.assertTrue(machine.group_saw_owner)
            self.assertEqual(result["selected"]["iphone"]["udid"], PHONE)
            command = result["commands"][-1]
            self.assertEqual(command["error_type"], "TimeoutExpired")
            self.assertEqual(command["quiescence_failure"]["error_type"], "RuntimeError")
            intent, known, attempted = owned.admitted_journal(root / "preflight", BINDING)
            self.assertEqual(attempted, 1); self.assertEqual(known[0]["udid"], PHONE)
            self.assertEqual(len(intent["lane_devices"]), 1)

    def test_preexisting_names_and_baseline_uuid_never_authorize_cleanup(self):
        for mode in ("existing-name", "baseline-uuid"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); machine = Machine(root, mode=mode)
                if mode == "existing-name":
                    machine.baseline["devices"][RUNTIME][0]["name"] = "Pinkha-UI27-" + BINDING["run_id"] + "-iphone"
                result = prepare_case(root, machine)
                self.assertEqual(result["status"], "FAIL")
                def unexpected(*args, **kwargs): self.fail("No command or cleanup policy may run")
                cleaned = owned.cleanup(root, root, BINDING, policy=unexpected, host=unexpected)
                self.assertEqual(cleaned["status"], "NO_OWNED_CREATION" if mode == "existing-name" else "FAIL")
                self.assertFalse(result["selected"])

    def test_prior_batch_cleanup_requires_exact_current_origin_and_journal_owned_uuids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); machine = Machine(root)
            prepare_case(root, machine)
            _, known, attempted = owned.admitted_journal(root / "preflight", BINDING)
            intent = dict(protocol=original.PROTOCOL, profile=owned.batch.COHERENT_HEART_PROFILE,
                source_sha=original.SOURCE, control_source_sha=BINDING["source_sha"],
                run_id=BINDING["run_id"], run_attempt=BINDING["run_attempt"],
                continuation=original.NAME, build_origin=original.origin_fields(), preflight_devices=known)
            report = dict(status="PASS", devices=[
                dict(name=known[0]["name"], status="NOT_PRESENT"),
                dict(name=known[1]["name"], udid=PAD, status="DELETED_OWNED_SIMULATOR", delete_exit_code=0)],
                inventory_queries=[dict(selector=PHONE, selector_kind="OWNED_UDID", status="RETURNED_VALID_SCOPED_INVENTORY")])
            execution = dict(intent, cleanup=report)
            def write(values):
                for name, value in zip(("batch-intent.json", "execution.json", "batch-cleanup.json"), values):
                    owned.save(root / name, value)
            write((intent, execution, report))
            self.assertEqual(owned.prior_batch_cleanup(root, BINDING, known, attempted)["new_cleanup_commands"], 0)
            with mock.patch.object(owned.subprocess, "check_output", return_value=BINDING["source_sha"] + "\n"):
                cleaned = owned.cleanup(root, root, BINDING, host=lambda: None,
                    policy=lambda *args: self.fail("Qualified current batch cleanup must not run again"))
            self.assertEqual(cleaned["status"], "PASS"); self.assertEqual(cleaned["cleanup_commands"], 0)
            for mode in ("stale-source", "stale-attempt", "foreign-owned-id", "status-only", "changed-original-report"):
                values = [copy.deepcopy(intent), copy.deepcopy(execution), copy.deepcopy(report)]
                if mode == "stale-source":
                    for value in values[:2]: value["control_source_sha"] = "f" * 40
                if mode == "stale-attempt":
                    for value in values[:2]: value["run_attempt"] = "1"
                if mode == "foreign-owned-id": values[0]["preflight_devices"][0]["udid"] = BASE
                if mode == "status-only": values[2]["devices"] = []; values[1]["cleanup"] = values[2]
                if mode == "changed-original-report": values[2]["extra"] = "changed"
                write(values)
                with self.subTest(mode=mode): self.assertIsNone(owned.prior_batch_cleanup(root, BINDING, known, attempted))

    def test_failure_before_creation_records_first_error_and_cleanup_does_not_scan(self):
        for mode in ("host-failure", "factory-failure", "precreate-deadline"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); machine = Machine(root, mode=mode)
                def host():
                    if mode == "host-failure": raise RuntimeError("original host admission failure")
                result = prepare_case(root, machine, host=host)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(owned.read(root / "preflight/preflight.json")["error"], result["error"])
                self.assertFalse(any(argv[:3] == ["xcrun", "simctl", "create"] for argv, _ in machine.calls))
                if mode == "precreate-deadline": self.assertGreater(result["elapsed_seconds"], owned.PREPARE_SECONDS)
                def unexpected(*args, **kwargs): self.fail("No host/source query or cleanup policy without owned creation")
                cleaned = owned.cleanup(root, root, BINDING, policy=unexpected, host=unexpected)
                self.assertEqual(cleaned["status"], "NO_OWNED_CREATION")

    def test_unknown_partial_create_never_cleans_baseline_or_foreign_type(self):
        for mode in ("baseline", "foreign-type"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); machine = Machine(root, mode="unknown-first")
                result = prepare_case(root, machine)
                self.assertEqual(result["error_type"], "CalledProcessError")
                self.assertFalse(result["selected"])
                signals = []
                def query(device, *, timeout, observation):
                    self.assertNotIn("udid", device)
                    self.assertEqual(device["name"], "Pinkha-UI27-" + BINDING["run_id"] + "-iphone")
                    return present(device, udid=BASE if mode == "baseline" else PHONE,
                                   device_type="different-type" if mode == "foreign-type" else "phone-type")
                with mock.patch.object(owned.subprocess, "check_output", return_value=BINDING["source_sha"] + "\n"), \
                     mock.patch.object(owned.batch, "scoped_device_inventory", side_effect=query), \
                     mock.patch.object(owned.batch.subprocess, "run", side_effect=lambda *args, **kwargs: signals.append(args)):
                    cleaned = owned.cleanup(root, root, BINDING, host=lambda: None)
                self.assertEqual(cleaned["status"], "FAIL")
                self.assertEqual(signals, [])


    def test_quiescence_timeout_and_late_zero_observations_remain_on_original_failed_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); receipt = {}
            argv = ["xcrun", "simctl", "create", "synthetic-owned-control", "type", "runtime"]
            primary = subprocess.TimeoutExpired(argv, 30)
            later = RuntimeError("Owned zero-member observation returned after its original cleanup deadline")
            later.timeout_observations = [dict(observation=1, timeout_seconds=10)]
            later.quiescence_observation = dict(status="FAIL_DEADLINE", pgid=701, live_members=0,
                observations=2, budget_seconds=10, cleanup_profile=owned.batch.COHERENT_HEART_PROFILE)
            def execute(command, cwd, path, timeout):
                path.write_text("")
                owned.save(path.with_suffix(".command.json"),
                    dict(argv=command, return_code=-9, worker_pid=701,
                         owned_group_cleanup="TERM_THEN_KILL", error_type="TimeoutExpired"), original=True)
                raise primary
            def stopped(path, *, cleanup_profile):
                self.assertEqual(cleanup_profile, owned.batch.COHERENT_HEART_PROFILE)
                raise later
            runner = owned.Commands(root, root, receipt, lambda: None, execute=execute, stopped=stopped)
            with self.assertRaises(subprocess.TimeoutExpired) as observed:
                runner.run(argv, "create-diagnostic-control", 30)
            self.assertIs(observed.exception, primary)
            detail = receipt["commands"][0]["quiescence_failure"]
            self.assertEqual(detail["timeout_observations"], later.timeout_observations)
            self.assertEqual(detail["quiescence_observation"], later.quiescence_observation)
            original_record = owned.read(root / "create-diagnostic-control.command.json")
            self.assertEqual(original_record["error_type"], "TimeoutExpired")
            self.assertNotIn("quiescence_failure", original_record)


if __name__ == "__main__":
    unittest.main()
