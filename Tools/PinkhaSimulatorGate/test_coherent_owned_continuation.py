"""Four new caller/ownership controls; no simulator, native or old suite execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

import coherent_cleanup_snapshot as snapshots
import coherent_fresh_construction as construction
import coherent_original_preflight as lifecycle
import coherent_original_products as products
import run_owned_single_lane as groups
import wave15_batch as batch

CONTROL = "c" * 40
RUN = "45199900001"
UDID = "11111111-1111-4111-8111-111111111111"
BASELINE = "22222222-2222-4222-8222-222222222222"
ENV = {"GITHUB_SHA": CONTROL, "GITHUB_RUN_ID": RUN, "GITHUB_RUN_ATTEMPT": "1"}
METHOD = "OwnedPreparationFixture/testPrepare"


def save(path, value):
    lifecycle.save(path, value)


def raw(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root, *, control=None, control_sha=CONTROL):
    owned = root.resolve()
    control = (owned / "control") if control is None else Path(control).resolve()
    owned = control / "build" if control_sha == CONTROL else owned
    app = owned / "private/App"
    evidence = owned / "evidence"
    app.mkdir(parents=True)
    evidence.mkdir(parents=True)
    derived = app / "build/derived"
    derived.mkdir(parents=True)
    native = derived / "native.xctestrun"
    native.write_bytes(b"owned control descriptor\n")
    runtime = {"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0"}
    device_type = {"identifier": "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-16GB"}
    token = "a" * 32
    plans = [dict(lane=lane, name="Pinkha-UI27-" + RUN + "-batch-" + token + "-" + lane,
                  runtime=runtime, device=device_type)
             for lane in batch.profile_spec(batch.COHERENT_HEART_PROFILE).lanes]
    planned = plans[0]
    inventory = {"devices": {runtime["identifier"]: [
        dict(udid=BASELINE, name="unrelated-original", state="Shutdown",
             isAvailable=True, deviceTypeIdentifier=device_type["identifier"])]}}
    save(evidence / "batch-simulator-baseline.json", inventory)
    intent = dict(protocol=products.PROTOCOL, continuation=products.NAME,
        source_sha=products.SOURCE, control_source_sha=control_sha, profile=batch.COHERENT_HEART_PROFILE,
        build_origin=products.origin_fields(), original_app_checkout=str(app),
        original_products_directory=str(derived), run_id=RUN, run_attempt="1",
        token=token, lane_devices=plans, baseline_udids=[BASELINE],
        baseline_inventory_sha256=digest(evidence / "batch-simulator-baseline.json"))
    save(evidence / "batch-intent.json", intent)
    directory = evidence / "lanes/editor"
    directory.mkdir(parents=True)
    origin = SimpleNamespace(control=control, app=app, evidence=evidence, control_sha=control_sha,
        args=SimpleNamespace(control=control, app=app, evidence=evidence, derived=derived, deadline=time.monotonic() + 1200),
        _constructions={}, context=None)
    container = root.resolve() / "owned-simulators" / UDID / "data"
    container.mkdir(parents=True)
    return SimpleNamespace(control=control, app=app, evidence=evidence, directory=directory,
        origin=origin, intent=intent, planned=planned, native=native, container=container)


def admission_fixture(f, origin):
    """Synthetic metadata for source/ownership controls, never Products admission."""
    origin.admission_path = f.evidence / "original-products/admission.json"
    admission = dict(protocol=products.PROTOCOL, continuation=products.NAME,
        build_origin=products.origin_fields(),
        execution_origin=dict(control_source_sha=origin.control_sha, run_id=RUN, run_attempt="1"),
        app_source_sha=products.SOURCE, source_tree_sha=products.SOURCE_TREE,
        app_builds_this_run=0, ui_runner_builds_this_run=0, original_app_builds=1,
        original_ui_runner_builds=1, original_product_tests_executed=0,
        current_shared_app_accepted=False, previous_test_acceptance_reused=False,
        every_archived_entry_build_origin_verified=False)
    save(origin.admission_path, admission)
    origin.admission_sha = digest(origin.admission_path)
    return admission


def retain_control_outputs(f, label):
    destination = os.environ.get("COHERENT_OWNED_CONTROL_EVIDENCE")
    if not destination:
        return
    root = Path(destination).resolve() / label
    root.mkdir(parents=True, exist_ok=False)
    paths = [f.evidence / name for name in
             ("batch-intent.json", "batch-simulator-baseline.json", "coherent-nested-cleanup.json",
              "coherent-cleanup-source-check.json")]
    paths += [p for p in f.directory.rglob("*") if p.is_file()]
    if (f.evidence / "control-source-snapshots").exists():
        paths += list((f.evidence / "control-source-snapshots").rglob("*.json"))
    ledger = {}
    for path in sorted(set(paths)):
        if not path.is_file():
            continue
        assert not path.is_symlink()
        relative = path.relative_to(f.evidence)
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        ledger[relative.as_posix()] = dict(sha256=digest(target), bytes=target.stat().st_size)
    save(root / "control-only.json", dict(scope="INJECTED_COMMAND_RESULTS_AND_OWNED_SOURCE_CONTROL_ONLY",
        simulator_commands_executed=0, product_methods_executed=0, originals=ledger))


class Commands:
    """Inject process results into the unchanged wrapper; never execute an OS command."""
    def __init__(self, f, *, primary=None, quiescence=None):
        self.f, self.primary, self.quiescence = f, primary, quiescence
        self.calls = []
        self.original_class = lifecycle.Commands

    def execute(self, argv, cwd, log, timeout):
        self.calls.append((list(argv), timeout))
        if argv[:3] == ["xcrun", "simctl", "create"]:
            value = (UDID + "\n").encode()
        elif argv == ["xcrun", "simctl", "get_app_container", UDID, batch.BUNDLE, "data"]:
            value = (str(self.f.container) + "\n").encode()
        else:
            raise AssertionError("Unexpected fixture command")
        log.write_bytes(value)
        record = dict(status="FAIL" if self.primary else "COMPLETE", argv=argv, cwd=str(cwd),
            timeout_seconds=timeout, worker_pid=42120, return_code=1 if self.primary else 0,
            owned_group_cleanup="TERM_THEN_KILL")
        lifecycle.save(log.with_suffix(".command.json"), record, original=True)
        if self.primary:
            raise self.primary
        return record

    def stopped(self, path, *, cleanup_profile):
        if cleanup_profile != batch.COHERENT_HEART_PROFILE:
            raise AssertionError("The new adapter lost its qualified coherent profile")
        if self.quiescence:
            if not (self.f.directory / "owned-simulator.json").is_file():
                raise AssertionError("Returned UUID was not durable before the later failure")
            raise self.quiescence
        return dict(status="PASS", scope="INJECTED_CONTROL_ONLY")

    def factory(self, control, directory, receipt, checkpoint):
        return self.original_class(control, directory, receipt, checkpoint,
            execute=self.execute, stopped=self.stopped)

    def patch(self):
        return mock.patch.object(lifecycle, "Commands", side_effect=self.factory)


def ready(f, device):
    before = dict(udid=UDID, name=device["name"], state="Shutdown", isAvailable=True,
                  deviceTypeIdentifier=device["device"]["identifier"])
    directory = f.directory / "owned-readiness"
    directory.mkdir()
    save(directory / "before.json", {"devices": {device["runtime"]["identifier"]: [before]}})
    (directory / "boot-status.log").write_bytes(b"control boot complete\n")
    observed = dict(before, runtime_identifier=device["runtime"]["identifier"])
    record = dict(status="OWNED_SIMULATOR_READY", destination=UDID, tests_executed=0, boot_required=True,
        before=observed, bootstatus_return_code=0, postboot_inventory_performed=False,
        readiness_basis="VERIFIED_PREBOOT_IDENTITY_AND_SUCCESSFUL_OWNED_BOOTSTATUS",
        preboot_identity_sha256=digest(directory / "before.json"),
        bootstatus_log_sha256=digest(directory / "boot-status.log"))
    save(directory / "readiness.json", record)
    for name, argv, timeout in [
        ("boot", ["xcrun", "simctl", "boot", UDID], 120),
        ("boot-status", ["xcrun", "simctl", "bootstatus", UDID, "-b"], 180)]:
        save(directory / (name + ".command.json"), dict(argv=argv, timeout_seconds=timeout,
            return_code=0, status="SUCCESS", owned_group_quiescence={"status": "PASS"}))
    save(f.directory / "selection-plan.json", dict(preparation=METHOD, methods=["OwnedUIFixture/testOwned"]))
    context = products.OriginalProductsContext(
        app=f.app, derived=f.origin.args.derived, ui_derived=f.origin.args.derived.with_name("derived-ui"),
        built=f.app / "Anytype.app", native_configuration=f.native, ui_configuration=f.native,
        shared=None, source={"source_sha": products.SOURCE}, candidate_hashes={}, artifacts={},
        native_bundles=(), runtime_receipt_path=f.app / "runtime.json", runtime_receipt_sha256="0"*64,
        fixtures={}, device=device, profile=batch.COHERENT_HEART_PROFILE, origin=f.origin)
    f.origin.context = context
    return context


class CoherentOwnedContinuationTests(unittest.TestCase):
    def test_construction_and_first_selection_bind_original_ownership_and_retained_outputs(self):
        with mock.patch.dict(os.environ, ENV), tempfile.TemporaryDirectory(prefix="coherent-construction-") as name:
            f = fixture(Path(name))
            commands = Commands(f)
            with commands.patch():
                device = construction.create(f.origin, f.intent, f.planned, f.directory)
                context = ready(f, device)
                fresh = context.confirm_empty_container(UDID, f.directory)
                self.assertFalse(fresh["container_absence_proved"])
                self.assertEqual(fresh["lookup"], "NOT_PERFORMED_CONSTRUCTION_CONTRACT")
                self.assertEqual([x[0][2] for x in commands.calls], ["create"])
                def delegate(instance, app, configuration, blueprint, udid, selections,
                             environment, evidence, prefix, app_path=None):
                    self.assertIs(instance, context)
                    attempt = raw(f.directory / "construction/first-selection-attempt.json")
                    self.assertEqual(attempt["methods"], [METHOD])
                    self.assertEqual(attempt["status"], "FIRST_NATIVE_SELECTION_ATTEMPT")
                    self.assertFalse(attempt["installation_success_proved"])
                    return {"status": "PASS", "scope": "INJECTED_NEW_CALLER_CONTROL"}
                with mock.patch.object(batch.FrozenBuild, "run_selection", new=delegate):
                    result = context.run_selection(f.app, f.native, "AnytypeTests", UDID,
                        [METHOD], {}, f.directory / "preparation", "prepare")
                    with self.assertRaises(ValueError):
                        context.run_selection(f.app, f.native, "AnytypeTests", UDID,
                            [METHOD], {}, f.directory / "preparation", "prepare")
                container = context.prepared_container(UDID, f.directory, result)
                self.assertEqual(container, f.container)
                context.observe_fixture({"spaceId": "owned-control-space"}, container, f.directory)
                construction.validate_saved(f.origin, fresh, f.directory, device, f.intent)
                with self.assertRaises(ValueError):
                    context.confirm_empty_container(UDID, f.directory)
            self.assertEqual([x[0][2] for x in commands.calls], ["create", "get_app_container"])
            self.assertEqual(commands.calls[0][1], 30)
            self.assertGreater(commands.calls[1][1], 0)
            self.assertLessEqual(commands.calls[1][1], 30)
            for receipt_name in ["created-proof.json", "post-preparation-container.json"]:
                receipt = raw(f.directory / "construction" / receipt_name)
                output = receipt["output"]
                path = f.directory / output["path"]
                self.assertEqual(path.suffix, ".log")  # Unchanged packager retains the actual raw original.
                self.assertEqual(output["format"], "STDOUT_STDERR_COMBINED")
                self.assertEqual(output["sha256"], digest(path))
                self.assertEqual(output["bytes"], path.stat().st_size)
            self.assertEqual([x["name"] for x in raw(
                f.directory / "construction/command-journal.json")["commands"]],
                ["create", "post-preparation-container"])
            retain_control_outputs(f, "construction-success")

        cases = ["baseline_uuid", "nonce", "runtime", "source", "run", "create_output",
                 "failed_create", "prior_selection", "prior_command"]
        for case in cases:
            with self.subTest(case=case), mock.patch.dict(os.environ, ENV), \
                    tempfile.TemporaryDirectory(prefix="coherent-construction-refusal-") as name:
                f = fixture(Path(name))
                commands = Commands(f)
                if case == "baseline_uuid":
                    inventory = raw(f.evidence / "batch-simulator-baseline.json")
                    inventory["devices"][f.planned["runtime"]["identifier"]][0]["udid"] = UDID
                    save(f.evidence / "batch-simulator-baseline.json", inventory)
                    f.intent.update(baseline_udids=[UDID],
                        baseline_inventory_sha256=digest(f.evidence / "batch-simulator-baseline.json"))
                    save(f.evidence / "batch-intent.json", f.intent)
                    with commands.patch(), self.assertRaises(ValueError):
                        construction.create(f.origin, f.intent, f.planned, f.directory)
                    self.assertFalse((f.directory / "owned-simulator.json").exists())
                    continue
                with commands.patch():
                    device = construction.create(f.origin, f.intent, f.planned, f.directory)
                context = ready(f, device)
                proof = f.directory / "construction"
                if case in {"nonce", "runtime", "source", "run"}:
                    path = proof / "created-proof.json"
                    value = raw(path)
                    value[{"nonce": "nonce", "runtime": "runtime_id",
                           "source": "control_source_sha", "run": "run_id"}[case]] = "different"
                    save(path, value)
                elif case == "create_output":
                    (proof / "create.log").write_bytes((BASELINE + "\n").encode())
                elif case == "failed_create":
                    for suffix in ["command", "observation"]:
                        path = proof / ("create." + suffix + ".json")
                        value = raw(path); value["return_code"] = 1
                        save(path, value)
                    returned = raw(proof / "created-proof.json")
                    returned["original_command_sha256"] = digest(proof / "create.command.json")
                    save(proof / "created-proof.json", returned)
                elif case == "prior_selection":
                    save(proof / "first-selection-attempt.json", {"status": "PRIOR_ATTEMPT"})
                else:
                    journal = raw(proof / "command-journal.json")
                    journal["commands"].append({"name": "unrecorded-install", "argv": ["xcrun", "simctl", "install"]})
                    save(proof / "command-journal.json", journal)
                with self.assertRaises(ValueError):
                    context.confirm_empty_container(UDID, f.directory)
                self.assertFalse((f.directory / "fresh-container.json").exists())

    def test_new_create_callback_persists_uuid_before_later_owned_failure(self):
        failures = [RuntimeError("original create failure"), subprocess.TimeoutExpired(["owned-query"], 10)]
        for index, failure in enumerate(failures):
            with self.subTest(boundary=index), mock.patch.dict(os.environ, ENV), \
                    tempfile.TemporaryDirectory(prefix="coherent-create-failure-") as name:
                f = fixture(Path(name))
                failure.timeout_observations = [{"observation": 1, "timeout_seconds": 10}]
                failure.quiescence_observation = {"status": "UNKNOWN", "absence_proved": False}
                commands = Commands(f, primary=failure if index == 0 else None,
                    quiescence=failure if index == 1 else None)
                try:
                    with commands.patch():
                        construction.create(f.origin, f.intent, f.planned, f.directory)
                except BaseException as observed:
                    self.assertIs(observed, failure)
                else:
                    self.fail("Original failure was swallowed")
                self.assertEqual(raw(f.directory / "owned-simulator.json")["udid"], UDID)
                returned = raw(f.directory / "construction/created-proof.json")
                self.assertEqual(returned["original_command_sha256"],
                                 digest(f.directory / "construction/create.command.json"))
                self.assertEqual((f.directory / "construction/create.log").read_bytes(), (UDID + "\n").encode())
                self.assertFalse((f.directory / "fresh-container.json").exists())
                self.assertFalse(f.origin._constructions[UDID.lower()]["first_selection_consumed"])
                if index == 1:
                    observation = raw(f.directory / "construction/create.observation.json")
                    self.assertEqual(observation["quiescence_failure"]["quiescence_observation"],
                                     failure.quiescence_observation)
                # Exercise the real root selection and original-receipt audit.
                # Only the independently covered anchor and OS observation are injected.
                import coherent_heart_release as heart
                import coherent_release_cleanup as cleanup
                origin = object.__new__(products.ContinuationOrigin)
                origin.__dict__.update(f.origin.__dict__)
                origin._cleanup_intent_sha = digest(f.evidence / "batch-intent.json")
                before = {p: p.read_bytes() for p in (f.directory / "construction").iterdir() if p.is_file()}
                checked = []
                def stopped(path, *, cleanup_profile):
                    self.assertEqual(cleanup_profile, batch.COHERENT_HEART_PROFILE)
                    self.assertEqual(path, f.directory / "construction/create.command.json")
                    self.assertEqual(raw(path)["worker_pid"], 42120)
                    checked.append(path)
                    return dict(status="PASS", scope="INJECTED_TERMINAL_GROUP_CONTROL_ONLY")
                with mock.patch.object(origin, "nested_cleanup_anchor", return_value=f.control), \
                        mock.patch.object(groups, "verify_owned_group_stopped", side_effect=stopped):
                    result = heart.nested_cleanup(origin.args, origin=origin)
                self.assertEqual(result["groups_checked"], 1)
                self.assertEqual(len(checked), 1)
                self.assertEqual(before, {p: p.read_bytes() for p in before})
                terminal = raw(f.evidence / "coherent-nested-cleanup.json")
                self.assertEqual(len(terminal["original_owned_commands"]), 1)
                self.assertEqual(terminal["original_owned_commands"][0]["path"],
                    (f.directory / "construction/create.command.json").relative_to(f.control).as_posix())
                self.assertEqual(terminal["original_owned_commands"][0]["original_command_status"],
                                 "FAIL" if index == 0 else "COMPLETE")
                self.assertFalse((f.directory / "fresh-container.json").exists())
                # The ordinary caller retains exactly its previous root list.
                ordinary = SimpleNamespace(app=f.app, derived=origin.args.derived,
                    evidence=f.control / "build/default-cleanup-control")
                with mock.patch.object(cleanup, "audit_nested_receipts") as audit:
                    heart.nested_cleanup(ordinary)
                    self.assertEqual(audit.call_args.args[0],
                        [heart.private_work(ordinary), ordinary.evidence / "coherent-t5",
                         *[ordinary.evidence / "lanes" / lane / "owned-readiness"
                           for lane in batch.profile_spec(batch.COHERENT_HEART_PROFILE).lanes]])
                retain_control_outputs(f, "create-failure-" + str(index))

    def test_outer_coherent_caller_forwards_profile_and_retains_original_failures(self):
        for case in ["return", "cleanup_failure", "primary_and_cleanup_failure"]:
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="coherent-outer-control-") as name:
                root = Path(name)
                primary = RuntimeError("original outer wait failure") if case.startswith("primary") else None
                late = subprocess.TimeoutExpired(["original-owned-query"], 10)
                late.timeout_observations = [{"observation": 1, "timeout_seconds": 10}]
                late.quiescence_observation = {"outcome": "UNKNOWN", "absence_proved": False}
                class Process:
                    pid = 42420
                    returncode = 1
                    calls = 0
                    def wait(self, timeout):
                        self.calls += 1
                        if primary is not None and self.calls == 1:
                            raise primary
                        return self.returncode
                process = Process()
                observation = {"status": "PASS", "scope": "INJECTED_NEW_CALLER_CONTROL"}
                def stopped(path, *, cleanup_profile):
                    self.assertEqual(cleanup_profile, batch.COHERENT_HEART_PROFILE)
                    record = raw(path)
                    self.assertEqual(record["worker_pid"], process.pid)
                    self.assertEqual(record["owned_group_cleanup"], "TERM_THEN_KILL")
                    if case != "return":
                        raise late
                    return observation
                with mock.patch.object(batch.subprocess, "Popen", return_value=process), \
                        mock.patch.object(batch.os, "getpgrp", return_value=77), \
                        mock.patch.object(batch.os, "killpg") as kill, \
                        mock.patch.object(groups, "verify_owned_group_stopped", side_effect=stopped) as check:
                    if case == "return":
                        result = batch.run_nested_worker_command(["fixture-owned-worker"], root,
                            root / "worker.log", 6300, profile=batch.COHERENT_HEART_PROFILE)
                        self.assertIs(result["owned_group_quiescence"], observation)
                        self.assertEqual(result["return_code"], 1)
                    else:
                        try:
                            batch.run_nested_worker_command(["fixture-owned-worker"], root,
                                root / "worker.log", 6300, profile=batch.COHERENT_HEART_PROFILE)
                        except BaseException as error:
                            self.assertIs(error, primary or late)
                        else:
                            self.fail("Original error was swallowed")
                        result = raw(root / "worker.command.json")
                        self.assertEqual(result["cleanup_probe_timeouts"], late.timeout_observations)
                        self.assertEqual(result["cleanup_quiescence_observation"], late.quiescence_observation)
                    check.assert_called_once_with(root / "worker.command.json",
                                                  cleanup_profile=batch.COHERENT_HEART_PROFILE)
                    self.assertTrue(kill.call_args_list)
                    self.assertTrue(all(call.args[0] == process.pid for call in kill.call_args_list))
                    self.assertEqual(result["inner_quiescence_seconds"], 10)
                    self.assertEqual(result["timeout_seconds"], 6300)

    def test_cleanup_snapshot_checks_live_bytes_closure_and_intent_without_git(self):
        # Actual current-repository preload -> Git admission -> cleanup, with the
        # worker-finally/T5 modules initially absent. No product operation is called.
        control = Path(__file__).resolve().parents[2]
        head = subprocess.check_output(["git", "-C", str(control), "rev-parse", "HEAD"], text=True).strip()
        branch = subprocess.check_output(["git", "-C", str(control), "branch", "--show-current"], text=True).strip()
        current_env = dict(ENV, GITHUB_SHA=head, GITHUB_REF="refs/heads/" + branch)
        (control / "build").mkdir(exist_ok=True)
        late = ("coherent_heart_release", "run_t5_apple_pair", "run_t5_native_ui",
                "t5_account_retry_existing_build", "t5_host_actions", "t5_remaining_freshness")
        with self.subTest(case="actual_production_preload_git_admission_cleanup"), \
                mock.patch.dict(os.environ, current_env), mock.patch.dict(sys.modules), \
                tempfile.TemporaryDirectory(prefix="coherent-current-source-", dir=control / "build") as name:
            for module_name in late:
                sys.modules.pop(module_name, None)
            f = fixture(Path(name), control=control, control_sha=head)
            origin = products.ContinuationOrigin(f.origin.args)
            admission_fixture(f, origin)
            origin.validate_intent(f.intent)
            names = dict(origin._cleanup_sources.module_names)
            self.assertEqual(dict(origin._cleanup_sources.required_modules), products.CLEANUP_MODULES)
            for module_name, relative in products.CLEANUP_MODULES.items():
                self.assertEqual(names.get(module_name), relative)
            import coherent_heart_release as heart
            with mock.patch.object(subprocess, "run", side_effect=AssertionError("Cleanup attempted a subprocess")), \
                    mock.patch.object(subprocess, "check_output", side_effect=AssertionError("Cleanup attempted Git")):
                result = heart.nested_cleanup(origin.args, origin=origin)
            self.assertEqual(result["groups_checked"], 0)
            observed = raw(f.evidence / "coherent-cleanup-source-check.json")
            self.assertEqual(observed["git_subprocesses"], 0)
            self.assertGreaterEqual(observed["admitted_sources"], len(set(products.CLEANUP_MODULES.values())))
            retain_control_outputs(f, "actual-source-admission")

        # A mandatory origin/helper initially bound outside the checkout cannot
        # disappear from the loaded map and thereby admit a smaller closure.
        for module_name in ("coherent_original_products", "coherent_cleanup_snapshot", "coherent_heart_release"):
            with self.subTest(case="initial_foreign_required_module", module=module_name), \
                    mock.patch.dict(os.environ, current_env), \
                    tempfile.TemporaryDirectory(prefix="coherent-foreign-module-") as name:
                foreign = Path(name) / (module_name + ".py")
                foreign.write_text("FOREIGN = True\n")
                origin = object.__new__(products.ContinuationOrigin)
                origin.control = control
                with mock.patch.dict(sys.modules, {module_name: SimpleNamespace(__file__=str(foreign))}), \
                        mock.patch.object(subprocess, "check_output", side_effect=AssertionError("Foreign source reached Git")):
                    with self.assertRaises(RuntimeError):
                        origin._preload_cleanup_sources()

        cases = ["valid", "changed_bytes", "missing_file", "symlink", "new_module",
                 "changed_module_origin", "changed_environment", "changed_intent", "changed_admission"]
        for case in cases:
            with self.subTest(case=case), mock.patch.dict(os.environ, ENV), \
                    tempfile.TemporaryDirectory(prefix="coherent-snapshot-control-") as name:
                f = fixture(Path(name))
                paths = []
                modules = {}
                for index in range(6):
                    path = f.control / ("owned_source_" + str(index) + ".py")
                    path.write_text("VALUE = " + str(index) + "\n")
                    paths.append(path)
                    modules["owned_cleanup_control_" + str(index)] = SimpleNamespace(__file__=str(path))
                origin = object.__new__(products.ContinuationOrigin)
                origin.__dict__.update(f.origin.__dict__)
                origin._cleanup_intent_sha = digest(f.evidence / "batch-intent.json")
                admission = admission_fixture(f, origin)
                with mock.patch.dict(sys.modules, modules), \
                        mock.patch.object(subprocess, "run", side_effect=AssertionError("Unexpected cleanup subprocess")), \
                        mock.patch.object(subprocess, "check_output", side_effect=AssertionError("Unexpected cleanup Git subprocess")):
                    admitted = {path.name: digest(path) for path in paths}
                    origin._cleanup_sources = snapshots.admit(f.control, CONTROL,
                        origin._cleanup_identity(), admitted,
                        required_modules={name: Path(module.__file__).name for name, module in modules.items()})
                    extra = {}
                    if case == "changed_bytes":
                        paths[0].write_text("VALUE = 'changed'\n")
                    elif case == "missing_file":
                        paths[0].unlink()
                    elif case == "symlink":
                        alternate = Path(name) / "alternate.py"
                        alternate.write_bytes(paths[0].read_bytes())
                        paths[0].unlink(); paths[0].symlink_to(alternate)
                    elif case == "new_module":
                        path = f.control / "unadmitted.py"
                        path.write_text("VALUE = 'unadmitted'\n")
                        extra["unadmitted_cleanup_control"] = SimpleNamespace(__file__=str(path))
                    elif case == "changed_module_origin":
                        alternate = Path(name) / "outside.py"
                        alternate.write_text("VALUE = 'outside'\n")
                        extra["owned_cleanup_control_0"] = SimpleNamespace(__file__=str(alternate))
                    elif case == "changed_environment":
                        os.environ["GITHUB_RUN_ATTEMPT"] = "2"
                    elif case == "changed_intent":
                        value = raw(f.evidence / "batch-intent.json")
                        value["token"] = "b" * 32
                        save(f.evidence / "batch-intent.json", value)
                    elif case == "changed_admission":
                        admission["current_shared_app_accepted"] = True
                        save(origin.admission_path, admission)
                    with mock.patch.dict(sys.modules, extra):
                        if case == "valid":
                            self.assertEqual(origin.nested_cleanup_anchor(origin.args), f.control)
                            result = raw(f.evidence / "coherent-cleanup-source-check.json")
                            self.assertEqual(result["git_subprocesses"], 0)
                            self.assertEqual(result["admitted_sources"], 6)
                            self.assertEqual(result["original_intent_sha256"], origin._cleanup_intent_sha)
                        else:
                            with self.assertRaises(RuntimeError if case in {"changed_intent", "changed_admission"} else ValueError):
                                origin.nested_cleanup_anchor(origin.args)
                            path = f.evidence / "coherent-cleanup-source-check.json"
                            if path.exists():
                                self.assertEqual(raw(path)["status"], "FAIL")
