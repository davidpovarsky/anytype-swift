#!/usr/bin/env python3
"""Execute the exact unresolved Release Return3/RTL scope from retained Products."""
from __future__ import annotations
from pathlib import Path
import plistlib
import shutil

import contracts as c
import current_execution as driver
import native_ui_retained as retained
import release_return_rtl as release

INPUTS = Path(__file__).with_name("release-retained-inputs.json")


def original_receipts(root, fixed):
    c.require(root.is_absolute() and root.resolve() == root and root.is_dir(),
              "fixed_retained_release_root_required")
    values = {}
    for name, expected in fixed["receipts"].items():
        path = root / "evidence" / name
        raw = c.read(path)
        c.require(path.resolve() == path and c.sha(raw) == expected,
                  "retained_release_receipt_changed:" + name)
        values[name] = c.strict_json(raw) if name.endswith(".json") else raw
    context = fixed["context"]
    original, execution, build = (values[n] for n in ("original-products.json", "execution.json", "build.json"))
    c.require(all(row["context"] == context for row in (original, execution, build))
              and context["profile"] == release.PROFILE, "retained_release_original_context_changed")
    c.require(execution["status"] == "FAIL" and not execution["fullAcceptance"]
              and execution["applicationBuilds"] == 1 and execution["uiRunnerBuilds"] == 0
              and execution["nativeLibraryBuilds"] == 0
              and set(execution["stages"]) == {"return-controls", "preparation"},
              "retained_release_original_scope_changed")
    for name, stage in execution["stages"].items():
        c.require(stage["status"] == "FAIL" and stage["testCommandInvoked"] is False
                  and stage["firstFailure"] == {
                      "message": "Compiled enumeration selected zero tests", "type": "ValueError"},
                  "retained_release_original_stage_was_not_zero_enumeration:" + name)
    c.require(not execution["groups"] and len(execution["simulatorCleanup"]) == 2
              and all(item["owned_simulator_cleanup_status"] == "COMPLETE"
                      and item["owned_simulator_cleanup"]["delete"]["status"] == "PASS_EXIT_0"
                      for item in execution["simulatorCleanup"]), "original_release_cleanup_incomplete")
    c.require(original["phase"] == "AFTER_BUILD_BEFORE_ADMISSION"
              and len(original["files"]) == fixed["productEntries"]
              and original["archiveSHA256"] == fixed["archiveSHA256"]
              and original["archiveBytes"] == fixed["archiveBytes"]
              and build["applicationBuilds"] == 1 and build["uiRunnerBuilds"] == 0
              and build["nativeBuilds"] == 0
              and build["descriptorSHA256"] == c.sha(values["original.xctestrun"])
              and build["productsReceiptSHA256"] == fixed["receipts"]["original-products.json"],
              "original_completed_release_build_receipt_changed")
    return values


def source_delta(original, source, fixed):
    c.require(original["compiledTrees"] == source["compiledTrees"]
              and original["compiledOrigin"] == source["compiledOrigin"],
              "retained_release_compiled_sources_changed")
    before, after = original["gitInputs"], source["gitInputs"]
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    c.require(set(changed).issubset(fixed["allowedHelperDeltaPaths"]),
              "unreviewed_retained_release_helper_delta:" +
              ",".join(sorted(set(changed) - set(fixed["allowedHelperDeltaPaths"]))))
    for root in original["compiledTrees"]:
        select = lambda rows: {n: v for n, v in rows.items() if n == root or n.startswith(root + "/")}
        c.require(select(before) == select(after), "retained_release_compiled_input_changed:" + root)
    return {name: {"original": before.get(name), "current": after.get(name)} for name in changed}


def restore_products(commands, profile, device, work, evidence, source):
    c.require(profile == release.PROFILE, "retained_release_profile_only")
    fixed = driver.read(INPUTS)
    driver.git("merge-base", "--is-ancestor", fixed["context"]["sourceCommit"], commands.context["sourceCommit"])
    root = Path(fixed["retainedRoot"])
    values = original_receipts(root, fixed)
    delta = source_delta(values["source-before.json"], source, fixed)
    run = driver.read(commands.run(["gh", "api", "repos/" + c.REPOSITORY + "/actions/runs/" +
                                   fixed["context"]["runID"]], "retained-release-run", 45))
    artifact = driver.read(commands.run(["gh", "api", "repos/" + c.REPOSITORY + "/actions/artifacts/" +
                                        str(fixed["artifact"]["id"])], "retained-release-artifact", 45))
    context, expected_artifact = fixed["context"], fixed["artifact"]
    c.require(str(run["id"]) == context["runID"] and str(run["run_attempt"]) == context["runAttempt"]
              and run["head_sha"] == context["sourceCommit"]
              and run["repository"]["full_name"] == c.REPOSITORY and run["status"] == "completed"
              and run["conclusion"] == "failure" and run["event"] == "workflow_dispatch",
              "retained_release_github_run_changed")
    c.require(artifact["id"] == expected_artifact["id"] and artifact["name"] == expected_artifact["name"]
              and artifact["size_in_bytes"] == expected_artifact["bytes"]
              and artifact["digest"] == "sha256:" + expected_artifact["sha256"]
              and artifact["workflow_run"]["id"] == int(context["runID"]),
              "retained_release_github_artifact_changed")
    original, execution = values["original-products.json"], values["execution.json"]
    archive = root / "evidence/original-build-products.tar.gz"
    c.require(archive.resolve() == archive and archive.is_file()
              and archive.stat().st_size == fixed["archiveBytes"]
              and driver.digest(archive) == fixed["archiveSHA256"], "retained_release_archive_changed")
    old_derived = root / "work/derived"
    old_expected = {**original["files"], **execution["integrity"]["products"]["newDescriptors"]}
    c.require(driver.inventory(old_derived / "Build/Products") == old_expected,
              "original_release_products_changed")
    derived = work / "derived"
    products = retained.extract_products(archive, derived, original)
    archived = driver.read(derived / "Build/PinkhaSourceInputs.json")
    c.require(archived["context"] == context and archived["sources"] == values["source-before.json"],
              "retained_release_archived_source_changed")
    package_files = driver.inventory(old_derived / "SourcePackages")
    shutil.copytree(old_derived / "SourcePackages", derived / "SourcePackages", symlinks=True)
    prefix = Path(values["build.json"]["descriptor"]).parents[2] / "SourcePackages"
    relocation = retained.relocate_package_alternates(derived / "SourcePackages", prefix, package_files)
    c.require(driver.inventory(old_derived / "SourcePackages") == package_files,
              "original_release_dependencies_changed")
    dependency = driver.dependencies(derived)
    c.require(dependency == values["actual-dependencies.json"], "restored_release_dependencies_changed")
    driver.write(evidence / "retained-package-inventory.json",
                 {"original": package_files, "copiedAlternatesRelocation": relocation})
    descriptor = products / Path(values["build.json"]["descriptor"]).name
    c.require(c.read(descriptor) == values["original.xctestrun"], "original_release_descriptor_changed")
    spec = c.PROFILES[profile]
    app = products / (spec["configuration"] + "-iphonesimulator") / spec["app"]
    c.require(plistlib.loads(c.read(app / "Info.plist"))["CFBundleIdentifier"] == spec["bundle"]
              and driver.code_carriers(app) == values["build.json"]["codeCarriers"],
              "original_release_application_identity_changed")
    commands.run(["codesign", "--verify", "--deep", "--strict", str(app)], "retained-release-signature", 60)
    origin = evidence / "retained-original"
    origin.mkdir(mode=0o700)
    for name, expected in fixed["receipts"].items():
        shutil.copyfile(root / "evidence" / name, origin / name)
        c.require(driver.digest(origin / name) == expected, "retained_release_receipt_copy_changed")
    for name in ("original-products.json", "original.xctestrun", "actual-dependencies.json"):
        shutil.copyfile(origin / name, evidence / name)
    driver.write(evidence / "retained-products.json", {
        "status": "EXACT_RETAINED_RELEASE_PRODUCTS_ADMITTED", "context": commands.context,
        "originalContext": context, "originalArtifact": fixed["artifact"],
        "originalWorkflowConclusion": "failure", "originalTestExecutions": 0,
        "originalResultsRelabeled": False, "compiledTreesUnchanged": True, "sourceDelta": delta,
        "exactSwiftTestingIdentifiers": {stage: c.selected_identifiers(profile, stage)
                                        for stage in spec["stages"]},
        "products": {"entries": len(original["files"]), "archiveSHA256": fixed["archiveSHA256"]},
        "copiedPackageAlternatesRelocation": relocation, "applicationBuilds": 0,
        "uiRunnerBuilds": 0, "nativeBuilds": 0})
    driver.write(evidence / "build.json", {
        "context": commands.context, "descriptor": str(descriptor),
        "descriptorSHA256": driver.digest(descriptor), "app": str(app),
        "codeCarriers": driver.code_carriers(app), "nativeBuilds": 0,
        "applicationBuilds": 0, "uiRunnerBuilds": 0,
        "productsReceiptSHA256": driver.digest(evidence / "original-products.json"),
        "originalBuildContext": context,
        "retainedAdmissionSHA256": driver.digest(evidence / "retained-products.json")})
    c.require(driver.inventory(old_derived / "Build/Products") == old_expected,
              "retained_release_original_changed_during_restore")
    return derived, original, descriptor, app, dependency


if __name__ == "__main__":
    raise SystemExit(driver.main(release.PROFILE, release.prepare_library, release.provider,
                                 restore_products=restore_products))
