#!/usr/bin/env python3
"""Run the six never-executed Native UI methods from the fixed retained build."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import plistlib
import shutil
import tarfile

import contracts as c
import current_execution as driver
import native_ui_failed as native

INPUTS = Path(__file__).with_name("native-ui-retained-inputs.json")


def original_receipts(root, fixed):
    """Read only the explicitly retained, hash-bound original receipts."""
    c.require(root.is_absolute() and root.resolve() == root and root.is_dir(),
              "fixed_retained_root_missing_or_linked")
    values = {}
    for name, sha in fixed["receipts"].items():
        path = root / "evidence" / name
        c.require(path.resolve() == path, "retained_receipt_path_linked")
        raw = c.read(path)
        c.require(c.sha(raw) == sha, "retained_original_receipt_changed:" + name)
        values[name] = c.strict_json(raw) if name.endswith(".json") else raw
    context = fixed["context"]
    original = values["original-products.json"]
    build = values["build.json"]
    execution = values["execution.json"]
    for value in (original, build, execution):
        c.require(value["context"] == context, "foreign_retained_original_context")
    c.require(execution["status"] == "FAIL" and execution["stages"] == {}
              and execution["applicationBuilds"] == 1 and execution["uiRunnerBuilds"] == 1
              and execution["nativeLibraryBuilds"] == 0 and not execution["fullAcceptance"],
              "original_run_was_not_build_only_provider_failure")
    c.require(execution["integrity"]["products"] == {
                  "complete": True, "originalEntries": fixed["productEntries"], "newDescriptors": {}},
              "original_product_integrity_not_complete")
    c.require(original["phase"] == "AFTER_BUILD_BEFORE_ADMISSION"
              and len(original["files"]) == fixed["productEntries"]
              and original["archive"] == "original-build-products.tar.gz"
              and original["archiveSHA256"] == fixed["archiveSHA256"]
              and original["archiveBytes"] == fixed["archiveBytes"],
              "original_archive_identity_changed")
    c.require(build["applicationBuilds"] == 1 and build["uiRunnerBuilds"] == 1
              and build["nativeBuilds"] == 0
              and build["productsReceiptSHA256"] == fixed["receipts"]["original-products.json"]
              and build["descriptorSHA256"] == c.sha(values["original.xctestrun"]),
              "original_completed_build_receipt_changed")
    return values


def qualify_source_delta(old, current, fixed):
    c.require(old["compiledTrees"] == current["compiledTrees"]
              and old["compiledOrigin"] == current["compiledOrigin"],
              "retained_compiled_sources_changed")
    before, after = old["gitInputs"], current["gitInputs"]
    changed = sorted(name for name in before.keys() | after.keys()
                     if before.get(name) != after.get(name))
    c.require(set(changed).issubset(fixed["allowedHelperDeltaPaths"]),
              "unreviewed_retained_helper_delta:" +
              ",".join(sorted(set(changed) - set(fixed["allowedHelperDeltaPaths"]))))
    for root in old["compiledTrees"]:
        selected = lambda rows: {name: value for name, value in rows.items()
                                 if name == root or name.startswith(root + "/")}
        c.require(selected(before) == selected(after), "original_compiled_inputs_changed:" + root)
    fixture = "Tools/AnyEngineValidation/HanlinProviderFixture/fixture.py"
    c.require(current["files"][fixture]["sha256"] == fixed["fixedTLSFixtureSHA256"],
              "qualified_tls_fixture_required")
    return {name: {"original": before.get(name), "current": after.get(name)}
            for name in changed}


def extract_products(archive, derived, original):
    c.require(not derived.exists(), "fresh_retained_derived_root_required")
    derived.mkdir(mode=0o700)
    expected = {"Build/Products": "directory", "Build/PinkhaSourceInputs.json": "file"}
    expected.update({"Build/Products/" + name: value["kind"]
                     for name, value in original["files"].items()})
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        c.require(len(members) == len(expected), "retained_archive_entry_count_changed")
        seen = set()
        for member in members:
            name = member.name.rstrip("/")
            path = PurePosixPath(name)
            c.require(name and not path.is_absolute() and ".." not in path.parts
                      and name not in seen and name in expected, "unsafe_retained_archive_member")
            seen.add(name)
            kind = ("directory" if member.isdir() else "symlink" if member.issym()
                    else "file" if member.isfile() else None)
            c.require(kind == expected[name] and member.size <= 512 * 1024**2,
                      "retained_archive_member_type_or_bound_changed")
        c.require(seen == set(expected), "retained_archive_member_missing")
        source.extractall(derived, filter="data")
    products = derived / "Build/Products"
    products.chmod(0o700)
    # Python's safe data filter intentionally drops directory permission metadata.
    # Restore only the hash-bound original directory modes before exact inventory.
    for name, value in original["files"].items():
        if value["kind"] == "directory":
            c.require(value["mode"] & ~0o777 == 0, "unsafe_original_directory_mode")
            (products / name).chmod(value["mode"])
    c.require(driver.inventory(products) == original["files"], "restored_products_differ")
    return products


def relocate_package_alternates(packages, original_packages_prefix, original_inventory):
    """Rebind only copied SwiftPM Git alternates after an owned directory move."""
    c.require(packages.resolve() == packages and original_packages_prefix.is_absolute(),
              "owned_package_copy_required")
    c.require(driver.inventory(packages) == original_inventory, "package_copy_not_original")
    changes, expected = {}, dict(original_inventory)
    for name in sorted(original_inventory):
        parts = PurePosixPath(name).parts
        if parts[-3:] != ("objects", "info", "alternates"):
            continue
        c.require(len(parts) == 6 and parts[0] == "checkouts" and parts[2] == ".git"
                  and original_inventory[name]["kind"] == "file",
                  "unreviewed_package_alternates_location")
        path = packages / name
        raw = c.read(path, 16384)
        lines = raw.decode().splitlines()
        c.require(len(lines) == 1, "one_owned_package_object_store_required")
        original = Path(lines[0])
        c.require(original.is_absolute() and original.is_relative_to(original_packages_prefix),
                  "external_original_package_object_store")
        relative = original.relative_to(original_packages_prefix)
        c.require(len(relative.parts) == 3 and relative.parts[0] == "repositories"
                  and relative.parts[2] == "objects" and ".." not in relative.parts,
                  "unexpected_original_package_object_store")
        target = packages / relative
        c.require(target.resolve() == target and target.is_dir(), "copied_package_object_store_missing")
        replacement = (str(target) + "\n").encode()
        mode = original_inventory[name]["mode"]
        path.chmod(mode | 0o200)
        try:
            path.write_bytes(replacement)
        finally:
            path.chmod(mode)
        expected[name] = driver.metadata(path)
        changes[name] = {"originalSHA256": c.sha(raw), "copiedSHA256": c.sha(replacement),
                         "originalObjectStore": str(original), "copiedObjectStore": str(target)}
    c.require(changes, "original_package_alternates_required")
    c.require(driver.inventory(packages) == expected, "package_relocation_changed_other_bytes")
    return changes


def restore_products(commands, profile, device, work, evidence, source):
    c.require(profile == native.PROFILE, "retained_native_profile_only")
    fixed = driver.read(INPUTS)
    c.require(fixed["context"]["repository"] == c.REPOSITORY
              and fixed["context"]["sourceCommit"] != commands.context["sourceCommit"],
              "retained_original_and_controller_identity_required")
    driver.git("merge-base", "--is-ancestor", fixed["context"]["sourceCommit"],
               commands.context["sourceCommit"])
    retained = Path(fixed["retainedRoot"])
    values = original_receipts(retained, fixed)
    delta = qualify_source_delta(values["source-before.json"], source, fixed)
    run = driver.read(commands.run(
        ["gh", "api", "repos/" + c.REPOSITORY + "/actions/runs/" + fixed["context"]["runID"]],
        "retained-original-run", 45))
    artifact = driver.read(commands.run(
        ["gh", "api", "repos/" + c.REPOSITORY + "/actions/artifacts/" + str(fixed["artifact"]["id"])],
        "retained-original-artifact", 45))
    c.require(str(run["id"]) == fixed["context"]["runID"]
              and run["run_attempt"] == int(fixed["context"]["runAttempt"])
              and run["head_sha"] == fixed["context"]["sourceCommit"]
              and run["repository"]["full_name"] == c.REPOSITORY
              and run["status"] == "completed" and run["conclusion"] == "failure"
              and run["event"] == "workflow_dispatch", "original_github_run_identity_changed")
    expected_artifact = fixed["artifact"]
    c.require(artifact["id"] == expected_artifact["id"]
              and artifact["name"] == expected_artifact["name"]
              and artifact["size_in_bytes"] == expected_artifact["bytes"]
              and artifact["digest"] == "sha256:" + expected_artifact["sha256"]
              and artifact["workflow_run"]["id"] == int(fixed["context"]["runID"]),
              "original_github_artifact_identity_changed")
    origin = evidence / "retained-original"
    origin.mkdir(mode=0o700)
    for name in fixed["receipts"]:
        shutil.copyfile(retained / "evidence" / name, origin / name)
        c.require(driver.digest(origin / name) == fixed["receipts"][name],
                  "retained_receipt_copy_changed")
    original = values["original-products.json"]
    archive = retained / "evidence" / original["archive"]
    c.require(archive.resolve() == archive and archive.is_file()
              and archive.stat().st_size == fixed["archiveBytes"]
              and driver.digest(archive) == fixed["archiveSHA256"],
              "retained_products_archive_changed")
    original_derived = retained / "work/derived"
    c.require(driver.inventory(original_derived / "Build/Products") == original["files"],
              "retained_original_products_changed")
    dependency = values["actual-dependencies.json"]
    # Retention preserves the original checkout bytes, including absolute Git
    # alternates that refer to the old workspace. Qualify only the fresh copy.
    packages = original_derived / "SourcePackages"
    packages_before = driver.inventory(packages)
    derived = work / "derived"
    products = extract_products(archive, derived, original)
    source_receipt = driver.read(derived / "Build/PinkhaSourceInputs.json")
    c.require(source_receipt["context"] == fixed["context"]
              and source_receipt["sources"] == values["source-before.json"],
              "archived_build_source_not_original")
    shutil.copytree(packages, derived / "SourcePackages", symlinks=True)
    c.require(driver.inventory(packages) == packages_before
              and driver.inventory(derived / "SourcePackages") == packages_before,
              "dependency_copy_changed")
    original_package_prefix = Path(values["build.json"]["descriptor"]).parents[2] / "SourcePackages"
    relocation = relocate_package_alternates(derived / "SourcePackages", original_package_prefix,
                                            packages_before)
    driver.write(evidence / "retained-package-inventory.json",
                 {"original": packages_before, "copiedAlternatesRelocation": relocation})
    c.require(driver.dependencies(derived) == dependency, "restored_dependencies_changed")
    descriptor = products / Path(values["build.json"]["descriptor"]).name
    c.require(descriptor.parent == products and c.read(descriptor) == values["original.xctestrun"],
              "restored_original_descriptor_changed")
    spec = c.PROFILES[profile]
    app = products / (spec["configuration"] + "-iphonesimulator") / spec["app"]
    c.require(plistlib.loads(c.read(app / "Info.plist"))["CFBundleIdentifier"] == spec["bundle"]
              and driver.code_carriers(app) == values["build.json"]["codeCarriers"],
              "restored_application_identity_changed")
    commands.run(["codesign", "--verify", "--deep", "--strict", str(app)],
                 "verify-retained-signature", 60)
    for name in ("original-products.json", "original.xctestrun", "actual-dependencies.json"):
        shutil.copyfile(origin / name, evidence / name)
    admission = {
        "status": "EXACT_RETAINED_PRODUCTS_ADMITTED", "context": commands.context,
        "originalContext": fixed["context"], "originalRunConclusion": "failure",
        "originalUIExecutions": 0, "originalArtifact": fixed["artifact"],
        "products": {"entries": len(original["files"]), "archiveSHA256": fixed["archiveSHA256"],
                     "receiptSHA256": fixed["receipts"]["original-products.json"]},
        "sourceDelta": delta, "compiledTreesUnchanged": True,
        "dependenciesUnchanged": True, "descriptorUnchanged": True,
        "copiedPackageAlternatesRelocation": relocation,
        "packageInventorySHA256": driver.digest(evidence / "retained-package-inventory.json"),
        "originalBuildResultsRelabeled": False,
        "applicationBuilds": 0, "uiRunnerBuilds": 0, "nativeBuilds": 0,
    }
    driver.write(evidence / "retained-products.json", admission)
    driver.write(evidence / "build.json", {
        "context": commands.context, "descriptor": str(descriptor),
        "descriptorSHA256": driver.digest(descriptor), "app": str(app),
        "codeCarriers": driver.code_carriers(app), "nativeBuilds": 0,
        "applicationBuilds": 0, "uiRunnerBuilds": 0,
        "productsReceiptSHA256": driver.digest(evidence / "original-products.json"),
        "originalBuildContext": fixed["context"],
        "retainedAdmissionSHA256": driver.digest(evidence / "retained-products.json"),
    })
    c.require(driver.inventory(original_derived / "Build/Products") == original["files"]
              and driver.digest(archive) == fixed["archiveSHA256"],
              "retained_original_changed_during_restore")
    return derived, original, descriptor, app, dependency


if __name__ == "__main__":
    raise SystemExit(driver.main(native.PROFILE, native.prepare_library, native.provider,
                                 restore_products=restore_products))
