"""Synthetic rejection controls only; these do not establish Apple/native acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_t5_native_pagination as controller
import t5_native_account_retry_evidence as evidence
import test_t5_native_pagination as original
from run_t5_native_ui import selected_configuration
from t5_native_ui_evidence import validate_selection


def inputs():
    baseline = original.inputs()
    baseline_bytes = json.dumps(baseline, sort_keys=True).encode()
    directories = dict(root=dict(pathSHA256=original.ROOT, device=7, inode=100, createdAt=1000.0),
                       account=dict(pathSHA256="d" * 64, device=7, inode=101, createdAt=1001.0))
    credential_sha = "e" * 64
    final = baseline["observations"][-1]
    queries = []
    for name, started in [("before_stop", 2120.0), ("while_stopped", 2160.0), ("after_restore", 2200.0)]:
        failed = name == "while_stopped"
        calls = copy.deepcopy(final["calls"])
        if failed:
            calls = calls[:1]
            calls[0].update(objectIDs=[], resultSpaceIDs=[])
        attempts = [dict(request=call, status="NATIVE_ERROR" if failed else "SUCCESS") for call in calls]
        if failed:
            attempts[0].update(errorCode=evidence.ERROR_CODE, errorDescription=evidence.ERROR_DESCRIPTION)
        query = dict(name=name, status="NATIVE_ERROR" if failed else "SUCCESS", startedAt=started, finishedAt=started + 10,
                     serviceID="retained-production-service", searchRecorderID="retained-recorder", upstreamSearchID="original-native-search",
                     activeSpaceID=baseline["spaceID"], requestedSpaceID=baseline["spaceID"], attempts=attempts,
                     rows=[] if failed else copy.deepcopy(final["rows"]), limitations=[] if failed else final["limitations"],
                     readbacks=[] if failed else copy.deepcopy(final["readbacks"]),
                     nativeCandidatesBefore=[] if failed else final["nativeCandidatesBefore"],
                     nativeCandidatesAfter=[] if failed else final["nativeCandidatesAfter"])
        if failed:
            query.update(errorCode=evidence.ERROR_CODE, errorDescription=evidence.ERROR_DESCRIPTION)
        else:
            query["coverage"] = final["coverage"]
        queries.append(query)
    receipt = dict(protocolVersion=evidence.PROTOCOL, status="PASS_NATIVE_ACCOUNT_RETRY", runAttempt="1",
        **{key: baseline[key] for key in ("token", "appSourceSHA", "runID", "processID", "runtimeVersion", "accountID", "spaceID", "rootPathSHA256")},
        wrapperStartedAt=2000.0, baselineFinishedAt=2100.0, finishedAt=2250.0,
        baselineReceiptSHA256Before=evidence.digest(baseline_bytes), baselineReceiptSHA256After=evidence.digest(baseline_bytes),
        credentialFileSHA256Before=credential_sha, credentialFileSHA256After=credential_sha,
        directories=[dict(stage=stage, **copy.deepcopy(directories)) for stage in evidence.DIRECTORY_STAGES],
        restores=[dict(name=name, startedAt=start, finishedAt=start + 10, selectedAccountID=baseline["accountID"],
                       selectedSpaceID=baseline["spaceID"], walletRecovered=True, accountSelected=True)
                  for name, start in [("first_restore", 2110.0), ("retry_restore", 2180.0)]],
        stops=[dict(name=name, startedAt=start, finishedAt=start + 10, removeData=False,
                    accountStopCompleted=True, accountNotRunningConfirmed=True)
               for name, start in [("account_stop", 2140.0), ("final_stop", 2220.0)]],
        queries=queries, appShutdownCompleted=True, appShutdownFinishedAt=2240.0,
        accountCreatedByTail=False, walletCreatedByTail=False, accountMigratedByTail=False,
        productLookupFlag="OFF", wholeIndexCompleteness="NOT_PROVEN", networkOutage="NOT_RUN", uiErrorPresentation="NOT_RUN")
    return receipt, baseline, baseline_bytes, dict(source=original.SOURCE, run_id=original.RUN, run_attempt="1",
        token=original.TOKEN, root_sha=original.ROOT, credential_sha=credential_sha,
        current_directories=directories, execution_window=[1990.0, 2260.0])


class NativeAccountRetryEvidenceControls(unittest.TestCase):
    def validate(self, values):
        receipt, baseline, raw, arguments = values
        return evidence.validate_receipt(receipt, baseline, raw, **arguments)

    def reject(self, mutate):
        values = inputs()
        mutate(*values)
        with self.assertRaises((RuntimeError, ValueError, KeyError, TypeError)):
            self.validate(values)

    def test_complete_synthetic_wrapper_has_one_selected_method_and_exact_independent_scope(self):
        result = self.validate(inputs())
        self.assertEqual(result["selected_test_methods"], 1)
        self.assertEqual(result["baseline_body_invocations"], 1)
        self.assertEqual((result["baseline_search_calls"], result["retry_successful_search_calls"], result["retry_failed_search_attempts"]), (36, 8, 1))
        self.assertEqual(result["total_search_calls_in_wrapper"], 45)
        self.assertEqual((result["network_outage"], result["ui_error_presentation"], result["product_lookup_flag"]), ("NOT_RUN", "NOT_RUN", "OFF"))

    def test_baseline_is_independently_revalidated_and_original_bytes_are_required(self):
        self.reject(lambda r, b, raw, a: b["observations"][0]["calls"].pop())
        self.reject(lambda r, b, raw, a: r.update(baselineReceiptSHA256After="f" * 64))
        values = inputs(); values = (values[0], values[1], values[2] + b" ", values[3])
        with self.assertRaises(RuntimeError):
            self.validate(values)

    def test_account_source_attempt_process_and_runtime_cannot_change_in_the_tail(self):
        for field, value in [("accountID", "another-account"), ("spaceID", "another-space"), ("processID", 999),
                             ("appSourceSHA", "f" * 40), ("runID", "1"), ("runAttempt", "2"),
                             ("rootPathSHA256", "f" * 64), ("runtimeVersion", "another-runtime")]:
            with self.subTest(field=field):
                self.reject(lambda r, b, raw, a: r.update({field: value}))

    def test_same_key_recovery_cannot_replace_the_private_credentials_or_native_directory(self):
        self.reject(lambda r, b, raw, a: r.update(credentialFileSHA256Before="f" * 64))
        self.reject(lambda r, b, raw, a: r.update(credentialFileSHA256After="f" * 64))
        for field, value in [("inode", 999), ("device", 8), ("createdAt", 1001.001), ("pathSHA256", "f" * 64)]:
            with self.subTest(field=field):
                self.reject(lambda r, b, raw, a: r["directories"][5]["account"].update({field: value}))
                self.reject(lambda r, b, raw, a: a["current_directories"]["account"].update({field: value}))

    def test_cross_language_creation_timestamp_ulp_does_not_allow_in_test_directory_changes(self):
        values = inputs()
        values[3]["current_directories"]["account"]["createdAt"] += 0.0000002
        self.validate(values)
        self.reject(lambda r, b, raw, a: r["directories"][-1]["account"].update(createdAt=1001.0000002))

    def test_every_existing_directory_checkpoint_and_two_explicit_restores_are_required(self):
        self.reject(lambda r, b, raw, a: r["directories"].pop(2))
        self.reject(lambda r, b, raw, a: r["restores"].pop())
        self.reject(lambda r, b, raw, a: r["restores"][1].update(selectedAccountID="replacement-account"))
        self.reject(lambda r, b, raw, a: r["restores"][1].update(accountSelected=False))
        for field in ["accountCreatedByTail", "walletCreatedByTail", "accountMigratedByTail"]:
            self.reject(lambda r, b, raw, a: r.update({field: True}))

    def test_actual_account_stop_must_keep_data_confirm_error_and_shutdown(self):
        for field, value in [("removeData", True), ("accountStopCompleted", False), ("accountNotRunningConfirmed", False)]:
            self.reject(lambda r, b, raw, a: r["stops"][0].update({field: value}))
        self.reject(lambda r, b, raw, a: r.update(appShutdownCompleted=False))

    def test_error_is_the_original_bad_input_rpc_and_not_an_empty_or_cached_snapshot(self):
        for change in [dict(status="SUCCESS"), dict(errorCode=0), dict(errorCode=True), dict(errorDescription="different error"),
                       dict(coverage="indexedTargetsOnly"), dict(rows=[{}]), dict(readbacks=[{}])]:
            with self.subTest(change=change):
                self.reject(lambda r, b, raw, a: r["queries"][1].update(change))
        self.reject(lambda r, b, raw, a: r["queries"][1]["attempts"].clear())
        self.reject(lambda r, b, raw, a: r["queries"][1]["attempts"][0].update(status="OTHER_ERROR"))

    def test_failed_request_retains_exact_native_filters_sort_space_and_no_returned_rows(self):
        for field, value in [("spaceID", "foreign"), ("limit", 50), ("offset", 2), ("objectIDs", ["cached"]), ("keys", [])]:
            self.reject(lambda r, b, raw, a: r["queries"][1]["attempts"][0]["request"].update({field: value}))
        self.reject(lambda r, b, raw, a: r["queries"][1]["attempts"][0]["request"]["filters"].pop())

    def test_all_three_queries_reuse_production_service_recorder_and_original_upstream(self):
        for field in ["serviceID", "searchRecorderID", "upstreamSearchID"]:
            self.reject(lambda r, b, raw, a: r["queries"][2].update({field: "replacement"}))
        self.reject(lambda r, b, raw, a: r["queries"][0].update(upstreamSearchID="retained-recorder"))
        self.reject(lambda r, b, raw, a: r["queries"][2].update(activeSpaceID="other-space"))

    def test_recovered_query_must_execute_each_real_small_page(self):
        self.reject(lambda r, b, raw, a: r["queries"][2]["attempts"].pop())
        self.reject(lambda r, b, raw, a: r["queries"][2]["attempts"][0].update(status="NATIVE_ERROR"))
        self.reject(lambda r, b, raw, a: r["queries"][2]["attempts"][1]["request"].update(objectIDs=["duplicate", "duplicate"]))
        self.reject(lambda r, b, raw, a: r["queries"][2].update(nativeCandidatesAfter=[]))

    def test_fresh_native_readback_rejects_stale_rows_changed_canonical_data_or_recreated_deleted_block(self):
        self.reject(lambda r, b, raw, a: r["queries"][2]["readbacks"][0].update(updatedAt=2199.0))
        self.reject(lambda r, b, raw, a: r["queries"][2]["readbacks"][0].update(canonicalRaw="{}"))
        self.reject(lambda r, b, raw, a: r["queries"][2]["rows"][0].update(canUnlink=False))
        self.reject(lambda r, b, raw, a: r["queries"][2]["readbacks"][4].update(nodes=copy.deepcopy(b["objects"][4]["original"]["nodes"])))

    def test_original_stale_target_and_index_limitations_remain_visible_after_recovery(self):
        self.reject(lambda r, b, raw, a: r["queries"][2].update(limitations=["indexFreshnessUnverified"]))
        self.reject(lambda r, b, raw, a: r["queries"][2].update(coverage="complete"))
        for field, value in [("networkOutage", "PASS"), ("uiErrorPresentation", "PASS"),
                             ("wholeIndexCompleteness", "PROVEN"), ("productLookupFlag", "ON")]:
            self.reject(lambda r, b, raw, a: r.update({field: value}))

    def test_retry_chronology_and_actual_xctest_window_are_required(self):
        self.reject(lambda r, b, raw, a: r["queries"][1].update(startedAt=2130.0))
        self.reject(lambda r, b, raw, a: r["restores"][1].update(finishedAt=2250.0))
        self.reject(lambda r, b, raw, a: r.update(finishedAt=3000.0))
        self.reject(lambda r, b, raw, a: a.update(execution_window=[2100.0, 2260.0]))
        self.reject(lambda r, b, raw, a: r["queries"][0].update(startedAt=float("nan")))


class NativeAccountRetrySelectionControls(unittest.TestCase):
    def test_separate_swift_suite_keeps_the_full_accepted_original_source_byte_identical(self):
        source = Path(__file__).resolve().parents[2] / "AnyTypeTests/Pinkha/TorahT5NativePaginationTests.swift"
        raw = source.read_bytes()
        self.assertEqual(hashlib.sha256(raw[:28741]).hexdigest(), "dff9dd58471659cc19d082ea0961f2ccff9666ad86c4aa052c85a3aa4e5d4990")
        added = raw[28741:].decode()
        self.assertEqual(added.count("@Test("), 1)
        self.assertEqual(added.count("try await original.nativePaginationCurrentSpaceAndMutationAcceptance()"), 1)
        self.assertIn("struct TorahT5NativeAccountRetryTests", added)
        self.assertNotIn("ClientCommands.accountCreate", added)
        self.assertNotIn("ClientCommands.walletCreate", added)
        self.assertNotIn("ClientCommands.accountMigrate", added)

    def test_real_xctestrun_filter_selects_only_the_wrapper_class_and_preserves_default_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "original.xctestrun"
            path.write_bytes(plistlib.dumps({"TestConfigurations": [{"TestTargets": [{"BlueprintName": "AnytypeTests"}]}]}))
            ui = SimpleNamespace(inject=lambda *args: None)
            for enabled, method in [(False, controller.evidence.METHOD), (True, evidence.METHOD)]:
                self.assertEqual(controller.selected_method(enabled), method)
                selected, filters = selected_configuration(path, "AnytypeTests", [method], {}, ui)
                self.assertEqual(filters, [method.split("/")[0]])
                data = plistlib.loads(selected.read_bytes())
                self.assertEqual(data["TestConfigurations"][0]["TestTargets"][0]["OnlyTestIdentifiers"], filters)
            self.assertNotEqual(controller.selected_method(False).split("/")[0], controller.selected_method(True).split("/")[0])

    def test_extra_original_test_or_missing_wrapper_cannot_be_counted_as_one_success(self):
        udid = "11111111-1111-1111-1111-111111111111"
        summary = dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0,
                       devicesAndConfigurations=[dict(device=dict(deviceId=udid, architecture="arm64", osVersion="27.0"))])
        validate_selection(summary, {evidence.METHOD + "()": "Passed"}, [evidence.METHOD], udid)
        for methods in [{controller.evidence.METHOD: "Passed"},
                        {evidence.METHOD: "Passed", controller.evidence.METHOD: "Passed"},
                        {evidence.METHOD: "Skipped"}]:
            with self.assertRaises(ValueError):
                validate_selection(summary, methods, [evidence.METHOD], udid)


class NativeAccountRetryPublicationControls(unittest.TestCase):
    def test_new_retry_receipt_and_controller_facts_use_existing_complete_secret_scan(self):
        for leaked in [False, True]:
            with self.subTest(leaked=leaked), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); work, proof, container = [root / name for name in ["work", "proof", "container"]]
                phase = work / "phase"; phase.mkdir(parents=True); proof.mkdir()
                private = container / controller.PRIVATE_RELATIVE_PATH; private.mkdir(parents=True)
                credentials = dict(token="token", mnemonic="complete disposable phrase", accountKey="complete native key")
                (private / "secrets.json").write_text(json.dumps(credentials))
                (phase / "account-retry-receipt.json").write_bytes(credentials["accountKey"].encode("utf-16-le") if leaked else b'{"diagnostic":"synthetic"}')
                (phase / "account-retry-controller.json").write_text('{"diagnostic":"synthetic"}')
                if leaked:
                    with self.assertRaises(RuntimeError):
                        controller.publish_native_evidence(work, proof, container, "token")
                    self.assertFalse((proof / "actual-native").exists())
                else:
                    self.assertTrue(controller.publish_native_evidence(work, proof, container, "token"))
                    self.assertEqual({p.name for p in (proof / "actual-native").iterdir()},
                                     {"account-retry-receipt.json", "account-retry-controller.json"})
                    policy = json.loads((proof / "native-evidence-policy.json").read_text())
                    self.assertFalse(policy["secrets_uploaded"])
                    self.assertFalse(policy["account_data_uploaded"])
                    self.assertFalse(policy["raw_xcresult_uploaded"])


class NativeAccountRetryControllerControls(unittest.TestCase):
    def execute_synthetic_phase(self, *, account_retry, missing_retry=False, foreign_credentials=False,
                                wrong_method=False, extra_original=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); app, work, container, built = [root / key for key in ("app", "work", "container", "built")]
            for path in (app, work, container, built):
                path.mkdir()
            private = container / controller.PRIVATE_RELATIVE_PATH; private.mkdir(parents=True)
            native_root = container / controller.pair.ROOT_RELATIVE_PATH; native_root.mkdir(parents=True)
            value, baseline, _, arguments = inputs()
            root_sha = controller.pair.sha_bytes(str(native_root).encode())
            baseline["rootPathSHA256"] = value["rootPathSHA256"] = root_sha
            baseline_bytes = json.dumps(baseline, sort_keys=True).encode()
            value.update(baselineReceiptSHA256Before=evidence.digest(baseline_bytes), baselineReceiptSHA256After=evidence.digest(baseline_bytes))
            native_account = native_root / baseline["accountID"]; native_account.mkdir()
            directories = arguments["current_directories"]
            directories["root"]["pathSHA256"] = root_sha
            directories["account"]["pathSHA256"] = controller.pair.sha_bytes(str(native_account).encode())
            value["directories"] = [dict(stage=stage, **copy.deepcopy(directories)) for stage in evidence.DIRECTORY_STAGES]
            credentials = json.dumps(dict(token=original.TOKEN, mnemonic="disposable phrase", accountKey="disposable key")).encode()
            credential_sha = evidence.digest(credentials)
            value.update(credentialFileSHA256Before=credential_sha, credentialFileSHA256After=credential_sha)
            (private / "secrets.json").write_bytes(credentials + (b" " if foreign_credentials else b""))
            (private / "receipt.json").write_bytes(baseline_bytes)
            if not missing_retry:
                (private / "account-retry-receipt.json").write_text(json.dumps(value))
            configuration = built / "original.xctestrun"
            configuration.write_bytes(plistlib.dumps({"TestConfigurations": [{"TestTargets": [{"BlueprintName": "AnytypeTests"}]}]}))
            calls, injected = [], []
            def inject(data, blueprint, environment, app_path):
                injected.append(dict(environment))
                data["TestConfigurations"][0]["TestTargets"][0]["EnvironmentVariables"] = environment
            ui = SimpleNamespace(inject=inject, code_carriers=lambda _: {"sha256": "f" * 64})
            method = controller.selected_method(account_retry)
            udid = "11111111-1111-1111-1111-111111111111"
            methods = {(controller.evidence.METHOD if wrong_method else method) + "()": "Passed"}
            if extra_original:
                methods[controller.evidence.METHOD + "()"] = "Passed"
            summary = dict(totalTestCount=len(methods), passedTests=len(methods), failedTests=0, skippedTests=0,
                           startTime=1990.0, finishTime=2260.0,
                           devicesAndConfigurations=[dict(device=dict(deviceId=udid, architecture="arm64", osVersion="27.0"))])
            def run_logged(command, app, directory, stem, timeout, **kwargs):
                calls.append((command, timeout))
                if stem == "test":
                    Path(command[command.index("-resultBundlePath") + 1]).mkdir()
                if stem.startswith("export-"):
                    kwargs["output"].write_text(json.dumps(summary if stem == "export-summary" else methods))
                return {"return_code": 0, "timed_out": False}, directory / (stem + ".log")
            with patch.object(controller.pair, "run_logged", side_effect=run_logged), \
                 patch.object(controller.pair, "app_container", side_effect=lambda _, kind: container if kind == "data" else built), \
                 patch.object(controller, "existing_directory_identity", side_effect=lambda path: directories["root" if path == native_root else "account"]), \
                 patch.dict(controller.os.environ, {"GITHUB_RUN_ATTEMPT": "1"}):
                counts = controller.execute_phase(app=app, work=work, build=dict(app=str(built), configuration=str(configuration), code_sha256="f" * 64),
                    udid=udid, source=original.SOURCE, run_id=original.RUN, token=original.TOKEN, ui=ui,
                    method_results=lambda value: value, account_retry=account_retry)
            record = json.loads((work / "phase/result.json").read_text())
            selected = json.loads((work / "phase/selection.json").read_text())
            command = next(command for command, _ in calls if command[0] == "xcodebuild")
            config = plistlib.loads(Path(command[command.index("-xctestrun") + 1]).read_bytes())
            return counts, record, selected, command, config, injected

    def test_actual_controller_branch_selects_one_wrapper_and_requires_full_tail_evidence(self):
        counts, record, selected, command, config, injected = self.execute_synthetic_phase(account_retry=True)
        self.assertEqual(counts["total_search_calls_in_wrapper"], 45)
        self.assertEqual(record["status"], "PASS")
        self.assertEqual(record["actual_test_counts"]["passed"], 1)
        self.assertEqual(selected["method"], evidence.METHOD)
        self.assertEqual(injected[0]["PINKHA_T5_NATIVE_PAGINATION"], "1")
        self.assertEqual(injected[0]["PINKHA_T5_ACCOUNT_RETRY"], "1")
        self.assertEqual(injected[0]["PINKHA_T5_ACCOUNT_RETRY_RUN_ATTEMPT"], "1")
        self.assertIn("-only-testing:AnytypeTests/TorahT5NativeAccountRetryTests", command)
        self.assertNotIn("-only-testing:AnytypeTests/TorahT5NativePaginationTests", command)
        self.assertEqual(config["TestConfigurations"][0]["TestTargets"][0]["OnlyTestIdentifiers"], ["TorahT5NativeAccountRetryTests"])

    def test_default_original_lane_keeps_its_single_original_selection_and_does_not_require_tail(self):
        counts, record, selected, command, _, injected = self.execute_synthetic_phase(account_retry=False, missing_retry=True)
        self.assertEqual(counts["native_test_methods"], 1)
        self.assertEqual(counts["actual_search_calls"], 36)
        self.assertEqual(selected["method"], controller.evidence.METHOD)
        self.assertIn("-only-testing:AnytypeTests/TorahT5NativePaginationTests", command)
        self.assertNotIn("PINKHA_T5_ACCOUNT_RETRY", injected[0])
        self.assertNotIn("account_retry_receipt_sha256", record)

    def test_missing_tail_replaced_private_bytes_or_wrong_actual_selection_cannot_pass(self):
        for arguments in [dict(missing_retry=True), dict(foreign_credentials=True), dict(wrong_method=True), dict(extra_original=True)]:
            with self.subTest(arguments=arguments), self.assertRaises((RuntimeError, ValueError, FileNotFoundError)):
                self.execute_synthetic_phase(account_retry=True, **arguments)


if __name__ == "__main__":
    unittest.main()
