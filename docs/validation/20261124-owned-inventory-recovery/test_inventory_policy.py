"""One new pure host control. All command execution and kernel observations are simulated."""
import copy
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest import mock

import contracts
import current_execution as current
import owned_inventory_recovery as recovery

DATA = Path(__file__).resolve().parent / "control-data"
OUTPUT = Path(os.environ["OWNED_INVENTORY_CONTROL_OUTPUT"])

def write(path, value):
    current.write(path, value)

class OriginalFixture:
    def __init__(self, name, *, cleanup=False, mutate=None, source_failure=False,
                 followup_failure=False, wrong_identity=False, preservation_failure=False):
        self.root = OUTPUT / name
        self.root.mkdir(mode=0o700)
        self.evidence = self.root / "evidence"
        self.evidence.mkdir(mode=0o700)
        self.commands = self.evidence / "commands"
        self.commands.mkdir(mode=0o700)
        self.directory = self.evidence / "device-0"
        self.directory.mkdir(mode=0o700)
        self.phase = "pre-cleanup" if cleanup else "postboot"
        self.name = "pre-cleanup-0" if cleanup else "booted-0"
        self.item = json.loads((DATA / "device-0/created.json").read_bytes())
        self.item["directory"] = str(self.directory)
        self.intent = json.loads((DATA / "device-0/intent.json").read_bytes())
        self.started = json.loads((DATA / "commands/booted-0.started.json").read_bytes())
        self.final = json.loads((DATA / "commands/booted-0.command.json").read_bytes())
        self.log = (DATA / "commands/booted-0.log").read_bytes()
        self.argv = self.started["argv"]
        self.first = subprocess.TimeoutExpired(self.argv, 30)
        self.followup_failure = followup_failure
        self.wrong_identity = wrong_identity
        self.source_failure = source_failure
        self.preservation_failure = preservation_failure
        self.calls, self.source_checks = [], 0
        self.valid_inventory = {"devices": {self.item["runtime"]["identifier"]: [{
            "udid": self.item["udid"], "name": self.item["name"],
            "deviceTypeIdentifier": self.item["device"]["identifier"],
            "isAvailable": True, "state": "Booted"}]}}
        if mutate:
            mutate(self)
        write(self.directory / "created.json", self.item)
        write(self.directory / "intent.json", self.intent)
        write(self.commands / (self.name + ".started.json"), self.started)
        write(self.commands / (self.name + ".command.json"), self.final)
        (self.commands / (self.name + ".log")).write_bytes(self.log)
        self.driver = SimpleNamespace(root=self.commands, context=self.started["context"],
                                      cleanup_mode=cleanup, json=self.query, run=self.run)
        self.policy = recovery.Policy(self.driver, cwd=self.started["cwd"],
                                      recheck_source=self.recheck, write_json=self.save_disposition)
        self.driver.inventory_recovery = self.policy
        self.initial_bytes = {p.name: p.read_bytes() for p in self.commands.iterdir()}

    def recheck(self):
        self.source_checks += 1
        if self.source_failure and self.source_checks == 2:
            raise ValueError("simulated_source_drift_before_followup")

    def save_disposition(self, path, value):
        if self.preservation_failure and path.name.endswith("-inventory-recovery.json"):
            raise OSError("simulated_disposition_write_failure")
        write(path, value)

    def query(self, argv, name, timeout=60):
        self.calls.append({"argv": argv, "name": name, "timeout": timeout})
        if name == self.name:
            raise self.first
        if argv != self.argv or name != self.name + "-inventory-recovery-v1":
            raise ValueError("unexpected_simulated_query")
        value = copy.deepcopy(self.valid_inventory)
        if self.wrong_identity:
            next(iter(value["devices"].values()))[0]["name"] = "another-device"
        raw = (json.dumps(value) + "\n").encode()
        start = copy.deepcopy(self.started)
        start.update(timeoutSeconds=timeout, started=self.final["finished"] + 1, pid=8281, pgid=8281)
        final = copy.deepcopy(self.final)
        final.pop("firstFailure", None)
        final.update(start)
        final.update(finished=start["started"] + 1, status="PASS", returnCode=0,
                     logSHA256=contracts.sha(raw), logBytes=len(raw))
        final["kernelObservation"]["pgid"] = start["pid"]
        failure = None
        if self.followup_failure:
            failure = subprocess.TimeoutExpired(argv, timeout)
            final.update(status="FAIL", returnCode=-15, firstFailure=recovery.error(failure))
        write(self.commands / (name + ".started.json"), start)
        write(self.commands / (name + ".command.json"), final)
        (self.commands / (name + ".log")).write_bytes(raw)
        if failure:
            raise failure
        return value

    def run(self, argv, name, timeout, observe=None):
        # This adapter is used only by the unchanged cleanup policy after identity admission.
        self.calls.append({"argv": argv, "name": name, "timeout": timeout})
        if argv not in (["xcrun", "simctl", "shutdown", self.item["udid"]],
                        ["xcrun", "simctl", "delete", self.item["udid"]]):
            raise ValueError("unexpected_simulated_cleanup")
        path = self.commands / (name + ".log")
        path.write_bytes(b"")
        return path

    def observe(self):
        return current.verify_owned_inventory(self.driver, self.item, self.name,
            None if self.phase == "pre-cleanup" else {"Booted"}, phase=self.phase)

    def record(self, label):
        for name, raw in self.initial_bytes.items():
            if (self.commands / name).exists():
                assert (self.commands / name).read_bytes() == raw, name
        write(self.root / "control-observation.json", {
            "label": label, "allCommandsSimulated": True, "productExecution": False,
            "calls": self.calls, "policy": self.policy.summary(), "sourceChecks": self.source_checks})

class InventoryRecoveryControl(unittest.TestCase):
    def test_exact_timeout_recovery_and_first_failure_contract(self):
        # No kernel call or child process is made. The process-group identity below is part
        # of this explicit pure fixture, not a statement about the control process itself.
        with mock.patch.object(recovery.os, "getpgrp", return_value=1):
            fixed = json.loads(current.MANIFEST.read_bytes())
            self.assertIsNone(current.inventory_spec(fixed, None))
            self.assertEqual(current.inventory_spec(fixed, current.INVENTORY_POLICY)["budgets"], recovery.BUDGETS)
            self.assertNotIn("owned_inventory_recovery", current.module_origins(fixed, {}))

            with self.subTest("default_original_timeout_no_followup"):
                case = OriginalFixture("01-default")
                del case.driver.inventory_recovery
                with self.assertRaises(subprocess.TimeoutExpired) as caught:
                    case.observe()
                self.assertIs(caught.exception, case.first)
                self.assertEqual(len(case.calls), 1)
                case.record("default_no_recovery")

            with self.subTest("real_original_timeout_exact_postboot_recovery"):
                case = OriginalFixture("02-postboot")
                result = case.observe()
                self.assertEqual(result["status"], "RECOVERED_EXACT_IDENTITY")
                self.assertEqual(result["originalStatus"], "FAIL")
                self.assertEqual(result["firstFailure"], recovery.error(case.first))
                self.assertEqual([c["timeout"] for c in case.calls], [30, 120])
                self.assertEqual([c["argv"] for c in case.calls], [case.argv, case.argv])
                with self.assertRaises(ValueError):
                    case.observe()
                self.assertEqual(len(case.calls), 2)
                case.record("same_uuid_once_original_retained")

            with self.subTest("precleanup_identity_then_unchanged_cleanup"):
                case = OriginalFixture("03-precleanup", cleanup=True)
                result = current.cleanup_devices(case.driver, case.evidence, [case.item])
                self.assertEqual(result[0]["owned_simulator_cleanup_status"], "COMPLETE")
                self.assertEqual(result[0]["owned_simulator_cleanup_budget"]["total_seconds"], 60.0)
                self.assertEqual([c["timeout"] for c in case.calls[:2]], [30, 90])
                self.assertEqual([c["argv"][2] for c in case.calls[2:]], ["shutdown", "delete"])
                case.record("strict_identity_precedes_total60_cleanup")

            refusals = (
                ("secondary", lambda c: c.final.update(secondaryFailures=[{"type":"OSError","message":"flush"}])),
                ("preservation", lambda c: c.final.update(preservationFailures=[{"stage":"log_close","type":"OSError"}])),
                ("cleanup_failure", lambda c: c.final.update(cleanupFailure={"type":"ValueError"})),
                ("different_argv", lambda c: c.final.update(argv=c.argv[:-1]+["-j"])),
                ("different_context", lambda c: c.final.update(context={**c.final["context"],"runAttempt":"3"})),
                ("different_timeout", lambda c: c.final.update(timeoutSeconds=31)),
                ("log_hash", lambda c: c.final.update(logSHA256="0"*64)),
                ("group_unknown", lambda c: c.final["kernelObservation"].update(outcome="UNKNOWN")),
                ("group_late", lambda c: c.final["kernelObservation"].update(after_monotonic=c.final["kernelObservation"]["deadline_monotonic"]+1)),
                ("exception_cause", lambda c: setattr(c.first,"__cause__",OSError("receipt_write_failure"))),
            )
            for index, (label, mutate) in enumerate(refusals, 4):
                with self.subTest("refuse_"+label):
                    case = OriginalFixture(f"{index:02d}-{label}", mutate=mutate)
                    with self.assertRaises(subprocess.TimeoutExpired) as caught:
                        case.observe()
                    self.assertIs(caught.exception, case.first)
                    self.assertEqual(len(case.calls), 1)
                    self.assertEqual(case.policy.records[0]["status"], "REFUSED")
                    self.assertTrue(case.policy.records[0]["secondaryFailures"])
                    case.record(label)

            with self.subTest("missing_final_receipt_refuses"):
                case = OriginalFixture("14-missing-final")
                (case.commands / (case.name+".command.json")).unlink()
                with self.assertRaises(subprocess.TimeoutExpired) as caught:
                    case.observe()
                self.assertIs(caught.exception, case.first)
                self.assertEqual(len(case.calls), 1)
                case.record("only_simulated_fixture_receipt_removed")

            for label, failure in (("nonzero",subprocess.CalledProcessError(1,["xcrun"])),
                                   ("parse",ValueError("simulated_original_parse_failure"))):
                with self.subTest("original_"+label):
                    case = OriginalFixture("15-"+label)
                    case.first = failure
                    with self.assertRaises(type(failure)) as caught:
                        case.observe()
                    self.assertIs(caught.exception, failure)
                    self.assertEqual(len(case.calls), 1)
                    self.assertEqual(case.policy.records, [])
                    case.record("original_"+label+"_never_recovered")

            for label, kwargs in (("source_drift",{"source_failure":True}),
                                  ("followup_timeout",{"followup_failure":True}),
                                  ("late_receipt_write",{"preservation_failure":True})):
                with self.subTest(label):
                    case = OriginalFixture("16-"+label, **kwargs)
                    with self.assertRaises(subprocess.TimeoutExpired) as caught:
                        case.observe()
                    self.assertIs(caught.exception, case.first)
                    self.assertNotEqual(case.policy.records[0]["status"], "RECOVERED_EXACT_IDENTITY")
                    self.assertTrue(case.policy.records[0]["secondaryFailures"])
                    self.assertEqual(len(case.calls), 1 if label=="source_drift" else 2)
                    case.record(label+"_retains_original_first")

            with self.subTest("wrong_followup_identity_never_authorizes_cleanup"):
                case = OriginalFixture("17-wrong-owned-identity", cleanup=True, wrong_identity=True)
                result = current.cleanup_devices(case.driver, case.evidence, [case.item])
                self.assertEqual(result[0]["owned_simulator_cleanup_status"], "INCOMPLETE")
                self.assertEqual(result[0]["firstFailure"], recovery.error(case.first))
                self.assertEqual(len(case.calls), 2)
                self.assertFalse(any(c["argv"][2] in ("shutdown","delete") for c in case.calls))
                case.record("identity_gate_still_fail_closed")

            with self.subTest("actual_command_body_secondary_is_durable_and_ineligible"):
                case = OriginalFixture("18-body-flush")
                evidence = case.root / "actual-command-wrapper"
                evidence.mkdir(mode=0o700)
                process = SimpleNamespace(pid=8280, returncode=None)
                def wait(timeout):
                    raise subprocess.TimeoutExpired(case.argv, timeout)
                process.wait = wait
                def terminate(owned):
                    self.assertIs(owned,process)
                    owned.returncode = -15
                def absence(pgid, deadline):
                    return {"before_monotonic":deadline-1,"after_monotonic":deadline-.5,
                            "deadline_monotonic":deadline,"errno":3,"error_type":"ProcessLookupError",
                            "operation":"os.killpg","outcome":"ABSENT_ESRCH","pgid":pgid,"signal":0}
                commands = current.Commands(evidence,case.driver.context,{
                    "wave15_batch":SimpleNamespace(terminate_owned=terminate),
                    "run_owned_single_lane":SimpleNamespace(_sdk06_kernel_group_observation=absence)})
                opener = Path.open
                class FlushOnce:
                    def __init__(self, stream): self.stream,self.calls=stream,0
                    def __getattr__(self, name): return getattr(self.stream,name)
                    def flush(self):
                        self.calls += 1
                        if self.calls==1: raise OSError("simulated_inner_log_flush_failure")
                        return self.stream.flush()
                def open_file(path, *args, **kwargs):
                    stream = opener(path,*args,**kwargs)
                    return FlushOnce(stream) if path == commands.root/"booted-0.log" and args==("xb",) else stream
                with mock.patch.object(current.subprocess,"Popen",return_value=process), mock.patch.object(Path,"open",open_file):
                    with self.assertRaises(subprocess.TimeoutExpired) as caught:
                        commands.run(case.argv,"booted-0",30)
                final = json.loads((commands.root/"booted-0.command.json").read_bytes())
                self.assertEqual(final["firstFailure"],recovery.error(caught.exception))
                self.assertEqual(final["secondaryFailures"][0]["stage"],"command_body")
                with self.assertRaises(ValueError):
                    recovery._command_proof(commands,"booted-0",case.argv,30,str(current.ROOT),caught.exception)
                case.record("actual_command_wrapper_timeout_and_secondary_preserved")

if __name__ == "__main__":
    raise SystemExit("Use the frozen one-method control wrapper; no direct discovery.")
