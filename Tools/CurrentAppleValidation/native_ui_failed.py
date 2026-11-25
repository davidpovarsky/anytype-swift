"""One current NativeApp build: three remaining independent UI journeys."""
from __future__ import annotations
import importlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import zipfile
import contracts as c
import current_execution as driver

PROFILE = "native-ui-failed"

def prepare_library(commands, work, evidence):
    run = commands.json(["gh", "api", "repos/" + c.REPOSITORY + "/actions/runs/" + c.ANY["run"]],
                        "original-any-run", 120)
    c.require(str(run.get("id")) == c.ANY["run"] and run.get("head_sha") == c.ANY["source"]
              and run.get("status") == "completed"
              and run.get("repository", {}).get("full_name") == c.REPOSITORY, "fixed_any_producer_mismatch")
    listing = commands.json(["gh", "api", "repos/" + c.REPOSITORY + "/actions/runs/" + c.ANY["run"]
                             + "/artifacts?per_page=100"], "original-any-artifacts", 120)
    items = listing.get("artifacts")
    c.require(isinstance(items, list) and listing.get("total_count") == len(items) <= 100,
              "complete_original_artifact_inventory_required")
    selected = [item for item in items if item.get("name") == c.ANY["artifactName"]]
    c.require(len(selected) == 1, "exact_original_native_artifact_required")
    item = selected[0]
    identity = item.get("workflow_run", {})
    expected = item.get("digest", "").removeprefix("sha256:")
    c.require(item.get("expired") is False and type(item.get("id")) is int
              and type(item.get("size_in_bytes")) is int and 0 < item["size_in_bytes"] <= 2 * 1024**3
              and re.fullmatch("[0-9a-f]{64}", expected)
              and str(identity.get("id")) == c.ANY["run"] and identity.get("head_sha") == c.ANY["source"],
              "original_native_artifact_identity_unverified")
    outer = commands.run(["gh", "api", "repos/" + c.REPOSITORY + "/actions/artifacts/"
                          + str(item["id"]) + "/zip"], "download-original-any", 600)
    c.require(outer.stat().st_size == item["size_in_bytes"] and driver.digest(outer) == expected,
              "original_native_artifact_bytes_changed")
    target = work / "native-originals"
    target.mkdir(mode=0o700)
    wanted = {"native-artifact.json": c.ANY["receipt"], "any.xcframework.zip": c.ANY["archive"]}
    seen, copied, total = set(), {}, 0
    with zipfile.ZipFile(outer) as archive:
        c.require(0 < len(archive.infolist()) <= 20000, "native_zip_count_exceeded")
        for entry in archive.infolist():
            name = entry.filename.rstrip("/")
            parts = PurePosixPath(name).parts
            mode = stat.S_IFMT(entry.external_attr >> 16)
            c.require(name and not name.startswith("/") and "\\" not in name and "\0" not in name
                      and all(p not in ("", ".", "..") for p in name.split("/"))
                      and name not in seen and not entry.flag_bits & 1
                      and mode in (0, stat.S_IFDIR if entry.is_dir() else stat.S_IFREG), "unsafe_native_zip")
            seen.add(name)
            total += entry.file_size
            c.require(total <= 4 * 1024**3, "native_zip_bytes_exceeded")
            if name in wanted:
                c.require(not entry.is_dir() and 0 < entry.file_size <= 2 * 1024**3, "native_payload_invalid")
                path = target / name
                with archive.open(entry) as source, path.open("xb") as output:
                    shutil.copyfileobj(source, output, 1024**2)
                c.require(path.stat().st_size == entry.file_size and driver.digest(path) == wanted[name],
                          "fixed_original_native_payload_differs")
                copied[name] = {"bytes": path.stat().st_size, "sha256": wanted[name], "crc32": entry.CRC}
    c.require(set(copied) == set(wanted), "native_payload_missing")
    driver.write(evidence / "original-native-download.json",
                 {"context": commands.context, "run": run, "artifact": item, "archiveSHA256": expected,
                  "fixedPayloads": copied, "producerWorkflowConclusionIsNotBinaryAcceptance": True})
    commands.run([sys.executable, "-B", "Tools/AnyEnginePort/prepare_native_runtime.py", "install",
                  "--artifact", str(target), "--producer-commit", c.ANY["source"]], "install-original-any", 300)
    library = driver.ROOT / "Modules/PinkhaAnyRuntime/Vendor"
    binding = driver.read(library / "consumer-binding.json")
    expected_binding = {"status": "SOURCE_IDENTICAL_NATIVE_ARTIFACT", "producerCommit": c.ANY["source"],
                        "consumerCommit": commands.context["sourceCommit"], "sourceManifestSHA256": c.ANY["manifest"],
                        "artifactReceiptSHA256": c.ANY["receipt"], "archiveSHA256": c.ANY["archive"],
                        "testResultsRelabeled": False}
    c.require(all(binding.get(k) == v for k, v in expected_binding.items()), "native_current_source_binding_changed")
    os.environ["PINKHA_ANY_NATIVE_ARTIFACT"] = "verified-v1"
    os.environ["ANY_BUILD_VERSION"] = c.ANY["version"]
    return {"path": str(library), "files": driver.inventory(library), "nativeBuildInvocations": 0,
            "binding": binding, "originalProducer": c.ANY, "cLoadedAccountWitnessIncluded": False}

def provider_environment(include_values):
    names = {"PINKHA_HANLIN_FIXTURE_OWNED_DIR", "PINKHA_HANLIN_FIXTURE_PRIVATE_CONFIG"}
    path = Path(os.environ.get("GITHUB_ENV", ""))
    c.require(path.is_absolute() and path.is_file(), "github_environment_file_required")
    found = {}
    for line in c.read(path, 1024**2).decode().splitlines():
        key, separator, value = line.partition("=")
        if key in names:
            c.require(separator and value and "\0" not in value, "invalid_owned_provider_environment")
            c.require(key not in found or found[key] == value, "provider_ownership_changed")
            found[key] = value
    # In a later always-cleanup workflow step the runner has already applied GITHUB_ENV.
    for key in names:
        if key not in found and os.environ.get(key):
            found[key] = os.environ[key]
    if not found:
        return None
    c.require(set(found) == names, "incomplete_provider_ownership")
    os.environ.update(found)
    module = importlib.import_module("hanlin_fixture_ci")
    c.require(Path(module.__file__).resolve() == driver.ROOT / "Tools/AnyEnginePort/hanlin_fixture_ci.py",
              "foreign_provider_helper")
    run_id, source, temp = module.github_context()
    owned, config, _ = module.read_owned_config(run_id, source, temp)
    if include_values:
        # Never record these values in a receipt or command.
        os.environ.update(module.validate_private_config(config, owned / "fixture"))
    return {"ownedDirectory": str(owned), "sourceCommit": source, "runID": run_id}

def provider(commands, operation, device, evidence):
    safe = driver.ROOT / "build/any-patched-evidence/hanlin-provider"
    receipt = safe.parent / "simulator.json"
    argv = [sys.executable, "-B", "Tools/AnyEnginePort/hanlin_fixture_ci.py", operation, "--safe-dir", str(safe)]
    if operation == "prepare":
        c.require(device is not None, "provider_owned_device_required")
        os.environ["ANY_NATIVE_SIMULATOR_UDID"] = device["udid"]
        driver.write(receipt, {"ownedUDID": device["udid"], "runtime": device["runtime"]["identifier"],
                               "deviceType": device["device"]["identifier"]})
        argv += ["--simulator-receipt", str(receipt)]
        first = None
        try:
            commands.run(argv, "provider-prepare", 300)
        except BaseException as failure:
            first = failure
        try:
            # Ownership survives a later starter or process-group failure.
            provider_environment(False)
        except BaseException as failure:
            driver.write(evidence / "provider-ownership-observation-failure.json", driver.error(failure))
            first = first or failure
        if first is not None:
            raise first
        provider_environment(True)
        result = driver.read(safe / "prepare.json")
        c.require(result.get("status") == "HOST_TLS_READY_SIMULATOR_ROOT_INSTALLED_UI_EXECUTION_PENDING",
                  "provider_setup_incomplete")
    elif operation == "verify":
        commands.run(argv, "provider-verify", 60)
        result = driver.read(safe / "verify.json")
        transcript = driver.read(safe / "provider-contract.json")
        c.require(result.get("status") == "FINITE_PROVIDER_CONTRACT_VERIFIED"
                  and transcript.get("complete") is True and transcript.get("state") == "complete"
                  and transcript.get("phase") == transcript.get("responsesDelivered") == 6,
                  "finite_provider_transcript_incomplete")
        result = {**result, "transcriptSHA256": driver.digest(safe / "provider-contract.json")}
    elif operation == "cleanup":
        prior = safe / "cleanup.json"
        if prior.exists():
            result = driver.read(prior)
        else:
            provider_environment(False)
            commands.run(argv, "provider-cleanup", 90)
            result = driver.read(safe / "cleanup.json")
        c.require(result.get("status") in ("NO_FIXTURE_DIRECTORY_WAS_CREATED",
                                          "OWNED_FIXTURE_STOPPED_AND_PRIVATE_MATERIAL_REMOVED"),
                  "provider_cleanup_incomplete")
    else:
        raise ValueError("unknown_provider_operation")
    c.require(result.get("sourceCommit") == commands.context["sourceCommit"]
              and result.get("githubRunID") == commands.context["runID"], "provider_origin_mismatch")
    return result

if __name__ == "__main__":
    raise SystemExit(driver.main(PROFILE, prepare_library, provider))
