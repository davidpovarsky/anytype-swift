"""Controller rejection controls only; these fixtures are not Apple acceptance."""
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import coherent_heart_release as coherent
import run_t5_apple_pair as pair
import run_t5_native_ui as native_ui
import run_ui27 as ui
import run_wave15_acceptance as lane
import run_owned_single_lane as supervisor
import t5_native_account_retry_evidence as retry
import t5_native_account_retry_pending_evidence as pending
import t5_host_actions as host_actions
import t5_remaining_freshness as freshness
import test_t5_native_account_retry_pending as pending_controls
import test_t5_native_ui as ui_controls
import wave15_batch as batch

SOURCE = "a" * 40
RUN = "9991"
UDID = "12345678-1234-1234-1234-123456789ABC"
OTHER = "22345678-1234-1234-1234-123456789ABC"
TOKEN = "d" * 32


def binding():
    profile = ui.heart_profiles.select(coherent.RUNTIME_PROFILE)
    return dict(runtime_profile=profile.name, native_marker=profile.version,
        heart_patch_sha256=profile.patch_sha256, heart_inventory_sha256=profile.inventory_sha256,
        heart_source_run_id=RUN, heart_source_attempt="1", heart_source_sha=SOURCE,
        heart_build_receipt_sha256="1" * 64, heart_artifact_id=1, heart_artifact_sha256="2" * 64,
        heart_proof_artifact_id=2, heart_proof_artifact_sha256="3" * 64)


def current_build(root):
    app = root / "app"
    proof, derived = app / "build/proof", app / "build/derived"
    context = SimpleNamespace(profile=coherent.PROFILE, app=app, derived=derived,
        ui_derived=app / "build/derived-ui", built=derived / "Build/Products/Release-Anytype-iphonesimulator/Anytype.app",
        native_configuration=derived / "Build/Products/native.xctestrun",
        ui_configuration=app / "build/derived-ui/Build/Products/ui.xctestrun",
        runtime_receipt_path=proof / "heart/heart-installation.json",
        source=dict(source_sha=SOURCE, hanlin_snapshot_sha256="b" * 64, package_locks={}),
        verify_current=Mock())
    build_path = proof / "batch-build/same-job-build.json"
    batch.write(build_path, {"controller_fixture_only": True})
    context.built.mkdir(parents=True)
    for path in (context.native_configuration, context.ui_configuration):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"controller-only original configuration")
    value = dict(role="coherent-r15", app_source_sha=SOURCE, flags=list(pair.FLAGS),
        runtime_binding=binding(), runtime_version=ui.heart_profiles.select(coherent.RUNTIME_PROFILE).version,
        hanlin_snapshot_sha256=context.source["hanlin_snapshot_sha256"], kit_sha=ui.KIT,
        code_sha256="c" * 64, app=str(context.built), configuration=str(context.native_configuration),
        ui_configuration=str(context.ui_configuration), app_builds=1, ui_runner_builds=1,
        same_job_build_receipt_sha256=batch.digest(build_path))
    return context, value


class CoherentControls(unittest.TestCase):
    def test_fixed_scope_retains_release_lanes_and_explicit_t5_flags(self):
        spec = batch.profile_spec(coherent.PROFILE)
        self.assertEqual(spec.lanes, ("editor", "quote-drop", "properties-set"))
        plans = batch.plan(lane, coherent.PROFILE)
        self.assertEqual((spec.ui_count, spec.preparation_count, spec.postflight_count), (6, 3, 1))
        self.assertEqual([row["lane"] for row in plans], list(spec.lanes))
        self.assertEqual(batch.profile_flags(coherent.PROFILE), pair.FLAGS)
        self.assertNotEqual(batch.profile_flags(coherent.PROFILE), batch.FLAGS)
        self.assertEqual(batch.profile_flags(batch.RETAINED_HEART_PROFILE), batch.FLAGS)
        self.assertEqual(batch.profile_spec(batch.PROFILE).ui_count, 15)

    def test_combined_builder_compiles_one_app_and_one_runner_with_exact_union(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = SimpleNamespace(app=root, evidence=root / "build/proof", derived=root / "build/derived",
                runtime_profile=coherent.RUNTIME_PROFILE, heart_source_run_id=RUN)
            preflight = dict(status="PREFLIGHT_PASS_UI_NOT_RUN", source_sha=SOURCE, run_id=RUN,
                             selected={"ipad": {"udid": UDID}})
            batch.write(args.evidence / "preflight/preflight.json", preflight)
            batch.write(args.evidence / "heart/heart-installation.json", {"controller_fixture_only": True})
            batch.write(root / "Tools/PinkhaSimulatorGate/required-coverage.json", {})
            native = args.derived / "Build/Products/native.xctestrun"
            runner_derived = args.derived.with_name(args.derived.name + "-ui")
            configuration = runner_derived / "Build/Products/ui.xctestrun"
            for path in (native, configuration):
                path.parent.mkdir(parents=True); path.write_text("controller-only xctestrun")
            (native.parent / "AnytypeTests.xctest").mkdir()
            source = {"source_sha": SOURCE, "package_locks": {}, "hanlin_snapshot_sha256": "b" * 64}
            shared = SimpleNamespace(git=lambda app, *args: SOURCE if args == ("rev-parse", "HEAD") else "branch",
                runtime_binding=lambda *args: binding(), candidate_identity=lambda *args: {"hashes": {}},
                command=Mock(), prepare_source_cache=Mock(), verify_signed_simulator=Mock(),
                verify_runtime_copies=Mock(), ui_only_project=lambda app: root / "UI.xcodeproj",
                test_configuration=lambda products, blueprint: native if blueprint == "AnytypeTests" else configuration)
            harness = SimpleNamespace(shared=shared, require_source_identity=Mock(), source_methods=Mock())
            receipt = {"profile": coherent.PROFILE}
            with patch.dict(os.environ, GITHUB_RUN_ID=RUN, GITHUB_SHA=SOURCE), \
                 patch.object(batch, "source_snapshot", return_value=source), \
                 patch.object(batch.FrozenBuild, "observed_artifacts", return_value={"controller_fixture_only": True}), \
                 patch.object(host_actions, "source_contract", return_value={"controller_fixture_only": True}), \
                 patch.object(freshness, "source_contract", return_value={"controller_fixture_only": True}), \
                 patch.object(pending, "validate_retained_source", return_value={"status": "REUSED_VERIFIED_PASS"}):
                context, _ = batch.build_once(args, harness, batch.plan(lane, coherent.PROFILE), receipt)
            commands = [call.args[0] for call in shared.command.call_args_list if "build-for-testing" in call.args[0]]
            self.assertEqual(len(commands), 2)
            native_selection = [item for item in commands[0] if item.startswith("-only-testing:")]
            expected_native = {item["preparation"].split("/")[0] for item in batch.plan(lane, coherent.PROFILE)}
            expected_native |= {native_ui.evidence.PREPARATION.split("/")[0], host_actions.SUITE,
                                pending.METHOD.split("/")[0], batch.preservation.SUITE, freshness.SUITE}
            self.assertEqual(set(native_selection), {"-only-testing:AnytypeTests/" + name for name in expected_native})
            selected_ui = {item for item in commands[1] if item.startswith("-only-testing:")}
            expected_ui = {method for item in batch.plan(lane, coherent.PROFILE) for method in item["methods"]}
            expected_ui |= {*native_ui.evidence.METHODS.values(), native_ui.r08.METHOD}
            self.assertEqual(selected_ui, {"-only-testing:PinkhaStage1AcceptanceUITests/" + name for name in expected_ui})
            self.assertEqual(len(selected_ui), 9)
            for command in commands:
                self.assertEqual(command[-len(pair.FLAGS):], pair.FLAGS)
            self.assertEqual(context.profile, coherent.PROFILE)
            self.assertEqual(context.lane_build_flags("quote-drop", batch.FLAGS, batch.CONFIGURATION), pair.FLAGS)
            with self.assertRaises(RuntimeError):
                context.lane_build_flags("hanlin-native", batch.FLAGS, batch.CONFIGURATION)

    def test_one_frozen_build_cannot_accept_changed_runtime_flags_source_or_ui_runner(self):
        with tempfile.TemporaryDirectory() as temporary:
            context, build = current_build(Path(temporary))
            with patch.object(ui, "code_carriers", return_value={"sha256": build["code_sha256"]}):
                self.assertEqual(coherent.validate_build(build, SOURCE, pair, ui, context).name, coherent.RUNTIME_PROFILE)
                mutations = [lambda b: b.update(role="corrected-r15"), lambda b: b.update(flags=batch.FLAGS),
                    lambda b: b.update(app_source_sha="f" * 40), lambda b: b.update(runtime_version="prefix-only"),
                    lambda b: b["runtime_binding"].pop("heart_build_receipt_sha256"),
                    lambda b: b.update(app_builds=True), lambda b: b.update(ui_runner_builds=2),
                    lambda b: b.update(configuration="another.xctestrun"),
                    lambda b: b.update(ui_configuration="another-ui.xctestrun"),
                    lambda b: b.update(app="another.app"), lambda b: b.update(code_sha256="e" * 64),
                    lambda b: b.update(same_job_build_receipt_sha256="e" * 64)]
                for index, change in enumerate(mutations):
                    bad = copy.deepcopy(build); change(bad)
                    with self.subTest(index=index), self.assertRaises(RuntimeError):
                        coherent.validate_build(bad, SOURCE, pair, ui, context)
                context.verify_current.side_effect = RuntimeError("Changed frozen native/UI bundle")
                with self.assertRaisesRegex(RuntimeError, "Changed frozen"):
                    coherent.validate_build(build, SOURCE, pair, ui, context)

    def test_explicit_coherent_runtime_does_not_relax_historical_r15_admission(self):
        with tempfile.TemporaryDirectory() as temporary:
            context, build = current_build(Path(temporary))
            with self.assertRaises(ValueError):
                native_ui.validate_corrected_build(build, SOURCE, pair, ui)
            args = SimpleNamespace(runtime_profile=coherent.RUNTIME_PROFILE, heart_source_run_id=RUN)
            coherent.require_runtime(args, binding(), ui)
            for name, run_id in (("r14", RUN), (pending.RUNTIME_PROFILE, RUN), (coherent.RUNTIME_PROFILE, "9992")):
                with self.subTest(name=name, run=run_id), self.assertRaises(RuntimeError):
                    coherent.require_runtime(SimpleNamespace(runtime_profile=name, heart_source_run_id=run_id), binding(), ui)

    def test_pending_nine_requires_explicit_runtime_and_never_calls_retained_baseline(self):
        receipt, fixture, _, arguments = pending_controls.pending_inputs()
        runtime = ui.heart_profiles.select(coherent.RUNTIME_PROFILE).version
        receipt["runtimeVersion"] = fixture["state"]["runtimeVersion"] = runtime
        raw = json.dumps(fixture, sort_keys=True).encode()
        receipt.update(baselineReceiptSHA256Before=retry.digest(raw), baselineReceiptSHA256After=retry.digest(raw))
        with patch.object(retry.pagination, "validate_receipt", side_effect=AssertionError("retained36 replayed")):
            actual = retry.validate_receipt(receipt, fixture, raw, **arguments,
                                            pending_only=True, runtime_profile=coherent.RUNTIME_PROFILE)
        self.assertEqual((actual["baseline_body_invocations"], actual["baseline_search_calls"],
                          actual["total_search_calls_in_wrapper"]), (0, 0, 9))
        with self.assertRaises(RuntimeError):
            retry.validate_receipt(receipt, fixture, raw, **arguments, pending_only=True)
        with self.assertRaises(RuntimeError):
            retry.validate_receipt(receipt, fixture, raw, **arguments, runtime_profile=coherent.RUNTIME_PROFILE)
        for value in ("r14", "unreviewed", "", None):
            with self.subTest(profile=value), self.assertRaises(RuntimeError):
                pending.expected_runtime_version(value)

    def test_counts_reject_replayed_baseline_missing_scopes_and_boolean_counts(self):
        coherent.validate_counts(dict(coherent.COUNTS))
        for key, value in (("baseline_pagination_body_invocations", 1), ("pending_retry_service_queries", 36),
                           ("app_builds", 2), ("ui_runner_builds", True), ("hebrew_readonly_ui_executions", 1)):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                coherent.validate_counts(dict(coherent.COUNTS, **{key: value}))
        with self.assertRaises(RuntimeError):
            coherent.validate_counts({key: value for key, value in coherent.COUNTS.items() if key != "host_action_cases"})

    def test_extra_simulator_ownership_is_planned_before_create_and_rejects_baseline(self):
        template = dict(device={"identifier": "ipad"}, runtime={"identifier": "ios27"})
        devices = coherent.extra_devices(template, TOKEN, RUN)
        self.assertEqual([x["lane"] for x in devices], list(coherent.EXTRA_DEVICES))
        self.assertEqual(len({x["name"] for x in devices}), 3)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent = dict(profile=coherent.PROFILE, extra_devices=devices, baseline_udids=[UDID])
            owned = coherent.owned_device(intent, root, "t5-native-ui")
            with patch.object(batch, "scoped_device_inventory", return_value={"devices": {"ios27": []}}):
                self.assertEqual(owned.prepare(), devices[2]["name"])
            self.assertTrue((owned.directory / "planned-simulator.json").is_file())
            with self.assertRaises(RuntimeError):
                owned.record_created(UDID)
            observed = dict(udid=OTHER, name=owned.ownership["name"], deviceTypeIdentifier="ipad",
                            state="Shutdown", isAvailable=True)
            with patch.object(batch, "scoped_device_inventory", return_value={"devices": {"ios27": [observed]}}):
                owned.record_created(OTHER)
            self.assertEqual(json.loads((owned.directory / "owned-simulator.json").read_bytes()), dict(devices[2], udid=OTHER))

    def test_t5_ui_reuses_original_runner_without_another_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context, build = current_build(root)
            work, proof = context.app / "build/private", context.app / "build/proof/coherent-t5"
            work.mkdir(parents=True)
            container = root / "disposable-container"
            native_root = container / native_ui.NATIVE_ROOT; native_root.mkdir(parents=True)
            fixture = ui_controls.fixture()
            fixture.update(appSourceSHA=SOURCE, runID=RUN, token=ui_controls.TOKEN,
                runtimeVersion=build["runtime_version"], accountRootPathSHA256=hashlib.sha256(str(native_root.resolve()).encode()).hexdigest())
            batch.write(container / native_ui.UI_FIXTURE, fixture)
            batch.write(container / native_ui.UI_SECRETS, dict(token=ui_controls.TOKEN,
                mnemonic="controller-only-disposable-phrase", accountKey="controller-only-disposable-key"))
            batch.write(container / native_ui.native_mutations.RELATIVE, {"controller_fixture_only": True})
            mutation_hash = batch.digest(container / native_ui.native_mutations.RELATIVE)
            original_project = context.app / "PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj/project.pbxproj"
            original_project.parent.mkdir(parents=True); original_project.write_text("PinkhaT5NativeAcceptanceUITests.swift")
            runner = context.ui_derived / "Build/Products/Release-Anytype-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app"
            runner.mkdir(parents=True)
            (runner / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "com.gloiiire.PinkhaStage1AcceptanceUITests.xctrunner"}))
            owned = SimpleNamespace(key="t5-native-ui", prepare=Mock(return_value="owned-coherent-ui"), record_created=Mock())
            selection = dict(udid=OTHER, device={"identifier": "ipad"}, runtime={"identifier": "ios27"})
            created, installed, state = False, False, "Shutdown"
            calls = []

            def command(argv, app, directory, name, timeout, check=True, output=None):
                nonlocal created, installed, state
                calls.append(list(argv))
                self.assertNotIn("build-for-testing", argv)
                directory.mkdir(parents=True, exist_ok=True)
                path = output or directory / (name + ".log")
                path.write_text("")
                if name == "create-ui-simulator":
                    created = True; path.write_text(UDID)
                elif name == "boot-ui": state = "Booted"
                elif name == "install-retained-r15": installed = True
                elif name == "shutdown-owned-ui": state = "Shutdown"
                if output:
                    device = dict(udid=UDID, name="owned-coherent-ui", state=state,
                                  isAvailable=True, deviceTypeIdentifier="ipad")
                    batch.write(output, {"devices": {"ios27": [device] if created else []}})
                return {"return_code": 0, "timed_out": False}, path

            api = SimpleNamespace(FLAGS=pair.FLAGS, write=batch.write, run_logged=command,
                git=lambda path, *args: SOURCE if args[0] == "rev-parse" else "", sha_bytes=pair.sha_bytes,
                app_container=lambda udid, kind, required=True: container if installed or required else None,
                contains_secret=pair.contains_secret)
            ui_api = SimpleNamespace(heart_profiles=ui.heart_profiles, KIT=ui.KIT,
                code_carriers=lambda path: {"sha256": build["code_sha256"]},
                test_configuration=lambda products, blueprint: context.ui_configuration,
                ui_only_project=Mock(side_effect=AssertionError("second UI runner build")))
            with patch.object(native_ui, "uuid4", return_value=SimpleNamespace(hex=ui_controls.TOKEN)), \
                 patch.object(native_ui.shutil, "disk_usage", return_value=SimpleNamespace(free=4 * 1024**3)), \
                 patch.object(native_ui, "select_tests", return_value={"controller_selection_only": True}), \
                 patch.object(native_ui.native_mutations, "capture", return_value={"receipt_sha256": mutation_hash}), \
                 patch.object(native_ui.evidence, "read_ui_receipts", return_value=({"controller_observation_only": True}, [])), \
                 patch.object(native_ui, "run_r08", return_value={"status": native_ui.r08.PASS}):
                result = native_ui.run_after_coherent_build(app=context.app, work=work, proof=proof, build=build,
                    selection=selection, pair=api, ui=ui_api, method_results=None, source=SOURCE, run_id=RUN,
                    build_context=context, owned_device=owned)
            self.assertEqual(result["status"], native_ui.PASS, result)
            self.assertEqual((result["app_builds_added"], result["ui_runner_builds"]), (0, 0))
            self.assertIs(result["ui_runner_reused_from_same_job"], True)
            self.assertTrue(result["ui_simulator_shutdown"])
            self.assertGreaterEqual(context.verify_current.call_count, 3)
            ui_api.ui_only_project.assert_not_called()
            owned.record_created.assert_called_once_with(UDID)

    def test_nested_cleanup_rejects_missing_or_changed_original_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary)
            args = SimpleNamespace(app=app, derived=app / "build/derived", evidence=app / "build/proof")
            work = coherent.private_work(args)
            original = work / "native-ui/commands/test.owned.command.json"
            batch.write(original, dict(worker_pid=12345, owned_group_cleanup="TERM_THEN_KILL"))
            metadata = original.with_name("test.command.json")
            batch.write(metadata, dict(original_owned_command=original.name,
                original_owned_command_sha256=batch.digest(original), owned_group_quiescence={"status": "PASS"}))
            with patch.object(supervisor, "verify_owned_group_stopped", return_value={"status": "PASS", "pgid": 12345, "live_members": 0}):
                self.assertEqual(coherent.nested_cleanup(args)["groups_checked"], 1)
                original.write_text("{}")
                with self.assertRaises(RuntimeError):
                    coherent.nested_cleanup(args)

    def test_cache_publication_requires_finished_hash_bound_outer_and_nested_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            nested_path = evidence / "coherent-nested-cleanup.json"
            worker_path, command_path = evidence / "batch-worker.json", evidence / "batch-worker.command.json"
            batch.write(nested_path, {"status": "PASS", "groups_checked": 0})
            batch.write(worker_path, dict(profile=coherent.PROFILE, finished_at="controller-finished",
                coherent_nested_cleanup=dict(status="PASS", path=nested_path.name, sha256=batch.digest(nested_path))))
            batch.write(command_path, dict(termination_profile=coherent.PROFILE, worker_pid=12345,
                owned_group_cleanup="TERM_THEN_KILL", owned_group_quiescence={"status": "PASS"}))
            result = dict(profile=coherent.PROFILE, finished_at="controller-finished", cleanup={"status": "PASS"},
                retained_worker_receipt={"sha256": batch.digest(worker_path)},
                retained_worker_command={"sha256": batch.digest(command_path)}, status="BATCH_FAILED_OBSERVED_TESTS")
            batch.write(evidence / "execution.json", result)
            with patch.object(supervisor, "verify_owned_group_stopped", return_value={"status": "PASS"}):
                self.assertEqual(coherent.check_cache_ready(evidence), 0)
                for field, value in (("finished_at", None), ("cleanup", {"status": "FAIL"}),
                                     ("retained_worker_receipt", {"sha256": "changed"})):
                    batch.write(evidence / "execution.json", dict(result, **{field: value}))
                    with self.subTest(field=field), self.assertRaises(RuntimeError):
                        coherent.check_cache_ready(evidence)
                batch.write(evidence / "execution.json", result)
                nested_path.write_text("{}")
                with self.assertRaises(RuntimeError):
                    coherent.check_cache_ready(evidence)


if __name__ == "__main__":
    unittest.main()
