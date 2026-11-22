"""Focused rejection controls. Synthetic receipts are never native acceptance."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_t5_native_pagination as controller
import t5_native_account_retry_evidence as retry
import t5_native_account_retry_pending_evidence as pending
import test_t5_native_account_retry as original


def pending_inputs():
    receipt, state, _, arguments = original.inputs()
    state["runtimeVersion"] = receipt["runtimeVersion"] = pending.expected_runtime_version()
    final = state["observations"][-1]
    fixture = dict(protocolVersion=pending.FIXTURE_PROTOCOL, status="READY_NATIVE_FIXTURE",
                   retainedPaginationRunID=pending.RETAINED_RUN, baselineBodyInvocations=0,
                   baselineSearchCalls=0, state=state, preparedReadbacks=copy.deepcopy(final["readbacks"]),
                   setupCompletedAt=2095.0)
    state.update(protocolVersion=pending.STATE_PROTOCOL, status="READY_NATIVE_FIXTURE_STATE",
                 observations=[], nativeMutationCounts={"BlockListDelete": 1})
    raw = json.dumps(fixture, sort_keys=True).encode()
    receipt.update(protocolVersion=pending.PROTOCOL, status=pending.STATUS,
                   baselineReceiptSHA256Before=retry.digest(raw), baselineReceiptSHA256After=retry.digest(raw))
    return receipt, fixture, raw, arguments


class PendingAccountRetryControls(unittest.TestCase):
    def validate(self, values):
        receipt, fixture, raw, arguments = values
        return retry.validate_receipt(receipt, fixture, raw, **arguments, pending_only=True)

    def reject(self, mutate, *, rebind_fixture=False):
        values = pending_inputs()
        mutate(*values)
        if rebind_fixture:
            receipt, fixture, _, arguments = values
            raw = json.dumps(fixture, sort_keys=True).encode()
            receipt.update(baselineReceiptSHA256Before=retry.digest(raw), baselineReceiptSHA256After=retry.digest(raw))
            values = receipt, fixture, raw, arguments
        with self.assertRaises((RuntimeError, ValueError, KeyError, TypeError)):
            self.validate(values)

    def test_pending_nine_never_invokes_the_baseline_validator(self):
        with patch.object(retry.pagination, "validate_receipt", side_effect=AssertionError("retained36 replayed")):
            counts = self.validate(pending_inputs())
        self.assertEqual((counts["baseline_body_invocations"], counts["baseline_observations"], counts["baseline_search_calls"]), (0, 0, 0))
        self.assertEqual((counts["retry_successful_search_calls"], counts["retry_failed_search_attempts"], counts["total_search_calls_in_wrapper"]), (8, 1, 9))
        self.assertFalse(counts["unchanged_original_baseline"])
        self.assertTrue(counts["unchanged_prepared_fixture"])
        self.assertEqual(counts["retained_pagination_run_id"], pending.RETAINED_RUN)

    def test_preparation_cannot_claim_a_pass_or_repeat_old_observations(self):
        changes = [lambda r, f, raw, a: f.update(status="PASS_NATIVE_OBSERVATIONS"),
                   lambda r, f, raw, a: f.update(baselineBodyInvocations=1),
                   lambda r, f, raw, a: f.update(baselineSearchCalls=36),
                   lambda r, f, raw, a: f["state"].update(observations=[{"name": "baseline"}]),
                   lambda r, f, raw, a: f["state"]["nativeMutationCounts"].update(ObjectListSetIsArchived=2),
                   lambda r, f, raw, a: f.update(retainedPaginationRunID="another-run")]
        for mutate in changes:
            with self.subTest(mutate=changes.index(mutate)):
                self.reject(mutate, rebind_fixture=True)

    def test_fixture_requires_original_objects_exact_canonical_and_only_deleted_block(self):
        changes = [lambda r, f, raw, a: f["state"]["objects"].pop(),
                   lambda r, f, raw, a: f["preparedReadbacks"].pop(),
                   lambda r, f, raw, a: f["preparedReadbacks"][0].update(canonicalRaw="{}"),
                   lambda r, f, raw, a: f["preparedReadbacks"][0].update(typeID="other-type"),
                   lambda r, f, raw, a: f["preparedReadbacks"][4].update(nodes=copy.deepcopy(f["state"]["objects"][4]["original"]["nodes"])),
                   lambda r, f, raw, a: f["preparedReadbacks"][0]["nodes"].append({"id": "foreign-node", "childIDs": []})]
        for mutate in changes:
            with self.subTest(mutate=changes.index(mutate)):
                self.reject(mutate, rebind_fixture=True)

    def test_pending_scope_rejects_missing_extra_cached_or_wrong_native_searches(self):
        self.reject(lambda r, f, raw, a: r["queries"][0]["attempts"].pop())
        self.reject(lambda r, f, raw, a: r["queries"][2]["attempts"].append(copy.deepcopy(r["queries"][2]["attempts"][-1])))
        self.reject(lambda r, f, raw, a: r["queries"][1].update(status="SUCCESS", errorCode=0))
        self.reject(lambda r, f, raw, a: r["queries"][1].update(rows=[{"id": "cached"}]))
        self.reject(lambda r, f, raw, a: r["queries"][1].update(errorDescription="other native failure"))
        self.reject(lambda r, f, raw, a: r["queries"][2]["attempts"][0]["request"].update(spaceID="other-space"))

    def test_account_service_directory_and_fixture_bytes_cannot_be_replaced(self):
        for key in ("accountID", "spaceID", "runtimeVersion", "appSourceSHA", "runID", "runAttempt"):
            with self.subTest(key=key):
                self.reject(lambda r, f, raw, a: r.update({key: "replacement"}))
        self.reject(lambda r, f, raw, a: r["queries"][2].update(serviceID="replacement"))
        self.reject(lambda r, f, raw, a: r["directories"][5]["account"].update(inode=999))
        self.reject(lambda r, f, raw, a: r.update(credentialFileSHA256After="f" * 64))
        self.reject(lambda r, f, raw, a: r.update(baselineReceiptSHA256After="f" * 64))
        self.reject(lambda r, f, raw, a: r.update(accountCreatedByTail=True))

    def test_actual_window_stops_and_current_native_readbacks_remain_required(self):
        self.reject(lambda r, f, raw, a: r["stops"][0].update(removeData=True))
        self.reject(lambda r, f, raw, a: r["restores"][1].update(accountSelected=False))
        self.reject(lambda r, f, raw, a: r.update(appShutdownCompleted=False))
        self.reject(lambda r, f, raw, a: f.update(setupCompletedAt=2199.0), rebind_fixture=True)
        self.reject(lambda r, f, raw, a: a.update(execution_window=[2100.0, 2260.0]))
        self.reject(lambda r, f, raw, a: r["queries"][2]["readbacks"][0].update(canonicalRaw="{}"))
        self.reject(lambda r, f, raw, a: r["queries"][2]["rows"][0].update(canUnlink=False))

    def test_prepared_fixture_cannot_enter_the_legacy_accepted_baseline_route(self):
        receipt, fixture, raw, arguments = pending_inputs()
        with self.assertRaises(RuntimeError):
            retry.validate_receipt(receipt, fixture, raw, **arguments)
        with self.assertRaises(RuntimeError):
            controller.selected_method(True, True)

    def test_retained_original_proof_and_swift_prefix_are_bound_without_reexecution(self):
        root = Path(__file__).resolve().parents[2]
        result = pending.validate_retained_source(root)
        self.assertEqual(result["replayed_baseline_search_calls"], 0)
        self.assertEqual(result["original_source_sha"], pending.RETAINED_SOURCE)
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary)
            source = app / "AnyTypeTests/Pinkha/TorahT5NativePaginationTests.swift"
            report = app / pending.RETAINED_REPORT
            source.parent.mkdir(parents=True); report.parent.mkdir(parents=True)
            source.write_bytes((root / source.relative_to(app)).read_bytes())
            report.write_bytes((root / pending.RETAINED_REPORT).read_bytes())
            source.write_bytes(b"X" + source.read_bytes()[1:])
            with self.assertRaises(RuntimeError):
                pending.validate_retained_source(app)

    def test_actual_controller_selects_one_pending_suite_and_disables_old_suites(self):
        helper = original.NativeAccountRetryControllerControls()
        counts, record, selection, command, config, injected = helper.execute_synthetic_phase(
            account_retry=False, pending_only=True, input_factory=pending_inputs)
        self.assertEqual(counts["total_search_calls_in_wrapper"], 9)
        self.assertEqual(record["actual_test_counts"]["passed"], 1)
        self.assertEqual(selection["method"], pending.METHOD)
        self.assertIn("-only-testing:AnytypeTests/TorahT5NativeAccountRetryPendingTests", command)
        self.assertEqual(config["TestConfigurations"][0]["TestTargets"][0]["OnlyTestIdentifiers"], [pending.METHOD.split("/")[0]])
        self.assertEqual(injected[0]["PINKHA_T5_ACCOUNT_RETRY_PENDING"], "1")
        self.assertNotIn("PINKHA_T5_NATIVE_PAGINATION", injected[0])
        self.assertNotIn("PINKHA_T5_ACCOUNT_RETRY", injected[0])

    def test_controller_refuses_replayed_missing_or_wrong_native_evidence(self):
        helper = original.NativeAccountRetryControllerControls()
        for change in [dict(replayed_baseline=True), dict(missing_fixture=True), dict(missing_retry=True),
                       dict(foreign_credentials=True), dict(wrong_method=True), dict(extra_original=True)]:
            with self.subTest(change=change), self.assertRaises((RuntimeError, ValueError, FileNotFoundError)):
                helper.execute_synthetic_phase(account_retry=False, pending_only=True, input_factory=pending_inputs, **change)

    def test_pending_fixture_uses_the_same_complete_secret_publication_scan(self):
        for leaked in (False, True):
            with self.subTest(leaked=leaked), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); work, proof, container = [root / name for name in ("work", "proof", "container")]
                phase = work / "phase"; phase.mkdir(parents=True); proof.mkdir()
                private = container / controller.PRIVATE_RELATIVE_PATH; private.mkdir(parents=True)
                credentials = dict(token="token", mnemonic="complete disposable phrase", accountKey="complete native key")
                (private / "secrets.json").write_text(json.dumps(credentials))
                path = phase / "account-retry-fixture.json"
                path.write_bytes(credentials["accountKey"].encode("utf-16-be") if leaked else b'{"synthetic":"fixture"}')
                if leaked:
                    with self.assertRaises(RuntimeError):
                        controller.publish_native_evidence(work, proof, container, "token")
                    self.assertFalse((proof / "actual-native").exists())
                else:
                    self.assertTrue(controller.publish_native_evidence(work, proof, container, "token"))
                    self.assertEqual({p.name for p in (proof / "actual-native").iterdir()}, {"account-retry-fixture.json"})


class CorrectedPendingRuntimeControls(unittest.TestCase):
    def binding(self):
        profile = pending.heart_profiles.select(pending.RUNTIME_PROFILE)
        return dict(runtime_profile=profile.name, native_marker=profile.version,
                    heart_patch_sha256=profile.patch_sha256, heart_inventory_sha256=profile.inventory_sha256,
                    heart_source_run_id=pending.RUNTIME_RUN, heart_source_attempt="1", heart_source_sha="a" * 40,
                    heart_build_receipt_sha256="b" * 64, heart_artifact_sha256="c" * 64,
                    heart_proof_artifact_sha256="d" * 64, heart_artifact_id=10, heart_proof_artifact_id=11)

    def test_build_identity_requires_full_corrected_producer_binding_and_keeps_legacy_defaults(self):
        ui = SimpleNamespace(heart_profiles=pending.heart_profiles)
        binding = self.binding()
        self.assertEqual(controller.pair.build_runtime_version("new", ui, binding), pending.expected_runtime_version())
        self.assertEqual(controller.pair.build_runtime_version("new", ui), controller.pair.runtime_version("new"))
        self.assertEqual(controller.pair.build_runtime_version("old", ui), controller.pair.runtime_version("old"))
        for changed in [dict(native_marker=controller.pair.runtime_version("new")),
                        dict(heart_patch_sha256="f" * 64), dict(heart_artifact_sha256=""),
                        dict(runtime_profile="r14")]:
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                controller.pair.build_runtime_version("new", ui, dict(binding, **changed))
        with self.assertRaises(RuntimeError):
            controller.pair.build_runtime_version("old", ui, binding)

    def test_pending_fixture_rejects_original_r15_and_cannot_relabel_its_result(self):
        receipt, fixture, _, arguments = pending_inputs()
        fixture["state"]["runtimeVersion"] = receipt["runtimeVersion"] = controller.pair.runtime_version("new")
        raw = json.dumps(fixture, sort_keys=True).encode()
        receipt.update(baselineReceiptSHA256Before=retry.digest(raw), baselineReceiptSHA256After=retry.digest(raw))
        with self.assertRaises(RuntimeError):
            retry.validate_receipt(receipt, fixture, raw, **arguments, pending_only=True)

    def test_pending_swift_and_workflow_use_current_artifact_without_native_rebuild(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "AnyTypeTests/Pinkha/TorahT5NativePaginationTests.swift").read_text(encoding="utf8")
        fixture = source.split("fileprivate func prepareStoppedAccountRetryFixture()", 1)[1]
        self.assertIn(pending.heart_profiles.select(pending.RUNTIME_PROFILE).patch_sha256, fixture)
        self.assertIn('"-pinkha-torah-attachment-v1-" + patch', fixture)
        workflow = (root / ".github/workflows/pinkha-t5-native-pagination.yml").read_text(encoding="utf8")
        step = workflow.split("      - name: Reuse the qualified corrected r15 artifact", 1)[1].split("      - name:", 1)[0]
        self.assertIn('test "$HEART_SOURCE_RUN_ID" = "' + pending.RUNTIME_RUN + '"', step)
        self.assertIn("download_heart_runtime.py", step)
        self.assertIn("--runtime-profile " + pending.RUNTIME_PROFILE, step)
        self.assertNotIn("build_t5_r15_runtime", step)
        self.assertNotIn("build_custom_heart", step)


if __name__ == "__main__":
    unittest.main()
