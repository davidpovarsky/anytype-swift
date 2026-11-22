"""New controller boundary controls only. No Apple/native results are fabricated."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import owned_simulator_readiness as simulator
import run_t5_apple_pair as pair
import t5_account_retry_existing_build as pending
import t5_host_actions as actions

RUN = "44960856322"
SOURCE = "a" * 40
HOST = "12345678-1234-1234-1234-123456789abc"
NEW = "22345678-1234-1234-1234-123456789abc"
RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
DEVICE = "com.apple.CoreSimulator.SimDeviceType.fixture-ipad"
NAME = "Pinkha-UI27-" + RUN + "-ipad"
SELECTION = dict(udid=HOST, name=NAME, device=dict(identifier=DEVICE), runtime=dict(identifier=RUNTIME))


def counts():
    return dict(selected_test_methods=1, baseline_body_invocations=0, baseline_observations=0,
        baseline_search_calls=0, retry_observations=3, retry_successful_search_calls=8,
        retry_failed_search_attempts=1, total_search_calls_in_wrapper=9, tail_existing_account_restores=2,
        tail_account_stops=2, pending_only=True, fixture_setup_only=True, baseline_acceptance_rerun="NOT_RUN")


class Harness:
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.devices = {HOST: dict(udid=HOST, name=NAME, deviceTypeIdentifier=DEVICE,
                                  state="Shutdown", isAvailable=True)}
        self.failures = {}
        self.return_codes = {}
        self.after_boot = None
        self.installed = False
        self.native_calls = []
        self.publications = []
        self.code = "b" * 64
        self.app = root / "app"
        self.work = self.app / "build/private"
        self.proof = self.app / "build/proof"
        self.products = self.work / "new/Products"
        self.bundle = self.products / "Anytype.app"
        self.bundle.mkdir(parents=True)
        self.proof.mkdir(parents=True)
        self.app_executable = self.bundle / "Anytype"
        self.test_executable = self.bundle / "Tests"
        self.configuration = self.products / "Anytype.xctestrun"
        for path in (self.app_executable, self.test_executable, self.configuration):
            path.write_bytes(b"controller-only synthetic product")
        self.build = dict(app=str(self.bundle), configuration=str(self.configuration), app_source_sha=SOURCE,
            code_sha256=self.code, app_builds=1, runtime_binding=dict(heart_source_run_id=pending.native.pending_evidence.RUNTIME_RUN))
        self.contract = dict(compiled_identifiers=["AnytypeTests/" + actions.SUITE + "/" + name + "("
            + "".join(p["name"] + ":" for p in spec["parameters"]) + ")" for name, spec in actions.METHODS.items()])
        self.api = SimpleNamespace(require=pair.require, write=pair.write, digest=pair.digest,
            run_logged=self.run, git=lambda *args: SOURCE if "rev-parse" in args else "",
            app_container=self.container, FLAGS=pair.FLAGS)
        self.ui = SimpleNamespace(code_carriers=lambda path: dict(sha256=self.code))

    def container(self, udid, kind, required=False):
        if self.installed and udid == NEW:
            return self.root / "disposable-native-container"
        return None

    def run(self, argv, app, directory, name, timeout, check=True, output=None):
        self.calls.append((name, list(argv), timeout))
        directory.mkdir(parents=True, exist_ok=True)
        path = output or directory / (name + ".log")
        path.write_text("", encoding="utf-8")
        if name in self.failures:
            raise self.failures[name]
        if argv[:3] == ["xcrun", "simctl", "list"]:
            path.write_text(json.dumps(dict(devices={RUNTIME: list(self.devices.values())})))
        elif argv[:3] == ["xcrun", "simctl", "create"]:
            self.devices[NEW] = dict(udid=NEW, name=argv[3], deviceTypeIdentifier=argv[4], state="Shutdown", isAvailable=True)
            path.write_text(NEW + "\n")
        elif argv[:3] == ["xcrun", "simctl", "boot"]:
            self.devices[argv[3]]["state"] = "Booted"
        elif argv[:3] == ["xcrun", "simctl", "bootstatus"] and self.after_boot:
            self.after_boot(self.devices[argv[3]])
        elif argv[:3] == ["xcrun", "simctl", "shutdown"]:
            self.devices[argv[3]]["state"] = "Shutdown"
        elif name == "enumerate":
            inventory = Path(argv[argv.index("-test-enumeration-output-path") + 1])
            inventory.write_text(json.dumps(dict(errors=[], values=[dict(testPlan="Anytype",
                enabledTests=[dict(identifier=v) for v in self.contract["compiled_identifiers"]], disabledTests=[])])))
        elif name == "test":
            Path(argv[argv.index("-resultBundlePath") + 1]).mkdir()
        elif name in {"export-summary", "export-tests"}:
            path.write_text("{}")
        return dict(return_code=self.return_codes.get(name, 0), timed_out=False), path

    def patches(self, stack):
        stack.enter_context(patch.object(actions.host, "xctest_products", return_value=(
            self.bundle, self.app_executable, self.bundle, self.test_executable)))
        stack.enter_context(patch.object(actions, "source_contract", return_value=self.contract))
        stack.enter_context(patch.object(actions, "validate_results", return_value=dict(actual_method_count=11, declared_case_count=12)))
        def scoped(original, selected, identifiers, helpers):
            selected.write_bytes(original.read_bytes())
            return dict(sha256=pair.digest(selected), path=str(selected))
        stack.enter_context(patch.object(actions.existing, "scoped_configuration", side_effect=scoped))
        stack.enter_context(patch.object(pending.native_ui, "validate_corrected_build", return_value=SimpleNamespace(
            name=pending.native.pending_evidence.RUNTIME_PROFILE)))
        stack.enter_context(patch.object(pending.native.pending_evidence, "validate_retained_source",
                                        return_value=dict(original_search_calls=36, replayed_baseline_search_calls=0)))
        def phase(**kwargs):
            self.native_calls.append(kwargs)
            self.installed = True
            pair.write(kwargs["work"] / "phase/result.json", dict(status="SYNTHETIC_CONTROLLER_CONTROL"))
            return counts()
        stack.enter_context(patch.object(pending.native, "execute_phase", side_effect=phase))
        def publish(*args):
            self.publications.append(args)
            return True
        stack.enter_context(patch.object(pending.native, "publish_native_evidence", side_effect=publish))
        stack.enter_context(patch.object(pending.native.pair, "build_app", side_effect=AssertionError("Additional App build forbidden")))

    def host(self):
        return actions.execute(app=self.app, build=self.build, selection=SELECTION,
            evidence=self.proof / "host", pair=self.api, ui=self.ui, source=SOURCE, run_id=RUN)

    def retry(self):
        return pending.run_after_corrected_build(app=self.app, work=self.work, proof=self.proof, build=self.build,
            selection=SELECTION, pair=self.api, ui=self.ui, method_results=None, source=SOURCE, run_id=RUN)


class OwnedReadinessControls(unittest.TestCase):
    def test_shutdown_destination_boots_once_and_is_observed_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            h = Harness(Path(directory))
            result = simulator.ensure_ready(app=h.app, evidence=h.proof / "ready", selection=SELECTION,
                expected_name=NAME, pair=h.api)
            self.assertEqual(result["status"], "OWNED_SIMULATOR_READY")
            self.assertEqual([(name, timeout) for name, _, timeout in h.calls],
                             [("before", 60), ("boot", 120), ("boot-status", 180)])
            self.assertEqual(h.calls[0][1], ["xcrun", "simctl", "list", "devices", HOST, "--json"])
            self.assertEqual(result["bootstatus_return_code"], 0)
            self.assertFalse(result["postboot_inventory_performed"])
            self.assertNotIn("after", result)

    def test_already_booted_destination_is_not_booted_again(self):
        with tempfile.TemporaryDirectory() as directory:
            h = Harness(Path(directory)); h.devices[HOST]["state"] = "Booted"
            simulator.ensure_ready(app=h.app, evidence=h.proof / "ready", selection=SELECTION, expected_name=NAME, pair=h.api)
            self.assertEqual([name for name, _, _ in h.calls], ["before", "boot-status"])

    def test_foreign_missing_ambiguous_or_unavailable_identity_never_boots(self):
        for mutate in [lambda h: h.devices[HOST].update(name="other-job"),
                       lambda h: h.devices[HOST].update(deviceTypeIdentifier="foreign"),
                       lambda h: h.devices[HOST].update(isAvailable=False),
                       lambda h: h.devices.clear(),
                       lambda h: h.devices.update(other=copy.deepcopy(h.devices[HOST]))]:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                h = Harness(Path(directory)); mutate(h)
                with self.assertRaises(RuntimeError):
                    simulator.ensure_ready(app=h.app, evidence=h.proof / "ready", selection=SELECTION, expected_name=NAME, pair=h.api)
                self.assertEqual([name for name, _, _ in h.calls], ["before"])

    def test_bootstatus_timeout_is_not_readiness_and_keeps_the_original_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            h = Harness(Path(directory)); error = subprocess.TimeoutExpired(["simctl", "bootstatus"], 180)
            h.failures["boot-status"] = error
            with self.assertRaises(subprocess.TimeoutExpired) as result:
                simulator.ensure_ready(app=h.app, evidence=h.proof / "ready", selection=SELECTION, expected_name=NAME, pair=h.api)
            self.assertIs(result.exception, error)
            self.assertEqual(json.loads((h.proof / "ready/readiness.json").read_text())["status"], "FAIL")

    def test_bootstatus_error_and_unexpected_fresh_prestate_cannot_claim_ready(self):
        for mode in ("bootstatus-error", "fresh-prestate"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                h = Harness(Path(directory))
                if mode == "bootstatus-error": h.return_codes["boot-status"] = 69
                else: h.devices[HOST]["state"] = "Booted"
                with self.assertRaises(RuntimeError):
                    simulator.ensure_ready(app=h.app, evidence=h.proof / "ready", selection=SELECTION,
                        expected_name=NAME, pair=h.api, require_initial_shutdown=True)
                self.assertNotIn("after", [name for name, _, _ in h.calls])

    def test_shutdown_requires_same_verified_receipt_and_makes_no_inventory_state_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            h = Harness(Path(directory))
            simulator.ensure_ready(app=h.app, evidence=h.proof / "ready", selection=SELECTION, expected_name=NAME, pair=h.api)
            ownership = h.proof / "ready/readiness.json"
            h.calls.clear()
            value = simulator.shutdown_owned(app=h.app, evidence=h.proof / "shutdown", selection=SELECTION,
                expected_name=NAME, pair=h.api, readiness_receipt_path=ownership)
            self.assertEqual(value["status"], "OWNED_SIMULATOR_SHUTDOWN_COMMAND_SUCCEEDED")
            self.assertEqual([name for name, _, _ in h.calls], ["shutdown"])
            self.assertEqual(value["observed_final_state"], "NOT_QUERIED")
            record = json.loads(ownership.read_text()); record["before"]["name"] = "foreign"
            pair.write(ownership, record); h.calls.clear()
            with self.assertRaises(RuntimeError):
                simulator.shutdown_owned(app=h.app, evidence=h.proof / "foreign", selection=SELECTION,
                    expected_name=NAME, pair=h.api, readiness_receipt_path=ownership)
            self.assertEqual(h.calls, [])

    def test_unknown_shutdown_error_is_not_treated_as_an_already_stopped_device(self):
        with tempfile.TemporaryDirectory() as directory:
            h = Harness(Path(directory))
            simulator.ensure_ready(app=h.app, evidence=h.proof / "ready", selection=SELECTION, expected_name=NAME, pair=h.api)
            h.return_codes["shutdown"] = 149
            with self.assertRaisesRegex(RuntimeError, "shutdown command failed"):
                simulator.shutdown_owned(app=h.app, evidence=h.proof / "shutdown", selection=SELECTION,
                    expected_name=NAME, pair=h.api, readiness_receipt_path=h.proof / "ready/readiness.json")
            self.assertEqual(json.loads((h.proof / "shutdown/shutdown.json").read_text())["status"], "FAIL")


class SameBuildControls(unittest.TestCase):
    def scenario(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        directory = stack.enter_context(tempfile.TemporaryDirectory())
        h = Harness(Path(directory)); h.patches(stack)
        return h, stack

    def test_host_readiness_precedes_enumeration_and_preserves_exact_timeout(self):
        h, _ = self.scenario(); value = h.host()
        names = [name for name, _, _ in h.calls]
        self.assertLess(names.index("boot-status"), names.index("enumerate"))
        self.assertLess(names.index("enumerate"), names.index("test"))
        self.assertEqual(next(timeout for name, _, timeout in h.calls if name == "enumerate"), 180)
        self.assertEqual(value["status"], actions.PASS)
        self.assertEqual(value["simulator_shutdown"]["status"], "OWNED_SIMULATOR_SHUTDOWN_COMMAND_SUCCEEDED")

    def test_readiness_failure_prevents_all_host_discovery_and_test_execution(self):
        h, _ = self.scenario(); h.failures["boot-status"] = subprocess.TimeoutExpired(["bootstatus"], 180)
        with self.assertRaises(subprocess.TimeoutExpired): h.host()
        self.assertFalse({"enumerate", "test"}.intersection(name for name, _, _ in h.calls))
        self.assertEqual(h.devices[HOST]["state"], "Shutdown")

    def test_enumeration_timeout_keeps_zero_test_execution_and_shuts_down(self):
        h, _ = self.scenario(); error = subprocess.TimeoutExpired(["enumerate-tests"], 180)
        h.failures["enumerate"] = error
        with self.assertRaises(subprocess.TimeoutExpired) as result: h.host()
        self.assertIs(result.exception, error)
        self.assertNotIn("test", [name for name, _, _ in h.calls])
        value = json.loads((h.proof / "host/execution.json").read_text())
        self.assertEqual(value["phase"], "COMPILED_SELECTION")
        self.assertEqual(value["status"], "FAIL")
        self.assertNotIn("actual", value)
        self.assertEqual(h.devices[HOST]["state"], "Shutdown")

    def test_pending_nine_uses_same_products_and_separate_account_without_build_or_baseline(self):
        h, _ = self.scenario(); value = h.retry()
        self.assertEqual(value["status"], pending.PASS)
        self.assertEqual(value["additional_app_builds"], 0)
        self.assertEqual(value["device_udid"], NEW)
        self.assertEqual(len(h.native_calls), 1)
        call = h.native_calls[0]
        self.assertIs(call["build"], h.build)
        self.assertIs(call["pending_only"], True)
        self.assertNotIn("account_retry", call)
        self.assertEqual(call["work"], h.work / "account-retry-pending")
        self.assertEqual(call["udid"], NEW)
        self.assertEqual(h.publications[0][2], h.root / "disposable-native-container")
        self.assertEqual(value["actual_counts"]["total_search_calls_in_wrapper"], 9)
        self.assertEqual(h.devices[NEW]["state"], "Shutdown")
        self.assertEqual(h.devices[HOST]["state"], "Shutdown")

    def test_pending_nine_refuses_old_producer_or_an_additional_app_build(self):
        for mutation in [lambda build: build["runtime_binding"].update(heart_source_run_id="44393343388"),
                         lambda build: build.update(app_builds=2)]:
            with self.subTest(mutation=mutation):
                h, _ = self.scenario(); mutation(h.build)
                with self.assertRaises(RuntimeError): h.retry()
                self.assertEqual(h.calls, [])
                self.assertEqual(h.native_calls, [])

    def test_changed_compiled_products_cannot_qualify_pending_results(self):
        h, stack = self.scenario()
        original = pending.native.execute_phase.side_effect
        def changed(**kwargs):
            value = original(**kwargs); h.test_executable.write_bytes(b"changed after execution"); return value
        stack.enter_context(patch.object(pending.native, "execute_phase", side_effect=changed))
        with self.assertRaisesRegex(RuntimeError, "XCTest or original configuration changed"): h.retry()
        self.assertEqual(json.loads((h.proof / "account-retry-pending/result.json").read_text())["status"], "FAIL")
        self.assertEqual(h.devices[NEW]["state"], "Shutdown")

    def test_pending_receipt_cannot_add_baseline_calls_or_omit_real_error(self):
        for mutation in [lambda value: value.update(total_search_calls_in_wrapper=45),
                         lambda value: value.update(baseline_search_calls=36),
                         lambda value: value.update(retry_failed_search_attempts=0)]:
            value = counts(); mutation(value)
            with self.subTest(value=value), self.assertRaises(RuntimeError): pending.validate_counts(value, pair)

    def test_unpublished_native_evidence_cannot_pass_even_with_valid_counts(self):
        h, stack = self.scenario()
        stack.enter_context(patch.object(pending.native, "publish_native_evidence", return_value=False))
        with self.assertRaisesRegex(RuntimeError, "secret-scanned"): h.retry()
        value = json.loads((h.proof / "account-retry-pending/result.json").read_text())
        self.assertEqual(value["status"], "FAIL")
        self.assertEqual(h.devices[NEW]["state"], "Shutdown")

    def test_native_failure_is_preserved_through_owned_shutdown_failure(self):
        h, stack = self.scenario(); error = ValueError("actual native failure")
        stack.enter_context(patch.object(pending.native, "execute_phase", side_effect=error))
        h.failures["shutdown"] = subprocess.TimeoutExpired(["shutdown"], 120)
        with self.assertRaises(ValueError) as result: h.retry()
        self.assertIs(result.exception, error)
        value = json.loads((h.proof / "account-retry-pending/result.json").read_text())
        self.assertEqual(value["status"], "FAIL")
        self.assertEqual(value["shutdown_error_type"], "TimeoutExpired")


if __name__ == "__main__":
    unittest.main()
