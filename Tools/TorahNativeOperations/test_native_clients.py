"""Rejection controls for source, isolated native clients and evidence publication.

These controls do not create accounts or claim Docker/Native acceptance.
"""
import copy
from contextlib import nullcontext, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import run_native_clients as lane


def state_fixture():
    return {"AccountID": "account", "SpaceID": "space", "DocumentID": "document", "BlockID": "block",
            "RootID": "root", "OperationID": "1" * 32, "OperationSHA256": "2" * 64,
            "ClaimID": "3" * 64 + "/" + "4" * 64, "ChangeID": "change",
            "RawChanges": {"root": "5" * 64, "change": "6" * 64}, "Heads": ["change"]}


def container_fixture(role="recovered"):
    return {"Id": "id-" + role, "Name": "/owned-" + role, "Image": "pinned-image-id",
            "Path": "/fixture/native.test", "Args": ["-test.run", "^" + lane.METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=1000s"],
            "Config": {"Labels": {lane.OWNER_LABEL: "owner"}, "Image": lane.IMAGE, "User": "1001:1001",
                       "Env": ["PINKHA_T2_CLIENT_ROLE=" + role, "PINKHA_T2_CLIENT_NONCE=owner"]},
            "HostConfig": {"ReadonlyRootfs": True, "Privileged": False, "CapDrop": ["ALL"],
                           "SecurityOpt": ["no-new-privileges"], "NetworkMode": "owned-network", "PortBindings": {}, "PidMode": "", "Init": False},
            "Mounts": [{"Type": "bind", "Destination": "/private", "Source": str(Path("/owned/" + role)), "RW": True},
                       {"Type": "bind", "Destination": "/fixture/native.test", "Source": str(Path("/owned/native.test")), "RW": False}],
            "State": {"Running": True, "Pid": 123},
            "NetworkSettings": {"SandboxID": "sandbox-" + role,
                                "Networks": {"owned-network": {"NetworkID": "network-id", "IPAddress": "172.30.0.3"}}}}


def ready_fixture(role="recovered"):
    state = state_fixture()
    identity = {"heart_sha": "heart", "runtime_version": "runtime", "fixture_sha256": "account-fixture",
                "rpc_manifest_sha256": "schema", "registration_patch_sha256": "registry"}
    report = {"protocol": lane.PROTOCOL, "role": role, "nonce": "owner", "pid": 1, "network_namespace": "net:[native]",
              "bridge_ipv4": "172.30.0.3", "peer_id": "peer", "native_server_port": 4000, "heart_sha": "heart",
              "runtime_version": "runtime", "account_fixture_sha256": "account-fixture", "rpc_manifest_sha256": "schema",
              "registration_patch_sha256": "registry", "client_fixture_sha256": "clients-fixture", "state_sha256": "state-hash",
              "account_id": state["AccountID"], "space_id": state["SpaceID"], "document_id": state["DocumentID"],
              "block_id": state["BlockID"], "private_root_id": state["RootID"], "raw_changes_sha256": state["RawChanges"],
              "heads": state["Heads"], "initial_account_root": "OBSERVED_EMPTY", "native_local_only_requested": True,
              "native_lan_enabled_requested": True, "ordinary_document": "PASS_NATIVE_OBJECT_SHOW",
              "private_read": "PASS_GENERATED_RPC_ORIGINAL_SIGNED_HISTORY", "app_capability": "OFF",
              "two_ios_apps": "NOT_RUN", "offline_conflict_merge": "NOT_RUN",
              "active_private_append": "NONE_RECOVERED_CLIENT_READ_ONLY" if role == "recovered" else "ONE_CREATOR_GENERATED_RPC_APPEND"}
    return state, identity, report


class NativeClientControls(unittest.TestCase):
    @unittest.skipUnless(hasattr(lane.os, "geteuid"), "POSIX publication modes")
    def test_exact_existing_publication_modes_do_not_attempt_foreign_chmod(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp)
            folder = evidence / "build"
            folder.mkdir(mode=0o755)
            path = folder / "receipt.json"
            path.write_text("{}")
            path.chmod(0o644)
            folder.chmod(0o755)
            # The actual files/modes are local; foreign process ownership and
            # the kernel's non-owner chmod failure are injected, not claimed
            # as an actual cross-UID filesystem execution.
            with patch.object(lane.os, "geteuid", return_value=path.stat().st_uid + 1), \
                    patch.object(Path, "chmod", side_effect=PermissionError("synthetic non-owner chmod")) as chmod:
                lane.normalize_evidence_permissions(evidence)
            chmod.assert_not_called()
            self.assertEqual(path.read_text(), "{}")

    @unittest.skipUnless(hasattr(lane.os, "geteuid"), "POSIX publication modes")
    def test_wrong_foreign_mode_and_symlink_remain_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            evidence = parent / "evidence"
            evidence.mkdir()
            path = evidence / "receipt.json"
            path.write_text("{}")
            path.chmod(0o600)
            with patch.object(lane.os, "geteuid", return_value=path.stat().st_uid + 1), \
                    patch.object(Path, "chmod", side_effect=AssertionError("foreign chmod must not run")) as chmod:
                with self.assertRaisesRegex(ValueError, "Foreign-owned evidence"):
                    lane.normalize_evidence_permissions(evidence)
            chmod.assert_not_called()
            self.assertEqual(lane.stat.S_IMODE(path.stat().st_mode), 0o600)
            lane.normalize_evidence_permissions(evidence)
            self.assertEqual(lane.stat.S_IMODE(path.stat().st_mode), 0o644)
            outside = parent / "outside.private"
            outside.write_text("synthetic private bytes")
            outside.chmod(0o600)
            (evidence / "link").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "Unsafe evidence publication entry"):
                lane.normalize_evidence_permissions(evidence)
            self.assertEqual(lane.stat.S_IMODE(outside.stat().st_mode), 0o600)

    def test_finalization_faults_emit_diagnostics_preserve_failure_and_propagate_cancellation(self):
        prefix = "::notice title=Pinkha T2 diagnostic::"
        for status, original_error in [("FAIL", "TimeoutError"), ("CANCELLED", "KeyboardInterrupt"),
                                       ("PASS_TWO_NATIVE_CLIENTS_LAN_COLD_BOOTSTRAP", None)]:
            receipt = {"status": status, "error_type": original_error, "diagnostic_stage": "WAIT_RECOVERED"}
            saved = []
            output = io.StringIO()
            with patch.object(lane, "normalize_evidence_permissions", side_effect=PermissionError("synthetic private path")), \
                    patch.object(lane, "normalize_evidence_entry"), \
                    redirect_stdout(output):
                accepted = lane.finish_evidence(receipt, Path("unused"), Path("unused/receipt.json"),
                                                lambda: saved.append(copy.deepcopy(receipt)), emit_notice=True)
            self.assertFalse(accepted)
            self.assertEqual(receipt["status"], "CANCELLED" if status == "CANCELLED" else "FAIL")
            self.assertEqual(receipt["error_type"], original_error)
            self.assertEqual(len(saved), 2)
            self.assertEqual(saved[-1], receipt)
            notice = json.loads(output.getvalue().strip()[len(prefix):])
            self.assertEqual(notice["finalization"]["permissions_error"], "PERMISSION_FAILURE")
            self.assertNotIn("synthetic private", output.getvalue())
        receipt = {"status": "FAIL", "error_type": "TimeoutError"}
        output = io.StringIO()
        with patch.object(lane, "normalize_evidence_permissions"), \
                patch.object(lane, "normalize_evidence_entry"), \
                patch("builtins.print", wraps=print) as emitted, redirect_stdout(output):
            checkpoint = unittest.mock.Mock(side_effect=OSError("synthetic receipt write"))
            self.assertFalse(lane.finish_evidence(receipt, Path("unused"), Path("unused/receipt.json"), checkpoint, emit_notice=True))
        self.assertEqual(checkpoint.call_count, 2)
        self.assertEqual(emitted.call_count, 1)
        self.assertEqual(receipt["error_type"], "TimeoutError")
        notice = json.loads(output.getvalue().strip()[len(prefix):])
        self.assertEqual(notice["finalization"]["receipt_error"], "FILESYSTEM_ERROR")
        for stopped_at in ["permissions", "checkpoint"]:
            for stop in [KeyboardInterrupt, SystemExit]:
                with patch.object(lane, "normalize_evidence_permissions", side_effect=stop if stopped_at == "permissions" else None), \
                        patch.object(lane.diagnostics, "emit_current_run_notice") as emitted:
                    checkpoint = unittest.mock.Mock(side_effect=stop if stopped_at == "checkpoint" else None)
                    with self.assertRaises(stop):
                        lane.finish_evidence(receipt, Path("unused"), Path("unused/receipt.json"), checkpoint, emit_notice=True)
                emitted.assert_not_called()

    @unittest.skipUnless(hasattr(lane.os, "geteuid"), "POSIX publication modes and umask")
    def test_atomic_receipt_mode_after_success_failure_and_failed_receipt_chmod(self):
        self.assertIs(lane.write, lane.base.write_json)
        cases = [
            ("PASS_TWO_NATIVE_CLIENTS_LAN_COLD_BOOTSTRAP", None, None),
            ("FAIL", "TimeoutError", "evidence"),
            ("CANCELLED", "KeyboardInterrupt", "evidence"),
            ("PASS_TWO_NATIVE_CLIENTS_LAN_COLD_BOOTSTRAP", None, "receipt_once"),
            ("PASS_TWO_NATIVE_CLIENTS_LAN_COLD_BOOTSTRAP", None, "receipt_always"),
        ]
        original_chmod = Path.chmod
        for status, original_error, fault in cases:
            with self.subTest(status=status, fault=fault), tempfile.TemporaryDirectory() as temp:
                evidence = Path(temp)
                path = evidence / "native-clients-build.json"
                receipt = {"status": status, "error_type": original_error,
                           "commands": [{"name": "completed-build", "status": "PASS_EXIT_0"}]}
                old_umask = lane.os.umask(0o077)
                try:
                    lane.write(path, receipt)
                    self.assertEqual(lane.stat.S_IMODE(path.stat().st_mode), 0o600)
                    chmod_calls = []

                    def controlled_chmod(item, mode, **kwargs):
                        if item == path:
                            chmod_calls.append(mode)
                            if fault == "receipt_always" or (fault == "receipt_once" and len(chmod_calls) == 1):
                                raise PermissionError("synthetic receipt mode failure")
                        return original_chmod(item, mode, **kwargs)

                    checkpoint = unittest.mock.Mock(side_effect=lambda: lane.write(path, receipt))
                    normalize = (patch.object(lane, "normalize_evidence_permissions", side_effect=PermissionError("synthetic evidence mode"))
                                 if fault == "evidence" else nullcontext())
                    with normalize, patch.object(Path, "chmod", controlled_chmod), \
                            patch.object(lane.diagnostics, "emit_current_run_notice") as emitted:
                        accepted = lane.finish_evidence(receipt, evidence, path, checkpoint, emit_notice=True)
                    self.assertEqual(accepted, fault is None)
                    self.assertEqual(checkpoint.call_count, 1 if fault is None else 2)
                    saved = json.loads(path.read_text())
                    self.assertEqual(saved["status"], status if fault is None or status == "CANCELLED" else "FAIL")
                    self.assertEqual(saved["error_type"], original_error)
                    self.assertEqual(saved["commands"], [{"name": "completed-build", "status": "PASS_EXIT_0"}])
                    self.assertTrue(saved["finished_at"])
                    if fault is not None:
                        self.assertEqual(saved["evidence_permissions_error_type"], "PermissionError")
                    # A persistent filesystem denial remains FAIL with a private
                    # file; it is never treated as successful publication.
                    self.assertEqual(lane.stat.S_IMODE(path.stat().st_mode), 0o600 if fault == "receipt_always" else 0o644)
                    emitted.assert_called_once_with(receipt, evidence)
                finally:
                    lane.os.umask(old_umask)

    def test_live_diagnostic_uses_only_fixed_records_and_labels_the_outer_context(self):
        raw = (b"unrelated synthetic-private-payload /private/account-id\n"
               b"T2_NATIVE_READ_BOUNDARY error_type=*private.syntheticType unwrap_type=*private.secretType "
               b"unknown_tree=true no_responsible_peers=false tree_closed=false tree_deleted=false "
               b"space_closed=false cancelled=false deadline=false context_nil=false context_peer_missing=true\n"
               b"    native_client_phase_test.go:381: T2_READ_OBSERVATION code=HISTORY_UNAVAILABLE snapshot_present=false readiness=WAIT\n")
        result = lane.diagnostics.parse_fixed_records(raw)
        self.assertEqual(result["last_read"], {"wire_code": "HISTORY_UNAVAILABLE", "snapshot_present": False, "readiness": "WAIT"})
        self.assertTrue(result["last_native_error"]["unknown_tree"])
        self.assertTrue(result["last_native_error"]["outer_context_peer_missing"])
        self.assertNotIn("context_peer_missing", result["last_native_error"])
        for private in ["private", "payload", "account-id", "syntheticType", "secretType"]:
            self.assertNotIn(private, json.dumps(result))

    def test_malformed_or_unknown_diagnostic_records_never_echo_raw_values(self):
        good = b"T2_READ_OBSERVATION code=NULL snapshot_present=true readiness=READY\n"
        for invalid in [b"T2_READ_OBSERVATION code=synthetic-private-code snapshot_present=false readiness=WAIT",
                        b"T2_READ_OBSERVATION code=NULL snapshot_present=true readiness=READY extra=synthetic-private-id",
                        b"T2_NATIVE_READ_BOUNDARY error_type=synthetic-private-error\n::error::synthetic-private-content",
                        b"T2_READ_OBSERVATION code=FUTURE_CODE snapshot_present=false readiness=WAIT"]:
            result = lane.diagnostics.parse_fixed_records(good + invalid)
            self.assertEqual(result, {"records": "MALFORMED_FIXED_RECORD", "last_read": "WITHHELD", "last_native_error": "WITHHELD"})

    def test_live_diagnostic_does_not_read_before_owned_cleanup_and_secret_scan(self):
        for cleanup, publication in [("FAIL", "PASS_SECRET_SCANNED_EXACT_ALLOWLIST"),
                                     ("PASS", "WITHHELD_NO_SECRET_INVENTORY"), (None, None)]:
            receipt = {"diagnostic_stage": "WAIT_RECOVERED", "owned_cleanup": {"status": cleanup},
                       "native_publication": {"status": publication}}
            with patch.object(lane.diagnostics, "read_current_published_log", side_effect=AssertionError("must not read")) as reader:
                result = lane.diagnostics.summarize(receipt, Path("unused"))
            reader.assert_not_called()
            self.assertEqual(result["log_publication"], "WITHHELD")
            self.assertEqual(result["roles"], {role: {"source": "WITHHELD"} for role in ["creator", "recovered"]})

    def test_live_diagnostic_requires_the_exact_current_published_log_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp)
            target = evidence / "native-clients/recovered/native.log"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"T2_READ_OBSERVATION code=PROJECTION_BEHIND snapshot_present=false readiness=WAIT\n")
            receipt = {"diagnostic_stage": "WAIT_RECOVERED", "status": "FAIL", "error_type": "TimeoutError",
                       "owned_cleanup": {"status": "PASS"}, "native_publication": {
                           "status": "PASS_SECRET_SCANNED_EXACT_ALLOWLIST", "files_sha256": {"recovered/native.log": lane.digest(target)}}}
            before = copy.deepcopy(receipt)
            result = lane.diagnostics.summarize(receipt, evidence)
            self.assertEqual(result["roles"]["recovered"]["last_read"]["wire_code"], "PROJECTION_BEHIND")
            self.assertEqual(result["roles"]["creator"]["source"], "UNAVAILABLE_OR_HASH_MISMATCH")
            self.assertEqual(receipt, before, "diagnostics cannot rewrite acceptance, source or cleanup")
            target.write_bytes(target.read_bytes() + b"changed synthetic run\n")
            result = lane.diagnostics.summarize(receipt, evidence)
            self.assertEqual(result["roles"]["recovered"], {"source": "UNAVAILABLE_OR_HASH_MISMATCH"})

    def test_diagnostic_notice_is_fixed_json_and_cannot_turn_failure_into_success(self):
        receipt = {"status": "FAIL", "diagnostic_stage": "private-stage\n::error::injected",
                   "error_type": "private-error-name", "cleanup_or_publication_error_type": "private-cleanup-name",
                   "run_id": "private-run-id", "app_sha": "private-source", "full_t2_acceptance": "NOT_RUN"}
        before = copy.deepcopy(receipt)
        output = io.StringIO()
        with redirect_stdout(output):
            lane.diagnostics.emit_current_run_notice(receipt, Path("unused"))
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        prefix = "::notice title=Pinkha T2 diagnostic::"
        self.assertTrue(lines[0].startswith(prefix))
        result = json.loads(lines[0][len(prefix):])
        self.assertEqual(result["controller_stage"], "UNRECOGNIZED_STAGE")
        self.assertEqual(result["controller_error"], "OTHER_ERROR")
        self.assertEqual(result["scope"], "DIAGNOSTIC_ONLY_NO_ACCEPTANCE")
        self.assertNotIn("private", output.getvalue())
        self.assertNotIn("::error", output.getvalue())
        self.assertEqual(receipt, before)

    def test_diagnostic_cancellation_reaches_existing_controller_finalization(self):
        receipt = {"status": "FAIL", "owned_cleanup": {"status": "PASS"},
                   "native_publication": {"status": "PASS_SECRET_SCANNED_EXACT_ALLOWLIST", "files_sha256": {}}}
        before = copy.deepcopy(receipt)
        with patch.object(lane.diagnostics, "read_current_published_log", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                lane.diagnostics.emit_current_run_notice(receipt, Path("unused"))
        self.assertEqual(receipt, before)
        with patch.object(lane.diagnostics, "summarize", side_effect=RuntimeError("synthetic-private-error")):
            output = io.StringIO()
            with redirect_stdout(output):
                lane.diagnostics.emit_current_run_notice(receipt, Path("unused"))
            self.assertIn('"diagnostic":"UNAVAILABLE"', output.getvalue())
            self.assertNotIn("synthetic-private", output.getvalue())
        self.assertEqual(receipt, before)

    def test_closed_diagnostic_output_and_serialization_cannot_mask_original_result(self):
        for status, error in [("FAIL", "TimeoutError"), ("CANCELLED", "KeyboardInterrupt")]:
            receipt = {"status": status, "error_type": error, "full_t2_acceptance": "NOT_RUN"}
            before = copy.deepcopy(receipt)
            output = io.StringIO()
            output.close()
            with redirect_stdout(output):
                lane.diagnostics.emit_current_run_notice(receipt, Path("unused"))
            self.assertEqual(receipt, before)
            with patch.object(lane.diagnostics.json, "dumps", side_effect=TypeError("synthetic-private-serialization-error")):
                lane.diagnostics.emit_current_run_notice(receipt, Path("unused"))
            self.assertEqual(receipt, before)
        for stop in [KeyboardInterrupt, SystemExit]:
            with patch.object(lane.diagnostics.json, "dumps", side_effect=stop):
                with self.assertRaises(stop):
                    lane.diagnostics.emit_current_run_notice(receipt, Path("unused"))
            with patch("builtins.print", side_effect=stop):
                with self.assertRaises(stop):
                    lane.diagnostics.emit_current_run_notice(receipt, Path("unused"))
            self.assertEqual(receipt, before)

    def test_changed_diagnostic_decoder_is_rejected_by_source_identity(self):
        tools = Path(lane.__file__).parent
        lane.source_inputs(tools.parents[1])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "Tools/TorahNativeOperations"
            for relative in ["two_clients/fixture.json", "two_clients/native-read-observation.patch",
                             *["two_clients/" + name for name in lane.GO_FILES],
                             "run_account_rpc.py", "native_client_diagnostics.py"]:
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(tools / relative, path)
            lane.source_inputs(root)
            decoder = target / "native_client_diagnostics.py"
            decoder.write_bytes(decoder.read_bytes() + b"\n# source drift\n")
            with self.assertRaisesRegex(ValueError, "Fixed-schema diagnostic decoder differs"):
                lane.source_inputs(root)

    def test_original_read_observation_is_exact_compile_overlay_and_preserves_source(self):
        tools = Path(lane.__file__).parent
        original = tools / "rpc/overlay/core/pinkha_torah_rpc.go"
        observation_patch = tools / "two_clients/native-read-observation.patch"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            heart, work = root / "heart", root / "work"
            source = heart / lane.account.NATIVE_READ_OBSERVATION["source_path"]
            source.parent.mkdir(parents=True)
            shutil.copyfile(original, source)
            work.mkdir()
            calls = []
            def run(command, label, cwd, env):
                calls.append(label)
                subprocess.run(command, cwd=cwd, env=env, check=True, timeout=10,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            replacement, receipt = lane.account.prepare_native_read_observation(heart, observation_patch, work, run)
            self.assertEqual(lane.digest(source), lane.account.NATIVE_READ_OBSERVATION["before_sha256"])
            self.assertEqual(lane.digest(replacement), lane.account.NATIVE_READ_OBSERVATION["after_sha256"])
            self.assertEqual(calls, ["native-read-observation-check", "native-read-observation-apply"])
            self.assertEqual(receipt["scope"], "TEST_COMPILE_OVERLAY_ONLY_ORIGINAL_READ_ERROR")
            self.assertEqual(replacement.read_text().count("mw.NativeTorahTargetRead(ctx, native)"), 1)
            self.assertEqual(replacement.read_text().count("return pinkhaTorahReadToWire(result, err)"), 1)
            with self.assertRaises(ValueError):
                lane.account.prepare_native_read_observation(heart, observation_patch, work, run)

    def test_changed_read_source_or_observation_patch_rejected_before_copy(self):
        tools = Path(lane.__file__).parent
        original = tools / "rpc/overlay/core/pinkha_torah_rpc.go"
        good_patch = tools / "two_clients/native-read-observation.patch"
        for changed in ["source", "patch"]:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                heart, work = root / "heart", root / "work"
                source = heart / lane.account.NATIVE_READ_OBSERVATION["source_path"]
                source.parent.mkdir(parents=True)
                source.write_bytes(original.read_bytes() + (b"\n// drift\n" if changed == "source" else b""))
                observation_patch = root / "native-read-observation.patch"
                observation_patch.write_bytes(good_patch.read_bytes() + (b"\n# drift\n" if changed == "patch" else b""))
                work.mkdir()
                def forbidden(*args): self.fail("Git patch must not run after source/patch drift")
                with self.assertRaises(ValueError):
                    lane.account.prepare_native_read_observation(heart, observation_patch, work, forbidden)
                self.assertEqual(list(work.iterdir()), [])

    def test_public_seed_rejects_device_database_and_signed_history_payloads(self):
        lane.validate_public_state(state_fixture())
        for field in ["DeviceKey", "PortKey", "Database", "RawTreeBytes"]:
            with self.subTest(field=field):
                state = state_fixture()
                state[field] = "synthetic-private-payload"
                with self.assertRaises(ValueError): lane.validate_public_state(state)
        state = state_fixture()
        state["RawChanges"]["root"] = "not-a-sha256-digest"
        with self.assertRaises(ValueError): lane.validate_public_state(state)

    def test_native_controls_require_every_named_case_and_no_skip(self):
        names = set(lane.CONTROL_METHODS)
        names.update(parent + "/" + child for parent, children in lane.CONTROL_METHODS.items() for child in children)
        output = "\n".join("--- PASS: " + name + " (0.01s)" for name in sorted(names))
        self.assertEqual(lane.validate_native_controls(output)["pass_terminals"], 17)
        for bad in [output.replace(sorted(names)[0], "OtherTest", 1), output + "\n--- SKIP: ignored (0s)",
                    output + "\n--- FAIL: ignored (0s)", output + "\n--- PASS: OtherTest (0s)"]:
            with self.subTest(bad=bad[-40:]):
                with self.assertRaises(ValueError): lane.validate_native_controls(bad)

    def test_container_rejects_foreign_owner_shared_data_and_external_network(self):
        network = {"Name": "owned-network", "Id": "network-id"}
        def validate(info):
            lane.validate_container(info, "owner", "recovered", network, Path("/owned/recovered"),
                                    Path("/owned/native.test"), "pinned-image-id", 1001, 1001)
        validate(container_fixture())
        mutations = [lambda x: x["Config"]["Labels"].update({lane.OWNER_LABEL: "foreign"}),
                     lambda x: x["Mounts"][0].update(Source="/owned/creator"),
                     lambda x: x["Mounts"].append({"Type": "bind", "Destination": "/other", "Source": "/owned/creator", "RW": False}),
                     lambda x: x["NetworkSettings"]["Networks"].update({"public-network": {"NetworkID": "other"}}),
                     lambda x: x["HostConfig"].update(Privileged=True),
                     lambda x: x["Config"].update(Image="golang:latest"),
                     lambda x: x["HostConfig"].update(Init=True)]
        for mutate in mutations:
            info = container_fixture(); mutate(info)
            with self.assertRaises(ValueError): validate(info)

    def test_same_peer_namespace_pid_or_sandbox_cannot_be_two_clients(self):
        reports = {role: ready_fixture(role)[2] for role in ["creator", "recovered"]}
        infos = {role: container_fixture(role) for role in reports}
        for index, role in enumerate(reports):
            reports[role].update(peer_id="peer-" + role, network_namespace="ns-" + role, bridge_ipv4=str(index))
            infos[role]["State"]["Pid"] = 100 + index
        lane.validate_pair(reports, infos)
        for key in ["peer_id", "network_namespace", "bridge_ipv4"]:
            bad = copy.deepcopy(reports)
            bad["recovered"][key] = bad["creator"][key]
            with self.assertRaises(ValueError): lane.validate_pair(bad, infos)
        for outer, key in [("State", "Pid"), ("NetworkSettings", "SandboxID")]:
            bad = copy.deepcopy(infos)
            bad["recovered"][outer][key] = bad["creator"][outer][key]
            with self.assertRaises(ValueError): lane.validate_pair(reports, bad)

    def test_readiness_does_not_accept_wrong_source_or_partial_history(self):
        state, identity, good = ready_fixture()
        def validate(report):
            with patch.object(lane.os, "readlink", return_value="net:[native]"):
                lane.validate_ready(report, "recovered", "owner", state, "state-hash", identity, "clients-fixture",
                                    container_fixture(), {"Name": "owned-network", "Id": "network-id"})
        validate(good)
        for key, value in [("heads", []), ("raw_changes_sha256", {}), ("client_fixture_sha256", "wrong"),
                           ("active_private_append", "ONE_CREATOR_GENERATED_RPC_APPEND"), ("app_capability", "ON"),
                           ("test_passed", True), ("private_read", "MISSING_HISTORY")]:
            bad = copy.deepcopy(good); bad[key] = value
            with self.subTest(field=key):
                with self.assertRaises(ValueError): validate(bad)

    def test_final_acceptance_requires_native_log_account_stop_and_no_active_b_append(self):
        _, _, ready = ready_fixture()
        calls = {"InitialSetParameters": 1, "AppGetVersion": 1, "WorkspaceOpen": 1, "DeviceNetworkStateSet": 1,
                 "ObjectShow": 1, "AccountStop": 1, "AppShutdown": 1, "WalletRecover": 1, "AccountSelect": 1,
                 "PinkhaTorahOperationsReadTarget": 2, "PinkhaTorahOperationsAppend": 1}
        good = {**ready, "closed": True, "account_stop_verified": True, "test_passed": True,
                "post_stop_rpc": "READ_AND_APPEND_NOT_LOGGED_IN", "rpc_calls": calls, "returned_byte_calls": dict(calls)}
        log = "--- PASS: " + lane.METHOD + " (0.1s)\nPASS\n"
        lane.validate_final(ready, good, log, "recovered")
        for key in ["closed", "account_stop_verified", "test_passed"]:
            bad = copy.deepcopy(good); bad[key] = False
            with self.assertRaises(ValueError): lane.validate_final(ready, bad, log, "recovered")
        bad = copy.deepcopy(good)
        bad["rpc_calls"]["PinkhaTorahOperationsAppend"] = bad["returned_byte_calls"]["PinkhaTorahOperationsAppend"] = 2
        with self.assertRaises(ValueError): lane.validate_final(ready, bad, log, "recovered")
        with self.assertRaises(ValueError): lane.validate_final(ready, good, "PASS\n", "recovered")

    def test_missing_secret_inventory_withholds_all_native_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            private, evidence = Path(tmp) / "private", Path(tmp) / "evidence"
            (private / "creator").mkdir(parents=True); evidence.mkdir()
            (private / "creator/native.log").write_text("synthetic unknown secret")
            result = lane.publish_native_evidence(private, evidence)
            self.assertEqual(result["status"], "WITHHELD_NO_SECRET_INVENTORY")
            self.assertFalse((evidence / "native-clients").exists())

    def test_all_secret_scanning_precedes_publication_and_excludes_databases(self):
        with tempfile.TemporaryDirectory() as tmp:
            private, evidence = Path(tmp) / "private", Path(tmp) / "evidence"
            creator = private / "creator"
            creator.mkdir(parents=True); evidence.mkdir()
            needles = ["synthetic-account-key-long", "synthetic mnemonic words long"]
            (creator / "sensitive-needles.private").write_text(json.dumps(needles))
            (creator / "native.log").write_text("contains " + needles[0])
            (creator / "ownership.json").write_text('{}')
            with self.assertRaises(ValueError): lane.publish_native_evidence(private, evidence)
            self.assertFalse((evidence / "native-clients").exists())
            (creator / "native.log").write_text("public synthetic native result")
            (creator / "account-key.private").write_text(needles[0])
            (creator / "store.db").write_bytes(b"synthetic database")
            result = lane.publish_native_evidence(private, evidence)
            self.assertEqual(result["status"], "PASS_SECRET_SCANNED_EXACT_ALLOWLIST")
            self.assertEqual(set(result["files_sha256"]), {"creator/ownership.json", "creator/native.log"})

    def test_daemon_mutation_records_owner_intent_before_a_cancelled_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = lane.OwnedDocker(Path(tmp), {"commands": []}, lambda: None)
            with patch.object(owner, "command", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt): owner.network()
            self.assertEqual(owner.resources, [{"kind": "network", "name": owner.prefix, "id": None}])
            self.assertIs(owner.receipt["owned_resources"], owner.resources)

    def test_foreign_container_is_never_removed_by_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = lane.OwnedDocker(Path(tmp), {"commands": []}, lambda: None)
            resource = {"kind": "container", "name": owner.prefix + "-recovered", "id": None, "private": tmp}
            owner.resources.append(resource)
            foreign = container_fixture()
            foreign["Name"] = "/" + resource["name"]
            with patch.object(owner, "command", side_effect=["abc123", json.dumps([foreign])]) as command:
                with self.assertRaises(ValueError): owner.cleanup()
            self.assertEqual(command.call_count, 2)
            self.assertTrue(all("rm" not in call.args[0] and "stop" not in call.args[0] for call in command.call_args_list))
            self.assertIn("name=^/" + resource["name"] + "$", command.call_args_list[0].args[0])

    def test_owned_container_removal_is_attempted_even_if_log_capture_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = lane.OwnedDocker(Path(tmp), {"commands": []}, lambda: None)
            owner.resources.append({"kind": "container", "name": owner.prefix + "-recovered", "id": "owned-id", "private": tmp})
            commands = []
            def command(args, name, *unused):
                commands.append(args)
                if name == "capture-owned-log": raise RuntimeError("synthetic capture failure")
                return ""
            with patch.object(owner, "find", return_value={"State": {"Running": False}}), patch.object(owner, "command", side_effect=command):
                with self.assertRaises(ValueError): owner.cleanup()
            self.assertIn(["container", "rm", "--force", "owned-id"], commands)
            self.assertEqual(owner.receipt["owned_cleanup"]["status"], "FAIL")

    def test_fixed_phase_deadline_does_not_reset_for_metadata_requests(self):
        with patch.object(lane.time, "monotonic", side_effect=[1, 9, 10]):
            self.assertEqual(lane.OwnedDocker.remaining(10), 9)
            self.assertEqual(lane.OwnedDocker.remaining(10), 1)
            with self.assertRaises(ValueError): lane.OwnedDocker.remaining(10)


if __name__ == "__main__":
    unittest.main()
