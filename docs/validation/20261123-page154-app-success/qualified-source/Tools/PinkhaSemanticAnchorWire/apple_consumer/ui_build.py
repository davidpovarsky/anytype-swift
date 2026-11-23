"""Compile and preserve the mounted UI runner without executing its methods."""
from __future__ import annotations

import json
from pathlib import Path
import plistlib
import re
import shutil
import stat

import consumer_contract as proof

ORIGIN = "9d7dbdd68da2e3d48ec84664c50954b9c9ec6762"
SOURCE_PLAN = "Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json"
SOURCE_PLAN_SHA = "19806530ea3f492ff221efac5a5430ec46893fb7066bf5294afaa06a390ad42f"
PREPARATION = "AnytypeTests/SemanticAnchorPage154MountedPreparationTests/testPrepareOwnedPage154MountedFixture"
SELECTOR = "PinkhaStage1AcceptanceUITests/SemanticAnchorPage154MountedUITests/testActualTextSelectionCancelThenCreateAndColdReopen"
BLUEPRINT = "PinkhaStage1AcceptanceUITests"
PROJECT = "PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj"
SCOPE = "semantic-page154-early-products"
STATUS = "BUILD_ONLY_ORIGINAL_PRODUCTS_PRESERVED"


def read_plan(app, inputs):
    path = Path(__file__).parent / "ui-build-plan.json"
    value = json.loads(path.read_bytes())
    proof.require(value.get("schema") == "pinkha-semantic-page154-ui-build-only-v1"
                  and value.get("mounted_source_origin_sha") == ORIGIN
                  and value.get("source_plan_path") == SOURCE_PLAN
                  and value.get("source_plan_sha256") == SOURCE_PLAN_SHA
                  and value.get("preparation_selector") == PREPARATION
                  and value.get("selector") == SELECTOR
                  and value.get("project_path") == PROJECT,
                  "The exact reviewed mounted build-only plan is required")
    source_path = app / SOURCE_PLAN
    proof.require(inputs.get(SOURCE_PLAN) == proof.digest(source_path) == SOURCE_PLAN_SHA,
                  "Mounted source plan differs from its frozen original")
    source = json.loads(source_path.read_bytes())
    proof.require(source.get("selectors") == dict(preparation=PREPARATION, journey=SELECTOR)
                  and source.get("native_manifest_sha256") == proof.MANIFEST_SHA
                  and source.get("producer_run_id") == proof.PRODUCER_RUN
                  and all(inputs.get(name) == row["sha256"] for name, row in source["files"].items()),
                  "Actual mounted App/fixture/UI/project inputs differ")
    expected = value.get("project_files_sha256", {})
    proof.require(set(expected) == {"project.pbxproj", "xcshareddata/xcschemes/PinkhaStage1Acceptance.xcscheme"},
                  "Unexpected original UI project inputs")
    proof.require(project_files(app / PROJECT) == expected
                  and all(inputs.get(PROJECT + "/" + name) == digest for name, digest in expected.items()),
                  "Exact tracked original UI project is required")
    return value


def project_files(root):
    proof.require(root.is_dir() and not root.is_symlink(), "UI project must be a regular owned directory")
    result = {}
    for path in sorted(root.rglob("*")):
        proof.require(not path.is_symlink(), "UI project cannot contain symlink inputs")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = proof.digest(path)
        else:
            proof.require(path.is_dir(), "UI project contains a special input")
    return result


def verify_preserved_products(derived, evidence, preservation, binding, flags, *, descriptor_additions=None):
    """Match all original entries and modes; allow only the exact new bound plist."""
    additions = descriptor_additions or {}
    proof.require(len(additions) <= 1 and all(
        re.fullmatch(r"Build/Products/Page154-[0-9a-f]{32}\.xctestrun", name)
        and re.fullmatch(r"[0-9a-f]{64}", digest) for name, digest in additions.items()),
        "Only the exact consumer-bound descriptor may be added to native Products")
    manifest_name = preservation["manifest_path"]; archive_name = preservation["archive_path"]
    prefixes = (SCOPE, "ui-runner/" + SCOPE)
    prefix = next((item for item in prefixes if manifest_name == item + "/manifest.json"), None)
    proof.require(prefix is not None and archive_name == prefix + "/BuildProducts.tar.gz",
                  "Unexpected preserved Products evidence paths")
    manifest_path, archive_path = evidence / manifest_name, evidence / archive_name
    proof.require(proof.digest(manifest_path) == preservation["manifest_sha256"],
                  "Original product manifest changed")
    manifest = json.loads(manifest_path.read_bytes())
    proof.require(manifest.get("status") == "OBSERVED_PRODUCTS_ARCHIVED_BEFORE_ADMISSION"
                  and manifest.get("capture_phase") == "AFTER_BUILD_BEFORE_ADMISSION"
                  and manifest.get("source_sha") == binding["sourceSHA"]
                  and manifest.get("run_id") == binding["runID"]
                  and manifest.get("run_attempt") == binding["runAttempt"]
                  and manifest.get("build_flags") == list(flags)
                  and manifest.get("archive_path") == SCOPE + "/BuildProducts.tar.gz"
                  and manifest.get("archive_sha256") == preservation["archive_sha256"]
                  and manifest.get("archive_bytes") == preservation["archive_bytes"]
                  and archive_path.stat().st_size == preservation["archive_bytes"]
                  and proof.digest(archive_path) == preservation["archive_sha256"],
                  "Original product build/archive identity differs")
    expected = manifest.get("products", {})
    proof.require(isinstance(expected, dict) and 0 < len(expected) <= 20_000
                  and len(expected) == preservation["entries"], "Invalid original product entry count")
    products = derived / "Build/Products"
    proof.require(products.is_dir() and not products.is_symlink(), "Original Products root changed")
    paths = [products, *sorted(products.rglob("*"))]
    source_inputs = derived / "Build/PinkhaSourceInputs.json"
    if source_inputs.exists() or source_inputs.is_symlink():
        paths.append(source_inputs)
    actual = {path.relative_to(derived).as_posix(): path for path in paths}
    proof.require(set(actual) == set(expected) | set(additions) and not set(expected).intersection(additions),
                  "Original Products gained, lost or replaced an entry")
    for name, row in expected.items():
        proof.relative(name)
        proof.require(name == "Build/PinkhaSourceInputs.json" or name == "Build/Products"
                      or name.startswith("Build/Products/"), "Original entry escaped Products")
        path = actual[name]; info = path.lstat()
        proof.require(stat.S_IMODE(info.st_mode) == row["mode"], "Original product mode changed: " + name)
        if row["kind"] == "directory":
            proof.require(stat.S_ISDIR(info.st_mode), "Original product directory changed")
        elif row["kind"] == "file":
            proof.require(stat.S_ISREG(info.st_mode) and info.st_size == row["bytes"]
                          and proof.digest(path) == row["sha256"], "Original product bytes changed: " + name)
        elif row["kind"] == "symlink":
            proof.require(stat.S_ISLNK(info.st_mode) and path.readlink().as_posix() == row["target"],
                          "Original product symlink changed")
        else:
            proof.require(False, "Unreviewed hardlink or special product requires separate admission")
    for name, expected_sha in additions.items():
        proof.require(proof.digest(actual[name]) == expected_sha, "Bound descriptor changed")
    return dict(status="ALL_ORIGINAL_PRODUCT_ENTRIES_UNCHANGED", entries=len(expected),
                manifest_sha256=preservation["manifest_sha256"], archive_sha256=preservation["archive_sha256"],
                exact_added_descriptors=additions, build_reuse_admission="SEPARATE_REVIEW_REQUIRED")


def descriptor_summary(path, products):
    raw = plistlib.loads(path.read_bytes())
    version = raw.get("__xctestrun_metadata__", {}).get("FormatVersion")
    if version == 1:
        candidates = [value for key, value in raw.items() if not key.startswith("__")]
    else:
        proof.require(version == 2 and len(raw.get("TestConfigurations", [])) == 1,
                      "Unexpected original UI descriptor format")
        candidates = raw["TestConfigurations"][0].get("TestTargets", [])
    proof.require(len(candidates) == 1 and isinstance(candidates[0], dict)
                  and candidates[0].get("BlueprintName") == BLUEPRINT
                  and candidates[0].get("IsUITestBundle") is True,
                  "Original descriptor must contain exactly the compiled UI target")
    target = candidates[0]
    host = target.get("TestHostPath", "")
    proof.require(host.startswith("__TESTROOT__/Debug-Anytype-iphonesimulator/")
                  and target.get("TestBundlePath") == "__TESTHOST__/PlugIns/" + BLUEPRINT + ".xctest",
                  "Original UI runner/test bundle paths differ")
    app = products / proof.relative(host.removeprefix("__TESTROOT__/"))
    binary = app / "PlugIns" / (BLUEPRINT + ".xctest") / BLUEPRINT
    proof.require(app.is_dir() and not app.is_symlink() and binary.is_file()
                  and not binary.is_symlink() and stat.S_IMODE(binary.stat().st_mode) & 0o111,
                  "Actual compiled UI test executable is missing")
    return dict(format_version=version, blueprint=BLUEPRINT,
                test_host_path=host, test_bundle_path=target["TestBundlePath"],
                executable_sha256=proof.digest(binary))


def build_mounted_ui(runner, app, work, evidence, binding, flags, plan, shared, receipt, udid):
    import early_build_products
    detail = dict(status="NOT_RUN", configuration="Debug-Anytype", scheme="PinkhaPrebuiltUI",
                  blueprint=BLUEPRINT, selector=SELECTOR, preparation_selector=PREPARATION,
                  mounted_source_origin_sha=ORIGIN, source_plan_sha256=SOURCE_PLAN_SHA,
                  build_flags=list(flags), preparation_executions=0, ui_executions=0, acceptance="NOT_RUN")
    receipt["ui_runner_build"] = detail
    destination = evidence / "ui-runner"; destination.mkdir(parents=True, exist_ok=False)
    derived = work / "derived-ui"
    proof.require(not derived.exists(), "UI runner needs a distinct fresh derived directory")
    try:
        proof.require(project_files(app / PROJECT) == plan["project_files_sha256"],
                      "Original UI project changed before the build")
        generated = shared.ui_only_project(app)
        generated_inputs = project_files(generated)
        proof.require(set(generated_inputs) == {"project.pbxproj", "xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme"},
                      "Unexpected UI-only generated project")
        detail.update(generated_project=generated.relative_to(app).as_posix(),
                      generated_project_files_sha256=generated_inputs,
                      original_project_files_sha256=plan["project_files_sha256"], builds_started=1)
        proof.save(evidence / "execution.json", receipt)
        runner.run(["xcodebuild", "build-for-testing", "-project", str(generated), "-scheme", "PinkhaPrebuiltUI",
                    "-configuration", "Debug-Anytype", "-destination", "platform=iOS Simulator,id=" + udid,
                    "-parallel-testing-enabled", "NO", "-derivedDataPath", str(derived),
                    "-only-testing:" + SELECTOR, *flags], "build-mounted-ui-runner", 1200)
        detail["builds_succeeded"] = 1
        preservation = early_build_products.capture(derived, destination, source_sha=binding["sourceSHA"],
            run_id=binding["runID"], run_attempt=binding["runAttempt"], build_flags=flags, scope="semantic-page154")
        detail["early_products"] = {**preservation,
            "archive_path": "ui-runner/" + preservation["archive_path"],
            "manifest_path": "ui-runner/" + preservation["manifest_path"]}
        proof.save(evidence / "execution.json", receipt)
        proof.require(project_files(app / PROJECT) == plan["project_files_sha256"]
                      and all(proof.digest(generated / name) == digest for name, digest in generated_inputs.items()),
                      "Original or generated UI build project changed")
        original = shared.test_configuration(derived / "Build/Products", BLUEPRINT)
        detail["descriptor"] = descriptor_summary(original, derived / "Build/Products")
        shutil.copyfile(original, destination / "original.xctestrun")
        detail["original_xctestrun"] = dict(path="ui-runner/original.xctestrun",
            products_path=original.relative_to(derived).as_posix(), sha256=proof.digest(original))
        detail["product_integrity"] = verify_preserved_products(
            derived, evidence, detail["early_products"], binding, flags)
        detail["status"] = STATUS
    except BaseException as error:
        detail.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        proof.save(destination / "build-only.json", detail)
        proof.save(evidence / "execution.json", receipt)
    return detail
