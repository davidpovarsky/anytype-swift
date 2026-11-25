"""Current Debug App Page154 build and exact setup/UI continuation.

The native library is the immutable 154-input production artifact. No native
build, passed factory test, or diagnostic package XCTest is invoked here.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import signal
import stat
import sys
import tarfile
import uuid
import zipfile

sys.dont_write_bytecode = True
import contracts as c
import current_execution as current
import page154_contract as policy
import page154_boundary as boundary

ROOT = current.ROOT
HERE = Path(__file__).resolve().parent
INPUTS = HERE / "page154-inputs.json"


def admit(expected, inventory_policy=None):
    c.require(platform.system() == "Darwin" and platform.machine() == "arm64"
              and os.environ.get("GITHUB_ACTIONS") == "true"
              and os.environ.get("GITHUB_REPOSITORY") == c.REPOSITORY, "current_page_owned_apple_ci_required")
    c.require(re.fullmatch("[0-9a-f]{40}", expected) and expected == os.environ.get("GITHUB_SHA")
              and current.git("rev-parse", "HEAD").decode().strip() == expected, "current_page_source_identity")
    c.require(not current.git("status", "--porcelain", "--untracked-files=no").strip(), "current_page_tracked_source_dirty")
    current.git("merge-base", "--is-ancestor", c.BASE, expected)
    for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        c.require(re.fullmatch("[1-9][0-9]*", os.environ.get(key, "")), "current_page_run_identity")
    fixed = current.read(INPUTS)
    c.require(fixed["profile"] == policy.PROFILE and fixed["selectors"] == list(policy.SELECTORS)
              and fixed["excludedFactory"] == policy.EXCLUDED_FACTORY
              and fixed["freshSetupAcceptanceCredit"] == 0
              and current.digest(current.MANIFEST) == fixed["commonManifestSHA256"],
              "current_page_fixed_policy_changed")
    recovery = current.inventory_spec(current.read(current.MANIFEST), inventory_policy)
    product_trees = fixed["productTrees"]
    if recovery is not None:
        page_recovery = fixed["inventoryRecovery"]
        c.require(page_recovery["policy"] == current.INVENTORY_POLICY
                  and page_recovery["sourceCommit"] == recovery["sourceCommit"]
                  and page_recovery["productTrees"] == recovery["productTrees"]["release-return-rtl"],
                  "page_inventory_recovery_source_changed")
        current.git("merge-base", "--is-ancestor", page_recovery["sourceCommit"], expected)
        product_trees = page_recovery["productTrees"]
    revision = fixed.get("currentProductRevision")
    if revision is not None:
        c.require(set(revision) == {"schemaVersion", "sourceCommit", "productTrees"}
                  and revision["schemaVersion"] == 1
                  and re.fullmatch("[0-9a-f]{40}", revision["sourceCommit"])
                  and set(revision["productTrees"]) == set(fixed["productTrees"]),
                  "current_page_product_revision_invalid")
        current.git("merge-base", "--is-ancestor", revision["sourceCommit"], expected)
        for name, oid in revision["productTrees"].items():
            c.require(current.git("rev-parse", revision["sourceCommit"] + ":" + name).decode().strip() == oid,
                      "current_page_product_revision_origin_changed:" + name)
        product_trees = revision["productTrees"]
    trees = {**product_trees, **fixed["helperTrees"]}
    for name, oid in trees.items():
        c.require(current.git("rev-parse", "HEAD:" + name).decode().strip() == oid,
                  "current_page_source_tree_changed:" + name)
    paths = [*trees, *fixed["inputs"], "Tools/CurrentAppleValidation", fixed["workflow"]]
    files, origins = {}, {}
    for row in current.git("ls-tree", "-r", "-z", "HEAD", "--", *paths).split(b"\0"):
        if not row:
            continue
        info, name = row.split(b"\t", 1)
        mode, kind, oid = info.decode().split()
        name = name.decode()
        c.require(kind == "blob" and mode in ("100644", "100755", "120000"), "current_page_source_type")
        path = ROOT / name
        c.require(path.parent.resolve() == path.parent, "current_page_source_parent_link")
        value = current.metadata(path)
        raw = c.read(path, 128 * 1024**2) if value["kind"] == "file" else value["target"].encode()
        c.require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == oid,
                  "current_page_physical_git_mismatch:" + name)
        c.require((mode == "120000") == (value["kind"] == "symlink"), "current_page_source_type_mismatch")
        if mode == "120000":
            c.require(path.resolve().is_relative_to(ROOT), "current_page_external_source_link")
        else:
            c.require(bool(value["mode"] & 0o111) == (mode == "100755"), "current_page_source_mode")
        if name in fixed["inputs"]:
            c.require(fixed["inputs"][name] == {"gitMode": mode, "gitBlob": oid, "sha256": c.sha(raw)},
                      "current_page_bound_input_changed:" + name)
        files[name], origins[name] = value, {"gitMode": mode, "gitBlob": oid}
    c.require(set(fixed["inputs"]).issubset(files), "current_page_bound_input_missing")
    context = {"profile": policy.PROFILE, "sourceCommit": expected, "runID": os.environ["GITHUB_RUN_ID"],
               "runAttempt": os.environ["GITHUB_RUN_ATTEMPT"], "repository": c.REPOSITORY}
    source = {"manifestSHA256": current.digest(current.MANIFEST), "pageManifestSHA256": current.digest(INPUTS),
              "files": files, "gitInputs": origins, "compiledTrees": product_trees,
              "compiledOrigin": revision["sourceCommit"] if revision is not None else expected,
              "projectionOrigins": fixed["projectionOrigins"]}
    if revision is not None:
        source["currentProductRevision"] = revision
    if recovery is not None:
        source["inventoryRecoveryPolicy"] = inventory_policy
        source["inventoryRecoverySourceOrigin"] = recovery["sourceCommit"]
        source["compiledSourceTreeOrigin"] = revision["sourceCommit"] if revision is not None else recovery["sourceCommit"]
    return context, source


def recheck(source):
    c.require(current.digest(INPUTS) == source["pageManifestSHA256"], "page_policy_manifest_changed")
    observed = current.recheck(source)
    for name, relative in current.read(INPUTS)["moduleOrigins"].items():
        if name in sys.modules:
            c.require(Path(sys.modules[name].__file__).resolve() == ROOT / relative,
                      "foreign_page_module:" + name)
    return observed


def helpers(source):
    result = current.helpers(source)
    for directory in ("Tools/PinkhaSemanticAnchorWire/apple_consumer",
                      "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
        sys.path.insert(0, str(ROOT / directory))
    fixed = current.read(INPUTS)
    for name, relative in fixed["moduleOrigins"].items():
        if name == "current_page_native_producer":
            continue
        spec = importlib.util.find_spec(name)
        c.require(spec is not None and spec.origin is not None
                  and Path(spec.origin).resolve() == ROOT / relative, "foreign_page_import_origin:" + name)
    for name in ("consumer_contract", "consumer_simulator", "mounted_contract", "warning_profile",
                 "rerun_original_ui", "run_ui27"):
        result[name] = importlib.import_module(name)
    name = "current_page_native_producer"
    path = ROOT / fixed["moduleOrigins"][name]
    if name in sys.modules:
        module = sys.modules[name]
        c.require(Path(module.__file__).resolve() == path, "foreign_native_producer_contract")
    else:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    result[name] = module
    c.require(result["mounted_contract"].PREP == policy.PREPARATION
              and result["mounted_contract"].UI == policy.JOURNEY
              and result["consumer_contract"].SELECTOR == policy.EXCLUDED_FACTORY
              and result["consumer_contract"].MANIFEST_SHA == policy.NATIVE_MANIFEST,
              "original_page_helper_policy_changed")
    recheck(source)
    return result


def configure_inventory_recovery(commands, source):
    current.configure_inventory_recovery(commands, source)
    policy = getattr(commands, "inventory_recovery", None)
    if policy is not None:
        # The Page lane additionally binds its own required-module origins and manifest.
        policy.recheck_source = lambda: recheck(source)
        recheck(source)


class Commands(current.Commands):
    def run(self, argv, name, timeout, observe=None):
        # Preserve the Page lane's original 90-second boot allowance when reusing
        # the common durable-create adapter (whose other profiles allow 120).
        if argv[:3] == ["xcrun", "simctl", "boot"]:
            c.require(timeout == 120, "unexpected_common_boot_adapter")
            timeout = 90
        return super().run(argv, name, timeout, observe)


def persist_final(path, value, primary=None):
    """A missing required receipt fails without replacing an earlier failure."""
    try:
        current.write(path, value)
    except BaseException as persistence:
        original = primary if primary is not None else persistence
        # Diagnostic recording is best effort only when the required write has
        # already failed; the original error is always raised below.
        try:
            detail = {"path": str(path), **current.error(persistence)}
            value["status"] = "FAIL"
            value.setdefault("persistenceFailures", []).append(detail)
            previous = getattr(original, "_page_final_receipt_failures", ())
            original._page_final_receipt_failures = (*previous, detail)
            print(json.dumps({"status": "FAIL", "receiptPersistenceFailure": detail,
                              "primaryFailure": current.error(original)}, sort_keys=True),
                  file=sys.stderr, flush=True)
        except BaseException:
            pass
        if primary is not None:
            raise primary from persistence
        raise


def native_runtime(commands, work, evidence):
    proof = commands.helpers["consumer_contract"]
    producer = commands.helpers["current_page_native_producer"]
    manifest = producer.candidate(ROOT)
    retained = producer.retained_native(ROOT, manifest)
    current.write(evidence / "retained-native-proof.json", retained)
    expected_files = current.read(ROOT / "Tools/PinkhaSemanticAnchorWire/apple_consumer/framework-files.json")
    proof.api_run(commands.json(["gh", "api", "repos/" + proof.REPOSITORY + "/actions/runs/" +
                                proof.PRODUCER_RUN + "/attempts/1"], "page-producer-run", 60))
    originals = evidence / "native-producer-originals"
    originals.mkdir(mode=0o700)
    carriers = {}
    for kind, expected in proof.ARTIFACTS.items():
        value = commands.json(["gh", "api", "repos/" + proof.REPOSITORY + "/actions/artifacts/" +
                               str(expected["id"])], "page-" + kind + "-api", 60)
        proof.api_artifact(value, kind)
        path = commands.run(["gh", "api", "repos/" + proof.REPOSITORY + "/actions/artifacts/" +
                             str(expected["id"]) + "/zip"], "page-" + kind + "-original-zip", 300)
        c.require(path.stat().st_size == expected["bytes"] and current.digest(path) == expected["sha256"],
                  "exact_page_producer_zip_required")
        carriers[kind] = path
    archive = work / proof.ARCHIVE_NAME
    with zipfile.ZipFile(carriers["runtime"]) as packed:
        c.require(packed.namelist() == [proof.ARCHIVE_NAME], "exact_page_runtime_wrapper_required")
        member = packed.getinfo(proof.ARCHIVE_NAME)
        c.require(member.file_size == proof.ARCHIVE_BYTES, "page_inner_archive_size")
        with packed.open(member) as incoming, archive.open("xb") as output:
            shutil.copyfileobj(incoming, output, 1024**2)
    packaged = proof.install_runtime(archive, ROOT / "Dependencies/Middleware", expected_files)
    with zipfile.ZipFile(carriers["proof"]) as packed:
        c.require(len(packed.namelist()) == len(set(packed.namelist())), "duplicate_original_producer_member")
        for name in ("build.json", "runtime-artifact.json", "generated-entry.json",
                     "actual-exported-symbols.log", "actual-swift-entry-typecheck.command.json"):
            c.require(packed.getinfo(name).file_size <= 8_000_000, "bounded_original_producer_proof")
            with (originals / name).open("xb") as stream:
                stream.write(packed.read(name))
    proof.producer_proof(current.read(originals / "build.json"), packaged, manifest, expected_files)
    shutil.copyfile(ROOT / "Dependencies/Middleware" / proof.RECEIPT_NAME, originals / proof.RECEIPT_NAME)
    root = ROOT / "Dependencies/Middleware/Lib.xcframework"
    result = {"path": str(root), "files": current.inventory(root), "nativeSourceCount": 154,
              "producerRun": proof.PRODUCER_RUN, "producerCommit": proof.PRODUCER_SHA,
              "artifacts": proof.ARTIFACTS, "archiveSHA256": proof.ARCHIVE_SHA, "receiptSHA256": proof.RECEIPT_SHA,
              "frameworkFiles": expected_files, "nativeBuilds": 0, "nativeTestsExecuted": 0}
    current.write(evidence / "native-runtime.json", result)
    os.environ["PINKHA_NATIVE_T2_AUTHORIZED_READ_V1"] = "1"
    os.environ["PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1"] = proof.MANIFEST_SHA
    return result


def preserve_products(commands, derived, directory, source, argv, *, generated=None):
    products = derived / "Build/Products"
    original = current.inventory(products)
    current.write(derived / "Build/PinkhaSourceInputs.json",
                  {"context": commands.context, "sources": source, "argv": argv,
                   "nativeManifest": policy.NATIVE_MANIFEST, "generatedSources": generated})
    archive = directory / "original-build-products.tar.gz"
    with tarfile.open(archive, "x:gz", dereference=False) as packed:
        packed.add(products, arcname="Build/Products")
        packed.add(derived / "Build/PinkhaSourceInputs.json", arcname="Build/PinkhaSourceInputs.json")
        if generated is not None:
            packed.add(Path(generated["root"]), arcname="Source/UI")
    c.require(current.inventory(products) == original, "page_products_changed_during_preservation")
    if generated is not None:
        c.require(current.inventory(Path(generated["root"])) == generated["files"],
                  "page_ui_generated_inputs_changed_during_preservation")
    receipt = {"context": commands.context, "files": original, "archive": str(archive),
               "archiveSHA256": current.digest(archive), "archiveBytes": archive.stat().st_size,
               "phase": "AFTER_BUILD_BEFORE_ADMISSION", "generatedSources": generated,
               "buildReuseAuthorized": False}
    current.write(directory / "original-products.json", receipt)
    return receipt


# Xcode 27 creates these exact empty workspace directories for this package-free
# generated project. Declare them before the source inventory is frozen.
GENERATED_WORKSPACE_DIRECTORIES = (
    "project.xcworkspace",
    "project.xcworkspace/xcshareddata",
    "project.xcworkspace/xcshareddata/swiftpm",
    "project.xcworkspace/xcshareddata/swiftpm/configuration",
)


def predeclare_generated_workspace(project):
    c.require(project.name == "PinkhaPrebuiltUI.xcodeproj" and project.resolve() == project,
              "fixed_generated_ui_project_required")
    for relative in GENERATED_WORKSPACE_DIRECTORIES:
        path = project / relative
        c.require(not path.exists() and path.parent.resolve() == path.parent,
                  "fresh_generated_workspace_directory_required")
        path.mkdir(mode=0o777)
        path.chmod(0o777)


def build_once(commands, kind, device, work, evidence, source):
    c.require(kind in ("app", "ui"), "exact_page_build_kind")
    directory = evidence / (kind + "-build")
    directory.mkdir(mode=0o700)
    derived = work / (kind + "-derived")
    c.require(not derived.exists(), "fresh_page_derived_root")
    generated = None
    if kind == "app":
        project, scheme, selector = ROOT / "Anytype.xcodeproj", "Anytype", policy.PREPARATION
    else:
        ui_source = work / "ui-source"
        c.require(not ui_source.exists(), "fresh_page_ui_source_root")
        ui_source.mkdir(mode=0o700)
        plan = current.read(INPUTS)["uiPlan"]
        for relative, row in plan["files"].items():
            raw = c.read(ROOT / relative)
            c.require(c.sha(raw) == row["sha256"] and len(raw) == row["bytes"], "page_ui_source_changed")
            path = ui_source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(raw)
            path.chmod(0o600)
        generator = commands.helpers["rerun_original_ui"].ui_only_project
        c.require(Path(generator.__code__.co_filename).resolve()
                  == ROOT / "Tools/PinkhaNativeDerived/rerun_original_ui.py", "page_ui_generator_origin")
        project = generator(ui_source)
        checked = commands.helpers["warning_profile"].generated_project(ui_source, project, plan)
        predeclare_generated_workspace(project)
        generated = {"root": str(ui_source), "files": current.inventory(ui_source), "validatedInputs": checked}
        scheme, selector = policy.UI_SCHEME, policy.JOURNEY
        source_archive = directory / "generated-ui-inputs.tar.gz"
        with tarfile.open(source_archive, "x:gz", dereference=False) as packed:
            packed.add(ui_source, arcname="Source/UI")
        c.require(current.inventory(ui_source) == generated["files"], "page_ui_copy_changed_during_source_archive")
        current.write(directory / "generated-ui-inputs.json",
                      {**generated, "archiveSHA256": current.digest(source_archive)})
    argv = ["xcodebuild", "build-for-testing", "-project", str(project), "-scheme", scheme,
            "-configuration", policy.CONFIGURATION, "-destination", "platform=iOS Simulator,id=" + device["udid"],
            "-parallel-testing-enabled", "NO", "-derivedDataPath", str(derived),
            "-resultBundlePath", str(directory / "build.xcresult"), "-only-testing:" + selector, *policy.FLAGS]
    current.write(directory / "build-intent.json", {"context": commands.context, "argv": argv,
                  "kind": kind, "nativeBuilds": 0, "factoryTestExecutions": 0,
                  "uiGraph": None if generated is None else {"appTargets": 0, "uiTargets": 1,
                      "packageReferences": 0, "implicitDependencies": False}})
    try:
        commands.run(argv, "page-build-" + kind, 3900 if kind == "app" else 1200)
    except BaseException as original_failure:
        partial = derived / "Build/Products"
        if partial.is_dir():
            try:
                entries = current.inventory(partial)
                archive = directory / "failed-build-partial-products.tar.gz"
                with tarfile.open(archive, "x:gz", dereference=False) as packed:
                    packed.add(partial, arcname="Build/Products")
                c.require(current.inventory(partial) == entries, "partial_page_products_changed")
                current.write(directory / "failed-build-partial-products.json",
                              {"status": "FAIL", "reusable": False, "files": entries,
                               "archiveSHA256": current.digest(archive)})
            except BaseException as preservation:
                try:
                    current.write(directory / "partial-preservation-error.json", current.error(preservation))
                except BaseException:
                    pass  # Retain the original build exception if its secondary receipt cannot be written.
        raise original_failure
    original = preserve_products(commands, derived, directory, source, argv, generated=generated)
    products = derived / "Build/Products"
    blueprint = "AnytypeTests" if kind == "app" else policy.UI_TARGET
    descriptors = []
    for path in products.glob("*.xctestrun"):
        value = plistlib.loads(c.read(path))
        targets = [t for cfg in value.get("TestConfigurations", []) for t in cfg.get("TestTargets", [])]
        if blueprint in value or any(t.get("BlueprintName") == blueprint for t in targets):
            descriptors.append(path)
    c.require(len(descriptors) == 1, "one_current_page_original_descriptor")
    descriptor = descriptors[0]
    shutil.copyfile(descriptor, directory / "original.xctestrun")
    app = None
    dependency = None
    if kind == "app":
        app = products / (policy.CONFIGURATION + "-iphonesimulator") / policy.APP_NAME
        c.require(plistlib.loads(c.read(app / "Info.plist")).get("CFBundleIdentifier") == policy.BUNDLE,
                  "current_page_built_bundle_identity")
        verification = ("import sys;from pathlib import Path;sys.path.insert(0," +
                        repr(str(ROOT / "Tools/PinkhaSimulatorGate")) + ");import run_ui27 as s;" +
                        "s.verify_signed_simulator(Path(" + repr(str(app)) + "),Path(" + repr(str(directory)) + "));" +
                        "s.verify_runtime_copies(Path(" + repr(str(app)) + ")," +
                        repr(commands.helpers["consumer_contract"].VERSION.encode()) + ",Path(" +
                        repr(str(directory)) + "))")
        commands.run([sys.executable, "-B", "-c", verification], "page-app-signature-runtime", 120)
        dependency = current.dependencies(derived)
        current.write(directory / "actual-dependencies.json", dependency)
    else:
        commands.helpers["warning_profile"].same_job_descriptor(c.read(descriptor))
        c.require(current.inventory(Path(generated["root"])) == generated["files"], "generated_page_ui_inputs_changed")
    recheck(source)
    result = {"kind": kind, "derived": derived, "products": products, "original": original,
              "descriptor": descriptor, "app": app, "dependency": dependency, "generated": generated, "copies": {}}
    current.write(directory / "build.json", {"context": commands.context, "kind": kind,
                  "originalDescriptorSHA256": current.digest(descriptor),
                  "originalProductsReceiptSHA256": current.digest(directory / "original-products.json"),
                  "codeCarriers": current.code_carriers(app) if app is not None else None,
                  "applicationBuilds": int(kind == "app"), "uiRunnerBuilds": int(kind == "ui"), "nativeBuilds": 0})
    return result


def built_integrity(built):
    result = current.check_products(built["products"], built["original"], built["copies"])
    if built["generated"] is not None:
        c.require(current.inventory(Path(built["generated"]["root"])) == built["generated"]["files"],
                  "page_generated_source_changed")
    if built["dependency"] is not None:
        c.require(current.dependencies(built["derived"]) == built["dependency"], "page_actual_dependency_changed")
    return result


def run_stage(commands, stage, device, built, application, binding, source, evidence, *, fixture=None):
    selector = policy.STAGES[stage]
    directory = evidence / stage
    directory.mkdir(mode=0o700)
    outcome = {"status": "FAIL", "stage": stage, "selector": selector, "testCommandInvoked": False,
               "partialNamed": None, "errors": [], "freshSetupAcceptanceCredit": 0, "factoryMethodsSelected": 0}
    first = None
    try:
        current.write(directory / "source-before.json", source)
        current.write(directory / "loaded-before.json", recheck(source))
        built_integrity(built)
        raw, descriptor_proof = policy.descriptor(c.read(built["descriptor"]), selector, built["products"],
                                                 application, binding, fixture=fixture)
        descriptor = built["products"] / ("Current-Page154-" + stage + ".xctestrun")
        c.require(not descriptor.exists() and descriptor.name not in built["copies"], "page_descriptor_replay")
        with descriptor.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        descriptor.chmod(0o600)
        built["copies"][descriptor.name] = current.metadata(descriptor)
        descriptor_proof.update(copiedPath=str(descriptor), copiedSHA256=c.sha(raw))
        current.write(directory / "descriptor-binding.json", descriptor_proof)
        shutil.copyfile(descriptor, directory / "bound.xctestrun")
        mounted = commands.helpers["mounted_contract"]
        listing = directory / "enumeration.json"
        enumeration = mounted.xctest_command(descriptor, device["udid"], selector, enumeration=listing)
        command = mounted.xctest_command(descriptor, device["udid"], selector, result=directory / "original.xcresult")
        # Installed Xcode27 policy, verified by the retained zero-build failure:
        # preserve XCTest/keepAlways evidence without post-failure sysdiagnose.
        command += ["-collect-test-diagnostics", "never"]
        c.require(policy.EXCLUDED_FACTORY not in enumeration + command
                  and enumeration.count(selector) == command.count(selector) == 1, "page_exact_one_selection_required")
        current.write(directory / "plan.json", {"context": commands.context, "binding": binding,
                      "enumeration": enumeration, "command": command, "factoryTestsSelected": 0,
                      "diagnosticPackageTestsSelected": 0, "setupNewAcceptanceCredit": 0})
        commands.run(enumeration, "page-" + stage + "-enumeration", 600)
        parser = commands.helpers["native_ui_transition_contract"].enumerated_identifiers
        plan, enabled, disabled = parser(current.read(listing))
        outcome["enumeration"] = mounted.exact_enumeration(
            plan, enabled, disabled, selector, descriptor_proof["enumerationPlan"])
        c.require(current.metadata(descriptor) == built["copies"][descriptor.name], "page_enumerated_descriptor_changed")
        built_integrity(built)
        recheck(source)
        outcome["testCommandInvoked"] = True
        current.write(directory / "test-invocation.json", {"context": commands.context, "argv": command,
                      "descriptorSHA256": current.digest(descriptor), "enumerationSHA256": current.digest(listing)})
        commands.run(command, "page-" + stage + "-test", 900)
    except BaseException as failure:
        first = failure
        outcome["firstFailure"] = current.error(failure)
    result = directory / "original.xcresult"
    if result.is_dir():
        for kind in ("summary", "tests"):
            try:
                log = commands.run(["xcrun", "xcresulttool", "get", "test-results", kind,
                                    "--path", str(result), "--format", "json"],
                                   "page-" + stage + "-xcresult-" + kind, 120)
                raw = c.read(log, 32 * 1024**2)
                c.strict_json(raw)
                with (directory / (kind + ".json")).open("xb") as stream:
                    stream.write(raw)
            except BaseException as failure:
                outcome["errors"].append({"phase": kind, **current.error(failure)})
        try:
            attachments = directory / "private-attachments"
            commands.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(result),
                          "--output-path", str(attachments)], "page-" + stage + "-attachments", 180)
            attachments.chmod(0o700)
        except BaseException as failure:
            outcome["errors"].append({"phase": "attachments", **current.error(failure)})
    elif outcome["testCommandInvoked"]:
        outcome["errors"].append({"phase": "original-xcresult", "type": "MissingOriginalResult"})
    if (directory / "tests.json").is_file():
        try:
            outcome["partialNamed"] = commands.helpers["verify_native_test_execution"].test_cases(
                current.read(directory / "tests.json"))
        except BaseException as failure:
            outcome["errors"].append({"phase": "partial-named", **current.error(failure)})
    try:
        current.write(directory / "loaded-after.json", recheck(source))
        current.write(directory / "source-after.json", source)
        outcome["integrity"] = built_integrity(built)
        if first is None and not outcome["errors"]:
            c.require(outcome["testCommandInvoked"], "page_actual_test_command_required")
            actual = commands.helpers["mounted_contract"].exact_execution(
                current.read(directory / "summary.json"), current.read(directory / "tests.json"), device["udid"], selector)
            c.require(actual["device"].get("osVersion") == device["runtime"]["version"]
                      and actual["device"].get("osBuildNumber") == device["runtime"]["buildversion"],
                      "page_actual_runtime_changed")
            outcome["actual"] = actual
            cases = {name.removeprefix(selector.split("/")[0] + "/"): value
                     for name, value in outcome["partialNamed"].items()}
            commands.helpers["continue_native_acceptance"].verify_log(
                c.read(commands.root / ("page-" + stage + "-test.log"), 32 * 1024**2), cases)
            outcome["rawNamedLogVerified"] = True
            outcome["installedApplication"] = current.installed_app(commands, device, application, policy.BUNDLE,
                                                                    "page-" + stage)
            outcome["status"] = "PASS"
    except BaseException as failure:
        first = first or failure
        outcome["errors"].append({"phase": "qualification", **current.error(failure)})
    if outcome["errors"] and first is None:
        first = RuntimeError("page_original_result_or_postflight_incomplete")
    if first is not None:
        outcome["firstFailure"] = current.error(first)
    persist_final(directory / "result.json", outcome, first)
    return outcome


def copy_application_receipts(commands, device, evidence, names, *, required):
    c.require(set(names).issubset({policy.FIXTURE, policy.CAPTURE, policy.REOPEN}), "unreviewed_page_private_file")
    label = "fixture" if names == (policy.FIXTURE,) else "observations"
    log = commands.run(["xcrun", "simctl", "get_app_container", device["udid"], policy.BUNDLE, "data"],
                       "page-" + label + "-data-container", 30)
    container = Path(c.read(log, 4096).decode().strip())
    owned_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / device["udid"]
    c.require(container.is_absolute() and container.resolve() == container and container.is_dir()
              and container.is_relative_to(owned_root), "page_owned_data_container_required")
    directory = evidence / "private-app-receipts"
    directory.mkdir(mode=0o700, exist_ok=True)
    copied = {}
    for name in names:
        source = container / "Library/Application Support" / name
        if not source.exists():
            c.require(not required, "required_page_native_receipt_missing:" + name)
            copied[name] = {"status": "MISSING", "path": str(source)}
            continue
        c.require(source.resolve() == source and source.is_file() and source.stat().st_nlink == 1,
                  "page_receipt_type_or_owner_path_changed")
        raw = c.read(source, 65536)
        c.strict_json(raw)
        destination = directory / name
        with destination.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        destination.chmod(0o600)
        c.require(current.digest(source) == c.sha(raw), "page_native_receipt_changed_during_copy")
        copied[name] = {"status": "COPIED_ORIGINAL", "path": str(destination),
                        "sha256": c.sha(raw), "bytes": len(raw)}
    current.write(evidence / ("copied-" + label + ".json"), copied)
    return copied


def copy_native_boundary(commands, device, work, evidence, capture, *, required):
    metadata = capture.get("nativeBoundaryEvidence")
    if metadata is None:
        c.require(not required, "required_original_native_boundary_missing")
        return {"status": "NOT_OBSERVED", "files": {}}
    c.require(isinstance(metadata, dict) and set(metadata) == {
        "protocolVersion", "files", "source", "extraNativeCalls"}
        and metadata["protocolVersion"] == 1 and metadata["extraNativeCalls"] == 0
        and metadata["source"] == "actual-client-call-results"
        and isinstance(metadata["files"], dict)
        and set(metadata["files"]).issubset(boundary.FILES), "native_boundary_receipt_shape_changed")
    if required:
        c.require(set(metadata["files"]) == set(boundary.FILES), "incomplete_original_native_boundary")
    log = commands.run(["xcrun", "simctl", "get_app_container", device["udid"], policy.BUNDLE, "data"],
                       "page-boundary-data-container", 30)
    container = Path(c.read(log, 4096).decode().strip())
    owned_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / device["udid"]
    c.require(container.is_absolute() and container.resolve() == container and container.is_dir()
              and container.is_relative_to(owned_root), "page_boundary_owned_container_required")
    # Raw object data stays in the private retained work root. The uploaded
    # evidence contains only hashes/counts and the comparison result below.
    private = work / "private-native-boundary"
    private.mkdir(mode=0o700)
    copied = {}
    for role, row in sorted(metadata["files"].items()):
        c.require(isinstance(row, dict) and set(row) == {"filename", "bytes", "sha256"}
                  and row["filename"] == boundary.FILES[role]
                  and type(row["bytes"]) is int and 0 < row["bytes"] <= boundary.MAXIMUM
                  and isinstance(row["sha256"], str) and re.fullmatch("[0-9a-f]{64}", row["sha256"]),
                  "native_boundary_file_binding_invalid")
        source = container / "Library/Application Support" / row["filename"]
        c.require(source.resolve() == source and source.is_file() and source.stat().st_nlink == 1,
                  "native_boundary_original_file_invalid")
        raw = c.read(source, boundary.MAXIMUM)
        c.require(len(raw) == row["bytes"] and c.sha(raw) == row["sha256"], "native_boundary_original_bytes_differ")
        destination = private / row["filename"]
        with destination.open("xb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        destination.chmod(0o600)
        c.require(current.digest(source) == row["sha256"] and current.digest(destination) == row["sha256"],
                  "native_boundary_changed_during_preservation")
        copied[role] = {**row, "path": str(destination), "status": "COPIED_ORIGINAL"}
    result = {"status": "COPIED_ORIGINAL", "files": copied, "extraNativeCalls": 0,
              "rawPayloadsUploaded": False}
    current.write(evidence / "copied-native-boundary.json", result)
    return result


def root_path():
    run, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    c.require(re.fullmatch("[1-9][0-9]*", run) and re.fullmatch("[1-9][0-9]*", attempt), "page_current_run_required")
    return ROOT / "build" / ("current-page154-" + run + "-" + attempt)


def execute(expected, inventory_policy=None, restore_build=None):
    root = root_path()
    c.require(not root.exists() and root.parent.resolve() == root.parent, "fresh_page_work_root_required")
    evidence, work = root / "evidence", root / "work"
    evidence.mkdir(parents=True, mode=0o700)
    work.mkdir(mode=0o700)
    receipt = {"status": "FAIL", "profile": policy.PROFILE, "sourceCommit": expected, "stages": {},
               "nativeBuilds": 0, "appBuildsStarted": 0, "uiBuildsStarted": 0, "factoryTestsExecuted": 0,
               "diagnosticPackageTestsExecuted": 0, "freshSetupAcceptanceCredit": 0,
               "oldSimulatorStateReused": False, "newUIAcceptance": "NOT_RUN",
               "limitations": {"physicalDevice": "NOT_RUN", "shipping": "OFF", "fullProductAcceptance": False}}
    source = commands = native = app_built = ui_built = device = None
    owned, primary = [], None
    try:
        context, source = admit(expected, inventory_policy)
        binding = {"sourceSHA": expected, "runID": context["runID"], "runAttempt": context["runAttempt"],
                   "nonce": uuid.uuid4().hex}
        current.write(evidence / "source-before.json", source)
        current.write(evidence / "execution-intent.json", {"context": context, "binding": binding,
                      "sourceAdmissionSHA256": current.digest(evidence / "source-before.json"),
                      "selectors": list(policy.SELECTORS), "freshSetupAcceptanceCredit": 0,
                      **({"inventoryRecoveryPolicy": inventory_policy} if inventory_policy is not None else {})})
        modules = helpers(source)
        modules["consumer_contract"].binding(binding)
        commands = Commands(evidence, context, modules)
        configure_inventory_recovery(commands, source)
        current.write(evidence / "loaded-before.json", recheck(source))
        receipt["context"], receipt["binding"] = context, binding
        native = native_runtime(commands, work, evidence)
        commands.run([sys.executable, "-B", "Tools/Hanlin/prepare_sdk.py", "--source",
                      str(ROOT / ".ci/hanlin-source")], "page-prepare-hanlin", 180)
        commands.run([sys.executable, "-B", "Tools/Hanlin/prepare_sdk.py", "--check"], "page-check-hanlin", 60)
        shutil.copyfile(ROOT / "Dependencies/Hanlin/.pinkha-source.json", evidence / "hanlin-snapshot.json")
        version = commands.run(["xcodebuild", "-version"], "page-xcode-version", 60)
        c.require(c.read(version, 65536).decode().startswith("Xcode 27."), "actual_xcode27_required")
        pair = modules["consumer_simulator"].choose_pair(
            commands.json(["xcrun", "simctl", "list", "runtimes", "--json"], "page-runtimes", 30),
            commands.json(["xcrun", "simctl", "list", "devicetypes", "--json"], "page-device-types", 30))
        current.write(evidence / "simulator-pair.json", pair)
        device = current.create_device(commands, pair, "CurrentPage154-" + binding["nonce"], evidence, owned)
        receipt["ownedSimulator"] = device
        builder = build_once if restore_build is None else restore_build
        app_built = builder(commands, "app", device, work, evidence, source)
        ui_built = builder(commands, "ui", device, work, evidence, source)
        if restore_build is not None:
            receipt["retainedBuildAdmission"] = current.read(evidence / "retained-build-admission.json")
        modules["consumer_contract"].framework_unchanged(Path(native["path"]), native["frameworkFiles"])
        receipt["stages"]["preparation"] = run_stage(
            commands, "preparation", device, app_built, app_built["app"], binding, source, evidence)
        setup = receipt["stages"]["preparation"]
        if setup["status"] != "PASS":
            receipt["firstFailure"] = setup.get("firstFailure", {"type": "IncompletePreparation"})
            raise RuntimeError("necessary_fresh_page_fixture_setup_failed")
        receipt["freshSetupActualMethodsPassed"] = 1
        originals = copy_application_receipts(commands, device, evidence, (policy.FIXTURE,), required=True)
        fixture = current.read(Path(originals[policy.FIXTURE]["path"]), 65536)
        modules["mounted_contract"].fixture(fixture, binding)
        built_integrity(app_built)
        receipt["stages"]["ui"] = run_stage(
            commands, "ui", device, ui_built, app_built["app"], binding, source, evidence, fixture=fixture)
        ui = receipt["stages"]["ui"]
        copied = None
        try:
            copied = copy_application_receipts(commands, device, evidence,
                                                (policy.CAPTURE, policy.REOPEN), required=ui["status"] == "PASS")
            receipt["actualApplicationReceipts"] = copied
            capture_copy = copied.get(policy.CAPTURE, {})
            if capture_copy.get("status") == "COPIED_ORIGINAL":
                receipt["nativeBoundaryFiles"] = copy_native_boundary(
                    commands, device, work, evidence,
                    current.read(Path(capture_copy["path"]), 65536), required=ui["status"] == "PASS")
        except BaseException as failure:
            receipt["applicationReceiptFailure"] = current.error(failure)
            if ui["status"] == "PASS":
                raise
        if ui["status"] != "PASS":
            receipt["firstFailure"] = ui.get("firstFailure", {"type": "IncompleteMountedUI"})
            raise RuntimeError("failed_page_journey_remains_unqualified")
        capture_path, reopen_path = (Path(copied[name]["path"]) for name in (policy.CAPTURE, policy.REOPEN))
        capture, reopen = current.read(capture_path, 65536), current.read(reopen_path, 65536)
        receipt["mountedProof"] = modules["mounted_contract"].observations(
            fixture, capture, reopen, c.read(capture_path, 65536), binding)
        boundary_files = receipt["nativeBoundaryFiles"]["files"]
        receipt["nativeBoundaryComparison"] = boundary.verify(
            {role: c.read(Path(row["path"]), boundary.MAXIMUM) for role, row in boundary_files.items()},
            fixture, capture, modules["consumer_contract"], modules["mounted_contract"])
        current.write(evidence / "native-boundary-comparison.json", receipt["nativeBoundaryComparison"])
        receipt["startupAndMountedAttachments"] = policy.mounted_attachments(
            evidence / "ui/private-attachments", device["udid"], capture, reopen, binding, modules["warning_profile"])
        receipt["newUIAcceptance"] = "PASS_ACTUAL_CURRENT_APP_MOUNTED_CANCEL_CREATE_AND_COLD_REOPEN"
        receipt["status"] = "PASS"
    except BaseException as failure:
        primary = failure
        receipt.setdefault("firstFailure", current.error(failure))
        if getattr(failure, "_page_final_receipt_failures", ()):
            receipt["persistenceFailures"] = list(failure._page_final_receipt_failures)
        receipt["status"] = "FAIL"
    finally:
        current._FINALIZING = True
        if commands is not None:
            commands.cleanup_mode = True
            for name, action in (
                ("ownedGroups", lambda: current.unfinished_groups(commands)),
                ("ownedDevices", lambda: current.cleanup_devices(commands, evidence,
                                                                  current.recover_owned(commands, evidence))),
            ):
                try:
                    receipt[name] = action()
                    if name == "ownedDevices":
                        c.require(all(row["owned_simulator_cleanup_status"] == "COMPLETE" for row in receipt[name]),
                                  "page_owned_device_cleanup_incomplete")
                except BaseException as failure:
                    receipt.setdefault("finalizationErrors", []).append({"phase": name, **current.error(failure)})
                    primary = primary or failure
                    receipt.setdefault("firstFailure", current.error(failure))
            try:
                if native is not None:
                    c.require(current.inventory(Path(native["path"])) == native["files"], "page_native_library_changed")
                for built in (app_built, ui_built):
                    if built is not None:
                        receipt.setdefault("finalProducts", {})[built["kind"]] = built_integrity(built)
                current.write(evidence / "loaded-after.json", recheck(source))
                current.write(evidence / "source-after.json", source)
                receipt["finalSourceAndProductsIntegrity"] = "PASS"
            except BaseException as failure:
                receipt.setdefault("finalizationErrors", []).append({"phase": "integrity", **current.error(failure)})
                primary = primary or failure
                receipt.setdefault("firstFailure", current.error(failure))
        if primary is not None or current._CANCELLED:
            receipt["status"] = "FAIL"
        if commands is not None:
            receipt["appBuildsStarted"] = int((commands.root / "page-build-app.started.json").is_file())
            receipt["uiBuildsStarted"] = int((commands.root / "page-build-ui.started.json").is_file())
        recovery = current.inventory_recovery_result(commands)
        if recovery is not None:
            receipt["inventoryRecovery"] = recovery
        receipt["cancelled"] = current._CANCELLED
        persist_final(evidence / "execution.json", receipt, primary)
    return receipt


def cleanup(expected, inventory_policy=None):
    current._FINALIZING = True
    root = root_path()
    if not root.exists():
        return {"status": "NO_CURRENT_CREATION_INTENT"}
    evidence = root / "evidence"
    c.require(root.resolve() == root and evidence.resolve() == evidence, "page_cleanup_owned_path")
    result = {"status": "FAIL", "profile": policy.PROFILE}
    final = evidence / "cleanup-final.json"
    c.require(not final.exists(), "page_cleanup_finalization_replay")
    primary = None
    try:
        c.require(platform.system() == "Darwin" and platform.machine() == "arm64"
                  and os.environ.get("GITHUB_ACTIONS") == "true"
                  and os.environ.get("GITHUB_REPOSITORY") == c.REPOSITORY
                  and expected == os.environ.get("GITHUB_SHA")
                  and current.git("rev-parse", "HEAD").decode().strip() == expected,
                  "page_current_cleanup_identity_required")
        intent_path = evidence / "execution-intent.json"
        if not intent_path.exists():
            c.require(not list(evidence.glob("device-*")) and not list((evidence / "commands").glob("*.started.json")),
                      "page_resources_without_current_intent")
            result["status"] = "NO_CURRENT_CREATION_INTENT"
        else:
            intent = current.read(intent_path)
            context = {"profile": policy.PROFILE, "sourceCommit": expected, "runID": os.environ["GITHUB_RUN_ID"],
                       "runAttempt": os.environ["GITHUB_RUN_ATTEMPT"], "repository": c.REPOSITORY}
            c.require(intent["context"] == context and intent["selectors"] == list(policy.SELECTORS)
                      and intent["sourceAdmissionSHA256"] == current.digest(evidence / "source-before.json"),
                      "page_cleanup_current_source_intent_required")
            source = current.read(evidence / "source-before.json")
            c.require(intent.get("inventoryRecoveryPolicy") == inventory_policy
                      and source.get("inventoryRecoveryPolicy") == inventory_policy, "page_cleanup_inventory_policy_changed")
            recheck(source)
            commands = Commands(evidence, context, helpers(source))
            configure_inventory_recovery(commands, source)
            commands.cleanup_mode = True
            for name, action in (
                ("ownedGroups", lambda: current.unfinished_groups(commands)),
                ("ownedDevices", lambda: current.cleanup_devices(commands, evidence,
                                                                  current.recover_owned(commands, evidence))),
                ("loadedAfter", lambda: recheck(source)),
            ):
                try:
                    result[name] = action()
                    if name == "ownedDevices":
                        c.require(all(row["owned_simulator_cleanup_status"] == "COMPLETE" for row in result[name]),
                                  "page_prior_or_current_cleanup_incomplete")
                except BaseException as failure:
                    result.setdefault("failures", []).append({"phase": name, **current.error(failure)})
                    primary = primary or failure
            recovery = current.inventory_recovery_result(commands)
            if recovery is not None:
                result["inventoryRecovery"] = recovery
            if primary:
                raise primary
            result["status"] = "PASS"
    except BaseException as failure:
        primary = primary if primary is not None else failure
        result["firstFailure"] = current.error(primary)
        if getattr(primary, "_page_final_receipt_failures", ()):
            result["persistenceFailures"] = list(primary._page_final_receipt_failures)
    persist_final(final, result, primary)
    return result


def main(restore_build=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("execute", "cleanup"))
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--inventory-recovery", dest="inventory_policy", choices=(current.INVENTORY_POLICY,))
    args = parser.parse_args()
    os.umask(0o077)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, current.cancel)
    result = (execute(args.expected_source, args.inventory_policy, restore_build) if args.action == "execute"
              else cleanup(args.expected_source, args.inventory_policy))
    print(json.dumps({"status": result["status"], "profile": policy.PROFILE,
                      "evidence": str(root_path() / "evidence")}, sort_keys=True))
    return 0 if result["status"] in ("PASS", "NO_CURRENT_CREATION_INTENT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
