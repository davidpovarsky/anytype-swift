"""Synthetic adversarial controls for the SDK CI gate, never native acceptance."""
import ast
import copy
import json
import os
from pathlib import Path
import plistlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import run_host_tests
from host_command import CommandCancelled, command

from run_host_tests import BRANCH, SUITES, require_identity, validate_results, xctest_products
from run_host_tests import EditorEvidenceReviewPending, HostTestProfile, expected_methods


class SDKResultGateTests(unittest.TestCase):
    def setUp(self):
        self.expected = {suite + "/actualMethod" for suite in SUITES}
        self.summary = dict(totalTestCount=4, passedTests=4, failedTests=0, skippedTests=0,
                            devicesAndConfigurations=[dict(device=dict(deviceId="disposable-id", osVersion="27.0",
                            osBuildNumber="24A-test", architecture="arm64", modelName="iPad (A16)"))])
        self.tree = dict(children=[dict(nodeType="Test Case", nodeIdentifier=name + "()", result="Passed")
                                   for name in sorted(self.expected)])

    def validate(self):
        return validate_results(self.summary, self.tree, self.expected, "disposable-id")

    def test_all_four_suites_pass_with_actual_method_identity(self):
        self.assertEqual(set(self.validate()["methods"]), self.expected)

    def test_zero_counts_cannot_pass_even_with_named_tree(self):
        self.summary.update(totalTestCount=0, passedTests=0)
        with self.assertRaisesRegex(ValueError, "Zero or incomplete"):
            self.validate()

    def test_missing_suite_cannot_hide_in_successful_summary(self):
        self.tree["children"].pop()
        with self.assertRaisesRegex(ValueError, "Missing SDK test methods"):
            self.validate()

    def test_unrelated_success_does_not_substitute_for_sdk_test(self):
        self.tree["children"][0]["nodeIdentifier"] = "Unrelated/testPassed()"
        with self.assertRaisesRegex(ValueError, "outside the four"):
            self.validate()

    def test_false_or_missing_or_skipped_results_are_rejected(self):
        for status in ("Failed", "Skipped", None):
            with self.subTest(status=status):
                self.tree["children"][0]["result"] = status
                with self.assertRaisesRegex(ValueError, "nonpassing"):
                    self.validate()

    def test_summary_failure_or_skip_cannot_be_hidden_by_passing_methods(self):
        for field in ("failedTests", "skippedTests"):
            with self.subTest(field=field):
                self.summary[field] = 1
                with self.assertRaisesRegex(ValueError, "Failed or skipped"):
                    self.validate()
                self.summary[field] = 0

    def test_missing_raw_device_os_or_architecture_fails(self):
        original = copy.deepcopy(self.summary["devicesAndConfigurations"][0]["device"])
        for field, value in (("deviceId", "different"), ("osVersion", "26.2"), ("architecture", "x86_64"),
                             ("osBuildNumber", ""), ("modelName", "iPhone 17")):
            with self.subTest(field=field):
                device = copy.deepcopy(original)
                device[field] = value
                self.summary["devicesAndConfigurations"][0]["device"] = device
                with self.assertRaisesRegex(ValueError, "Raw xcresult device"):
                    self.validate()

    def test_boolean_counts_are_not_real_test_counts(self):
        self.summary["failedTests"] = False
        with self.assertRaisesRegex(ValueError, "integer xcresult"):
            self.validate()

    def test_duplicate_identifiers_are_not_counted_twice(self):
        self.tree["children"].append(copy.deepcopy(self.tree["children"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.validate()

    def test_parameter_cases_can_cover_one_declaration_with_actual_passes(self):
        node = self.tree["children"][0]
        second = copy.deepcopy(node)
        second["nodeIdentifier"] = "AnytypeTests/" + node["nodeIdentifier"] + "/argument-2"
        self.tree["children"].append(second)
        self.summary.update(totalTestCount=5, passedTests=5)
        self.assertEqual(set(self.validate()["methods"]), self.expected)

    def test_wrong_source_or_branch_or_missing_run_is_rejected(self):
        valid = ["a" * 40, "a" * 40, BRANCH, BRANCH, "123", "1"]
        require_identity(*valid)
        for index, replacement in ((0, "b" * 40), (1, ""), (2, "develop"),
                                   (3, "codex/chatgpt-wave15-sdk06-20261118"), (4, ""), (5, "0")):
            with self.subTest(index=index):
                values = valid.copy()
                values[index] = replacement
                with self.assertRaises(ValueError):
                    require_identity(*values)


class SDKReturnReceiptGateTests(unittest.TestCase):
    # Review inventory independent of the controller registry: all six must be
    # present in tracked Swift source AND observed as passing actual methods.
    return_methods = {
        "nativeReturnReceiptCompletesOnceWithoutRearmingExecution",
        "nativeReturnHandoffCannotBeMintedTwiceOrForAnAliasedTarget",
        "nativeReturnCannotAcknowledgeQueuedOrDifferentMountedTargets",
        "cancelledOrExpiredNativeReturnNeverRunsMountValidation",
        "nativeReturnScopeLossPreservesQueuedReceiptWithoutRetry",
        "reentrantNativeReturnCancellationCannotPublishMountedReceipt",
    }

    def source_fixture(self, root):
        files, expected = [], set()
        for suite, count in (("HanlinHostAdapterTests", 28), ("HanlinHostWriteTests", 12),
                             ("HanlinHostReadWriteTests", 17), ("HanlinSDKConsumerTests", 6)):
            names = sorted(self.return_methods) if suite == "HanlinHostAdapterTests" else []
            names += ["existingMethod" + str(i) for i in range(count - len(names))]
            relative = "AnytypeTests/Pinkha/" + suite + ".swift"
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join("@Test func " + name + "() {}" for name in names))
            files.append(relative)
            expected.update(suite + "/" + name for name in names)
        return files, expected

    def test_all_six_return_methods_are_required_even_when_declaration_count_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files, expected = self.source_fixture(root)
            with patch.object(subprocess, "check_output", return_value=("\0".join(files) + "\0").encode()):
                actual, hashes = expected_methods(root)
                self.assertEqual(len(actual), 63)
                self.assertEqual(actual, expected)
                self.assertEqual(set(hashes), set(files))
                adapter = root / files[0]
                original = adapter.read_text()
                for name in self.return_methods:
                    with self.subTest(missing=name):
                        adapter.write_text(original.replace(name, "substitutedUnreviewedMethod"))
                        with self.assertRaisesRegex(ValueError, "native return test declarations"):
                            expected_methods(root)

    def test_each_new_return_method_requires_an_actual_pass_not_a_successful_aggregate(self):
        with tempfile.TemporaryDirectory() as temp:
            _, expected = self.source_fixture(Path(temp))
        summary = dict(totalTestCount=63, passedTests=63, failedTests=0, skippedTests=0,
                       devicesAndConfigurations=[dict(device=dict(deviceId="disposable-id", osVersion="27.0",
                       osBuildNumber="24A-test", architecture="arm64", modelName="iPad (A16)"))])
        tree = dict(children=[dict(nodeType="Test Case", nodeIdentifier=name + "()", result="Passed")
                              for name in sorted(expected)])
        self.assertEqual(len(validate_results(summary, tree, expected, "disposable-id")["methods"]), 63)
        for name in self.return_methods:
            with self.subTest(missing=name):
                incomplete = copy.deepcopy(tree)
                incomplete["children"] = [node for node in incomplete["children"]
                                           if node["nodeIdentifier"] != "HanlinHostAdapterTests/" + name + "()"]
                with self.assertRaisesRegex(ValueError, "Missing SDK test methods"):
                    validate_results(summary, incomplete, expected, "disposable-id")


class EditorResultGateTests(unittest.TestCase):
    # Full signatures from root fcdf0cb5; deliberately independent of the
    # runner's method registry. Display labels are not method identities.
    signatures = [
        "delayedDropDoesNotRegainAuthorityOnReactivation()",
        "staleInspectorInsertionIsRejected(dismiss:)",
        "deniedDropDoesNotCreateTextOrMetadata()",
        "dropDeduplicationIsPerGesture()",
        "dropLifetimeIsIndependentOfInspectorPresentation()",
        "revocationDuringBlockResponseStopsMetadata()",
        "lateBlockResponseDoesNotMutateTheNewLifetime()",
        "lateInspectorResponseDoesNotReplaceNewSelectionStatus()",
        "metadataWriteRevalidatesAfterSuspendedNativeRead(cancel:)",
        "inspectorInsertionPersistsConfirmedCanonicalMetadata()",
    ]

    def setUp(self):
        self.expected = {"TorahQuoteInsertionTests/" + signature.split("(")[0] for signature in self.signatures}
        self.summary = dict(totalTestCount=10, passedTests=10, failedTests=0, skippedTests=0,
                            devicesAndConfigurations=[dict(device=dict(deviceId="disposable-id", osVersion="27.0",
                            osBuildNumber="24A-test", architecture="arm64", modelName="iPad (A16)"))])
        nodes = []
        for signature in self.signatures:
            node = dict(nodeType="Test Case", nodeIdentifier="TorahQuoteInsertionTests/" + signature,
                        name="Reviewed display label", result="Passed")
            if ":)" in signature:
                node["children"] = [dict(nodeType="Arguments", name=value, result="Passed") for value in ("false", "true")]
            nodes.append(node)
        self.tree = dict(testNodes=[dict(nodeType="Test Suite", children=nodes)])

    def validate(self):
        return validate_results(self.summary, self.tree, self.expected, "disposable-id", HostTestProfile.EDITOR)

    def test_ten_methods_require_twelve_distinct_declared_cases_independently_of_summary_unit(self):
        for total in (10, 12):
            with self.subTest(raw_summary_total=total):
                self.summary.update(totalTestCount=total, passedTests=total)
                actual = self.validate()
                self.assertEqual(actual["actual_method_count"], 10)
                self.assertEqual(actual["declared_case_count"], 12)
                self.assertEqual(set(actual["methods"]), self.expected)
                self.assertEqual(actual["counts"]["totalTestCount"], total)

    def test_missing_duplicate_skipped_or_failed_argument_cannot_hide_under_a_passing_method(self):
        original = copy.deepcopy(self.tree)
        for corruption in ("missing", "duplicate", "skipped", "failed-run"):
            with self.subTest(corruption=corruption):
                self.tree = copy.deepcopy(original)
                arguments = self.tree["testNodes"][0]["children"][1]["children"]
                if corruption == "missing":
                    arguments.pop()
                elif corruption == "duplicate":
                    arguments[1]["name"] = "false"
                elif corruption == "skipped":
                    arguments[1]["result"] = "Skipped"
                else:
                    arguments[1]["children"] = [dict(nodeType="Test Case Run", result="Failed")]
                with self.assertRaises(ValueError):
                    self.validate()

    def test_unrecognized_argument_representation_is_review_pending_not_pass(self):
        for arguments in ([], [dict(nodeType="Arguments", name="dismiss: false", result="Passed")]):
            with self.subTest(arguments=arguments):
                self.tree["testNodes"][0]["children"][1]["children"] = arguments
                with self.assertRaises(EditorEvidenceReviewPending):
                    self.validate()

    def test_unknown_execution_child_cannot_hide_failed_or_unrecognized_run_evidence(self):
        argument = self.tree["testNodes"][0]["children"][1]["children"][1]
        for result in ("Passed", "Failed"):
            with self.subTest(result=result):
                argument["children"] = [dict(nodeType="Unknown Execution Schema", result=result)]
                error = EditorEvidenceReviewPending if result == "Passed" else ValueError
                with self.assertRaises(error):
                    self.validate()

    def test_extra_summary_count_foreign_method_and_wrong_full_parameter_label_are_rejected(self):
        self.summary.update(totalTestCount=11, passedTests=11)
        with self.assertRaisesRegex(ValueError, "Editor summary"):
            self.validate()
        self.summary.update(totalTestCount=10, passedTests=10)
        node = self.tree["testNodes"][0]["children"][1]
        node["nodeIdentifier"] = "TorahQuoteInsertionTests/staleInspectorInsertionIsRejected(foreign:)"
        with self.assertRaisesRegex(ValueError, "full editor method identity"):
            self.validate()
        node["nodeIdentifier"] = "HanlinHostAdapterTests/unrelatedSDKMethod()"
        with self.assertRaisesRegex(ValueError, "Unexpected xcresult editor"):
            self.validate()

    def test_source_contract_requires_exact_methods_and_both_bool_arguments(self):
        lines = []
        for signature in self.signatures:
            parameters = signature[signature.index("(") + 1:-1]
            attribute = '@Test("source fixture", arguments: [false, true])' if parameters else "@Test"
            lines.append(attribute + "\nfunc " + signature.replace(":)", ": Bool)") + " {}\n")
        source = "\n".join(lines)
        path = "AnytypeTests/Pinkha/TorahQuoteInsertionTests.swift"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / path
            target.parent.mkdir(parents=True)
            with patch.object(subprocess, "check_output", return_value=(path + "\0").encode()):
                target.write_text(source)
                expected, hashes = expected_methods(root, HostTestProfile.EDITOR)
                self.assertEqual(expected, self.expected)
                self.assertEqual(set(hashes), {path})
                for bad in (source.replace("[false, true]", "[false, false]"),
                            source.replace("dismiss: Bool", "foreign: Bool"),
                            source.replace("deniedDropDoesNotCreateTextOrMetadata", "substitutedMethod")):
                    with self.subTest(source=bad[:80]):
                        target.write_text(bad)
                        with self.assertRaises(ValueError):
                            expected_methods(root, HostTestProfile.EDITOR)

    def test_profile_bound_receipts_cannot_turn_editor_success_into_sdk_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp) / "evidence"
            argv = ["run_host_tests.py", "--app", temp, "--evidence", str(evidence),
                    "--derived", str(Path(temp) / "derived"), "--expected-app-branch", BRANCH,
                    "--heart-source-run-id", "123", "--profile", "editor"]
            for status, code in (("SDK06_COMPONENT_PASS", 1), ("EDITOR_COMPONENT_PASS", 0)):
                def completed(args, receipt):
                    receipt.update(status=status, phase="COMPLETE", build_succeeded=True, test_command_exit_code=0)
                with self.subTest(status=status), patch.object(sys, "argv", argv), \
                        patch.object(run_host_tests, "execute", side_effect=completed), patch.object(run_host_tests, "cleanup"):
                    self.assertEqual(run_host_tests.main(), code)
                    receipt = json.loads((evidence / "execution.json").read_text())
                    self.assertEqual(receipt["profile"], "editor")
                    self.assertEqual(receipt["status"], "FAIL" if code else "EDITOR_COMPONENT_PASS")

    def test_unknown_apple_argument_schema_preserves_raw_evidence_receipt_for_review(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp) / "evidence"
            argv = ["run_host_tests.py", "--app", temp, "--evidence", str(evidence),
                    "--derived", str(Path(temp) / "derived"), "--expected-app-branch", BRANCH,
                    "--heart-source-run-id", "123", "--profile", "editor"]
            def review_pending(args, receipt):
                receipt.update(phase="RESULT_REVIEW", build_succeeded=True, test_command_exit_code=0,
                               raw_tests_sha256="a" * 64, post_execution_source_verified=True)
                raise EditorEvidenceReviewPending("unrecognized raw Apple schema")
            with patch.object(sys, "argv", argv), patch.object(run_host_tests, "execute", side_effect=review_pending), \
                    patch.object(run_host_tests, "cleanup"):
                self.assertEqual(run_host_tests.main(), 1)
            receipt = json.loads((evidence / "execution.json").read_text())
            self.assertEqual(receipt["status"], "EDITOR_EVIDENCE_REVIEW_PENDING")
            self.assertEqual(receipt["raw_tests_sha256"], "a" * 64)
            self.assertTrue(receipt["post_execution_source_verified"])
            self.assertEqual(receipt["test_command_exit_code"], 0)
            self.assertTrue(receipt["finished_at"])


class XcodeProductIdentityTests(unittest.TestCase):
    def fixture(self, root, embedded=True, executable="ActualTestExecutable"):
        host = root / "Debug-Anytype-iphonesimulator/Anytype.app"
        bundle = (host / "PlugIns" if embedded else host.parent) / "AnytypeTests.xctest"
        host.mkdir(parents=True)
        bundle.mkdir(parents=True)
        for owner, name in ((host, "Anytype"), (bundle, executable)):
            (owner / "Info.plist").write_bytes(plistlib.dumps(dict(CFBundleExecutable=name)))
            if name == Path(name).name:
                (owner / name).write_bytes(b"synthetic gate fixture only")
        entry = dict(BlueprintName="AnytypeTests", TestHostPath="__TESTROOT__/Debug-Anytype-iphonesimulator/Anytype.app",
                     TestBundlePath="__TESTHOST__/PlugIns/AnytypeTests.xctest" if embedded
                     else "__TESTROOT__/Debug-Anytype-iphonesimulator/AnytypeTests.xctest")
        configuration = root / "Actual.xctestrun"
        configuration.write_bytes(plistlib.dumps(dict(TestConfigurations=[dict(TestTargets=[entry])])))
        return configuration, host, bundle

    def test_actual_xctestrun_and_plist_select_embedded_or_separate_test_binary(self):
        for embedded in (True, False):
            with self.subTest(embedded=embedded), tempfile.TemporaryDirectory() as temp:
                configuration, host, bundle = self.fixture(Path(temp), embedded=embedded)
                # macOS exposes its temporary directory through /var -> /private/var.
                # The product guard returns canonical filesystem paths intentionally.
                self.assertEqual(xctest_products(configuration),
                                 tuple(path.resolve() for path in
                                       (host, host / "Anytype", bundle, bundle / "ActualTestExecutable")))

    def test_missing_executable_cannot_be_reported_as_built(self):
        with tempfile.TemporaryDirectory() as temp:
            configuration, _, bundle = self.fixture(Path(temp))
            (bundle / "ActualTestExecutable").unlink()
            with self.assertRaisesRegex(ValueError, "executable is missing"):
                xctest_products(configuration)

    def test_real_products_directory_with_double_underscores_is_not_a_placeholder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "actual__products__directory"
            root.mkdir()
            configuration, host, bundle = self.fixture(root)
            self.assertEqual(xctest_products(configuration), tuple(path.resolve() for path in
                             (host, host / "Anytype", bundle, bundle / "ActualTestExecutable")))

    def test_unknown_xcode_placeholder_is_still_rejected_before_path_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            configuration, _, _ = self.fixture(Path(temp))
            value = plistlib.loads(configuration.read_bytes())
            entry = value["TestConfigurations"][0]["TestTargets"][0]
            entry["TestHostPath"] = entry["TestHostPath"].replace("__TESTROOT__", "__UNKNOWN_ROOT__")
            configuration.write_bytes(plistlib.dumps(value))
            with self.assertRaisesRegex(ValueError, "Unsupported Xcode product placeholder"):
                xctest_products(configuration)

    def test_executable_cannot_escape_its_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            configuration, _, _ = self.fixture(Path(temp), executable="../foreign")
            with self.assertRaisesRegex(ValueError, "Unsafe or missing"):
                xctest_products(configuration)


class SDKCancellationReceiptTests(unittest.TestCase):
    def test_cancellation_during_cleanup_keeps_completed_build_and_test_facts(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp) / "evidence"
            argv = ["run_host_tests.py", "--app", temp, "--evidence", str(evidence),
                    "--derived", str(Path(temp) / "derived"), "--expected-app-branch", BRANCH,
                    "--heart-source-run-id", "123"]

            def completed(args, receipt):
                receipt.update(status="SDK06_COMPONENT_PASS", phase="COMPLETE", build_succeeded=True,
                               test_command_exit_code=0, actual={"completed_control_sentinel": True})

            with patch.object(sys, "argv", argv), patch.object(run_host_tests, "execute", side_effect=completed), \
                    patch.object(run_host_tests, "cleanup", side_effect=CommandCancelled(signal.SIGINT)):
                self.assertEqual(run_host_tests.main(), 1)
            receipt = json.loads((evidence / "execution.json").read_text())
            self.assertEqual(receipt["status"], "CANCELLED")
            self.assertEqual(receipt["cancellation_signal"], signal.SIGINT)
            self.assertEqual(receipt["phase"], "COMPLETE")
            self.assertTrue(receipt["build_succeeded"])
            self.assertEqual(receipt["test_command_exit_code"], 0)
            self.assertEqual(receipt["actual"], {"completed_control_sentinel": True})
            self.assertTrue(receipt["finished_at"])

    def test_cancelled_execution_is_not_initial_fail_or_pass_and_starts_no_cleanup_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp) / "evidence"
            argv = ["run_host_tests.py", "--app", temp, "--evidence", str(evidence),
                    "--derived", str(Path(temp) / "derived"), "--expected-app-branch", BRANCH,
                    "--heart-source-run-id", "123"]
            previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
            with patch.object(sys, "argv", argv), patch.object(run_host_tests, "execute",
                    side_effect=CommandCancelled(signal.SIGTERM)), patch.object(run_host_tests, "cleanup") as cleanup:
                self.assertEqual(run_host_tests.main(), 1)
            receipt = json.loads((evidence / "execution.json").read_text())
            self.assertEqual(receipt["status"], "CANCELLED")
            self.assertEqual(receipt["cancellation_signal"], signal.SIGTERM)
            self.assertFalse(receipt["build_succeeded"])
            self.assertIsNone(receipt["test_command_exit_code"])
            cleanup.assert_not_called()
            self.assertEqual({sig: signal.getsignal(sig) for sig in previous}, previous)

    def test_injected_xctest_runner_preserves_failure_exports_and_skips_commands_after_cancel(self):
        # Exercise the actual small shared wrapper without importing its Apple
        # build dependencies into these portable controller controls.
        source = Path(__file__).resolve().parents[1] / "PinkhaNativeDerived/build_native_ipa.py"
        if not source.is_file():
            source = Path(__file__).with_name("build_native_ipa.py")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_xctest")
        process_api, default = Mock(), Mock()
        namespace = {"subprocess": process_api, "command": default}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = root / "actual.xcresult"
            result.mkdir()
            runner = Mock(side_effect=CommandCancelled(signal.SIGINT))
            with self.assertRaises(CommandCancelled):
                namespace["run_xctest"](["xcodebuild"], root, root, result, "sdk06", command_runner=runner)
            runner.assert_called_once_with(["xcodebuild"], root, root)
            default.assert_not_called()
            process_api.run.assert_not_called()
            runner.side_effect = subprocess.CalledProcessError(65, ["xcodebuild"])
            with self.assertRaises(subprocess.CalledProcessError):
                namespace["run_xctest"](["xcodebuild"], root, root, result, "sdk06", command_runner=runner)
            self.assertEqual(process_api.run.call_count, 3)
            process_api.reset_mock()
            namespace["run_xctest"](["xcodebuild"], root, root, result, "sdk06")
            default.assert_called_once_with(["xcodebuild"], root, root)
            self.assertEqual(process_api.run.call_count, 3)


@unittest.skipUnless(os.name == "posix", "Actual isolated process-group controls require POSIX")
class SDKCommandProcessTests(unittest.TestCase):
    def test_success_and_failure_keep_output_and_distinct_completed_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            command([sys.executable, "-c", "print('completed command')"], root, root)
            first = json.loads((root / "command-00.json").read_text())
            self.assertEqual((first["status"], first["exit_code"]), ("SUCCEEDED", 0))
            self.assertEqual((root / "command-00.log").read_text(), "completed command\n")
            with self.assertRaises(subprocess.CalledProcessError) as raised:
                command([sys.executable, "-c", "print('error: actual exit seven'); raise SystemExit(7)"], root, root)
            self.assertEqual(raised.exception.returncode, 7)
            second = json.loads((root / "command-01.json").read_text())
            self.assertEqual((second["status"], second["exit_code"]), ("FAILED", 7))
            self.assertIn("actual exit seven", (root / "command-01.log").read_text())
            self.assertEqual(json.loads((root / "command-00.json").read_text()), first)

    def test_sigterm_flushes_partial_log_and_stops_only_the_owned_child_group(self):
        module = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            child = root / "child.py"
            descendant = ("import os,signal,time;from pathlib import Path;"
                          "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
                          "Path('descendant.pid').write_text(str(os.getpid()));"
                          "print('descendant ready',flush=True);time.sleep(60)")
            child.write_text("import subprocess,sys,time\n"
                             "subprocess.Popen([sys.executable,'-c'," + repr(descendant) + "])\n"
                             "print('live child before cancellation',flush=True)\n"
                             "time.sleep(60)\n")
            harness = ("import sys;from pathlib import Path;sys.path.insert(0," + repr(str(module)) + ");"
                       "from host_command import command,cancellation_signals,CommandCancelled\n"
                       "with cancellation_signals():\n"
                       " try: command([sys.executable," + repr(str(child)) + "],Path(" + repr(temp)
                       + "),Path(" + repr(temp) + "))\n"
                       " except CommandCancelled as error: raise SystemExit(128+error.signum)\n")
            unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"],
                                          start_new_session=True)
            owner = subprocess.Popen([sys.executable, "-c", harness], stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            owned_pgid = None
            try:
                log, metadata = root / "command-00.log", root / "command-00.json"
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if log.exists() and "descendant ready" in log.read_text():
                        break
                    self.assertIsNone(owner.poll(), "Command owner exited before the live-output check")
                    time.sleep(0.02)
                self.assertIn("live child before cancellation", log.read_text())
                self.assertIn("descendant ready", log.read_text())
                started = json.loads(metadata.read_text())
                self.assertEqual(started["status"], "RUNNING")
                owned_pgid = started["pgid"]
                descendant_pid = int((root / "descendant.pid").read_text())
                owner.send_signal(signal.SIGTERM)
                output, _ = owner.communicate(timeout=6)
                self.assertEqual(owner.returncode, 128 + signal.SIGTERM, output.decode())
                receipt = json.loads(metadata.read_text())
                self.assertEqual(receipt["status"], "CANCELLED")
                self.assertEqual(receipt["signal"], signal.SIGTERM)
                self.assertEqual(receipt["owned_group_cleanup"]["pgid"], owned_pgid)
                self.assertTrue(receipt["owned_group_cleanup"]["child_reaped"])
                self.assertIsNone(unrelated.poll(), "A different process group must remain untouched")
                state = subprocess.run(["ps", "-p", str(descendant_pid), "-o", "stat="],
                                       capture_output=True, text=True, timeout=2).stdout.strip()
                self.assertTrue(not state or state.startswith("Z"), "Owned descendant is still running: " + state)
                self.assertIn("live child before cancellation", log.read_text())
            finally:
                for pgid in (owned_pgid, owner.pid, unrelated.pid):
                    if pgid is not None:
                        try:
                            os.killpg(pgid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                owner.communicate(timeout=3)
                unrelated.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
