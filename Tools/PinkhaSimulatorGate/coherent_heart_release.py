"""One explicit coherent Release build for retained UI, pending T5 and R07.

The existing native/UI validators remain the acceptance authorities. This
controller shares immutable products only, gives each native fixture a new
owned simulator, and never replays the retained 36-query pagination body.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

import wave15_batch as batch

PROFILE = "coherent-heart-release"
RUNTIME_PROFILE = "r15-attachment-authorized-current-read-v1"
PASS = "COHERENT_R15_T5_SHARED_BUILD_PASS_VISUAL_REVIEW_PENDING"
EXTRA_DEVICES = ("t5-pending-nine", "t5-remaining-freshness", "t5-native-ui")
COUNTS = dict(app_builds=1, ui_runner_builds=1, host_action_methods=11, host_action_cases=12,
              pending_retry_methods=1, pending_retry_observations=3, pending_retry_service_queries=9,
              remaining_freshness_methods=1, remaining_freshness_observations=6,
              remaining_freshness_service_queries=6, remaining_freshness_native_mutations=3,
              native_preparation_methods=1, native_mutations=2, native_mutation_observations=3,
              core_ui_methods=2, hebrew_readonly_ui_executions=2, ui_app_lifetimes=5,
              baseline_pagination_body_invocations=0, failed=0, skipped=0)


def original_products_context(context):
    from coherent_original_products import OriginalProductsContext
    return isinstance(context, OriginalProductsContext)


def build_reference(build):
    from coherent_original_products import reference
    return reference(build)


def reference_matches(record, build):
    from coherent_original_products import reference_matches as matches
    return matches(record, build)


def reuse_fields(build):
    from coherent_original_products import reuse_fields as fields
    return fields(build)


def reuse_matches(record, build):
    from coherent_original_products import reuse_matches as matches
    return matches(record, build)


def actual_counts(context):
    if original_products_context(context):
        from coherent_original_products import counts
        return counts()
    return dict(COUNTS)


def validate_counts(actual):
    batch.require(isinstance(actual, dict) and set(actual) == set(COUNTS)
                  and all(type(actual[key]) is int and actual[key] == value for key, value in COUNTS.items()),
                  "Exact coherent current-run counts are required; no prior pagination body may run")


def private_work(args):
    return args.derived.resolve().with_name(args.derived.name + "-coherent-private")


def require_runtime(args, binding, ui):
    batch.require(getattr(args, "runtime_profile", None) == RUNTIME_PROFILE
                  and binding.get("runtime_profile") == RUNTIME_PROFILE
                  and binding.get("heart_source_run_id") == getattr(args, "heart_source_run_id", None),
                  "The coherent batch requires its explicit runtime and original producer run")
    profile = ui.heart_profiles.select(RUNTIME_PROFILE)
    batch.require(ui.heart_profiles.verify_binding(binding) == profile.version,
                  "The coherent runtime binding must retain its exact native version")
    return profile


def build_selection(args, app, binding):
    import run_ui27 as ui
    import run_t5_native_ui as native_ui
    import t5_host_actions as host_actions
    import t5_native_account_retry_pending_evidence as pending
    import t5_remaining_freshness as freshness
    require_runtime(args, binding, ui)
    host = host_actions.source_contract(app)
    retained = pending.validate_retained_source(app, runtime_binding=binding)
    quote_source = freshness.source_contract(app)
    batch.write(args.evidence.resolve() / "coherent-build-selection.json", dict(
        profile=PROFILE, runtime_profile=RUNTIME_PROFILE, host_actions=host,
        retained_pagination=retained, remaining_freshness_source=quote_source, planned_t5_counts=COUNTS,
        planned_focus_counts={"return_methods": 3, "rtl_preparation_methods": 1, "additional_app_builds": 0},
        build_flags=batch.profile_flags(PROFILE), configuration=batch.CONFIGURATION,
        shipping_default_build=False, release_accepted=False, full_matrix_accepted=False))
    from coherent_release_focus import RETURN_SUITE
    return ([RETURN_SUITE, native_ui.evidence.PREPARATION.split("/")[0], host_actions.SUITE,
             pending.METHOD.split("/")[0], freshness.SUITE],
            [*native_ui.evidence.METHODS.values(), native_ui.r08.METHOD])


def extra_devices(template, token, run_id):
    batch.require(re.fullmatch(r"[0-9a-f]{32}", token or "") and run_id.isdigit(),
                  "Coherent simulator ownership requires this run's nonce")
    return [dict(lane=key, name="Pinkha-UI27-" + run_id + "-batch-" + token + "-" + key,
                 device=template["device"], runtime=template["runtime"]) for key in EXTRA_DEVICES]


@dataclass(frozen=True)
class OwnedExtraDevice:
    key: str
    ownership: dict
    directory: Path
    baseline_udids: tuple

    def prepare(self):
        batch.require(self.key in EXTRA_DEVICES and self.ownership.get("lane") == self.key,
                      "Unknown coherent fixture destination")
        self.directory.mkdir(parents=True, exist_ok=False)
        batch.write(self.directory / "planned-simulator.json", self.ownership)
        inventory = batch.scoped_device_inventory(self.ownership, timeout=30)
        batch.require(not any(items for items in inventory["devices"].values()),
                      "Refuse a pre-existing coherent fixture simulator")
        return self.ownership["name"]

    def record_created(self, udid):
        batch.require(batch.valid_udid(udid) and udid.lower() not in {x.lower() for x in self.baseline_udids},
                      "Coherent fixture must have a new owned simulator identity")
        device = dict(self.ownership, udid=udid)
        batch.write(self.directory / "owned-simulator.json", device)
        batch.validate_owned_device(batch.scoped_device_inventory(device, timeout=30), device,
                                    expected_state="Shutdown")
        return device


def owned_device(intent, evidence, key):
    batch.require(intent.get("profile") == PROFILE and key in EXTRA_DEVICES,
                  "Explicit coherent ownership intent required")
    devices = intent.get("extra_devices", [])
    batch.require([x.get("lane") for x in devices] == list(EXTRA_DEVICES),
                  "Coherent fixture destinations differ from the reviewed set")
    ownership = next(x for x in devices if x["lane"] == key)
    return OwnedExtraDevice(key, ownership, evidence / "lanes" / key, tuple(intent["baseline_udids"]))


def validate_build(build, source, pair, ui, context):
    if original_products_context(context):
        return context.origin.validate_build(build, source, pair, ui, context)
    batch.require(context is not None and context.profile == PROFILE and context.source["source_sha"] == source,
                  "T5 requires this job's in-memory coherent frozen build")
    context.verify_current()
    profile = ui.heart_profiles.select(RUNTIME_PROFILE)
    batch.require(build.get("role") == "coherent-r15" and build.get("app_source_sha") == source
                  and build.get("flags") == pair.FLAGS == batch.profile_flags(PROFILE)
                  and build.get("runtime_version") == profile.version
                  and build.get("runtime_binding", {}).get("runtime_profile") == RUNTIME_PROFILE
                  and ui.heart_profiles.verify_binding(build["runtime_binding"]) == profile.version,
                  "Coherent T5 runtime, actual build flags or source differ")
    batch.require(all(type(build.get(key)) is int and build[key] == 1 for key in ("app_builds", "ui_runner_builds"))
                  and Path(build.get("app", "")).resolve() == context.built.resolve()
                  and Path(build.get("configuration", "")).resolve() == context.native_configuration.resolve()
                  and Path(build.get("ui_configuration", "")).resolve() == context.ui_configuration.resolve(),
                  "Coherent T5 must reuse the exact one App and one UI runner from this job")
    batch.require(build.get("hanlin_snapshot_sha256") == context.source["hanlin_snapshot_sha256"]
                  and build.get("kit_sha") == ui.KIT
                  and build.get("code_sha256") == ui.code_carriers(context.built)["sha256"],
                  "Coherent T5 dependency or executable carrier identity differs")
    original = context.runtime_receipt_path.parent.parent / "batch-build/same-job-build.json"
    batch.require(build.get("same_job_build_receipt_sha256") == batch.digest(original),
                  "Coherent T5 original same-job build receipt changed")
    return profile


def make_build(args, context, receipt, ui, pair):
    if original_products_context(context):
        return context.origin.make_build(context, receipt, ui, pair)
    source = context.source["source_sha"]
    installation = json.loads(context.runtime_receipt_path.read_bytes())
    binding = ui.heart_profiles.installed_binding(context.app, installation, source, RUNTIME_PROFILE,
                                                  args.heart_source_run_id)
    profile = require_runtime(args, binding, ui)
    lock = json.loads((context.app / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved").read_bytes())
    pins = [item["state"]["revision"] for item in lock["pins"] if item["identity"].casefold() == "torahinspectorkit"]
    checkouts = [p for p in (context.derived / "SourcePackages/checkouts").iterdir()
                 if p.name.casefold() == "torahinspectorkit"]
    batch.require(pins == [ui.KIT] and len(checkouts) == 1 and ui.git(checkouts[0], "rev-parse", "HEAD") == ui.KIT,
                  "Coherent T5 resolved Kit differs from its reviewed lock")
    carriers = ui.code_carriers(context.built)
    build = dict(role="coherent-r15", app_source_sha=source, flags=batch.profile_flags(PROFILE),
        runtime_version=profile.version, runtime_binding=binding,
        package_lock_hashes=context.source["package_locks"],
        hanlin_snapshot_sha256=context.source["hanlin_snapshot_sha256"], kit_sha=ui.KIT,
        code_sha256=carriers["sha256"], code_carriers=carriers,
        app=str(context.built), configuration=str(context.native_configuration),
        ui_configuration=str(context.ui_configuration), app_builds=1, ui_runner_builds=1,
        same_job_build_receipt_sha256=receipt["build_receipt_sha256"],
        shipping_default_build=False, full_matrix_accepted=False, release_accepted=False)
    validate_build(build, source, pair, ui, context)
    return build


def execute(args, context, preflight, receipt, intent):
    import run_t5_apple_pair as pair
    import run_t5_native_ui as native_ui
    import t5_account_retry_existing_build as pending
    import t5_host_actions as actions
    import t5_remaining_freshness as freshness
    import run_ui27 as ui
    from validate_release import method_results
    evidence, work = args.evidence.resolve(), private_work(args)
    proof = evidence / "coherent-t5"
    batch.require(work.is_relative_to(context.app / "build") and not work.exists() and not proof.exists(),
                  "Fresh job-owned coherent private and public work required")
    work.mkdir(parents=True, mode=0o700)
    proof.mkdir(parents=True)
    build = make_build(args, context, receipt, ui, pair)
    original_products = original_products_context(context)
    if not original_products:
        from coherent_test_diagnostics import Pair
        pair = Pair(pair)
    batch.write(proof / ("original-products-build.json" if original_products else "same-job-build.json"), build)
    source, run_id = context.source["source_sha"], intent["run_id"]
    selection = preflight["selected"]["ipad"]
    result = dict(profile=PROFILE, runtime_profile=RUNTIME_PROFILE, status="RUNNING", phase="HOST_ACTIONS",
        source_sha=source, run_id=run_id, run_attempt=intent["run_attempt"],
        **build_reference(build),
        host_actions_status="NOT_RUN", pending_retry_status="NOT_RUN", remaining_freshness_status="NOT_RUN", native_ui_status="NOT_RUN",
        mixed_version_accepted=False, host_freshness_accepted=False,
        shipping_default_build=False, full_matrix_accepted=False, release_accepted=False,
        physical_device_accepted=False, voice_over_status="NOT_RUN", visual_review_status="PENDING",
        started_at=batch.now())
    batch.write(proof / "result.json", result)
    try:
        host = actions.execute(app=context.app, build=build, selection=selection,
            evidence=proof / "host-actions", pair=pair, ui=ui, source=source, run_id=run_id)
        batch.require(host["status"] == actions.PASS, "Actual pending T5 host actions did not pass")
        context.verify_current()
        result.update(host_actions_status=host["status"], phase="PENDING_NINE")
        batch.write(proof / "result.json", result)
        tail = pending.run_after_coherent_build(app=context.app, work=work, proof=proof, build=build,
            selection=selection, pair=pair, ui=ui, method_results=method_results, source=source, run_id=run_id,
            build_context=context, owned_device=owned_device(intent, evidence, "t5-pending-nine"))
        batch.require(tail["status"] == pending.PASS, "Actual pending nine-query native tail did not pass")
        context.verify_current()
        result.update(pending_retry_status=tail["status"], phase="REMAINING_QUOTE_FRESHNESS")
        batch.write(proof / "result.json", result)
        quote = freshness.run_after_coherent_build(app=context.app, work=work, proof=proof, build=build,
            selection=selection, pair=pair, ui=ui, method_results=method_results, source=source, run_id=run_id,
            run_attempt=intent["run_attempt"], build_context=context,
            owned_device=owned_device(intent, evidence, "t5-remaining-freshness"))
        batch.require(quote["status"] == freshness.PASS, "Actual remaining native quote freshness did not pass")
        context.verify_current()
        result.update(remaining_freshness_status=quote["status"], phase="NATIVE_UI")
        batch.write(proof / "result.json", result)
        outcome = native_ui.run_after_coherent_build(app=context.app, work=work, proof=proof, build=build,
            selection=selection, pair=pair, ui=ui, method_results=method_results, source=source, run_id=run_id,
            build_context=context, owned_device=owned_device(intent, evidence, "t5-native-ui"))
        result["native_ui_status"] = outcome["status"]
        batch.require(outcome["status"] == native_ui.PASS and outcome.get("ui_runner_builds") == 0
                      and reuse_matches(outcome, build)
                      and outcome.get("app_builds_added") == 0,
                      "Actual T5 UI must pass on the original single App and UI runner")
        context.verify_current()
        result.update(status=PASS, phase="COMPLETE", actual_counts=actual_counts(context))
        batch.write(proof / "result.json", result)
        validate_results(evidence, intent, receipt, ui, require_release_fixtures=False,
                         origin=context.origin if original_products else None)
    except BaseException as error:
        result.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                      error_type=type(error).__name__, error=str(error))
        raise
    finally:
        result["finished_at"] = batch.now()
        batch.write(proof / "result.json", result)
    return result


def publication(root, policy):
    batch.require(policy.get("status") == "PASS" and policy.get("secrets_uploaded") is False
                  and policy.get("account_data_uploaded") is False and policy.get("raw_xcresult_uploaded") is False,
                  "Complete original credential-scanned evidence is required")
    files = policy.get("files", [])
    batch.require(files and len({item["path"] for item in files}) == len(files),
                  "Published coherent evidence is empty or duplicates paths")
    for item in files:
        path = root / item["path"]
        batch.require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
                      and batch.digest(path) == item["sha256"] and path.stat().st_size == item["bytes"],
                      "Published original coherent evidence changed")


def validate_results(evidence, intent, worker, ui, *, require_release_fixtures=True, origin=None):
    """Re-read original current-run results; no historical pass is relabelled."""
    import run_t5_apple_pair as pair
    import run_t5_native_ui as native_ui
    import t5_account_retry_existing_build as pending
    import t5_host_actions as actions
    import t5_remaining_freshness as freshness
    from validate_release import method_results
    proof = evidence / "coherent-t5"
    read = lambda path: json.loads(path.read_bytes())
    result = read(proof / "result.json")
    if origin is None:
        validate_counts(result.get("actual_counts"))
    else:
        from coherent_original_products import validate_counts as validate_original_counts
        validate_original_counts(result.get("actual_counts"))
    reference_key = "same_job_build_receipt_sha256" if origin is None else origin.reference_key
    batch.require(result.get("status") == PASS and result.get("profile") == PROFILE
                  and result.get("runtime_profile") == RUNTIME_PROFILE
                  and all(result.get(key) == intent[key] for key in ("source_sha", "run_id", "run_attempt"))
                  and result.get(reference_key) == worker["build_receipt_sha256"],
                  "Original coherent T5 result identity, build or exact counts differ")
    batch.require(all(result.get(key) is False for key in ("mixed_version_accepted", "host_freshness_accepted",
                  "shipping_default_build", "full_matrix_accepted", "release_accepted", "physical_device_accepted")),
                  "Coherent T5 result widened its acceptance scope")
    if origin is None:
        build = read(proof / "same-job-build.json")
        batch.require(build.get("flags") == batch.profile_flags(PROFILE)
                      and build.get("same_job_build_receipt_sha256") == worker["build_receipt_sha256"]
                      and build.get("runtime_binding", {}).get("runtime_profile") == RUNTIME_PROFILE
                      and build.get("runtime_version") == ui.heart_profiles.verify_binding(build["runtime_binding"]),
                      "Coherent T5 original build/runtime proof differs")
    else:
        build = read(proof / "original-products-build.json")
        origin.validate_saved_build(build, intent["source_sha"], worker)
    batch.require(reference_matches(result, build), "Original result provenance reference differs")
    host_dir = proof / "host-actions"
    host = read(host_dir / "execution.json")
    host_udid = next(x["udid"] for x in intent["preflight_devices"] if x["name"].endswith("-ipad"))
    batch.require(host.get("status") == actions.PASS and host.get("app_source_sha") == intent["source_sha"]
                  and host.get("run_id") == intent["run_id"] and host.get("additional_app_builds") == 0,
                  "Original pending T5 host evidence is incomplete")
    actions.validate_results(read(host_dir / "summary.json"), read(host_dir / "tests.json"), host_udid)
    tail_dir = proof / "account-retry-pending"
    tail = read(tail_dir / "result.json")
    batch.require(tail.get("status") == pending.PASS and tail.get("runtime_profile") == RUNTIME_PROFILE
                  and tail.get("runtime_binding") == build["runtime_binding"]
                  and tail.get("app_source_sha") == intent["source_sha"] and tail.get("run_id") == intent["run_id"]
                  and tail.get("additional_app_builds") == 0,
                  "Original pending-nine source/runtime evidence is incomplete")
    pending.validate_counts(tail["actual_counts"], pair)
    publication(tail_dir, read(tail_dir / "native-evidence-policy.json"))
    original = tail_dir / "actual-native"
    fixture_path = original / "account-retry-fixture.json"
    fixture, controller = read(fixture_path), read(original / "account-retry-controller.json")
    expected_runtime = ui.heart_profiles.select(RUNTIME_PROFILE).version
    pending.native.retry_evidence.validate_receipt(read(original / "account-retry-receipt.json"),
        fixture, fixture_path.read_bytes(), source=intent["source_sha"], run_id=intent["run_id"],
        run_attempt=intent["run_attempt"], token=fixture["state"]["token"],
        root_sha=controller["current_directories"]["root"]["pathSHA256"],
        credential_sha=controller["credential_sha256"], current_directories=controller["current_directories"],
        execution_window=controller["actual_xctest_execution_window"], pending_only=True, runtime_profile=RUNTIME_PROFILE)
    native_ui.evidence.validate_selection(read(original / "summary.json"),
        method_results(read(original / "tests.json")), [pending.native.pending_evidence.METHOD], tail["device_udid"])
    quote = freshness.validate_saved(proof / "remaining-freshness", source=intent["source_sha"],
        run_id=intent["run_id"], run_attempt=intent["run_attempt"], build=build, ui=ui, method_results=method_results)
    batch.require(result.get("remaining_freshness_status") == quote["status"] == freshness.PASS,
                  "Coherent result lacks the original remaining quote freshness proof")
    ui_dir = proof / "native-ui"
    actual_ui = read(ui_dir / "result.json")
    batch.require(actual_ui.get("status") == native_ui.PASS
                  and actual_ui.get("runtime_profile") == RUNTIME_PROFILE
                  and actual_ui.get("app_source_sha") == intent["source_sha"]
                  and actual_ui.get("run_id") == intent["run_id"]
                  and actual_ui.get("app_flags") == batch.profile_flags(PROFILE)
                  and actual_ui.get("packaged_code_sha256") == build["code_sha256"]
                  and actual_ui.get("installed_code_sha256") == build["code_sha256"]
                  and actual_ui.get("prerequisite_scope") == "SINGLE_CORRECTED_RUNTIME"
                  and actual_ui.get("ui_simulator_shutdown") is True
                  and actual_ui.get("ui_runner_builds") == 0 and actual_ui.get("app_builds_added") == 0
                  and reuse_matches(actual_ui, build),
                  "Original T5 UI did not reuse and shut down the exact coherent build")
    publication(ui_dir / "actual", read(ui_dir / "evidence-policy.json"))
    actual = ui_dir / "actual"
    ui_fixture = read(actual / "fixture.json")
    native_ui.evidence.validate_standalone_fixture(ui_fixture, source=intent["source_sha"], run_id=intent["run_id"],
        token=actual_ui["token"], runtime=expected_runtime)
    mutations = native_ui.native_mutations.validate(read(actual / native_ui.native_mutations.COPY_NAME), ui_fixture)
    batch.require(mutations["actual_mutations"] == 2 and mutations["actual_observations"] == 3,
                  "Actual coherent native type change/delete observations are missing")
    observed, _ = native_ui.evidence.read_ui_receipts(actual / "ui/attachments", ui_fixture)
    retained = observed["receipts"]["note-lifecycle"]["observations"][-1]
    retained = {key: retained[key] for key in ("objectID", "blockID", "actualText")}
    processes = {ui_fixture["preparationProcessID"]}
    processes.update(pid for values in observed["actual_processes"].values() for pid in values)
    phases = [("preparation", [native_ui.evidence.PREPARATION]), ("ui", list(native_ui.evidence.METHODS.values()))]
    for appearance in native_ui.r08.APPEARANCES:
        name = "r08-he-" + appearance
        phases.append((name, [native_ui.r08.METHOD]))
        report, _ = native_ui.r08.read_receipt(actual / name / "attachments", appearance, ui_fixture, retained, processes)
        processes.add(report["process_id"])
    for name, methods in phases:
        native_ui.evidence.validate_selection(read(actual / name / "summary.json"),
            method_results(read(actual / name / "tests.json")), methods, actual_ui["device_udid"])
    fixture_paths = [evidence / "lanes" / name / "fixture-isolation.json" for name in batch.profile_spec(PROFILE).lanes]
    batch.require(not require_release_fixtures or all(path.is_file() for path in fixture_paths),
                  "Passing coherent batch lacks a Release fixture isolation receipt")
    spaces = [read(path)["space_id"] for path in fixture_paths if path.is_file()]
    spaces += [fixture["state"]["spaceID"], quote["space_id"], ui_fixture["spaceID"]]
    accounts = [fixture["state"]["accountID"], quote["account_id"], ui_fixture["accountID"]]
    batch.require(len(spaces) == len(set(spaces)) and len(accounts) == len(set(accounts)),
                  "Coherent Release/T5/R07/freshness reused a native account or Space")
    extra_udids = []
    for key, value in zip(EXTRA_DEVICES, (tail, quote, actual_ui), strict=True):
        created = read(evidence / "lanes" / key / "owned-simulator.json")
        planned = next(x for x in intent["extra_devices"] if x["lane"] == key)
        batch.require(created == dict(planned, udid=value["device_udid"])
                      and value["device_udid"].lower() not in {x.lower() for x in intent["baseline_udids"]},
                      "Coherent fixture used another or pre-existing simulator")
        extra_udids.append(value["device_udid"].lower())
    device_paths = [evidence / "lanes" / name / "owned-simulator.json" for name in batch.profile_spec(PROFILE).lanes]
    lane_udids = [read(path)["udid"].lower() for path in device_paths if path.is_file()]
    batch.require(len(set(lane_udids + extra_udids)) == len(lane_udids) + len(EXTRA_DEVICES), "Coherent fixtures reused a simulator")
    if origin is not None:
        from coherent_original_products import counts
    return dict(status="ORIGINAL_COHERENT_RESULTS_REVALIDATED",
                t5_counts=dict(COUNTS) if origin is None else counts(),
                independent_native_fixture_spaces=len(spaces), additional_app_builds=0, additional_ui_runner_builds=0)


def nested_cleanup(args, *, origin=None):
    """Recheck exact original groups while retaining any earlier command failure."""
    from coherent_release_cleanup import audit_nested_receipts
    evidence, work = args.evidence.resolve(), private_work(args)
    focus_roots = []
    if origin is None:
        from coherent_release_focus import KEYS as focus_keys
        focus_roots = [evidence / "lanes" / key for key in focus_keys]
    roots = [work, evidence / "coherent-t5", *focus_roots,
             *[evidence / "lanes" / name / "owned-readiness" for name in batch.profile_spec(PROFILE).lanes]]
    result = dict(status="RUNNING", original_owned_commands=[], groups_checked=0,
                  evidence_scope="CLEANUP_ONLY_ORIGINAL_COMMAND_AND_PRODUCT_STATUS_UNCHANGED")
    try:
        anchor = args.app.resolve() if origin is None else origin.nested_cleanup_anchor(args)
        if origin is not None:
            roots.extend(origin.construction_cleanup_roots(args))
        audit_nested_receipts(roots, anchor, work, result)
        result["status"] = "PASS"
    except BaseException as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        result["finished_at"] = batch.now()
        batch.write(evidence / "coherent-nested-cleanup.json", result)
    return dict(status="PASS", groups_checked=result["groups_checked"], path="coherent-nested-cleanup.json",
                sha256=batch.digest(evidence / "coherent-nested-cleanup.json"))


def check_cache_ready(evidence):
    from run_owned_single_lane import verify_owned_group_stopped
    evidence = evidence.resolve()
    result = json.loads((evidence / "execution.json").read_bytes())
    worker_path = evidence / "batch-worker.json"
    command_path = evidence / "batch-worker.command.json"
    worker = json.loads(worker_path.read_bytes())
    command = json.loads(command_path.read_bytes())
    nested = worker.get("coherent_nested_cleanup", {})
    batch.require(result.get("profile") == worker.get("profile") == PROFILE
                  and result.get("finished_at") and worker.get("finished_at")
                  and result.get("cleanup", {}).get("status") == "PASS"
                  and result.get("retained_worker_receipt", {}).get("sha256") == batch.digest(worker_path)
                  and result.get("retained_worker_command", {}).get("sha256") == batch.digest(command_path)
                  and command.get("termination_profile") == PROFILE
                  and command.get("owned_group_quiescence", {}).get("status") == "PASS"
                  and nested.get("status") == "PASS" and nested.get("path") == "coherent-nested-cleanup.json"
                  and nested.get("sha256") == batch.digest(evidence / "coherent-nested-cleanup.json"),
                  "Coherent owned workers and simulators have not completed cleanup; refuse cache publication")
    verify_owned_group_stopped(command_path)
    print("COHERENT_OWNED_GROUPS_QUIESCENT_CACHE_READY")
    return 0


if __name__ == "__main__":
    batch.require(len(sys.argv) == 3 and sys.argv[1] == "--check-cache-ready",
                  "This helper only exposes its reviewed coherent cache-readiness check")
    raise SystemExit(check_cache_ready(Path(sys.argv[2])))
