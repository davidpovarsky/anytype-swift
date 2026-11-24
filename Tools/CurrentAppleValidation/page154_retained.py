#!/usr/bin/env python3
"""Continue Page154 from the one fixed original App/UI build and exact UI delta."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import hashlib
import plistlib
import shutil
import sys
import tarfile
import zipfile

import contracts as c
import current_execution as current
import native_ui_retained as retained
import page154_contract as policy
import page154_current as page

INPUTS = Path(__file__).with_name("page154-retained-inputs.json")
UI_INPUTS = Path(__file__).with_name("page154-retained-ui-products.json")


def original_receipts(root, fixed):
    c.require(root.is_absolute() and root.resolve() == root and root.is_dir(),
              "fixed_retained_page_root_missing_or_linked")
    values = {}
    for name, row in fixed["members"].items():
        path = root / "evidence" / name
        c.require(path.resolve() == path and path.is_file()
                  and path.stat().st_size == row["bytes"]
                  and current.digest(path) == row["sha256"], "retained_page_member_changed:" + name)
        if name.endswith((".json", ".xctestrun")):
            raw = c.read(path, 16 * 1024**2)
            values[name] = c.strict_json(raw) if name.endswith(".json") else raw
    context = fixed["context"]
    execution = values["execution.json"]
    c.require(execution["context"] == context and execution["status"] == "FAIL"
              and execution["firstFailure"] == {
                  "message": "page_ui_generated_inputs_changed_during_preservation", "type": "ValueError"}
              and execution["stages"] == {} and execution["appBuildsStarted"] == 1
              and execution["uiBuildsStarted"] == 1 and execution["nativeBuilds"] == 0
              and execution["newUIAcceptance"] == "NOT_RUN",
              "original_page_failure_or_execution_scope_changed")
    for kind, selector in (("app", policy.PREPARATION), ("ui", policy.JOURNEY)):
        command = values["commands/page-build-" + kind + ".command.json"]
        c.require(command["context"] == context and command["status"] == "PASS"
                  and command["returnCode"] == 0
                  and command["kernelObservation"]["outcome"] == "ABSENT_ESRCH"
                  and command["argv"][:2] == ["xcodebuild", "build-for-testing"]
                  and [x for x in command["argv"] if x.startswith("-only-testing:")]
                  == ["-only-testing:" + selector], "actual_original_page_build_not_pass:" + kind)
    original = values["app-build/original-products.json"]
    build = values["app-build/build.json"]
    c.require(original["context"] == context and build["context"] == context
              and original["phase"] == "AFTER_BUILD_BEFORE_ADMISSION"
              and len(original["files"]) == 5006
              and original["archiveSHA256"] == fixed["members"]["app-build/original-build-products.tar.gz"]["sha256"]
              and build["originalDescriptorSHA256"] == c.sha(values["app-build/original.xctestrun"])
              and build["originalProductsReceiptSHA256"] == fixed["members"]["app-build/original-products.json"]["sha256"]
              and build["applicationBuilds"] == 1 and build["uiRunnerBuilds"] == 0,
              "original_page_app_receipt_changed")
    for name in ("ui-build/original-products.json", "ui-build/build.json"):
        c.require(not (root / "evidence" / name).exists(), "original_incomplete_ui_receipt_was_replaced")
    return values


def qualify_source_delta(old, source, fixed):
    c.require(old["compiledTrees"] == source["compiledTrees"]
              and old.get("compiledSourceTreeOrigin") == source.get("compiledSourceTreeOrigin")
              and old["projectionOrigins"] == source["projectionOrigins"], "retained_page_compiled_sources_changed")
    before, after = old["gitInputs"], source["gitInputs"]
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    c.require(set(changed).issubset(fixed["allowedHelperDeltaPaths"]),
              "unreviewed_retained_page_helper_delta:" +
              ",".join(sorted(set(changed) - set(fixed["allowedHelperDeltaPaths"]))))
    for root in old["compiledTrees"]:
        select = lambda rows: {name: row for name, row in rows.items()
                               if name == root or name.startswith(root + "/")}
        c.require(select(before) == select(after), "original_page_compiled_input_changed:" + root)
    return {name: {"original": before.get(name), "current": after.get(name)} for name in changed}


def generated_inventory(original, observed):
    prefix = "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj/"
    additions = {prefix + name: {"kind": "directory", "mode": 0o777}
                 for name in page.GENERATED_WORKSPACE_DIRECTORIES}
    c.require(len(original) == 19 and not (original.keys() & additions.keys())
              and observed == {**original, **additions}, "page_generated_delta_is_not_exact_four_empty_directories")
    return additions


def qualify_uploaded_artifact(fixed):
    path = Path(fixed["uploadedArtifactPath"])
    c.require(path.resolve() == path and path.is_file()
              and path.stat().st_size == fixed["artifact"]["bytes"]
              and current.digest(path) == fixed["artifact"]["sha256"], "original_uploaded_page_artifact_changed")
    with zipfile.ZipFile(path) as packed:
        c.require(len(packed.namelist()) == len(set(packed.namelist())), "duplicate_original_page_artifact_member")
        for name, row in fixed["members"].items():
            item = packed.getinfo(row["artifactMember"])
            c.require(item.file_size == row["bytes"], "original_page_artifact_member_size_changed:" + name)
            digest = hashlib.sha256()
            with packed.open(item) as stream:
                for chunk in iter(lambda: stream.read(1024**2), b""):
                    digest.update(chunk)
            c.require(digest.hexdigest() == row["sha256"], "original_page_artifact_member_changed:" + name)


def extract_ui(archive, derived, original, generated):
    c.require(not derived.exists(), "fresh_retained_page_ui_root_required")
    derived.mkdir(mode=0o700)
    expected = {"Build/Products": "directory", "Build/PinkhaSourceInputs.json": "file",
                "Source/UI": "directory"}
    expected.update({"Build/Products/" + n: r["kind"] for n, r in original.items()})
    expected.update({"Source/UI/" + n: r["kind"] for n, r in generated.items()})
    with tarfile.open(archive, "r:gz") as packed:
        members = packed.getmembers()
        c.require(len(members) == len(expected), "retained_page_ui_archive_count_changed")
        seen = set()
        for member in members:
            name = member.name.rstrip("/")
            path = PurePosixPath(name)
            kind = ("directory" if member.isdir() else "symlink" if member.issym()
                    else "file" if member.isfile() else None)
            c.require(name in expected and name not in seen and not path.is_absolute()
                      and ".." not in path.parts and kind == expected[name]
                      and member.size <= 512 * 1024**2, "unsafe_retained_page_ui_archive_member")
            seen.add(name)
        c.require(seen == set(expected), "retained_page_ui_archive_member_missing")
        packed.extractall(derived, filter="data")
    products, ui_source = derived / "Build/Products", derived / "Source/UI"
    for root, inventory in ((products, original), (ui_source, generated)):
        root.chmod(0o700)
        for name, row in inventory.items():
            if row["kind"] == "directory":
                c.require(row["mode"] & ~0o777 == 0, "unsafe_retained_page_directory_mode")
                (root / name).chmod(row["mode"])
        c.require(current.inventory(root) == inventory, "retained_page_ui_extraction_changed")
    return products, ui_source


def qualify_github(commands, fixed):
    run = commands.json(["gh", "api", "repos/" + c.REPOSITORY + "/actions/runs/" +
                         fixed["context"]["runID"]], "page-retained-original-run", 45)
    artifact = commands.json(["gh", "api", "repos/" + c.REPOSITORY + "/actions/artifacts/" +
                              str(fixed["artifact"]["id"])], "page-retained-original-artifact", 45)
    context, expected = fixed["context"], fixed["artifact"]
    c.require(str(run["id"]) == context["runID"] and str(run["run_attempt"]) == context["runAttempt"]
              and run["head_sha"] == context["sourceCommit"] and run["repository"]["full_name"] == c.REPOSITORY
              and run["status"] == "completed" and run["conclusion"] == "failure"
              and run["event"] == "workflow_dispatch", "original_page_run_identity_changed")
    c.require(artifact["id"] == expected["id"] and artifact["name"] == expected["name"]
              and artifact["size_in_bytes"] == expected["bytes"]
              and artifact["digest"] == "sha256:" + expected["sha256"]
              and artifact["workflow_run"]["id"] == int(context["runID"]),
              "original_page_artifact_identity_changed")


def restore_build(commands, kind, device, work, evidence, source):
    c.require(kind in ("app", "ui"), "exact_retained_page_build_kind")
    fixed = current.read(INPUTS)
    c.require(fixed["context"]["profile"] == policy.PROFILE
              and fixed["context"]["sourceCommit"] != commands.context["sourceCommit"],
              "retained_page_original_and_current_context_required")
    current.git("merge-base", "--is-ancestor", fixed["context"]["sourceCommit"], commands.context["sourceCommit"])
    root = Path(fixed["retainedRoot"])
    values = original_receipts(root, fixed)
    delta = qualify_source_delta(values["source-before.json"], source, fixed)
    old_native, now_native = values["native-runtime.json"], current.read(evidence / "native-runtime.json")
    c.require({k: v for k, v in old_native.items() if k != "path"}
              == {k: v for k, v in now_native.items() if k != "path"}, "retained_page_native_runtime_changed")
    c.require(current.digest(UI_INPUTS) == fixed["uiInventorySHA256"], "retained_page_ui_inventory_changed")
    ui = current.read(UI_INPUTS)
    c.require(ui["originalRunID"] == fixed["context"]["runID"]
              and ui["originalSource"] == fixed["context"]["sourceCommit"]
              and ui["originalControllerUIReceiptMissing"] is True, "retained_page_ui_reconstruction_identity")
    additions = generated_inventory(values["ui-build/generated-ui-inputs.json"]["files"], ui["generatedSourceFiles"])
    origin = evidence / "retained-original"
    if kind == "app":
        c.require(c.read(commands.run(["xcodebuild", "-version"], "page-retained-xcode", 30)).decode().strip()
                  == "Xcode 27.0\nBuild version 27A266a", "retained_page_exact_xcode_required")
        qualify_github(commands, fixed)
        qualify_uploaded_artifact(fixed)
        origin.mkdir(mode=0o700)
        for name, row in fixed["members"].items():
            if name.endswith((".json", ".xctestrun")):
                target = origin / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / "evidence" / name, target)
                c.require(current.digest(target) == row["sha256"], "retained_page_receipt_copy_changed")
    else:
        c.require((evidence / "app-build/build.json").is_file(), "retained_page_app_admission_required")
    directory = evidence / (kind + "-build")
    directory.mkdir(mode=0o700)
    archive = root / "evidence" / (kind + "-build/original-build-products.tar.gz")
    old_derived, derived = root / "work" / (kind + "-derived"), work / (kind + "-derived")
    dependency = generated = app = None
    relocation = {}
    if kind == "app":
        original = values["app-build/original-products.json"]
        c.require(current.inventory(old_derived / "Build/Products") == original["files"], "original_page_app_products_changed")
        products = retained.extract_products(archive, derived, original)
        packages = old_derived / "SourcePackages"
        package_files = current.inventory(packages)
        shutil.copytree(packages, derived / "SourcePackages", symlinks=True)
        argv = values["commands/page-build-app.command.json"]["argv"]
        original_prefix = Path(argv[argv.index("-derivedDataPath") + 1]) / "SourcePackages"
        relocation = retained.relocate_package_alternates(derived / "SourcePackages", original_prefix, package_files)
        c.require(len(relocation) == ui["appDependencyAlternates"] == 46
                  and current.inventory(packages) == package_files, "retained_page_dependency_relocation_changed")
        dependency = current.dependencies(derived)
        c.require(dependency == values["app-build/actual-dependencies.json"], "retained_page_dependencies_changed")
        current.write(directory / "package-copy.json", {"original": package_files, "alternatesRelocation": relocation})
        app = products / (policy.CONFIGURATION + "-iphonesimulator") / policy.APP_NAME
        c.require(plistlib.loads(c.read(app / "Info.plist"))["CFBundleIdentifier"] == policy.BUNDLE
                  and current.code_carriers(app) == values["app-build/build.json"]["codeCarriers"],
                  "retained_page_app_identity_changed")
        commands.run(["codesign", "--verify", "--deep", "--strict", str(app)], "page-retained-app-signature", 60)
        for name in ("original-products.json", "actual-dependencies.json"):
            shutil.copyfile(origin / "app-build" / name, directory / name)
    else:
        c.require(current.inventory(old_derived / "Build/Products") == ui["files"], "original_page_ui_products_changed")
        c.require(current.inventory(root / "work/ui-source") == ui["generatedSourceFiles"], "original_page_ui_source_changed")
        products, ui_source = extract_ui(archive, derived, ui["files"], ui["generatedSourceFiles"])
        checked = commands.helpers["warning_profile"].generated_project(
            ui_source, ui_source / "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj",
            current.read(page.INPUTS)["uiPlan"])
        c.require(checked == values["ui-build/generated-ui-inputs.json"]["validatedInputs"],
                  "retained_page_ui_plan_changed")
        generated = {**values["ui-build/generated-ui-inputs.json"], "root": str(ui_source),
                     "files": ui["generatedSourceFiles"], "qualifiedEmptyDirectoryAdditions": additions}
        original = {"context": fixed["context"], "files": ui["files"],
                    "phase": "RECONSTRUCTED_FROM_VERIFIED_ORIGINAL_UPLOADED_ARCHIVE",
                    "originalControllerUIReceiptMissing": True, "archive": str(archive),
                    "archiveSHA256": ui["archiveSHA256"], "generatedSources": generated}
        c.require(current.digest(derived / "Build/PinkhaSourceInputs.json") == ui["archivedSourceInputSHA256"],
                  "retained_page_ui_archived_source_receipt_changed")
        current.write(directory / "original-products.json", original)
        runner = products / (policy.CONFIGURATION + "-iphonesimulator") / (policy.UI_TARGET + "-Runner.app")
        commands.run(["codesign", "--verify", "--deep", "--strict", str(runner)], "page-retained-ui-signature", 60)
    archived = current.read(derived / "Build/PinkhaSourceInputs.json")
    c.require(archived["context"] == fixed["context"] and archived["sources"] == values["source-before.json"]
              and archived["nativeManifest"] == policy.NATIVE_MANIFEST,
              "retained_page_archived_source_receipt_changed")
    descriptors = list(products.glob("*.xctestrun"))
    c.require(len(descriptors) == 1, "one_retained_page_original_descriptor_required")
    descriptor = descriptors[0]
    if kind == "app":
        c.require(c.read(descriptor) == values["app-build/original.xctestrun"], "original_page_app_descriptor_changed")
    else:
        c.require(descriptor.name == ui["descriptor"] and current.digest(descriptor) == ui["descriptorSHA256"],
                  "original_page_ui_descriptor_changed")
        commands.helpers["warning_profile"].same_job_descriptor(c.read(descriptor))
    shutil.copyfile(descriptor, directory / "original.xctestrun")
    page.recheck(source)
    current.write(directory / "build.json", {"context": commands.context, "kind": kind,
                  "originalContext": fixed["context"], "originalBuildConclusion": "PASS",
                  "originalControllerConclusion": "FAIL", "originalResultsRelabeled": False,
                  "originalDescriptorSHA256": current.digest(descriptor),
                  "originalProductsReceiptSHA256": current.digest(directory / "original-products.json"),
                  "codeCarriers": current.code_carriers(app) if app is not None else None,
                  "applicationBuilds": 0, "uiRunnerBuilds": 0, "nativeBuilds": 0})
    if kind == "ui":
        current.write(evidence / "retained-build-admission.json", {
            "status": "EXACT_RETAINED_PAGE_APP_UI_ADMITTED", "context": commands.context,
            "originalContext": fixed["context"], "originalArtifact": fixed["artifact"],
            "originalControllerConclusion": "FAIL", "originalUIExecutions": 0,
            "originalUIControllerReceiptMissing": True, "originalResultsRelabeled": False,
            "compiledTreesUnchanged": True, "projectionOriginsUnchanged": True,
            "sourceDelta": delta, "originalGeneratedEntries": 19,
            "qualifiedEmptyDirectoryAdditions": additions, "appProductEntries": 5006,
            "uiProductEntries": len(ui["files"]), "applicationBuilds": 0,
            "uiRunnerBuilds": 0, "nativeBuilds": 0})
    return {"kind": kind, "derived": derived, "products": products, "original": original,
            "descriptor": descriptor, "app": app, "dependency": dependency,
            "generated": generated, "copies": {}}


if __name__ == "__main__":
    raise SystemExit(page.main(restore_build=restore_build))
