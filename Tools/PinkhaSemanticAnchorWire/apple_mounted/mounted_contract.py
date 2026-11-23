"""Strict admission and evidence checks for the separate mounted Page154 lane."""
from __future__ import annotations
import base64
import copy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import shutil
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "apple_consumer"))
import consumer_contract as native

PREP = "AnytypeTests/SemanticAnchorPage154MountedPreparationTests/testPrepareOwnedPage154MountedFixture"
UI = "PinkhaStage1AcceptanceUITests/SemanticAnchorPage154MountedUITests/testActualTextSelectionCancelThenCreateAndColdReopen"
PROTOCOL = "pinkha-semantic-page154-mounted-v1"
PASS = "PASS_ACTUAL_MOUNTED_CANCEL_CREATE_AND_COLD_REOPEN"
MAX_ARCHIVE = 4 * 1024**3
require = native.require
digest = native.digest
save = native.save


def read(path, maximum=64 * 1024**2):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum, "Unsafe/unbounded original JSON")
    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, "Duplicate evidence JSON key")
            value[key] = item
        return value
    return json.loads(path.read_text(encoding="utf8"), object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def descriptor_admission(value, selector):
    native.keys(value, {"sha256", "main_thread_checker_token"})
    native.hex_value(value["sha256"])
    require(selector in (PREP, UI), "Unowned descriptor admission")
    token = value["main_thread_checker_token"]
    require(token is None or (isinstance(token, str) and 0 < len(token) <= 4096
            and token.startswith("/") and token.isprintable() and ":" not in token
            and all(part not in {".", ".."} for part in token.split("/"))
            and token.endswith("/libMainThreadChecker.dylib")),
            "Pin the exact original MainThreadChecker token or explicit absence")
    return value


def admission(value):
    native.keys(value, {"consumer_run", "consumer_attempt", "consumer_sha", "artifact_id", "artifact_bytes",
                        "artifact_sha256", "native_manifest_sha256", "ui_manifest_sha256",
                        "native_descriptor", "ui_descriptor"})
    for name in ("consumer_run", "consumer_attempt"):
        require(isinstance(value[name], str) and re.fullmatch("[1-9][0-9]{0,19}", value[name]), "Invalid original CI identity")
    native.hex_value(value["consumer_sha"], 40)
    for name in ("artifact_sha256", "native_manifest_sha256", "ui_manifest_sha256"):
        native.hex_value(value[name])
    require(type(value["artifact_id"]) is int and value["artifact_id"] > 0
            and type(value["artifact_bytes"]) is int and 0 < value["artifact_bytes"] <= 2 * MAX_ARCHIVE,
            "Invalid original artifact identity/size")
    descriptor_admission(value["native_descriptor"], PREP)
    descriptor_admission(value["ui_descriptor"], UI)
    return value


def original_api(run, artifact, approved):
    admission(approved)
    require(run.get("id") == int(approved["consumer_run"]) and run.get("run_attempt") == int(approved["consumer_attempt"])
            and run.get("head_sha") == approved["consumer_sha"] and run.get("status") == "completed"
            and run.get("conclusion") == "success" and run.get("event") == "workflow_dispatch"
            and run.get("repository", {}).get("full_name") == native.REPOSITORY,
            "Exact successful original App consumer run required")
    require(artifact.get("id") == approved["artifact_id"] and artifact.get("expired") is False
            and artifact.get("name") == "Pinkha-Semantic-Page-App-Consumer-" +
                approved["consumer_run"] + "-" + approved["consumer_attempt"]
            and artifact.get("size_in_bytes") == approved["artifact_bytes"]
            and artifact.get("digest") == "sha256:" + approved["artifact_sha256"]
            and artifact.get("workflow_run", {}).get("id") == int(approved["consumer_run"])
            and artifact.get("workflow_run", {}).get("head_sha") == approved["consumer_sha"],
            "Exact original App/UI artifact identity differs")


def restore_products(archive, manifest_path, destination, approved):
    """Admit every original entry; retain bytes/modes and self-contained links."""
    value = read(manifest_path)
    require(value.get("status") == "OBSERVED_PRODUCTS_ARCHIVED_BEFORE_ADMISSION"
            and value.get("capture_phase") == "AFTER_BUILD_BEFORE_ADMISSION"
            and value.get("source_sha") == approved["consumer_sha"]
            and value.get("run_id") == approved["consumer_run"]
            and value.get("run_attempt") == approved["consumer_attempt"]
            and value.get("build_reuse_enabled") is False
            and value.get("native_acceptance_reused") is False and value.get("ui_acceptance_reused") is False,
            "Original early Products provenance differs")
    require(digest(archive) == value.get("archive_sha256") and archive.stat().st_size == value.get("archive_bytes")
            and archive.stat().st_size <= MAX_ARCHIVE, "Original Products archive bytes differ")
    flags = value.get("build_flags")
    require(isinstance(flags, list) and all(isinstance(v, str) for v in flags)
            and any("-D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1" in v
                    and "-D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1" in v for v in flags)
            and "ONLY_ACTIVE_ARCH=YES" in flags and "ENABLE_TESTABILITY=YES" in flags,
            "Actual active Page154/lifetime build profile required")
    rows = value.get("products")
    require(isinstance(rows, dict) and 0 < len(rows) < 100_000, "Missing original product inventory")
    require(not destination.exists(), "Fresh owned restore root required")
    destination.mkdir(parents=True)
    links = []
    seen = set(); folded = set()
    total = 0
    with tarfile.open(archive, "r:gz") as packed:
        for member in packed:
            name = member.name
            relative = native.relative(name)
            require(name in rows and name not in seen and name.casefold() not in folded,
                    "Extra, duplicate or case-colliding product member")
            require(name == "Build/PinkhaSourceInputs.json" or name == "Build/Products"
                    or name.startswith("Build/Products/"), "Product outside exact archive roots")
            seen.add(name); folded.add(name.casefold())
            row = rows[name]
            require(type(row.get("mode")) is int and row["mode"] == member.mode
                    and 0 <= member.mode <= 0o777, "Original product mode differs")
            path = destination / relative
            if member.isdir():
                require(row.get("kind") == "directory", "Product kind differs")
                path.mkdir(parents=True, exist_ok=True)
                os.chmod(path, member.mode)
            elif member.isfile():
                require(row.get("kind") == "file" and row.get("bytes") == member.size
                        and 0 <= member.size <= MAX_ARCHIVE, "Product file size/kind differs")
                total += member.size
                require(total <= 3 * MAX_ARCHIVE, "Unbounded restored Products")
                # No links have been created yet, so no member can traverse one.
                path.parent.mkdir(parents=True, exist_ok=True)
                with packed.extractfile(member) as source, path.open("xb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                require(digest(path) == row.get("sha256"), "Original product SHA-256 differs")
                os.chmod(path, member.mode)
            elif member.issym() or member.islnk():
                kind = "symlink" if member.issym() else "hardlink"
                require(row.get("kind") == kind and row.get("target") == member.linkname
                        and member.linkname and not PurePosixPath(member.linkname).is_absolute()
                        and "\\" not in member.linkname, "External or mismatched link requires separate admission")
                links.append((name, kind, member.linkname))
            else:
                raise ValueError("Special product member refused")
    require(seen == set(rows), "Original product inventory incomplete")
    for name, kind, target in links:
        path = destination / native.relative(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if kind == "symlink":
            path.symlink_to(target)
        else:
            source = destination / native.relative(target)
            require(source.is_file() and not source.is_symlink(), "Hard-link target is not an admitted file")
            os.link(source, path)
    for name, kind, _ in links:
        actual = (destination / native.relative(name)).resolve(strict=True)
        require(actual.is_relative_to(destination / "Build/Products"), "Product link escaped admitted Products")
        require(actual.relative_to(destination).as_posix() in rows, "Product link resolves to an unadmitted entry")
    return {"archive_sha256": digest(archive), "manifest_sha256": digest(manifest_path),
            "entries": len(seen), "links_separately_verified": len(links), "restored_bytes": total,
            "source_sha": approved["consumer_sha"], "status": "PASS_EXACT_SELF_CONTAINED_PRODUCTS_RESTORE"}


def verify_restored_products(destination, manifest_path, extra_descriptors=()):
    rows = read(manifest_path)["products"]
    allowed = set(rows) | {p.relative_to(destination).as_posix() for p in extra_descriptors}
    actual = {"Build/Products"} | {p.relative_to(destination).as_posix()
        for p in (destination / "Build/Products").rglob("*")}
    if (destination / "Build/PinkhaSourceInputs.json").exists(): actual.add("Build/PinkhaSourceInputs.json")
    require(actual == allowed, "Restored product inventory changed outside owned descriptors")
    for name, row in rows.items():
        path = destination / native.relative(name)
        require(path.lstat().st_mode & 0o777 == row["mode"], "Original restored product mode changed")
        if row["kind"] == "symlink":
            require(path.is_symlink() and path.readlink().as_posix() == row["target"]
                and path.resolve(strict=True).is_relative_to(destination / "Build/Products"),
                "Original restored product link changed")
        elif row["kind"] in ("file", "hardlink"):
            require(path.is_file() and not path.is_symlink(), "Original restored file kind changed")
            expected = rows[row["target"]] if row["kind"] == "hardlink" else row
            require(digest(path) == expected["sha256"], "Original restored product bytes changed")
        else:
            require(path.is_dir() and not path.is_symlink(), "Original restored directory kind changed")
    return {"original_entries_checked": len(rows), "owned_descriptors_only": len(extra_descriptors)}


def exact_original_descriptor(products, original_bytes):
    found = [p for p in products.glob("*.xctestrun") if p.is_file() and not p.is_symlink()
             and p.read_bytes() == original_bytes]
    require(len(found) == 1, "One byte-identical original compiled descriptor required")
    return found[0]


RUNTIME_HELPER_SHA256 = "ce2987846cdd42ebab7702e7dff51068bfb15ee48a66011f621695dbd72ebbce"


def relocated_injection(target, runtime, approved):
    """Change only a source token already bound to the immutable descriptor."""
    before = copy.deepcopy(target.get("TestingEnvironmentVariables", {}))
    require(isinstance(before, dict)
            and all(isinstance(k, str) and isinstance(v, str) for k, v in before.items()),
            "Invalid original testing environment")
    injected = before.get("DYLD_INSERT_LIBRARIES")
    tokens = [] if injected is None else injected.split(":")
    matching = [token for token in tokens if token.rsplit("/", 1)[-1] == "libMainThreadChecker.dylib"]
    expected = approved["main_thread_checker_token"]
    if expected is None:
        require(not matching, "Admitted MainThreadChecker absence differs from original descriptor")
        return {"status": "ABSENCE_PRESERVED", "original_token": None,
                "original_descriptor_sha256": approved["sha256"]}
    require(matching == [expected] and tokens.count(expected) == 1,
            "Only the descriptor-pinned single MainThreadChecker token may change")
    # The ordinary SDK caller retains its original default token/profile. This
    # caller must supply a different token explicitly, after descriptor admission.
    sys.path.insert(0, str(HERE.parents[1] / "PinkhaSimulatorGate"))
    import sdk06_enumeration_probe as runtime_helper
    require(digest(Path(runtime_helper.__file__)) == RUNTIME_HELPER_SHA256,
            "Reviewed per-descriptor runtime normalizer bytes differ")
    result = runtime_helper.normalize_runtime_injection(target, runtime, expected_original_token=expected)
    exact = copy.deepcopy(before)
    exact["DYLD_INSERT_LIBRARIES"] = ":".join(
        result["replacement_token"] if token == expected else token for token in tokens)
    require(target.get("TestingEnvironmentVariables") == exact,
            "Runtime normalization changed another testing-environment field")
    return dict(result, status="EXACT_PINNED_TOKEN_RELOCATED",
                original_descriptor_sha256=approved["sha256"], helper_sha256=RUNTIME_HELPER_SHA256)


def copied_descriptor(original, destination, selector, binding, *, runtime, approved, fixture=None, app_path=None):
    native.binding(binding)
    descriptor_admission(approved, selector)
    require(selector in (PREP, UI) and original != destination
            and original.parent.resolve() == destination.parent.resolve()
            and original.is_file() and not original.is_symlink()
            and not destination.exists(), "Fresh exact mounted descriptor required")
    raw = original.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == approved["sha256"],
            "Original descriptor differs from reviewed SHA-256")
    value = plistlib.loads(raw)
    require(isinstance(value, dict) and isinstance(value.get("__xctestrun_metadata__"), dict),
            "Original descriptor metadata missing")
    version = value["__xctestrun_metadata__"].get("FormatVersion")
    blueprint, suite, method = selector.split("/")
    configuration = None
    if type(version) is int and version == 2 and selector == PREP:
        require(isinstance(value.get("TestConfigurations"), list)
                and len(value["TestConfigurations"]) == 1, "One original v2 configuration required")
        configuration = value["TestConfigurations"][0]
        require(isinstance(configuration, dict) and isinstance(configuration.get("TestTargets"), list),
                "Original v2 targets missing")
        found = [target for target in configuration["TestTargets"]
                 if isinstance(target, dict) and target.get("BlueprintName") == blueprint]
        require(len(found) == 1, "Required compiled test target absent or ambiguous")
        target = found[0]
    else:
        require(type(version) is int and version == 1 and selector == UI
                and set(value) == {"__xctestrun_metadata__", blueprint}
                and isinstance(value[blueprint], dict),
                "Only one exact UI blueprint is admitted in a v1 descriptor")
        def unnamed(node):
            if isinstance(node, dict):
                for key, child in node.items():
                    normalized = key.replace("_", "").lower()
                    require("testplan" not in normalized and "testconfiguration" not in normalized
                            and normalized != "configurationname",
                            "Unexpected named plan/configuration in the frozen v1 UI descriptor")
                    unnamed(child)
            elif isinstance(node, list):
                for child in node: unnamed(child)
        unnamed(value)
        target = value[blueprint]
        require(target.get("BlueprintName", blueprint) == blueprint
                and target.get("IsUITestBundle") is True, "Original v1 UI target differs")
    require(target.get("IsEnabled", True) is True, "Required compiled test target disabled")
    before = copy.deepcopy(target)
    existing = target.get("EnvironmentVariables", {})
    require(isinstance(existing, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in existing.items())
            and not any(k.startswith("PINKHA_") or k.startswith("TEST_RUNNER_PINKHA_") for k in existing),
            "Original descriptor has stale candidate environment")
    injection = relocated_injection(target, runtime, approved)
    additions = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
                 "PINKHA_SEMANTIC_MOUNTED_PREPARE" if selector == PREP else "PINKHA_SEMANTIC_MOUNTED_TESTING": "1"}
    for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
        additions["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
    if selector == UI:
        require(isinstance(fixture, dict) and app_path is not None and app_path.is_dir(), "Real native fixture/App required")
        raw_fixture = json.dumps(fixture, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        require(len(raw_fixture.encode("utf8")) <= 65_536, "UI fixture exceeds bound")
        additions["PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON"] = raw_fixture
        target["UITargetAppPath"] = str(app_path)
    else:
        require(fixture is None and app_path is None, "Preparation cannot receive a UI fixture")
    target["EnvironmentVariables"] = existing | additions
    target["OnlyTestIdentifiers"] = [suite + "/" + method]
    if configuration is not None: configuration["TestTargets"] = [target]
    restored = copy.deepcopy(target)
    for key in ("EnvironmentVariables", "OnlyTestIdentifiers", "UITargetAppPath"):
        if key in before: restored[key] = before[key]
        else: restored.pop(key, None)
    if injection["status"] == "EXACT_PINNED_TOKEN_RELOCATED":
        current = restored["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"].split(":")
        replacement = injection["replacement_token"]
        require(current.count(replacement) == 1, "Relocated testing token became ambiguous")
        restored["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = ":".join(
            injection["original_token"] if token == replacement else token for token in current)
    require(restored == before and original.read_bytes() == raw, "Non-binding descriptor fields changed")
    with destination.open("xb") as output:
        plistlib.dump(value, output, sort_keys=False)
    return {"original_sha256": digest(original), "copied_sha256": digest(destination),
            "selector": selector, "binding": binding, "environment_keys": sorted(additions),
            "format_version": version, "enumeration_plan": "AnytypeTests" if selector == PREP else None,
            "enumeration_plan_policy": "EXACT_NATIVE_NAMED_PLAN" if selector == PREP else
                "OBSERVED_METADATA_FOR_EXACT_UNNAMED_V1_UI",
            "runtime_injection": injection,
            "all_other_testing_environment_fields_unchanged": True,
            "original_testing_environment_unchanged": target.get("TestingEnvironmentVariables") == before.get("TestingEnvironmentVariables")}


def exact_enumeration(plan, enabled, disabled, selector, expected_plan):
    require(selector in (PREP, UI) and isinstance(plan, str)
            and ((selector == PREP and plan == expected_plan == "AnytypeTests")
                 or (selector == UI and expected_plan is None)),
            "Native plan must be AnytypeTests; unnamed v1 UI records its actual plan metadata")
    blueprint, suite, method = selector.split("/")
    actual = [value.removeprefix(blueprint + "/").removesuffix("()") for value in enabled]
    require(actual == [suite + "/" + method] and not enabled.intersection(disabled),
            "Actual compiled selection differs from exact owned new method")
    return {"plan": plan, "enabled": sorted(enabled)}


def xctest_command(descriptor, udid, selector, *, enumeration=None, result=None):
    require(selector in (PREP, UI) and (enumeration is None) != (result is None),
            "One owned exact execution or enumeration required")
    command = ["xcodebuild", "test-without-building", "-xctestrun", str(descriptor),
        "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
        "-only-testing", selector]
    if enumeration is not None:
        command += ["-enumerate-tests", "-test-enumeration-style", "flat", "-test-enumeration-format", "json",
                    "-test-enumeration-output-path", str(enumeration)]
    else:
        command += ["-resultBundlePath", str(result)]
    return command


def exact_execution(summary, tree, udid, selector):
    require(selector in (PREP, UI), "Unowned actual selector")
    counts = {key: summary.get(key) for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    require(all(type(v) is int for v in counts.values())
            and counts == dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0)
            and summary.get("result") == "Passed", "Exactly one actual PASS without skips/failures required")
    destinations = summary.get("devicesAndConfigurations", [])
    require(len(destinations) == 1, "One actual simulator required")
    device = destinations[0].get("device", {})
    require(str(device.get("deviceId", "")).lower() == udid.lower()
            and device.get("architecture") == "arm64" and device.get("platform") == "iOS Simulator"
            and str(device.get("osVersion", "")).split(".")[0] == "27"
            and device.get("osBuildNumber"), "Actual owned OS27 ARM64 simulator differs")
    cases = []
    def walk(value):
        if isinstance(value, dict):
            if value.get("nodeType") == "Test Case": cases.append((value.get("nodeIdentifier"), value.get("result")))
            for child in value.values():
                if isinstance(child, (dict, list)): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(tree)
    blueprint, suite, method = selector.split("/")
    require(len(cases) == 1 and cases[0][0].removeprefix(blueprint + "/").removesuffix("()") == suite + "/" + method
            and cases[0][1] == "Passed", "Wrong or duplicate actual mounted method")
    return {"selector": selector, "counts": counts, "cases": cases, "device": device}


def native_block(raw, block_id, text):
    fields = native.protobuf(raw)
    require(native.one(fields, 1, 2) == block_id.encode("utf8") and native.one(fields, 3, 2) == b""
            and [row[0] for row in fields if row[0] >= 11] == [14], "Exact text block/restrictions identity differs")
    body = native.protobuf(native.one(fields, 14, 2, b""))
    require(native.one(body, 1, 2) == text.encode("utf8") and native.one(body, 2, 0, 0) == 0,
            "Exact native paragraph bytes differ")
    raw_marks = native.one(body, 3, 2, b"")
    return {"fields": fields, "body": body, "raw_marks": raw_marks, "marks": native.marks(raw_marks)}


def snapshot(text, marks):
    value = json.dumps({"text": text, "marks": marks}, ensure_ascii=False, separators=(",", ":"))
    for char in ("&", "<", ">", "\u2028", "\u2029"):
        value = value.replace(char, "\\u%04x" % ord(char))
    return hashlib.sha256(value.encode("utf8")).hexdigest()


def fixture(value, binding, *, now=None):
    native.binding(binding)
    native.keys(value, {"sourceSHA", "runID", "runAttempt", "nonce", "createdAt", "preparationProcessID",
        "accountID", "spaceID", "objectID", "blockID", "excludedBlockID", "text", "excludedText",
        "beforeBlockBase64", "excludedBlockBase64"})
    require(all(value[k] == binding[k] for k in binding), "Native fixture source/run/nonce differs")
    for key in ("accountID", "spaceID", "objectID", "blockID", "excludedBlockID"): native.identity(value[key])
    require(value["blockID"] != value["excludedBlockID"] and value["text"] == "Anchor"
            and value["excludedText"] == "Unselected " + binding["nonce"]
            and type(value["preparationProcessID"]) is int and value["preparationProcessID"] > 1,
            "Synthetic native fixture shape differs")
    created = value["createdAt"]
    require(type(created) in (int, float) and math.isfinite(created)
            and 0 <= (time.time() if now is None else now) - (created + 978307200) < 7200,
            "Native fixture not fresh")
    before = native_block(native.decode64(value["beforeBlockBase64"]), value["blockID"], value["text"])
    excluded = native_block(native.decode64(value["excludedBlockBase64"]), value["excludedBlockID"], value["excludedText"])
    require(before["marks"] == [{"from": 0, "to": 3, "kind": 3, "param": ""}]
            and excluded["marks"] == [], "Original native marks differ")
    return before


CAPTURE_CHECKS = {"actualEditorAndInputMounted", "actualUserSelection", "cancelNativeUnchanged", "explicitApplyOnce",
                 "ordinaryDocumentPublication", "renderedBeforeIndependentReadback", "nativeReceiptVerified",
                 "nonMarkAndExcludedBlockUnchanged", "middlewareLoggingDisabled"}
REOPEN_CHECKS = {"actualEditorAndInputMounted", "distinctColdProcessAndGeneration", "persistedNativeBlockIdentical",
                "renderedBeforeIndependentReadback", "excludedBlockUnchanged", "noNewApply", "middlewareLoggingDisabled"}


def observations(fixture_value, capture, reopen, capture_raw, binding, *, now=None):
    before = fixture(fixture_value, binding, now=now)
    require(json.loads(capture_raw) == capture, "Capture receipt byte binding differs")
    for value, mode, phase, checks in ((capture, "capture", "PASS_CAPTURE_MOUNTED", CAPTURE_CHECKS),
                                        (reopen, "reopen", "PASS_COLD_REOPEN_MOUNTED", REOPEN_CHECKS)):
        require(value.get("protocol") == PROTOCOL and value.get("phase") == phase and value.get("mode") == mode
                and all(value.get(k) == binding[k] for k in binding), "Mounted observation source/phase differs")
        require(all(value.get(k) == fixture_value[k] for k in ("accountID", "spaceID", "objectID", "blockID",
                    "excludedBlockID", "preparationProcessID")), "Mounted observation identity differs")
        require(value.get("runtimeVersion") == native.VERSION and value.get("nativeManifestSHA256") == native.MANIFEST_SHA
                and native.uuid(value.get("generation")) and type(value.get("processID")) is int and value["processID"] > 1,
                "Actual runtime/generation/process missing")
        require(value.get("failure") is None and isinstance(value.get("checks"), dict) and set(value["checks"]) == checks
                and all(item is True for item in value["checks"].values()), "Incomplete mounted observations")
        require(type(value.get("startedAt")) in (int, float) and type(value.get("finishedAt")) in (int, float)
                and value["finishedAt"] >= value["startedAt"], "Original observation timestamps missing")
    require(capture.get("preparations") == 2 and capture.get("cancellations") == 1 and capture.get("applyAttempts") == 1
            and capture.get("documentPublications") == 1 and capture.get("publicationGeneration") == capture["generation"],
            "One explicit native document publication required")
    for value in (capture, reopen):
        require(all(type(value.get(k)) is int for k in ("preparations", "cancellations", "applyAttempts", "documentPublications")),
                "Noninteger operation count")
    require(capture.get("selection") == {"blockID": fixture_value["blockID"], "location": 0, "length": 6,
                "visibleTextSHA256": hashlib.sha256(b"Anchor").hexdigest()}, "Actual UIKit selection differs")
    require(capture.get("cancelNativeBlockSHA256") == hashlib.sha256(native.decode64(fixture_value["beforeBlockBase64"])).hexdigest(),
            "Cancel did not preserve original native block")
    receipt = capture.get("native")
    native.keys(receipt, {"anchorID", "marker", "changeID", "nativeChangeSHA256",
                           "beforeTextMarksSHA256", "afterTextMarksSHA256"})
    require(native.uuid(receipt["anchorID"]), "Actual anchor UUID missing")
    component = lambda text: base64.urlsafe_b64encode(text.encode("utf8")).decode("ascii").rstrip("=")
    marker = "pinkha-anchor://v1/" + component(fixture_value["spaceID"]) + "/" + component(fixture_value["objectID"]) + "/" + receipt["anchorID"]
    cancelled = capture.get("cancelledMarker")
    prefix = marker.rsplit("/", 1)[0] + "/"
    require(receipt["marker"] == marker and isinstance(cancelled, str) and cancelled.startswith(prefix)
            and native.uuid(cancelled.removeprefix(prefix)) and cancelled != marker,
            "Confirmed anchor reused cancelled or foreign intent")
    native.identity(receipt["changeID"]); native.hex_value(receipt["nativeChangeSHA256"])
    after = native_block(native.decode64(capture["afterBlockBase64"]), fixture_value["blockID"], "Anchor")
    require(after["marks"] == before["marks"] + [{"from": 0, "to": 6, "kind": 5, "param": marker}],
            "Original ordered native marks or added anchor differs")
    require([x[3] for x in before["fields"] if x[0] != 14] == [x[3] for x in after["fields"] if x[0] != 14]
            and [x[3] for x in before["body"] if x[0] != 3] == [x[3] for x in after["body"] if x[0] != 3],
            "Opaque non-mark native block bytes changed")
    require(receipt["beforeTextMarksSHA256"] == snapshot("Anchor", before["marks"])
            and receipt["afterTextMarksSHA256"] == snapshot("Anchor", after["marks"]),
            "Actual native digest disagrees with original protobuf")
    for value in (capture, reopen):
        require(native.decode64(value["documentMarksBase64"]) == after["raw_marks"]
                and value["renderedLinks"] == [{"marker": marker, "location": 0, "length": 6}],
                "Actual document/rendered link differs")
    require(len({fixture_value["preparationProcessID"], capture["processID"], reopen["processID"]}) == 3
            and reopen.get("captureProcessID") == capture["processID"] and reopen["generation"] != capture["generation"],
            "Preparation/capture/cold reopen are not distinct owned processes")
    require(reopen.get("preparations") == reopen.get("cancellations") == reopen.get("applyAttempts") ==
            reopen.get("documentPublications") == 0 and reopen.get("native") == receipt
            and reopen.get("afterBlockBase64") == capture["afterBlockBase64"]
            and reopen.get("captureReceiptSHA256") == hashlib.sha256(capture_raw).hexdigest(),
            "Cold reopen mutated, changed native data or lost original receipt identity")
    return {"status": PASS, "binding": binding, "capture_process_id": capture["processID"],
            "reopen_process_id": reopen["processID"], "native_change_id": receipt["changeID"],
            "native_change_sha256": receipt["nativeChangeSHA256"],
            "capture_receipt_sha256": hashlib.sha256(capture_raw).hexdigest(),
            "limitations": {"physicalDevice": "NOT_RUN", "shipping": "OFF", "fullProductAcceptance": False}}
