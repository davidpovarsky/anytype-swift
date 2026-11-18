"""Focused rejection controls for the optional owned process-crash tail.

Docker/process observations below are injected unit fixtures, never Native
acceptance. The workflow must run the real signed-history and process phases.
"""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_native_clients as lane
from test_native_clients import container_fixture, offline_branch_fixture, state_fixture


NOW = 1_000_000_000_000


def crash_fixture():
    history = lane.merge_offline_histories({role: offline_branch_fixture(role) for role in ["creator", "recovered"]}, state_fixture())
    baseline = {"nonce": "owner", "peer_id": "original-peer", "client_fixture_sha256": "b" * 64,
                "state_sha256": "c" * 64, "history": history, "snapshot_sha256_without_local_sequence": "d" * 64}
    identity = {"heart_sha": "heart", "runtime_version": "runtime", "rpc_manifest_sha256": "schema", "registration_patch_sha256": "registry"}
    common = {"protocol": lane.CRASH_PROTOCOL, "phase": "armed_after_signed_commit_before_client_ack",
              "role": "creator", "nonce": "owner", "pid": 1, "network_namespace": "net:[actual-fixture]", "actual_ipv4": [],
              "native_network_mode": "DISCONNECTED_PROCESS_CRASH_NO_PEER_REPAIR", "peer_id": "original-peer",
              **identity, "client_fixture_sha256": "b" * 64, "state_sha256": "c" * 64, "clean_reopen_receipt_sha256": "a" * 64,
              "app_capability": "OFF", "power_loss": "NOT_RUN", "two_ios_apps": "NOT_RUN", "full_t2_acceptance": "NOT_RUN"}
    committed = {"changes_sha256": {**history["changes_sha256"], "crash-change": "e" * 64},
                 "parents": {**history["parents"], "crash-change": history["heads"]}, "heads": ["crash-change"]}
    returned = {**lane.crash_base_calls(), "PinkhaTorahOperationsReadTarget": 1}
    arm = {**common, "history_before": copy.deepcopy(history), "history_committed": copy.deepcopy(committed),
           "baseline_snapshot_sha256": "d" * 64, "request_sha256": "f" * 64, "request_bytes": 260,
           "withheld_response_bytes": 755, "claim_id": "7" * 64 + "/" + "8" * 64, "committed_change_id": "crash-change",
           "first_reply_decoded": False, "client_append_returned": False, "read_target_after_commit": 0,
           "native_append_attempts": 1, "rpc_calls": {**returned, "PinkhaTorahOperationsAppend": 1},
           "returned_byte_calls": returned, "kill_deadline_unix_ns": NOW + 30_000_000_000,
           "expected_termination": "OWNED_CONTAINER_SIGKILL", "test_passed": False}
    return baseline, identity, arm


def recovery_fixture(arm, *, finished=False):
    report = {key: arm[key] for key in lane.CRASH_COMMON_KEYS}
    calls = {**lane.crash_base_calls(), "PinkhaTorahOperationsReadTarget": 3 if finished else 2,
             "PinkhaTorahOperationsAppend": 2 if finished else 1}
    if finished:
        calls.update(AccountStop=1, AppShutdown=1)
    report.update(phase="recovered_after_owned_sigkill" if finished else "recovered_state_before_native_stop",
        armed_receipt_sha256="9" * 64, request_sha256=arm["request_sha256"], retry_request_sha256=arm["request_sha256"],
        request_bytes=arm["request_bytes"], claim_id=arm["claim_id"], committed_change_id=arm["committed_change_id"],
        history_before_read=copy.deepcopy(arm["history_committed"]), history_after_retry=copy.deepcopy(arm["history_committed"]),
        snapshot_before_retry_sha256="1" * 64, snapshot_after_retry_sha256="1" * 64,
        local_sequence_before_retry=42, local_sequence_after_retry=42, retry_disposition="ALREADY_EXISTS_SAME_PAYLOAD",
        retry_change_id="", rpc_calls=calls, returned_byte_calls=copy.deepcopy(calls), test_passed=finished)
    if finished:
        report.update(closed=True, account_stop_verified=True, post_stop_rpc="READ_AND_APPEND_NOT_LOGGED_IN")
    return report


class CrashTailControls(unittest.TestCase):
    def test_baseline_42_and_crash_12_controls_are_separate_exact_sets(self):
        original = "\n".join("--- PASS: " + name + " (0s)" for name in [*lane.CONTROL_METHODS,
            *(method + "/" + subcase for method, cases in lane.CONTROL_METHODS.items() for subcase in cases)])
        crash = "\n".join("--- PASS: " + name + " (0s)" for name in [*lane.CRASH_CONTROL_METHODS,
            *(method + "/" + subcase for method, cases in lane.CRASH_CONTROL_METHODS.items() for subcase in cases)])
        self.assertEqual(lane.validate_native_controls(original)["pass_terminals"], 42)
        self.assertEqual(lane.validate_crash_native_controls(crash)["pass_terminals"], 12)
        for changed in [original, crash + "\n--- PASS: " + lane.CRASH_COMMIT_METHOD + " (0s)",
                        crash.replace("--- PASS:", "--- SKIP:", 1), crash.rsplit("\n", 1)[0], crash + "\n" + original]:
            with self.subTest(changed=changed[-70:]), self.assertRaises(ValueError):
                lane.validate_crash_native_controls(changed)

    def test_arm_requires_commit_before_read_or_ack_and_exact_baseline(self):
        baseline, identity, arm = crash_fixture()
        lane.validate_crash_arm(arm, baseline, "a" * 64, identity, NOW)
        changes = {
            "decoded": lambda r: r.update(first_reply_decoded=True),
            "returned": lambda r: r.update(client_append_returned=True),
            "claimed-pass": lambda r: r.update(test_passed=True),
            "read-before-kill": lambda r: r.update(read_target_after_commit=1),
            "second-append": lambda r: r.update(native_append_attempts=2),
            "no-held-reply": lambda r: r.update(withheld_response_bytes=0),
            "expired": lambda r: r.update(kill_deadline_unix_ns=NOW),
            "unbounded": lambda r: r.update(kill_deadline_unix_ns=NOW + 120_000_000_000),
            "no-native-source": lambda r: r.update(heart_sha="different"),
            "different-device": lambda r: r.update(peer_id="different"),
            "different-original-store": lambda r: r.update(clean_reopen_receipt_sha256="e" * 64),
            "peer-network": lambda r: r.update(actual_ipv4=["172.20.0.2"]),
            "power-loss-overclaim": lambda r: r.update(power_loss="PASS"),
            "extra-private-field": lambda r: r.update(request_payload="unexpected"),
            "append-acked": lambda r: r["returned_byte_calls"].update(PinkhaTorahOperationsAppend=1),
            "graceful-stop": lambda r: r["rpc_calls"].update(AccountStop=1),
            "missing-commit": lambda r: r["history_committed"]["changes_sha256"].pop("crash-change"),
            "extra-commit": lambda r: r["history_committed"]["changes_sha256"].update(extra="e" * 64),
            "changed-original": lambda r: r["history_committed"]["changes_sha256"].update(root="e" * 64),
            "missing-second-parent": lambda r: r["history_committed"]["parents"].update({"crash-change": ["creator-change-2"]}),
            "wrong-head": lambda r: r["history_committed"].update(heads=["creator-change-2"]),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                altered = copy.deepcopy(arm)
                change(altered)
                with self.assertRaises((ValueError, KeyError)):
                    lane.validate_crash_arm(altered, baseline, "a" * 64, identity, NOW)

    def test_recovery_requires_encoded_identity_history_snapshot_and_native_stop(self):
        baseline, identity, arm = crash_fixture()
        changes = {
            "rewritten-request": lambda r: r.update(retry_request_sha256="0" * 64),
            "different-claim": lambda r: r.update(claim_id="0" * 64 + "/" + "1" * 64),
            "created-on-retry": lambda r: r.update(retry_disposition="CREATED"),
            "extra-change-id": lambda r: r.update(retry_change_id="extra"),
            "missing-persisted": lambda r: r["history_before_read"]["changes_sha256"].pop("crash-change"),
            "retry-repairs-history": lambda r: r["history_after_retry"]["changes_sha256"].update(extra="0" * 64),
            "snapshot-changed": lambda r: r.update(snapshot_after_retry_sha256="0" * 64),
            "sequence-changed": lambda r: r.update(local_sequence_after_retry=43),
            "wrong-ack-count": lambda r: r["returned_byte_calls"].update(PinkhaTorahOperationsAppend=99),
            "account-recreated": lambda r: r["rpc_calls"].update(AccountCreate=1),
        }
        for finished in [False, True]:
            value = recovery_fixture(arm, finished=finished)
            lane.validate_crash_recovery(value, baseline, "a" * 64, identity, arm, "9" * 64, finished=finished)
            for name, change in changes.items():
                with self.subTest(finished=finished, name=name):
                    altered = copy.deepcopy(value)
                    change(altered)
                    with self.assertRaises(ValueError):
                        lane.validate_crash_recovery(altered, baseline, "a" * 64, identity, arm, "9" * 64, finished=finished)
            with self.assertRaises(ValueError):
                lane.validate_crash_recovery(value, baseline, "a" * 64, identity, arm, "9" * 64, finished=not finished)

    def run_kill_fixture(self, temp, *, mutate=None, exit_code=137, oom=False, terminal="",
                         arm_age_seconds=0, phase_seconds=60, elapsed_after_kill=None, command_budgets=None, start_record=None):
        directory, binary = Path(temp), Path(temp) / "native.test"
        baseline, identity, arm = crash_fixture()
        path = directory / "crash-armed.json"
        path.write_text(json.dumps(arm))
        arm_hash = lane.digest(path)
        docker = lane.OwnedDocker(directory, {}, lambda: None, scenario="offline", crash_after_commit=True)
        docker.owner, docker.prefix = "owner", "owned"
        resource = {"kind": "container", "name": "owned-creator-crash-commit", "id": "id-creator",
                    "role": "creator", "private": str(directory)}
        info = container_fixture("creator")
        info["Name"] = "/" + resource["name"]
        info["Args"] = lane.native_arguments("offline", lane.CRASH_COMMIT_METHOD)
        info["Config"]["User"] = f"{os.getuid()}:{os.getgid()}"
        info["Config"]["Env"] += ["PINKHA_T2_CLIENT_SCENARIO=" + lane.OFFLINE_PROTOCOL, "PINKHA_T2_CRASH_PHASE=commit"]
        info["HostConfig"]["NetworkMode"] = "none"
        info["NetworkSettings"]["Networks"] = {"none": {"IPAddress": ""}}
        info["Mounts"][0]["Source"], info["Mounts"][1]["Source"] = str(directory), str(binary)
        info["State"].update(StartedAt="synthetic-fixed-start", OOMKilled=False)
        info["RestartCount"] = 0
        live = {"container_id": "id-creator", "host_pid": 123, "network_namespace": arm["network_namespace"],
                "started_at": "synthetic-fixed-start"}
        namespace = arm["network_namespace"]
        if mutate:
            namespace = mutate(info, resource, arm) or namespace
        commands = []
        clock = {"wall_ns": NOW + int(arm_age_seconds * 1_000_000_000), "monotonic": 100.0}
        def command(args, name, timeout=30, destination=None):
            commands.append(list(args))
            if command_budgets is not None:
                command_budgets.append((name, timeout))
            # Inject elapsed time only for the kill call and its subsequent
            # observations. These are controller controls, not real Docker proof.
            if name == "inject-owned-crash" or info["State"].get("Running") is False:
                elapsed = (elapsed_after_kill or {}).get(name, 0)
                clock["wall_ns"] += int(elapsed * 1_000_000_000)
                clock["monotonic"] += elapsed
            if args[:2] == ["container", "ls"]:
                return info["Id"]
            if args[:2] == ["container", "inspect"]:
                return json.dumps([info])
            if args[:2] == ["container", "kill"]:
                info["State"].update(Running=False, Pid=0, ExitCode=exit_code, OOMKilled=oom, FinishedAt="synthetic-finish")
                return info["Id"]
            if args[:2] == ["container", "wait"]:
                return str(exit_code)
            if args[:2] == ["container", "logs"]:
                header = "=== RUN   " + lane.CRASH_COMMIT_METHOD + "\n" if start_record is None else start_record
                destination.write_text(header + terminal)
                return ""
            self.fail("Unexpected unit-fixture Docker operation")
        with patch.object(docker, "command", side_effect=command), patch.object(lane.os, "readlink", return_value=namespace), \
                patch.object(lane.time, "time_ns", side_effect=lambda: clock["wall_ns"]), \
                patch.object(lane.time, "monotonic", side_effect=lambda: clock["monotonic"]):
            try:
                result = lane.kill_owned_crash_process(docker, resource, live, arm, arm_hash, baseline, "a" * 64, identity,
                                                        directory, binary, "pinned-image-id", lane.time.monotonic() + phase_seconds)
                return result, commands, None
            except ValueError as error:
                return None, commands, error

    def test_only_exact_owned_live_identity_can_receive_deliberate_kill(self):
        with tempfile.TemporaryDirectory() as temp:
            result, commands, error = self.run_kill_fixture(temp)
            self.assertIsNone(error)
            self.assertEqual(result["native_named_pass"], 0)
            self.assertEqual(result["intentional_kill_count"], 1)
            self.assertEqual([c for c in commands if c[:2] == ["container", "kill"]],
                             [["container", "kill", "--signal", "KILL", "id-creator"]])
            self.assertLess(result["termination_observed_unix_ns"], result["kill_deadline_unix_ns"])
        for age, phase, expected in [(29.5, 60, 0.5), (0, 0.25, 0.25), (29.5, 0.25, 0.25)]:
            with self.subTest(arm_age=age, phase_remaining=phase), tempfile.TemporaryDirectory() as temp:
                budgets = []
                result, _, error = self.run_kill_fixture(temp, arm_age_seconds=age, phase_seconds=phase,
                                                        command_budgets=budgets)
                self.assertIsNone(error)
                self.assertIsNotNone(result)
                bounded = [(name, timeout) for name, timeout in budgets
                           if name in {"inject-owned-crash", "wait-owned-crash"}]
                self.assertEqual(len(bounded), 2)
                for _, timeout in bounded:
                    self.assertGreater(timeout, 0)
                    self.assertLessEqual(timeout, expected)
        with tempfile.TemporaryDirectory() as temp:
            budgets = []
            result, _, error = self.run_kill_fixture(
                temp, arm_age_seconds=29, elapsed_after_kill={"inject-owned-crash": 0.25, "wait-owned-crash": 0.25},
                command_budgets=budgets)
            self.assertIsNone(error)
            self.assertEqual(dict(budgets)["inject-owned-crash"], 1)
            self.assertEqual(dict(budgets)["wait-owned-crash"], 0.75)
            self.assertEqual(result["termination_observed_unix_ns"], NOW + 29_500_000_000)
        alterations = {
            "foreign-owner": lambda i, r, a: i["Config"]["Labels"].update({lane.OWNER_LABEL: "foreign"}),
            "foreign-id": lambda i, r, a: i.update(Id="other-container"),
            "foreign-name": lambda i, r, a: i.update(Name="/someone-else"),
            "replaced-pid": lambda i, r, a: i["State"].update(Pid=999),
            "replaced-start": lambda i, r, a: i["State"].update(StartedAt="later-start"),
            "auto-restart": lambda i, r, a: i.update(RestartCount=1),
            "already-exited": lambda i, r, a: i["State"].update(Running=False),
            "namespace": lambda i, r, a: "net:[someone-else]",
            "expired-arm": lambda i, r, a: a.update(kill_deadline_unix_ns=NOW - 1),
            "wrong-phase": lambda i, r, a: i["Args"].__setitem__(1, "^" + lane.METHOD + "$"),
            "wrong-mount": lambda i, r, a: i["Mounts"][0].update(Source="/other-data"),
        }
        for name, mutate in alterations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                result, commands, error = self.run_kill_fixture(temp, mutate=mutate)
                self.assertIsNotNone(error)
                self.assertIsNone(result)
                self.assertFalse(any(c[:2] == ["container", "kill"] for c in commands))

    def test_wrong_exit_oom_or_normal_terminal_cannot_be_intentional_crash_pass(self):
        for case in [{"exit_code": 0}, {"oom": True},
                     {"terminal": "--- PASS: " + lane.CRASH_COMMIT_METHOD + " (1s)\n"},
                     {"terminal": "--- FAIL: " + lane.CRASH_COMMIT_METHOD + " (1s)\n"},
                     {"terminal": "--- SKIP: " + lane.CRASH_COMMIT_METHOD + " (1s)\n"},
                     {"start_record": ""},
                     {"start_record": "=== RUN:   " + lane.CRASH_COMMIT_METHOD + "\n"},
                     {"start_record": ("=== RUN   " + lane.CRASH_COMMIT_METHOD + "\n") * 2},
                     {"start_record": "=== RUN   " + lane.CRASH_COMMIT_METHOD + "Suffix\n"},
                     {"start_record": "prefix === RUN   " + lane.CRASH_COMMIT_METHOD + "\n"},
                     {"start_record": "=== RUN\n" + lane.CRASH_COMMIT_METHOD + "\n"},
                     {"elapsed_after_kill": {"inject-owned-crash": 30}},
                     {"elapsed_after_kill": {"wait-owned-crash": 30}},
                     {"elapsed_after_kill": {"inject-owned-crash": 29.75, "wait-owned-crash": 0.25}},
                     {"elapsed_after_kill": {"inspect-owned": 30}},
                     {"phase_seconds": 0.25, "elapsed_after_kill": {"wait-owned-crash": 0.25}}]:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                result, commands, error = self.run_kill_fixture(temp, **case)
                self.assertIsNone(result)
                self.assertIsNotNone(error)
                self.assertEqual(sum(c[:2] == ["container", "kill"] for c in commands), 1)

    def test_private_request_and_original_store_identity_are_not_synthesized(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            request = directory / "request.private"
            request.write_bytes(b"synthetic-encoded-request")
            request.chmod(0o600)
            identity = lane.crash_request_identity(request)
            self.assertEqual(identity["bytes"], len(b"synthetic-encoded-request"))
            request.chmod(0o644)
            with self.assertRaises(ValueError):
                lane.crash_request_identity(request)
            link = directory / "link.private"
            link.symlink_to(request)
            with self.assertRaises(ValueError):
                lane.crash_request_identity(link)
            (directory / "account-root").mkdir()
            with self.assertRaises(ValueError):
                lane.crash_store_identity(directory)
            db = directory / "account-root" / "synthetic.db"
            db.write_bytes(b"synthetic-store")
            old = lane.crash_store_identity(directory)
            replacement = db.with_suffix(".tmp")
            replacement.write_bytes(b"replacement")
            replacement.replace(db)
            self.assertNotEqual(old, lane.crash_store_identity(directory))

    def test_crash_publication_excludes_retained_request_and_scans_new_logs(self):
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            creator = private / "creator"
            creator.mkdir(parents=True)
            needles = ["synthetic-account-key-long", "synthetic-mnemonic-long"]
            (creator / "sensitive-needles.private").write_text(json.dumps(needles))
            (creator / "crash-request.private").write_text("private encoded request")
            for name in ["crash-armed.json", "crash-recover-ready.json", "crash-recovered.json", "crash-native.log", "crash-recover-native.log"]:
                (creator / name).write_text("fixed-public-proof")
            evidence = Path(temp) / "evidence"
            evidence.mkdir()
            result = lane.publish_native_evidence(private, evidence, scenario="offline", crash_after_commit=True)
            self.assertEqual(len(result["files_sha256"]), 5)
            self.assertFalse(any(name.endswith(".private") for name in result["files_sha256"]))
            default = Path(temp) / "default"
            default.mkdir()
            self.assertEqual(lane.publish_native_evidence(private, default, scenario="offline")["files_sha256"], {})
            (creator / "crash-native.log").write_text(needles[0])
            withheld = Path(temp) / "withheld"
            withheld.mkdir()
            with self.assertRaises(ValueError):
                lane.publish_native_evidence(private, withheld, scenario="offline", crash_after_commit=True)
            self.assertFalse((withheld / "native-clients").exists())

    def test_default_or_wrong_role_cannot_start_a_crash_process(self):
        with tempfile.TemporaryDirectory() as temp:
            for enabled, role, network in [(False, "creator", None), (True, "recovered", None), (True, "creator", {"Name": "lan"})]:
                docker = lane.OwnedDocker(Path(temp), {}, lambda: None, scenario="offline", crash_after_commit=enabled)
                with patch.object(docker, "command") as command, self.assertRaises(ValueError):
                    docker.start(role, network, Path(temp), Path(temp) / "native.test", "fixture", lane.time.monotonic() + 1,
                                 method=lane.CRASH_COMMIT_METHOD)
                command.assert_not_called()
                self.assertEqual(docker.resources, [])
            with self.assertRaises(ValueError):
                lane.native_arguments("bootstrap", lane.CRASH_COMMIT_METHOD)
            with self.assertRaises(ValueError):
                lane.OwnedDocker(Path(temp), {}, lambda: None, scenario="bootstrap", crash_after_commit=True)


if __name__ == "__main__":
    unittest.main()
