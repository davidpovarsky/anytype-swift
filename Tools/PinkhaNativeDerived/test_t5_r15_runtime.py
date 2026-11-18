"""Pure build-control checks. No Apple framework or runtime is executed here."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import unittest
import subprocess
from unittest import mock
import tempfile

import build_t5_r15_runtime as runtime
import r15_runtime_go as launcher


def metadata():
    return {"AvailableLibraries": [
        {"LibraryIdentifier": "ios-arm64", "LibraryPath": "Lib.framework",
         "SupportedArchitectures": ["arm64"], "SupportedPlatform": "ios"},
        {"LibraryIdentifier": "ios-arm64_x86_64-simulator", "LibraryPath": "Lib.framework",
         "SupportedArchitectures": ["arm64", "x86_64"], "SupportedPlatform": "ios",
         "SupportedPlatformVariant": "simulator"},
    ]}


def slices():
    return [dict(path=path, architecture=arch, marker=runtime.VERSION, sha256="a" * 64)
            for path, arch in sorted(runtime.EXPECTED_SLICES)]


def module_inputs():
    heart = Path("/owned/heart").resolve()
    native = dict(Path=launcher.NATIVE_MODULE, Replace=dict(Dir=str(heart), Path=str(heart)))
    selected = dict(Path=launcher.GENPROTO, Version="obsolete-root-version",
                    Replace=dict(Path=launcher.GENPROTO, Version=launcher.VERSION,
                                 Sum=launcher.MODULE_SUM, GoModSum=launcher.MOD_SUM))
    downloaded = dict(Path=launcher.GENPROTO, Version=launcher.VERSION,
                      Sum=launcher.MODULE_SUM, GoModSum=launcher.MOD_SUM)
    return heart, native, selected, downloaded


class R15RuntimeControls(unittest.TestCase):
    def test_exact_device_and_both_simulator_architectures_are_accepted(self):
        proof = runtime.validate_framework(metadata(), slices())
        self.assertEqual(proof["verified_architecture_count"], 3)
        self.assertEqual(proof["simulator_architectures"], ["arm64", "x86_64"])

    def test_missing_duplicate_and_foreign_slices_are_rejected(self):
        for change in ["missing", "duplicate", "foreign"]:
            with self.subTest(change=change):
                values = slices()
                if change == "missing":
                    values.pop()
                elif change == "duplicate":
                    values[1] = copy.deepcopy(values[0])
                else:
                    values[0]["architecture"] = "armv7"
                with self.assertRaises(RuntimeError):
                    runtime.validate_framework(metadata(), values)

    def test_legacy_marker_or_invalid_binary_hash_cannot_enable_r15(self):
        for field, value in [("marker", runtime.MARKER), ("marker", runtime.VERSION + "-unexpected"),
                             ("sha256", ""), ("sha256", "g" * 64)]:
            with self.subTest(field=field, value=value[:16]):
                values = slices()
                values[0][field] = value
                with self.assertRaises(RuntimeError):
                    runtime.validate_framework(metadata(), values)

    def test_metadata_cannot_relabel_a_missing_or_different_platform(self):
        for field, value in [("SupportedPlatform", "macos"), ("SupportedPlatformVariant", ""),
                             ("SupportedArchitectures", ["arm64"]), ("LibraryPath", "../Lib.framework")]:
            with self.subTest(field=field):
                info = metadata()
                info["AvailableLibraries"][1][field] = value
                with self.assertRaises(RuntimeError):
                    runtime.validate_framework(info, slices())

    def test_native_and_generated_modules_have_explicit_different_workspace_scopes(self):
        heart, generated, work = Path("/owned/heart"), Path("/owned/tmp"), Path("/owned/work/go.work")
        self.assertEqual(launcher.select_scope(heart / "clientlibrary", heart, generated, work),
                         ("heart-source", str(work.resolve())))
        self.assertEqual(launcher.select_scope(generated / "gomobile-work/ios/src-arm64", heart, generated, work),
                         ("generated-gobind", "off"))
        with self.assertRaises(RuntimeError):
            launcher.select_scope(Path("/unowned/location"), heart, generated, work)

    def test_generated_module_must_retain_native_source_and_effective_genproto(self):
        heart, native, selected, downloaded = module_inputs()
        actual = launcher.validate_modules(native, selected, downloaded, heart)
        self.assertEqual(actual["genproto_download"]["Sum"], launcher.MODULE_SUM)

    def test_generated_module_checksum_or_revision_drift_is_rejected(self):
        for field, value in [("Path", "example.invalid/fork"), ("Version", "unexpected"),
                             ("Sum", "h1:wrong"), ("GoModSum", "h1:wrong")]:
            with self.subTest(field=field):
                heart, native, selected, downloaded = module_inputs()
                downloaded[field] = value
                with self.assertRaises(RuntimeError):
                    launcher.validate_modules(native, selected, downloaded, heart)

    def test_downloading_the_right_version_cannot_hide_the_wrong_selected_version(self):
        heart, native, selected, downloaded = module_inputs()
        selected["Replace"]["Version"] = "wrong-selected-version"
        with self.assertRaises(RuntimeError):
            launcher.validate_modules(native, selected, downloaded, heart)

    def test_correct_download_cannot_hide_selected_checksum_drift_or_absence(self):
        for field in ["Sum", "GoModSum"]:
            for value in ["h1:wrong", None]:
                with self.subTest(field=field, value=value):
                    heart, native, selected, downloaded = module_inputs()
                    if value is None:
                        selected["Replace"].pop(field)
                    else:
                        selected["Replace"][field] = value
                    with self.assertRaises(RuntimeError):
                        launcher.validate_modules(native, selected, downloaded, heart)

    def test_native_module_cannot_be_replaced_by_another_checkout(self):
        heart, native, selected, downloaded = module_inputs()
        native["Replace"]["Dir"] = str(Path("/different/heart").resolve())
        with self.assertRaises(RuntimeError):
            launcher.validate_modules(native, selected, downloaded, heart)


    def test_launcher_retains_failed_selected_query_before_losing_the_verified_result(self):
        for arguments in [["mod", "tidy"], ["build", "example.invalid/unused"]]:
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                heart, generated, audit = root / "heart", root / "generated", root / "audit"
                cwd = generated / "ios-arm64"
                cwd.mkdir(parents=True)
                audit.mkdir()
                (cwd / "go.mod").write_text("module gobind\n\ngo 1.26.5\n", encoding="utf8")
                _, native, selected, downloaded = module_inputs()
                native["Replace"].update(Dir=str(heart), Path=str(heart))
                selected["Replace"].pop("Sum")
                query_values = [native, downloaded, selected]
                responses = [subprocess.CompletedProcess([], 0, stdout=json.dumps(value), stderr="")
                             for value in query_values]
                responses.insert(2, subprocess.CompletedProcess([], 0, stdout=json.dumps(downloaded), stderr=""))
                if arguments[0] == "mod":
                    responses.insert(0, subprocess.CompletedProcess([], 0))
                env = dict(PINKHA_T5_REAL_GO=str(root / "go"), PINKHA_T5_HEART=str(heart),
                           PINKHA_T5_GOWORK=str(root / "go.work"), PINKHA_T5_MOBILE_TMP=str(generated),
                           PINKHA_T5_GO_AUDIT=str(audit), PINKHA_T5_GENERATED_CONTRACT=str(root / "contract.json"),
                           PINKHA_T5_GENERATED_CONTRACT_SHA256="a" * 64, GOPROXY="off")
                with (mock.patch.dict(launcher.os.environ, env),
                      mock.patch.object(launcher.Path, "cwd", return_value=cwd),
                      mock.patch.object(launcher, "load_seed_contract", return_value={"before_tidy_manifest": {}}),
                      mock.patch.object(launcher, "audit_initial_manifest", return_value={}),
                      mock.patch.object(launcher, "prepare_generated_module", return_value={}),
                      mock.patch.object(launcher.subprocess, "run", side_effect=responses) as invoked,
                      redirect_stderr(io.StringIO())):
                    self.assertEqual(launcher.main(arguments), 91)
                receipts = list(audit.glob("*.json"))
                self.assertEqual(len(receipts), 1)
                receipt = json.loads(receipts[0].read_text(encoding="utf8"))
                phase = "after_tidy" if arguments[0] == "mod" else "before_build"
                self.assertEqual(receipt["return_code"], 91)
                self.assertEqual(receipt["error"], "Generated gobind module changed the reviewed genproto identity or checksum")
                self.assertNotIn(phase + "_modules", receipt)
                if phase == "after_tidy":
                    self.assertEqual(receipt["command_return_code"], 0)
                    self.assertEqual(invoked.call_count, 5)
                else:
                    self.assertNotIn("command_return_code", receipt)
                    self.assertEqual(invoked.call_count, 4)
                observation = receipt[phase + "_observation"]
                self.assertEqual(observation["status"], "FAIL")
                self.assertEqual(observation["public_genproto_checks"]["effective_sum"], "MISSING")
                self.assertEqual(observation["public_genproto_checks"]["downloaded_sum"], "MATCH")
                self.assertEqual([item["module"] for item in observation["queries"]], query_values)
                for captured, value in zip(observation["queries"], query_values):
                    self.assertEqual(captured["stdout"], json.dumps(value))
                    self.assertEqual(captured["stdout_utf8_sha256"], hashlib.sha256(json.dumps(value).encode()).hexdigest())

    def test_identity_query_failure_or_invalid_json_retains_original_output_and_still_fails(self):
        for response in [subprocess.CompletedProcess([], 1, stdout="partial", stderr="private path diagnostic"),
                         subprocess.CompletedProcess([], 0, stdout="invalid json", stderr="")]:
            with self.subTest(return_code=response.returncode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "go.mod").write_text("module gobind\n", encoding="utf8")
                observation = {}
                with mock.patch.object(launcher.subprocess, "run", return_value=response), self.assertRaises((RuntimeError, ValueError)):
                    launcher.audit_modules(root / "go", dict(GOWORK="off", GOPROXY="off"), root, root / "heart", {}, observation)
                self.assertEqual(observation["status"], "FAIL")
                self.assertNotIn("public_genproto_checks", observation)
                self.assertEqual(len(observation["queries"]), 1)
                captured = observation["queries"][0]
                self.assertEqual(captured["stdout"], response.stdout)
                self.assertEqual(captured["stderr"], response.stderr)
                self.assertEqual(captured["return_code"], response.returncode)

    def test_full_graph_failure_retains_go_error_and_actual_post_tidy_module_files(self):
        # Exact JSON shape produced by the real Go 1.26.5 offline synthetic probe;
        # this is an error-channel fixture, not a claim about the CI dependency.
        original_stdout = ('{\n\t"Path": "example.invalid/pinkha-t5-missing",\n'
                           '\t"Version": "v1.0.0",\n'
                           '\t"Error": "module lookup disabled by GOPROXY=off"\n}\n')
        for arguments in [["mod", "tidy"], ["build", "example.invalid/unused"]]:
            for original_stderr in ["", "go: offline dependency lookup failed\n"]:
                with self.subTest(arguments=arguments, stderr=bool(original_stderr)), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary).resolve()
                    heart, generated, audit = root / "heart", root / "generated", root / "audit"
                    cwd = generated / "ios-arm64"
                    cwd.mkdir(parents=True)
                    audit.mkdir()
                    post_tidy = b"module gobind\n\ngo 1.26.5\n\nrequire example.invalid/pinkha-t5-missing v1.0.0\n"
                    before_sums, after_sums = b"checksums before query\n", b"checksums after failed query\n"
                    (cwd / "go.mod").write_bytes(post_tidy if arguments[0] == "build" else b"module gobind\n")
                    (cwd / "go.sum").write_bytes(before_sums)
                    _, native, _, downloaded = module_inputs()
                    native["Replace"].update(Dir=str(heart), Path=str(heart))
                    calls = []

                    def invoke(command, **kwargs):
                        current = command[1:]
                        calls.append(current)
                        self.assertEqual(kwargs["env"]["GOWORK"], "off")
                        self.assertEqual(kwargs["env"]["GOPROXY"], "off")
                        if current == ["mod", "tidy"]:
                            (cwd / "go.mod").write_bytes(post_tidy)
                            return subprocess.CompletedProcess(command, 0)
                        self.assertEqual(kwargs["timeout"], 60)
                        if current == ["list", "-m", "-json", launcher.NATIVE_MODULE]:
                            return subprocess.CompletedProcess(command, 0, json.dumps(native), "")
                        if current == ["mod", "download", "-json", launcher.GENPROTO + "@" + launcher.VERSION]:
                            return subprocess.CompletedProcess(command, 0, json.dumps(downloaded), "")
                        self.assertEqual(current, ["mod", "download", "-json", "all"])
                        (cwd / "go.sum").write_bytes(after_sums)
                        return subprocess.CompletedProcess(command, 1, original_stdout, original_stderr)

                    env = dict(PINKHA_T5_REAL_GO=str(root / "go"), PINKHA_T5_HEART=str(heart),
                               PINKHA_T5_GOWORK=str(root / "go.work"), PINKHA_T5_MOBILE_TMP=str(generated),
                               PINKHA_T5_GO_AUDIT=str(audit), PINKHA_T5_GENERATED_CONTRACT=str(root / "contract.json"),
                               PINKHA_T5_GENERATED_CONTRACT_SHA256="a" * 64, GOPROXY="off")
                    with (mock.patch.dict(launcher.os.environ, env),
                          mock.patch.object(launcher.Path, "cwd", return_value=cwd),
                          mock.patch.object(launcher, "load_seed_contract", return_value={"before_tidy_manifest": {}}),
                          mock.patch.object(launcher, "audit_initial_manifest", return_value={}),
                          mock.patch.object(launcher, "prepare_generated_module", return_value={}),
                          mock.patch.object(launcher.subprocess, "run", side_effect=invoke),
                          redirect_stderr(io.StringIO())):
                        self.assertEqual(launcher.main(arguments), 91)
                    receipts = list(audit.glob("*.json"))
                    self.assertEqual(len(receipts), 1)
                    receipt = json.loads(receipts[0].read_text(encoding="utf8"))
                    phase = "after_tidy" if arguments[0] == "mod" else "before_build"
                    if phase == "after_tidy":
                        self.assertEqual(receipt["command_return_code"], 0)
                        self.assertEqual(len(calls), 4)
                    else:
                        self.assertNotIn("command_return_code", receipt)
                        self.assertEqual(len(calls), 3)
                    self.assertNotIn(phase + "_modules", receipt)
                    observation = receipt[phase + "_observation"]
                    self.assertEqual(observation["status"], "FAIL")
                    self.assertNotIn("public_genproto_checks", observation)
                    self.assertEqual([item["identity"] for item in observation["queries"]], ["native", "downloaded"])
                    self.assertEqual(len(observation["supporting_queries"]), 1)
                    query = observation["supporting_queries"][0]
                    self.assertEqual(query["argv"], ["mod", "download", "-json", "all"])
                    self.assertEqual(query["status"], "COMMAND_COMPLETED")
                    self.assertEqual(query["return_code"], 1)
                    self.assertEqual(query["stdout"], original_stdout)
                    self.assertEqual(query["stderr"], original_stderr)
                    self.assertEqual(query["stdout_utf8_sha256"], hashlib.sha256(original_stdout.encode()).hexdigest())
                    self.assertEqual(query["stderr_utf8_sha256"], hashlib.sha256(original_stderr.encode()).hexdigest())
                    self.assertEqual(json.loads(query["stdout"])["Error"], "module lookup disabled by GOPROXY=off")
                    for stage, sums in [("input", before_sums), ("output", after_sums)]:
                        for name, expected in [("go.mod", post_tidy), ("go.sum", sums)]:
                            captured = observation[stage + "_module_files"][name]
                            self.assertEqual(captured["status"], "CAPTURED")
                            self.assertEqual(captured["utf8_text"].encode(), expected)
                            self.assertEqual(captured["size_bytes"], len(expected))
                            self.assertEqual(captured["sha256"], hashlib.sha256(expected).hexdigest())

    def test_full_graph_parse_failure_retains_raw_stdout_without_accepting_a_dependency_error(self):
        for output in ["invalid json", '{"Path":"example.invalid/missing","Error":"offline error"}\n']:
            with self.subTest(output=output), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                (root / "go.mod").write_text("module gobind\n", encoding="utf8")
                heart, native, _, downloaded = module_inputs()
                responses = [subprocess.CompletedProcess([], 0, json.dumps(value), "") for value in [native, downloaded]]
                responses.append(subprocess.CompletedProcess([], 0, output, ""))
                observation = {}
                with mock.patch.object(launcher.subprocess, "run", side_effect=responses) as invoked:
                    with self.assertRaises((RuntimeError, ValueError)):
                        launcher.audit_modules(root / "go", dict(GOWORK="off", GOPROXY="off"), root, heart, {}, observation)
                self.assertEqual(invoked.call_count, 3)
                self.assertEqual(observation["status"], "FAIL")
                self.assertNotIn("public_genproto_checks", observation)
                query = observation["supporting_queries"][0]
                self.assertEqual(query["status"], "COMMAND_COMPLETED")
                self.assertEqual(query["stdout"], output)
                self.assertEqual(query["return_code"], 0)
                self.assertEqual(query["stdout_utf8_sha256"], hashlib.sha256(output.encode()).hexdigest())
                self.assertEqual(observation["output_module_files"]["go.sum"]["status"], "MISSING")

    def test_module_snapshot_read_error_cannot_mask_the_original_go_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "go.mod").write_text("module gobind\n", encoding="utf8")
            observation = {}
            response = subprocess.CompletedProcess([], 1, '{"Error":"original Go failure"}', "original stderr")
            with (mock.patch.object(launcher.Path, "read_bytes", side_effect=PermissionError("diagnostic denied")),
                  mock.patch.object(launcher.subprocess, "run", return_value=response)):
                with self.assertRaisesRegex(RuntimeError, "original stderr"):
                    launcher.audit_modules(root / "go", dict(GOWORK="off", GOPROXY="off"), root, root / "heart", {}, observation)
            self.assertEqual(observation["status"], "FAIL")
            self.assertEqual(observation["error_type"], "RuntimeError")
            self.assertEqual(observation["queries"][0]["stdout"], response.stdout)
            for stage in ["input", "output"]:
                for name in ["go.mod", "go.sum"]:
                    self.assertEqual(observation[stage + "_module_files"][name],
                                     dict(status="UNREADABLE", error_type="PermissionError"))

    def test_public_checks_cannot_export_arbitrary_module_values_or_annotation_text(self):
        _, _, selected, downloaded = module_inputs()
        private = "PRIVATE_SENTINEL%0A::warning::/private/runner/token"
        selected["Replace"].update(Version=private, Sum=private, Dir=private)
        selected["Replace"].pop("GoModSum")
        downloaded["GoModSum"] = {"private": private}
        checks = launcher.public_genproto_checks(selected, downloaded)
        self.assertEqual(set(checks), set(launcher.IDENTITY_CHECK_FIELDS))
        self.assertTrue(set(checks.values()) <= launcher.IDENTITY_CHECK_STATES)
        self.assertEqual(checks["effective_version"], "DIFFERENT")
        self.assertEqual(checks["effective_sum"], "DIFFERENT")
        self.assertEqual(checks["effective_go_mod_sum"], "MISSING")
        self.assertEqual(checks["downloaded_go_mod_sum"], "INVALID_VALUE")
        self.assertNotIn(private, json.dumps(checks))
        self.assertEqual(set(launcher.public_genproto_checks(None, []).values()), {"INVALID_RECORD"})

    def diagnostic_record(self):
        _, native, selected, downloaded = module_inputs()
        selected["Replace"].pop("Sum")
        queries = [dict(identity=identity, status="PARSED", return_code=0, module=value)
                   for identity, value in [("native", native), ("downloaded", downloaded), ("selected", selected)]]
        return dict(scope="generated-gobind", return_code=91, command_return_code=0,
                    goos="ios", goarch="arm64", darwin_sdk="iphoneos",
                    after_tidy_observation=dict(status="FAIL", queries=queries))

    def test_builder_publishes_only_sanitized_comparisons_and_keeps_original_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            record = self.diagnostic_record()
            private = "PRIVATE_SENTINEL%0A::warning::/private/runner/token"
            record.update(cwd=private, error=private, goarch=private)
            record["after_tidy_observation"]["queries"][2]["module"]["Replace"]["GoModSum"] = private
            def fail(args, control, evidence):
                audit = evidence / "go-launcher"
                audit.mkdir()
                (audit / "observed.json").write_text(json.dumps(record), encoding="utf8")
                raise RuntimeError("gomobile-bind failed; see original retained log")
            output = io.StringIO()
            with mock.patch.object(runtime, "execute", side_effect=fail), redirect_stdout(output):
                code = runtime.main(["--source", str(root / "source"), "--heart-source", str(root / "heart"),
                                     "--work", str(root / "work"), "--artifacts", str(root / "artifacts"),
                                     "--evidence", str(root / "evidence")])
            receipt = json.loads((root / "evidence/runtime-build-result.json").read_text(encoding="utf8"))
            self.assertEqual(code, 1)
            self.assertEqual(receipt["status"], "FAIL")
            self.assertEqual(receipt["error"], "gomobile-bind failed; see original retained log")
            self.assertEqual(receipt["native_test_invocations"], 0)
            self.assertEqual(receipt["swift_pairing_status"], "NOT_RUN")
            self.assertEqual(receipt["client_enablement"], runtime.pair_ci.CLIENT_DISABLED)
            self.assertEqual(receipt["module_identity_diagnostic_status"], "RECORDED")
            self.assertNotIn(private, output.getvalue())
            annotations = [line for line in output.getvalue().splitlines() if line.startswith("::error")]
            self.assertEqual(len(annotations), 1)
            diagnostic = json.loads(annotations[0].split("::", 2)[2])
            self.assertEqual(diagnostic["phase"], "AFTER_TIDY")
            self.assertEqual(diagnostic["command_return_code"], 0)
            self.assertEqual(diagnostic["goarch"], "UNRECOGNIZED")
            self.assertEqual(diagnostic["checks"]["effective_sum"], "MISSING")
            self.assertEqual(diagnostic["checks"]["effective_go_mod_sum"], "DIFFERENT")
            self.assertEqual(diagnostic["receipt_sha256"], runtime.digest(root / "evidence/go-launcher/observed.json"))

    def test_missing_or_incomplete_observation_cannot_be_fabricated_from_legacy_error_text(self):
        for change in ["legacy", "incomplete", "duplicate", "command-failed", "phase-passed"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                audit = root / "go-launcher"
                audit.mkdir()
                record = self.diagnostic_record()
                observation = record["after_tidy_observation"]
                if change == "legacy":
                    record.pop("after_tidy_observation")
                    record["error"] = "Generated gobind module changed the reviewed genproto identity or checksum"
                elif change == "incomplete":
                    observation["queries"].pop()
                elif change == "duplicate":
                    observation["queries"][2] = copy.deepcopy(observation["queries"][1])
                elif change == "command-failed":
                    observation["queries"][2]["return_code"] = 1
                else:
                    observation["status"] = "PASS"
                (audit / "observed.json").write_text(json.dumps(record), encoding="utf8")
                self.assertEqual(runtime.failed_module_identity_diagnostics(root), [])

    def test_diagnostic_read_failure_never_replaces_original_build_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with (mock.patch.object(runtime, "execute", side_effect=RuntimeError("original build failure")),
                  mock.patch.object(runtime, "failed_module_identity_diagnostics", side_effect=ValueError("private invalid receipt")),
                  redirect_stdout(io.StringIO()) as output):
                code = runtime.main(["--source", str(root / "source"), "--heart-source", str(root / "heart"),
                                     "--work", str(root / "work"), "--artifacts", str(root / "artifacts"),
                                     "--evidence", str(root / "evidence")])
            receipt = json.loads((root / "evidence/runtime-build-result.json").read_text(encoding="utf8"))
            self.assertEqual(code, 1)
            self.assertEqual(receipt["status"], "FAIL")
            self.assertEqual(receipt["error"], "original build failure")
            self.assertEqual(receipt["module_identity_diagnostic_status"], "DIAGNOSTIC_READ_FAILED")
            self.assertEqual(receipt["native_test_invocations"], 0)
            self.assertNotIn("private invalid receipt", output.getvalue())


    def mobile_fixture(self, root):
        work, cache, gobind = root / "work", root / "module-cache", root / "deps/gobind"
        work.mkdir()
        cache.mkdir()
        gobind.parent.mkdir()
        gobind.write_bytes(b"fixture pinned gobind binary")
        env = dict(GOPROXY="off", GOFLAGS="-mod=readonly", GOWORK="reviewed.work",
                   GOPATH="original-shared-path", PATH="unchanged-path")
        return work, cache, gobind, runtime.digest(gobind), env

    def test_apple_workspace_preserves_original_module_cache_and_pinned_gobind(self):
        with tempfile.TemporaryDirectory() as temporary:
            work, cache, gobind, expected, env = self.mobile_fixture(Path(temporary).resolve())
            original = dict(env)
            selected, receipt = runtime.prepare_apple_bind(work, cache, gobind, str(gobind), expected, env)
            self.assertEqual(env, original)
            self.assertEqual(selected["GOMODCACHE"], str(cache))
            self.assertEqual(selected["GOPROXY"], "off")
            self.assertEqual(selected["GOFLAGS"], "-mod=readonly")
            self.assertEqual(selected["GOWORK"], "reviewed.work")
            self.assertTrue((Path(selected["GOPATH"]) / "pkg/gomobile").is_dir())
            self.assertEqual(receipt["gobind_sha256"], expected)
            self.assertEqual(receipt["gomobile_init"], "NOT_INVOKED_UNPINNED_LATEST_INSTALL")
            self.assertEqual(receipt["mobile_version"], runtime.MOBILE_VERSION)

    def test_foreign_path_tool_or_changed_pinned_binary_is_rejected_before_workspace_creation(self):
        for change in ["foreign-path", "changed-binary", "missing-path"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                work, cache, gobind, expected, env = self.mobile_fixture(Path(temporary).resolve())
                selected = str(gobind)
                if change == "foreign-path":
                    selected = str(gobind.parent / "different-gobind")
                elif change == "changed-binary":
                    gobind.write_bytes(b"unexpected replacement binary")
                else:
                    selected = None
                with self.assertRaises(RuntimeError):
                    runtime.prepare_apple_bind(work, cache, gobind, selected, expected, env)
                self.assertFalse((work / "gomobile-gopath").exists())

    def test_apple_preparation_cannot_enable_network_or_replace_missing_module_cache(self):
        for change in ["network", "mutable-modules", "missing-cache", "relative-cache"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                work, cache, gobind, expected, env = self.mobile_fixture(Path(temporary).resolve())
                if change == "network":
                    env["GOPROXY"] = "https://proxy.golang.org"
                elif change == "mutable-modules":
                    env["GOFLAGS"] = "-mod=mod"
                elif change == "missing-cache":
                    cache = cache / "absent"
                else:
                    cache = Path("relative-cache")
                with self.assertRaises(RuntimeError):
                    runtime.prepare_apple_bind(work, cache, gobind, str(gobind), expected, env)
                self.assertFalse((work / "gomobile-gopath").exists())

    def test_existing_mobile_workspace_is_not_reused_or_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            work, cache, gobind, expected, env = self.mobile_fixture(Path(temporary).resolve())
            previous = work / "gomobile-gopath"
            previous.mkdir()
            marker = previous / "preserve-existing"
            marker.write_text("must remain")
            with self.assertRaises(FileExistsError):
                runtime.prepare_apple_bind(work, cache, gobind, str(gobind), expected, env)
            self.assertEqual(marker.read_text(), "must remain")


    def dependency_fixture(self, root):
        source, work = root / "cached-mobile", root / "owned-work"
        source.mkdir()
        work.mkdir()
        primary = Path(__file__).resolve().parents[2] / (
            "docs/validation/20261118-t5-r15-runtime/44235484816/dependency-source")
        for name in runtime.MOBILE_SEED_HASHES:
            (source / name).write_bytes((primary / ("mobile." + name)).read_bytes())
        selected = dict(Path="golang.org/x/mobile", Version=runtime.MOBILE_VERSION,
                        Sum=runtime.MOBILE_MODULE_SUM, GoModSum=runtime.MOBILE_MOD_SUM, Dir=str(source))
        return source, work, selected

    def test_mobile_seed_uses_exact_primary_files_without_mutating_the_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, work, selected = self.dependency_fixture(Path(temporary).resolve())
            before = {name: (source / name).read_bytes() for name in runtime.MOBILE_SEED_HASHES}
            seed, receipt = runtime.prepare_mobile_dependency_seed(work, selected)
            self.assertEqual({name: (seed / name).read_bytes() for name in before}, before)
            self.assertEqual({name: (source / name).read_bytes() for name in before}, before)
            self.assertEqual(receipt["seed_sha256"], runtime.MOBILE_SEED_HASHES)
            self.assertEqual(seed.parent, work)

    def test_mobile_selection_or_cached_declaration_drift_is_rejected_before_copy(self):
        for change in ["module", "version", "sum", "mod-sum", "replace", "go.mod", "go.sum"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                source, work, selected = self.dependency_fixture(Path(temporary).resolve())
                if change in ["go.mod", "go.sum"]:
                    (source / change).write_bytes(b"changed declaration bytes")
                elif change == "replace":
                    selected["Replace"] = {"Path": "foreign/mobile"}
                else:
                    field = {"module": "Path", "version": "Version", "sum": "Sum", "mod-sum": "GoModSum"}[change]
                    selected[field] = "unexpected"
                with self.assertRaises(RuntimeError):
                    runtime.prepare_mobile_dependency_seed(work, selected)
                self.assertFalse((work / "mobile-dependency-seed").exists())

    def test_existing_dependency_seed_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, work, selected = self.dependency_fixture(Path(temporary).resolve())
            target = work / "mobile-dependency-seed"
            target.mkdir()
            marker = target / "preserve"
            marker.write_text("existing owned state")
            with self.assertRaises(FileExistsError):
                runtime.prepare_mobile_dependency_seed(work, selected)
            self.assertEqual(marker.read_text(), "existing owned state")

    def test_pinned_shiny_and_metal_download_receipts_bind_both_checksums(self):
        values = [dict(Path=path, **fields) for path, fields in runtime.MOBILE_GRAPH_REQUIRED.items()]
        receipt = runtime.validate_mobile_dependency_download("\n".join(json.dumps(value) for value in values))
        self.assertEqual(receipt["modules"], runtime.MOBILE_GRAPH_REQUIRED)
        self.assertEqual(receipt["downloaded_module_count"], 2)

    def test_missing_old_or_ambiguous_metal_cache_receipt_cannot_pass(self):
        for change in ["missing", "version", "sum", "mod-sum", "error", "duplicate"]:
            with self.subTest(change=change):
                values = [dict(Path=path, **fields) for path, fields in runtime.MOBILE_GRAPH_REQUIRED.items()]
                if change == "missing":
                    values.pop()
                elif change == "duplicate":
                    values.append(copy.deepcopy(values[-1]))
                elif change == "error":
                    values[-1]["Error"] = "not downloaded"
                else:
                    field = {"version": "Version", "sum": "Sum", "mod-sum": "GoModSum"}[change]
                    values[-1][field] = "old-native-only-receipt"
                with self.assertRaises(RuntimeError):
                    runtime.validate_mobile_dependency_download("\n".join(json.dumps(value) for value in values))



    def generated_fixture(self, root):
        work, heart, mobile = root / "owned-work", root / "owned-heart", root / "pinned-mobile"
        for directory in [work, heart, mobile]:
            directory.mkdir()
        (heart / "preserve-native").write_bytes(b"unchanged native input")
        proof = Path(__file__).resolve().parents[2] / "docs/validation/20261118-t5-r15-runtime/44240654969"
        for path in runtime.MOBILE_BIND_SOURCES:
            target = mobile / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if path == "cmd/gomobile/main.go":
                primary = Path(__file__).resolve().parent / "fixtures/gomobile-cd096645fcd3/main.go"
            else:
                primary = proof / "dependency-source" / ("gomobile-" + Path(path).name)
            target.write_bytes(primary.read_bytes())
        module = dict(Path="golang.org/x/mobile", Version=runtime.MOBILE_VERSION,
                      Sum=runtime.MOBILE_MODULE_SUM, GoModSum=runtime.MOBILE_MOD_SUM, Dir=str(mobile))
        source = proof / "unpacked/Pinkha-Native-Derived-Evidence/runtime/resolved-native-modules.log"
        records = launcher.module_records(source.read_text(encoding="utf8"))
        # This is a controller fixture. Only the machine-local root path changes;
        # all captured remote module/version/replacement data remains original.
        records[0]["Dir"] = str(heart)
        return work, heart, module, records

    def graph_fixture(self):
        heart, native, genproto, _ = module_inputs()
        fields = runtime.GENERATED_GRAPH_REQUIRED["git.sr.ht/~sbinet/gg"]
        gg = dict(Path=fields["effective_path"], Version=fields["effective_version"],
                  Sum=fields["sum"], GoModSum=fields["go_mod_sum"])
        rows = [dict(Path="gobind", Main=True), native, gg, genproto]
        graph = launcher.selected_graph(rows, heart)
        downloads = {
            value["effective_path"] + "@" + value["effective_version"]: dict(
                Path=value["effective_path"], Version=value["effective_version"],
                Sum=value["sum"], GoModSum=value["go_mod_sum"])
            for value in graph.values()
        }
        return heart, rows, graph, downloads

    def manifest_fixture(self, heart):
        return dict(Module={"Path": "gobind"}, Go="1.26",
                    Require=[dict(Path="example.org/dependency", Version="v1.2.3")],
                    Replace=[dict(Old={"Path": launcher.NATIVE_MODULE}, New={"Path": str(heart)}),
                             dict(Old={"Path": launcher.GENPROTO, "Version": "v0.0.0-20240903143218-8af14fe29dc1"},
                                  New={"Path": launcher.GENPROTO, "Version": launcher.VERSION})])

    def test_full_graph_hydration_precedes_strict_selected_checksum_and_seed_checks(self):
        changes = ["unchanged", "selected-still-missing", "selected-sum-drift", "pinned-download-drift",
                   "full-download-drift", "selected-graph-drift", "offline-cache-miss"]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                heart, rows, graph, downloads = self.graph_fixture()
                _, _, selected, pinned_download = module_inputs()
                manifest = launcher.reviewed_generated_manifest(self.manifest_fixture(heart))
                mod = b"module gobind\n\ngo 1.26.5\n"
                (root / "go.mod").write_bytes(mod)
                (root / "go.sum").write_text("", encoding="utf8")
                state = {"hydrated": False, "full_download_calls": 0}

                def command(args, **kwargs):
                    self.assertEqual(kwargs["env"]["GOPROXY"], "off")
                    self.assertEqual(kwargs["env"]["GOWORK"], "off")
                    selection = args[1:]
                    if selection == ["list", "-m", "-json", launcher.NATIVE_MODULE]:
                        value = rows[1]
                    elif selection == ["mod", "download", "-json", launcher.GENPROTO + "@" + launcher.VERSION]:
                        value = copy.deepcopy(pinned_download)
                        if change == "pinned-download-drift":
                            value["Sum"] = launcher.MOD_SUM
                    elif selection == ["mod", "download", "-json", "all"]:
                        state["full_download_calls"] += 1
                        if change == "offline-cache-miss":
                            return subprocess.CompletedProcess(args, 1, stdout='{"Error":"module lookup disabled by GOPROXY=off"}', stderr="")
                        state["hydrated"] = True
                        values = copy.deepcopy(list(downloads.values()))
                        if change == "full-download-drift":
                            values[0]["Sum"] = launcher.MODULE_SUM
                        (root / "go.sum").write_text("\n".join(item["Path"] + " " + item["Version"] + " " + item["Sum"] for item in values) + "\n", encoding="utf8")
                        return subprocess.CompletedProcess(args, 0, stdout="\n".join(json.dumps(item) for item in values), stderr="")
                    elif selection == ["list", "-m", "-json", launcher.GENPROTO]:
                        value = copy.deepcopy(selected)
                        if not state["hydrated"] or change == "selected-still-missing":
                            value["Replace"].pop("Sum")
                        elif change == "selected-sum-drift":
                            value["Replace"]["Sum"] = launcher.MOD_SUM
                    elif selection == ["list", "-m", "-json", "all"]:
                        values = copy.deepcopy(rows)
                        if change == "selected-graph-drift":
                            values[2]["Version"] = "v9.9.9"
                        return subprocess.CompletedProcess(args, 0, stdout="\n".join(json.dumps(item) for item in values), stderr="")
                    elif selection == ["mod", "edit", "-json"]:
                        value = manifest
                    else:
                        raise AssertionError("Unexpected metadata command")
                    return subprocess.CompletedProcess(args, 0, stdout=json.dumps(value), stderr="")

                observation = {}
                contract = dict(selected_dependencies=graph, prepared_tidy_manifest=manifest,
                                post_tidy_manifest=copy.deepcopy(manifest))
                with mock.patch.object(launcher.subprocess, "run", side_effect=command):
                    if change == "unchanged":
                        result = launcher.audit_modules(root / "go", dict(GOWORK="off", GOPROXY="off"),
                                                        root, heart, contract, observation)
                        self.assertEqual(result["genproto_selection"]["Replace"]["Sum"], launcher.MODULE_SUM)
                        self.assertEqual(result["selected_dependency_graph"], graph)
                        self.assertEqual(result["go_mod_sha256"], hashlib.sha256(mod).hexdigest())
                        self.assertEqual(observation["status"], "PASS")
                    else:
                        with self.assertRaises(RuntimeError):
                            launcher.audit_modules(root / "go", dict(GOWORK="off", GOPROXY="off"),
                                                   root, heart, contract, observation)
                        self.assertEqual(observation["status"], "FAIL")
                self.assertEqual(state["full_download_calls"], 1)
                self.assertEqual((root / "go.mod").read_bytes(), mod)

    def test_post_tidy_identity_rejects_each_stale_native_toolchain_or_input_field(self):
        current = runtime.post_tidy_source_inputs()
        runtime.validate_post_tidy_inputs(current, runtime.POST_TIDY_ORIGINAL_MANIFEST_SHA)
        for field in current:
            with self.subTest(field=field):
                changed = copy.deepcopy(current)
                if field == "bind_sources":
                    changed[field]["cmd/gomobile/bind.go"] = "0" * 64
                else:
                    changed[field] = "stale-" + changed[field]
                with self.assertRaises(RuntimeError):
                    runtime.validate_post_tidy_inputs(changed, runtime.POST_TIDY_ORIGINAL_MANIFEST_SHA)
        for original_sha in ["", "0" * 64, runtime.POST_TIDY_MANIFEST_SHA]:
            with self.subTest(original_sha=original_sha), self.assertRaises(RuntimeError):
                runtime.validate_post_tidy_inputs(current, original_sha)

    def test_post_tidy_normalization_rejects_missing_duplicate_and_extra_local_replacements(self):
        heart = Path("/owned/heart").resolve()
        original = self.manifest_fixture(heart)
        saved = copy.deepcopy(original)
        normalized = runtime.normalized_native_manifest(original, heart)
        self.assertEqual(original, saved)
        local = next(item for item in normalized["Replace"] if item["Old"]["Path"] == launcher.NATIVE_MODULE)
        self.assertEqual(local["New"], {"Path": runtime.POST_TIDY_PLACEHOLDER})
        for change in ["missing", "duplicate", "different-directory", "local-version", "extra-local"]:
            with self.subTest(change=change):
                candidate = copy.deepcopy(original)
                if change == "missing":
                    candidate["Replace"].pop(0)
                elif change == "duplicate":
                    candidate["Replace"].append(copy.deepcopy(candidate["Replace"][0]))
                elif change == "different-directory":
                    candidate["Replace"][0]["New"]["Path"] = "/other/heart"
                elif change == "local-version":
                    candidate["Replace"][0]["New"]["Version"] = "v1.0.0"
                else:
                    candidate["Replace"].append(dict(Old={"Path": "example.org/local"}, New={"Path": "/other"}))
                with self.assertRaises(RuntimeError):
                    runtime.normalized_native_manifest(candidate, heart)

    def test_post_tidy_seed_changes_only_the_owned_heart_path_and_preserves_the_fixture(self):
        fixture = Path(__file__).resolve().parents[2] / runtime.POST_TIDY_FIXTURE
        original_bytes = fixture.read_bytes()
        self.assertEqual(hashlib.sha256(original_bytes).hexdigest(), runtime.POST_TIDY_FIXTURE_SHA)
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary).resolve()
            heart = work / "Heart with spaces"
            original = self.manifest_fixture(heart)
            normalized_sha = runtime.manifest_digest(runtime.normalized_native_manifest(original, heart))
            with mock.patch.object(runtime, "POST_TIDY_ORIGINAL_MANIFEST_SHA", normalized_sha):
                seed, receipt = runtime.prepare_post_tidy_seed(work, fixture.parents[4], heart, original)
                materialized = (seed / "go.mod").read_text(encoding="utf8")
                self.assertNotIn(runtime.POST_TIDY_PLACEHOLDER, materialized)
                self.assertEqual(materialized.replace(json.dumps(str(heart)), runtime.POST_TIDY_PLACEHOLDER),
                                 original_bytes.decode("utf8"))
                self.assertEqual(receipt["source_inputs"], runtime.POST_TIDY_INPUTS)
                self.assertEqual(receipt["initial_go_mod_sha256"], runtime.digest(seed / "go.mod"))
                with self.assertRaises(FileExistsError):
                    runtime.prepare_post_tidy_seed(work, fixture.parents[4], heart, original)
        self.assertEqual(fixture.read_bytes(), original_bytes)

    def test_post_tidy_seed_rejects_stale_bytes_and_unresolved_or_extra_placeholders(self):
        fixture = Path(__file__).resolve().parents[2] / runtime.POST_TIDY_FIXTURE
        original_bytes = fixture.read_bytes()
        for change in ["stale", "missing", "duplicate", "misplaced"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                control = Path(temporary).resolve()
                work = control / "work"
                work.mkdir()
                heart = control / "heart"
                original = self.manifest_fixture(heart)
                target = control / runtime.POST_TIDY_FIXTURE
                target.parent.mkdir(parents=True)
                raw = original_bytes
                if change == "stale":
                    raw += b"\n// changed\n"
                elif change == "missing":
                    raw = raw.replace(runtime.POST_TIDY_PLACEHOLDER.encode(), b"/unreviewed/heart")
                elif change == "duplicate":
                    raw += ("\n// " + runtime.POST_TIDY_PLACEHOLDER + "\n").encode()
                else:
                    raw = raw.replace((" => " + runtime.POST_TIDY_PLACEHOLDER).encode(),
                                      (" => \"" + runtime.POST_TIDY_PLACEHOLDER + "\"").encode())
                target.write_bytes(raw)
                normalized_sha = runtime.manifest_digest(runtime.normalized_native_manifest(original, heart))
                expected_fixture = runtime.POST_TIDY_FIXTURE_SHA if change == "stale" else hashlib.sha256(raw).hexdigest()
                with (mock.patch.object(runtime, "POST_TIDY_ORIGINAL_MANIFEST_SHA", normalized_sha),
                      mock.patch.object(runtime, "POST_TIDY_FIXTURE_SHA", expected_fixture),
                      self.assertRaises(RuntimeError)):
                    runtime.prepare_post_tidy_seed(work, control, heart, original)
                self.assertFalse((work / "post-tidy-dependency-seed").exists())

    def test_post_tidy_manifest_requires_exact_roots_and_all_original_replacements(self):
        heart = Path("/owned/heart").resolve()
        prepared = launcher.reviewed_generated_manifest(self.manifest_fixture(heart))
        expected = copy.deepcopy(prepared)
        sha = runtime.manifest_digest(runtime.normalized_native_manifest(expected, heart, prepared=True))
        for change in ["unchanged", "require-version", "missing-require", "extra-require", "indirect",
                       "extra-replace", "local-replace", "remote-replace", "module", "go"]:
            with self.subTest(change=change):
                value = copy.deepcopy(expected)
                if change == "require-version":
                    value["Require"][0]["Version"] = "v9.9.9"
                elif change == "missing-require":
                    value["Require"].clear()
                elif change == "extra-require":
                    value["Require"].append(dict(Path="example.org/unexpected", Version="v1.0.0"))
                elif change == "indirect":
                    value["Require"][0]["Indirect"] = True
                elif change == "extra-replace":
                    value["Replace"].append(dict(Old={"Path": "example.org/extra"}, New={"Path": "example.org/fork", "Version": "v1.0.0"}))
                elif change == "local-replace":
                    next(item for item in value["Replace"] if item["Old"]["Path"] == launcher.NATIVE_MODULE)["New"]["Path"] = "/foreign"
                elif change == "remote-replace":
                    next(item for item in value["Replace"] if item["Old"]["Path"] == launcher.GENPROTO)["New"]["Version"] = "v9.9.9"
                elif change == "module":
                    value["Module"]["Path"] = "other"
                elif change == "go":
                    value["Go"] = "1.26.6"
                with mock.patch.object(runtime, "POST_TIDY_MANIFEST_SHA", sha):
                    if change == "unchanged":
                        self.assertEqual(runtime.validate_post_tidy_manifest(value, prepared, heart), expected)
                    else:
                        with self.assertRaises(RuntimeError):
                            runtime.validate_post_tidy_manifest(value, prepared, heart)

    def test_post_tidy_seed_requires_actual_checksums_for_both_missing_archives(self):
        graph = {path: dict(fields, version=fields["effective_version"], replaced=False)
                 for path, fields in runtime.POST_TIDY_GRAPH_REQUIRED.items()}
        downloads = {value["effective_path"] + "@" + value["effective_version"]: dict(
            Path=value["effective_path"], Version=value["effective_version"], Sum=value["sum"], GoModSum=value["go_mod_sum"])
            for value in graph.values()}
        self.assertEqual(runtime.validate_post_tidy_seed_graph(graph, downloads)["selected_module_count"], 3)
        for path in graph:
            for change in ["missing", "version", "sum", "go_mod_sum"]:
                with self.subTest(path=path, change=change):
                    selected, cached = copy.deepcopy(graph), copy.deepcopy(downloads)
                    if change == "missing":
                        selected.pop(path)
                    elif change == "version":
                        selected[path]["effective_version"] = "v9.9.9"
                    else:
                        # Even internally matching wrong download/selection hashes
                        # must fail against the fixed authoritative dependency.
                        selected[path][change] = launcher.MODULE_SUM
                        key = selected[path]["effective_path"] + "@" + selected[path]["effective_version"]
                        cached[key]["Sum" if change == "sum" else "GoModSum"] = launcher.MODULE_SUM
                    with self.assertRaises(RuntimeError):
                        runtime.validate_post_tidy_seed_graph(selected, cached)

    def test_actual_post_tidy_selection_rejects_pruning_drift_and_missing_contract(self):
        heart, _, graph, _ = self.graph_fixture()
        manifest = launcher.reviewed_generated_manifest(self.manifest_fixture(heart))
        contract = dict(selected_dependencies=graph, prepared_tidy_manifest=copy.deepcopy(manifest),
                        post_tidy_manifest=copy.deepcopy(manifest))
        proof = launcher.validate_post_tidy_selection(graph, manifest, contract)
        self.assertEqual(proof["policy"], "EXACT_PREPARED_POST_TIDY_GRAPH_AND_MANIFEST")
        for change in ["extra", "missing", "version", "replacement", "checksum", "require",
                       "local", "extra-replacement", "missing-manifest", "changed-contract-replacement"]:
            with self.subTest(change=change):
                actual, declaration, bound = copy.deepcopy(graph), copy.deepcopy(manifest), copy.deepcopy(contract)
                key = next(iter(actual))
                if change == "extra":
                    actual["example.org/unexpected"] = copy.deepcopy(actual[key])
                elif change == "missing":
                    actual.pop(key)
                elif change == "version":
                    actual[key]["version"] = "v9.9.9"
                elif change == "replacement":
                    actual[key]["replaced"] = not actual[key]["replaced"]
                elif change == "checksum":
                    actual[key]["sum"] = launcher.MOD_SUM
                elif change == "require":
                    declaration["Require"][0]["Version"] = "v9.9.9"
                elif change == "local":
                    next(item for item in declaration["Replace"] if item["Old"]["Path"] == launcher.NATIVE_MODULE)["New"]["Path"] = "/foreign"
                elif change == "extra-replacement":
                    declaration["Replace"].append(dict(Old={"Path": "example.org/a"}, New={"Path": "example.org/b", "Version": "v1.0.0"}))
                elif change == "missing-manifest":
                    bound.pop("post_tidy_manifest")
                else:
                    bound["post_tidy_manifest"]["Replace"].append(dict(Old={"Path": "example.org/a"}, New={"Path": "example.org/b", "Version": "v1.0.0"}))
                    declaration = copy.deepcopy(bound["post_tidy_manifest"])
                with self.assertRaises((RuntimeError, KeyError)):
                    launcher.validate_post_tidy_selection(actual, declaration, bound)

    def test_original_generated_go_directive_is_minor_only_and_never_a_version_range(self):
        original = self.manifest_fixture(Path("/owned/heart"))
        self.assertEqual(launcher.canonical_manifest(original)["Go"], "1.26")
        for changed in ["1.26.5", "1.26.0", "1.25", "1.27", "", None]:
            with self.subTest(go=changed):
                candidate = copy.deepcopy(original)
                candidate["Go"] = changed
                with self.assertRaises(RuntimeError):
                    launcher.canonical_manifest(candidate)

    def test_prepared_go_directive_requires_the_exact_pinned_native_patch(self):
        prepared = launcher.reviewed_generated_manifest(self.manifest_fixture(Path("/owned/heart")))
        self.assertEqual(launcher.canonical_manifest(prepared, prepared=True)["Go"], "1.26.5")
        for changed in ["1.26", "1.26.0", "1.26.4", "1.26.6", "1.27.0", "", None]:
            with self.subTest(go=changed):
                candidate = copy.deepcopy(prepared)
                candidate["Go"] = changed
                with self.assertRaises(RuntimeError):
                    launcher.canonical_manifest(candidate, prepared=True)

    def test_generated_seed_keeps_original_native_floors_and_exact_gomobile_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            work, heart, mobile, rows = self.generated_fixture(Path(directory).resolve())
            before = copy.deepcopy(rows)
            seed, receipt = runtime.generated_dependency_seed(
                work, "\n".join(json.dumps(item) for item in rows), heart, mobile)
            self.assertEqual(rows, before)
            self.assertEqual(receipt["source_module_count"], 882)
            text = (seed / "go.mod").read_text()
            self.assertTrue(text.startswith("module gobind\n\ngo 1.26\n"))
            self.assertNotIn("go 1.26.5", text)
            self.assertEqual(receipt["bind_source_sha256"]["cmd/gomobile/main.go"],
                             "7e28b18d4d3791bf05fe11d6323777fe7ad344baa54f57894442afeccd7e6a5c")
            self.assertIn("git.sr.ht/~sbinet/gg v0.3.1", text)
            self.assertNotIn("git.sr.ht/~sbinet/gg v0.6.0", text)
            self.assertIn("gonum.org/v1/gonum v0.17.0", text)
            self.assertIn("replace (", text)
            genproto = next(item for item in rows if item["Path"] == launcher.GENPROTO)
            self.assertIn(launcher.GENPROTO + " " + genproto["Version"] + " => "
                          + launcher.GENPROTO + " " + launcher.VERSION, text)
            self.assertEqual((heart / "preserve-native").read_bytes(), b"unchanged native input")

    def test_invalid_native_graph_or_changed_generator_is_rejected_before_seed_creation(self):
        for change in ["duplicate", "foreign-native", "native-go", "foreign-local", "newline-path", "mobile", "genproto", "source", "source-main"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                work, heart, mobile, rows = self.generated_fixture(Path(directory).resolve())
                if change == "duplicate":
                    rows.append(copy.deepcopy(rows[-1]))
                elif change == "foreign-native":
                    rows[0]["Dir"] = str(heart.parent / "other")
                elif change == "native-go":
                    rows[0]["GoVersion"] = "1.27.0"
                elif change == "foreign-local":
                    rows[1]["Replace"] = dict(Path="../foreign", Dir="/foreign")
                elif change == "newline-path":
                    rows[1]["Path"] += "\nreplace injected"
                elif change == "mobile":
                    next(item for item in rows if item["Path"] == "golang.org/x/mobile")["Version"] = "v1.2.3"
                elif change == "genproto":
                    next(item for item in rows if item["Path"] == launcher.GENPROTO)["Replace"]["Sum"] = "h1:wrong"
                elif change == "source-main":
                    (Path(mobile["Dir"]) / "cmd/gomobile/main.go").write_bytes(b"changed pinned version generator")
                else:
                    (Path(mobile["Dir"]) / "cmd/gomobile/bind.go").write_bytes(b"changed pinned generator")
                with self.assertRaises(RuntimeError):
                    runtime.generated_dependency_seed(
                        work, "\n".join(json.dumps(item) for item in rows), heart, mobile)
                self.assertFalse((work / "generated-dependency-seed").exists())

    def test_selected_graph_and_authoritative_expanded_dependency_hashes_are_bound(self):
        _, _, graph, downloads = self.graph_fixture()
        receipt = runtime.validate_generated_seed_graph(graph, downloads)
        self.assertEqual(receipt["selected_module_count"], 2)
        self.assertEqual(receipt["downloaded_module_count"], 2)

    def test_changed_or_missing_selected_and_downloaded_hashes_are_rejected(self):
        for field in ["sum", "go_mod_sum", "effective_version", "effective_path"]:
            with self.subTest(field=field):
                _, _, graph, downloads = self.graph_fixture()
                graph["git.sr.ht/~sbinet/gg"][field] = "changed"
                with self.assertRaises(RuntimeError):
                    runtime.validate_generated_seed_graph(graph, downloads)
        for field in ["Sum", "GoModSum"]:
            with self.subTest(download_field=field):
                _, _, graph, downloads = self.graph_fixture()
                downloads["git.sr.ht/~sbinet/gg@v0.6.0"].pop(field)
                with self.assertRaises(RuntimeError):
                    launcher.validate_downloaded_graph(graph, downloads)

    def test_post_tidy_graph_allows_pruning_but_no_selection_drift(self):
        _, _, expected, _ = self.graph_fixture()
        only_genproto = {launcher.GENPROTO: expected[launcher.GENPROTO]}
        result = launcher.validate_seeded_graph(only_genproto, expected)
        self.assertEqual(result["pruned_seed_modules"], ["git.sr.ht/~sbinet/gg"])
        for field in ["version", "replaced", "effective_path", "effective_version", "sum", "go_mod_sum", "new-module"]:
            with self.subTest(field=field):
                actual = copy.deepcopy(only_genproto)
                if field == "new-module":
                    actual["unexpected.org/new"] = copy.deepcopy(actual[launcher.GENPROTO])
                elif field == "replaced":
                    actual[launcher.GENPROTO][field] = False
                else:
                    actual[launcher.GENPROTO][field] = "changed"
                with self.assertRaises(RuntimeError):
                    launcher.validate_seeded_graph(actual, expected)

    def test_selected_graph_cannot_hide_duplicate_or_foreign_local_modules(self):
        for change in ["duplicate", "foreign-native", "missing-main", "other-main", "sum", "mod-sum"]:
            with self.subTest(change=change):
                heart, rows, _, _ = self.graph_fixture()
                if change == "duplicate":
                    rows.append(copy.deepcopy(rows[-1]))
                elif change == "foreign-native":
                    rows[1]["Replace"]["Dir"] = str(heart.parent / "different-heart")
                elif change == "missing-main":
                    rows.pop(0)
                elif change == "other-main":
                    rows[0]["Path"] = "other-main"
                else:
                    rows[2].pop("Sum" if change == "sum" else "GoModSum")
                with self.assertRaises(RuntimeError):
                    launcher.selected_graph(rows, heart)

    def test_failed_conflicting_or_unverified_download_streams_are_rejected(self):
        _, _, _, downloads = self.graph_fixture()
        original = list(downloads.values())
        for change in ["error", "conflict", "missing-sum", "bad-mod-sum"]:
            with self.subTest(change=change):
                rows = copy.deepcopy(original)
                if change == "error":
                    rows[0]["Error"] = "not downloaded"
                elif change == "conflict":
                    rows.append(dict(rows[0], Sum=launcher.MODULE_SUM))
                elif change == "missing-sum":
                    rows[0].pop("Sum")
                else:
                    rows[0]["GoModSum"] = "h1:not-a-real-hash"
                with self.assertRaises(RuntimeError):
                    launcher.downloaded_modules("\n".join(json.dumps(item) for item in rows))

    def test_actual_pre_tidy_manifest_is_checked_before_the_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            manifest = self.manifest_fixture(root / "heart")
            contract = dict(before_tidy_manifest=launcher.canonical_manifest(manifest),
                            input_native_graph_sha256="a" * 64)
            (root / "go.mod").write_text("module gobind\n\ngo 1.26\n", encoding="utf8")
            env = dict(GOWORK="off", GOPROXY="off")
            for change in ["unchanged", "require", "replace", "go"]:
                with self.subTest(change=change):
                    actual = copy.deepcopy(manifest)
                    if change == "require":
                        actual["Require"][0]["Version"] = "v9.9.9"
                    elif change == "replace":
                        actual["Replace"][0]["New"]["Path"] = "/different/heart"
                    elif change == "go":
                        actual["Go"] = "1.25.6"
                    response = subprocess.CompletedProcess([], 0, stdout=json.dumps(actual), stderr="")
                    with mock.patch.object(launcher.subprocess, "run", return_value=response):
                        if change == "unchanged":
                            result = launcher.audit_initial_manifest(root / "go", env, root, contract)
                            self.assertEqual(result["status"], "EXACT_GENERATED_INPUT")
                        else:
                            with self.assertRaises(RuntimeError):
                                launcher.audit_initial_manifest(root / "go", env, root, contract)

    def test_seed_contract_is_owned_hashed_and_tied_to_native_identity(self):
        for change in ["unchanged", "outside", "hash", "native", "schema", "override-missing", "override-changed"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                work, heart = root / "work", root / "heart"
                work.mkdir()
                generated = work / "gomobile-tmp"
                generated.mkdir()
                _, _, graph, _ = self.graph_fixture()
                data = dict(schema="pinkha-generated-module-graph-v2", native_directory=str(heart),
                            selected_dependencies=graph,
                            before_tidy_manifest=self.manifest_fixture(heart),
                            prepared_tidy_manifest=launcher.reviewed_generated_manifest(self.manifest_fixture(heart)))
                if change == "native":
                    data["native_directory"] = str(root / "foreign")
                elif change == "schema":
                    data["schema"] = "unrelated"
                elif change == "override-missing":
                    data.pop("prepared_tidy_manifest")
                elif change == "override-changed":
                    data["prepared_tidy_manifest"]["Replace"][1]["New"]["Version"] = "v9.9.9"
                path = (root if change == "outside" else work) / "contract.json"
                path.write_text(json.dumps(data), encoding="utf8")
                expected = hashlib.sha256(path.read_bytes()).hexdigest()
                if change == "hash":
                    expected = "0" * 64
                if change == "unchanged":
                    self.assertEqual(launcher.load_seed_contract(path, expected, heart, generated), data)
                else:
                    with self.assertRaises(RuntimeError):
                        launcher.load_seed_contract(path, expected, heart, generated)


    def test_generated_hydration_copy_preserves_exact_original_bind_input(self):
        with tempfile.TemporaryDirectory() as directory:
            work, heart, mobile, rows = self.generated_fixture(Path(directory).resolve())
            seed, receipt = runtime.generated_dependency_seed(work, "\n".join(json.dumps(item) for item in rows), heart, mobile)
            original = (seed / "go.mod").read_bytes()
            hydrated = runtime.prepare_generated_hydration(work, seed, receipt["initial_go_mod_sha256"])
            self.assertNotEqual(seed, hydrated)
            self.assertEqual((hydrated / "go.mod").read_bytes(), original)
            # Emulate the observed Go metadata operation, not a native build.
            (hydrated / "go.mod").write_text("mutated disposable hydration declaration")
            self.assertEqual((seed / "go.mod").read_bytes(), original)
            self.assertEqual(runtime.digest(seed / "go.mod"), receipt["initial_go_mod_sha256"])
            self.assertEqual((heart / "preserve-native").read_bytes(), b"unchanged native input")

    def test_generated_hydration_requires_original_bytes_and_fresh_owned_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            work, heart, mobile, rows = self.generated_fixture(Path(directory).resolve())
            seed, receipt = runtime.generated_dependency_seed(work, "\n".join(json.dumps(item) for item in rows), heart, mobile)
            for location, expected in [(work.parent, receipt["initial_go_mod_sha256"]), (work, "0" * 64)]:
                with self.subTest(location=location, expected=expected), self.assertRaises(RuntimeError):
                    runtime.prepare_generated_hydration(location, seed, expected)
            runtime.prepare_generated_hydration(work, seed, receipt["initial_go_mod_sha256"])
            with self.assertRaises(FileExistsError):
                runtime.prepare_generated_hydration(work, seed, receipt["initial_go_mod_sha256"])

    def test_reviewed_scope_override_keeps_original_and_all_other_declarations(self):
        original = self.manifest_fixture(Path("/owned/heart"))
        original["Replace"].append(dict(Old={"Path": launcher.GENPROTO + "/googleapis/rpc", "Version": "v0.0.0-20260819154853-08b0e4226688"},
                                       New={"Path": launcher.GENPROTO + "/googleapis/rpc", "Version": launcher.VERSION}))
        original["Exclude"] = [dict(Path="example.org/excluded", Version="v1.0.0")]
        preserved = copy.deepcopy(original)
        expected = copy.deepcopy(original)
        expected["Go"] = "1.26.5"
        expected["Replace"][1]["Old"].pop("Version")
        prepared = launcher.reviewed_generated_manifest(original)
        self.assertEqual(prepared, launcher.canonical_manifest(expected, prepared=True))
        self.assertEqual(original, preserved)

    def test_missing_ambiguous_or_changed_original_override_is_rejected(self):
        changes = {
            "missing": lambda value: value["Replace"].pop(1),
            "duplicate": lambda value: value["Replace"].append(copy.deepcopy(value["Replace"][1])),
            "already-normalized": lambda value: value["Replace"][1]["Old"].pop("Version"),
            "wrong-version": lambda value: value["Replace"][1]["New"].update(Version="v9.9.9"),
            "wrong-path": lambda value: value["Replace"][1]["New"].update(Path="other.example/genproto"),
            "extra-old-field": lambda value: value["Replace"][1]["Old"].update(Unexpected=True),
        }
        for name, change in changes.items():
            with self.subTest(case=name):
                original = self.manifest_fixture(Path("/owned/heart"))
                change(original)
                with self.assertRaises(RuntimeError):
                    launcher.reviewed_generated_manifest(original)

    def override_command_fixture(self, root, original, changed_preimage=False, changed_after=None):
        before, after = b"original declaration bytes\n", b"prepared declaration bytes\n"
        (root / "go.mod").write_bytes(before)
        prepared = launcher.reviewed_generated_manifest(original)
        responses = [copy.deepcopy(original), copy.deepcopy(prepared)]
        if changed_preimage:
            responses[0]["Require"][0]["Version"] = "v9.9.9"
        if changed_after:
            changed_after(responses[1])

        def command(args, **kwargs):
            self.assertEqual(kwargs["env"]["GOWORK"], "off")
            self.assertEqual(kwargs["env"]["GOPROXY"], "off")
            self.assertEqual(kwargs["env"]["GOTOOLCHAIN"], "local")
            if args[-1] == "-json":
                return subprocess.CompletedProcess(args, 0, stdout=json.dumps(responses.pop(0)), stderr="")
            self.assertEqual(args[1:3], ["mod", "edit"])
            self.assertEqual(args[3:], [
                "-go=1.26.5",
                "-dropreplace=" + launcher.GENPROTO + "@" + original["Replace"][1]["Old"]["Version"],
                "-replace=" + launcher.GENPROTO + "=" + launcher.GENPROTO + "@" + launcher.VERSION])
            (root / "go.mod").write_bytes(after)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return before, after, command

    def test_generated_override_records_exact_before_after_bytes_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            original = self.manifest_fixture(root / "heart")
            before, after, command = self.override_command_fixture(root, original)
            with mock.patch.object(launcher.subprocess, "run", side_effect=command) as invoked:
                receipt = launcher.prepare_generated_module(root / "go", {"GOWORK": "off"}, root, original)
            self.assertEqual(invoked.call_count, 3)
            self.assertEqual(receipt["original_go_mod_sha256"], hashlib.sha256(before).hexdigest())
            self.assertEqual(receipt["prepared_go_mod_sha256"], hashlib.sha256(after).hexdigest())
            self.assertEqual(receipt["go_directive_preparation"], dict(
                original="1.26", prepared="1.26.5", basis="PINNED_NATIVE_GO_MOD_AND_TOOLCHAIN"))
            self.assertEqual(launcher.validate_generated_preparation_receipt(receipt, original),
                             launcher.reviewed_generated_manifest(original))

    def test_changed_preimage_or_native_workspace_cannot_be_edited(self):
        for case in ["preimage", "workspace", "missing-file"]:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                original = self.manifest_fixture(root / "heart")
                before, _, command = self.override_command_fixture(root, original, changed_preimage=True)
                env = {"GOWORK": "off" if case != "workspace" else "original-native-workspace"}
                if case == "missing-file":
                    (root / "go.mod").unlink()
                with mock.patch.object(launcher.subprocess, "run", side_effect=command) as invoked:
                    with self.assertRaises(RuntimeError):
                        launcher.prepare_generated_module(root / "go", env, root, original)
                self.assertEqual(invoked.call_count, 1 if case == "preimage" else 0)
                if case != "missing-file":
                    self.assertEqual((root / "go.mod").read_bytes(), before)

    def test_override_cannot_hide_changes_to_requires_go_or_other_replacements(self):
        changes = {
            "require": lambda value: value["Require"][0].update(Version="v9.9.9"),
            "go": lambda value: value.update(Go="1.27.0"),
            "native": lambda value: value["Replace"][0]["New"].update(Path="/foreign/heart"),
        }
        for name, change in changes.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                original = self.manifest_fixture(root / "heart")
                _, _, command = self.override_command_fixture(root, original, changed_after=change)
                with mock.patch.object(launcher.subprocess, "run", side_effect=command):
                    with self.assertRaises(RuntimeError):
                        launcher.prepare_generated_module(root / "go", {"GOWORK": "off"}, root, original)

    def test_override_receipt_cannot_drop_or_change_either_declaration_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            original = self.manifest_fixture(root / "heart")
            _, _, command = self.override_command_fixture(root, original)
            with mock.patch.object(launcher.subprocess, "run", side_effect=command):
                receipt = launcher.prepare_generated_module(root / "go", {"GOWORK": "off"}, root, original)
            changes = {
                "status": lambda value: value.update(status="unverified"),
                "original-manifest": lambda value: value["original_manifest"]["Require"][0].update(Version="v9.9.9"),
                "prepared-manifest": lambda value: value["prepared_manifest"]["Replace"][1]["New"].update(Version="v9.9.9"),
                "original-text": lambda value: value.update(original_go_mod_text="changed"),
                "prepared-text": lambda value: value.update(prepared_go_mod_text="changed"),
                "original-sha": lambda value: value.pop("original_go_mod_sha256"),
                "prepared-sha": lambda value: value.pop("prepared_go_mod_sha256"),
                "go-preparation-missing": lambda value: value.pop("go_directive_preparation"),
                "go-preparation-changed": lambda value: value["go_directive_preparation"].update(prepared="1.26.0"),
            }
            for name, change in changes.items():
                with self.subTest(case=name):
                    changed = copy.deepcopy(receipt)
                    change(changed)
                    with self.assertRaises(RuntimeError):
                        launcher.validate_generated_preparation_receipt(changed, original)

    def hydration_manifests(self):
        original = dict(Module={"Path": "gobind"}, Go="1.26.5", Exclude=None, Retract=None,
                        Replace=[dict(Old={"Path": "original.example/dependency", "Version": "v1.0.0"},
                                      New={"Path": "reviewed.example/fork", "Version": "v1.0.1"})],
                        Require=[dict(Path="example.test/a", Version="v1.0.0"),
                                 dict(Path="example.test/b", Version="v1.0.0")])
        hydrated = copy.deepcopy(original)
        hydrated["Require"][1]["Version"] = "v1.1.0"
        hydrated["Require"].append(dict(Path="example.test/c", Version="v1.2.0", Indirect=True))
        # These versions model already independently checksum-verified selection.
        graph = {path: dict(version=version) for path, version in
                 [("example.test/a", "v1.0.0"), ("example.test/b", "v1.1.0"), ("example.test/c", "v1.2.0")]}
        return original, hydrated, graph

    def test_generated_hydration_records_only_selected_mvs_and_indirect_additions(self):
        original, hydrated, graph = self.hydration_manifests()
        before, after = copy.deepcopy(original), copy.deepcopy(hydrated)
        receipt = runtime.validate_generated_hydration_manifest(original, hydrated, graph)
        self.assertEqual(original, before)
        self.assertEqual(hydrated, after)
        self.assertEqual(receipt["selected_version_updates"], [dict(path="example.test/b", original="v1.0.0", hydrated="v1.1.0")])
        self.assertEqual(receipt["selected_indirect_additions"], [dict(path="example.test/c", hydrated="v1.2.0")])
        self.assertEqual((receipt["original_requirements"], receipt["hydrated_requirements"]), (2, 3))
        self.assertTrue(receipt["original_non_require_declarations_preserved"])

    def test_generated_hydration_rejects_other_declaration_or_selection_changes(self):
        changes = {
            "module": lambda value: value.update(Module={"Path": "other"}),
            "toolchain": lambda value: value.update(Toolchain="go1.27.0"),
            "go": lambda value: value.update(Go="1.27.0"),
            "original-go-in-prepared-scope": lambda value: value.update(Go="1.26"),
            "replace": lambda value: value["Replace"][0]["New"].update(Version="v2.0.0"),
            "exclude": lambda value: value.update(Exclude=[dict(Path="example.test/a", Version="v1.0.0")]),
            "removed-original": lambda value: value["Require"].pop(0),
            "version-drift": lambda value: value["Require"][1].update(Version="v1.0.9"),
            "directness": lambda value: value["Require"][0].update(Indirect=True),
            "new-direct": lambda value: value["Require"][2].update(Indirect=False),
            "unselected-module": lambda value: value["Require"].append(dict(Path="unknown.test/module", Version="v1.0.0", Indirect=True)),
            "duplicate": lambda value: value["Require"].append(copy.deepcopy(value["Require"][0])),
            "unknown-require-field": lambda value: value["Require"][0].update(Changed=True),
            "invalid-indirect": lambda value: value["Require"][2].update(Indirect=1),
        }
        for name, change in changes.items():
            with self.subTest(case=name):
                original, hydrated, graph = self.hydration_manifests()
                change(hydrated)
                with self.assertRaises(RuntimeError):
                    runtime.validate_generated_hydration_manifest(original, hydrated, graph)


if __name__ == "__main__":
    unittest.main(verbosity=2)
