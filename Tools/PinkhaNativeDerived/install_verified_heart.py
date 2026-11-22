"""Install one explicitly selected, source-bound verified Heart runtime."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import zipfile

from build_custom_heart import PIN, digest, git, verify_framework_slices
import heart_runtime_profile as profiles

APPROVED_BRANCHES = [
    "codex/torah-native-derived-properties-20261103",
    "codex/anytype-wave1-integration-20261115",
    "codex/chatgpt-wave15-startup-20261118",
    "codex/chatgpt-wave15-integration-20261118",
    "codex/chatgpt-wave15-hanlin-consumer-20261119",
    "codex/any-engine-port-20261119",
    "codex/chatgpt-wave15-ui-resume-20261119",
    "codex/chatgpt-wave15-shared-20261121",
    "codex/chatgpt-wave15-acceptance-continuation-20261122",
]


def original_proof(args, profile, archive_receipt_raw, inventory):
    profiles.require(args.producer_run and args.producer_proof and args.download_receipt and args.repository,
                     "Corrected runtime requires original producer and artifact evidence")
    run = json.loads(args.producer_run.read_bytes())
    producer = profiles.validate_producer(run, args.source_run_id, args.repository, args.expected_app_branch)
    downloaded = json.loads(args.download_receipt.read_bytes())
    profiles.require(downloaded.get("status") == "VERIFIED_ORIGINAL_GITHUB_ARTIFACTS"
                     and downloaded.get("producer") == producer, "Original artifact download is unverified")
    profiles.require(downloaded.get("payload_sha256", {}).get("runtime") == digest(args.archive)
                     and downloaded.get("payload_sha256", {}).get("proof") == digest(args.producer_proof),
                     "Original downloaded runtime or proof payload changed before installation")
    proof_name = "Pinkha-T5-Attachment-Runtime-" + profile.name + "-" + args.source_run_id + "-" + producer["run_attempt"]
    for kind, name in (("runtime", profile.artifact_name), ("proof", proof_name)):
        expected = profiles.validate_artifact(downloaded["artifacts"][kind], run, name)
        profiles.require(downloaded["archive_sha256"].get(kind) == expected,
                         "Downloaded original GitHub ZIP digest differs")
    with zipfile.ZipFile(args.producer_proof) as proof:
        def read(name):
            full = "runtime/" + name
            entries = [item for item in proof.infolist() if item.filename == full]
            profiles.require(len(entries) == 1 and not entries[0].is_dir()
                             and 0 < entries[0].file_size <= 50 * 1024 * 1024,
                             "Original source proof member is missing, repeated or unbounded")
            return proof.read(entries[0])
        profiles.require(read("custom-heart-build.json") == archive_receipt_raw,
                         "Runtime archive and original producer proof have different build receipts")
        profiles.require(read("corrected-native-source/native-heart-integration.patch.txt") == args.patch.read_bytes()
                         and read("corrected-native-source/native-heart-integration.json") == args.inventory.read_bytes(),
                         "Corrected source was not the exact source retained by the producer")
        artifact = json.loads(read("runtime-artifact.json"))
        profiles.require(artifact.get("status") == "APPLE_RUNTIME_ARTIFACT_BUILT_NOT_EXECUTED"
                         and artifact.get("sha256") == digest(args.archive)
                         and artifact.get("receipt_sha256") == profiles.digest_bytes(archive_receipt_raw)
                         and artifact.get("github_run_id") == producer["run_id"]
                         and artifact.get("github_run_attempt") == producer["run_attempt"]
                         and artifact.get("integration_sha") == producer["source_sha"]
                         and artifact.get("runtime_variant") == profile.name
                         and artifact.get("expected_app_get_version") == profile.version,
                         "Original runtime archive does not bind the producer's full version and bytes")
        log_raw = read("corrected-attachment-fixtures.log")
        fixture_receipt = json.loads(read("corrected-attachment-fixtures.json"))
    # Replay the original two-fixture log; no test is re-executed.
    from build_t5_r15_runtime import qualify_corrected_fixtures
    with tempfile.TemporaryDirectory(prefix="pinkha-original-fixture-log-") as directory:
        log = Path(directory) / "original.log"
        log.write_bytes(log_raw)
        replay = qualify_corrected_fixtures(log)
    profiles.require(replay == fixture_receipt
                     and replay == json.loads(archive_receipt_raw).get("native_attachment_fixtures"),
                     "Original native fixture log differs from the runtime build receipt")
    args.evidence.mkdir(parents=True, exist_ok=True)
    (args.evidence / "original-corrected-attachment-fixtures.log").write_bytes(log_raw)
    (args.evidence / "original-corrected-attachment-fixtures.json").write_text(
        json.dumps(fixture_receipt, indent=2) + "\n", encoding="utf8")
    return producer, downloaded


def install(args):
    profile = profiles.select(args.runtime_profile)
    inventory = profiles.verify_source(profile, args.patch.read_bytes(), args.inventory.read_bytes())
    profiles.require(git(args.app_source, "branch", "--show-current") == args.expected_app_branch,
                     "Wrong application branch")
    with tempfile.TemporaryDirectory(prefix="pinkha-verified-heart-") as directory:
        staging = Path(directory)
        with tarfile.open(args.archive) as archive:
            archive.extractall(staging, filter="data")
        profiles.require({p.name for p in staging.iterdir()} == {"Lib.xcframework", "PinkhaNativeHeartBuild.json"},
                         "Unexpected artifact payload")
        framework = staging / "Lib.xcframework"
        receipt_raw = (staging / "PinkhaNativeHeartBuild.json").read_bytes()
        receipt = json.loads(receipt_raw)
        producer = downloaded = None
        if profile.name == profiles.CORRECTED:
            producer, downloaded = original_proof(args, profile, receipt_raw, inventory)
        marker = profiles.validate_build(profile, receipt, inventory, args.source_run_id, producer)
        paths = [entry["path"] for entry in receipt["artifacts"]]
        actual_paths = {p.relative_to(framework).as_posix() for p in framework.rglob("*") if p.is_file()}
        profiles.require(len(paths) == len(set(paths)) and actual_paths == set(paths),
                         "Framework file inventory differs or repeats a member")
        for entry in receipt["artifacts"]:
            path = (framework / entry["path"]).resolve(strict=True)
            profiles.require(path.is_relative_to(framework.resolve()) and digest(path) == entry["sha256"],
                             "Framework content or path differs: " + entry["path"])
        actual_slices = verify_framework_slices(framework, marker)
        slice_key = lambda entry: (entry["path"], entry["architecture"])
        profiles.require(sorted(actual_slices, key=slice_key) == sorted(receipt.get("binary_slices", []), key=slice_key),
                         "Framework thin-architecture proof differs")
        if profile.name == profiles.CORRECTED:
            from build_t5_r15_runtime import EXPECTED_SLICES
            profiles.require(len(actual_slices) == 3
                             and {(s["path"], s["architecture"]) for s in actual_slices} == EXPECTED_SLICES,
                             "All three corrected runtime architectures are required")
        destination = args.app_source / "Dependencies/Middleware"
        destination.mkdir(parents=True, exist_ok=True)
        profiles.require(not (destination / "Lib.xcframework").exists()
                         and not (destination / "PinkhaNativeHeartBuild.json").exists(),
                         "Refusing to overwrite an existing middleware installation")
        shutil.copytree(framework, destination / "Lib.xcframework")
        shutil.copyfile(staging / "PinkhaNativeHeartBuild.json", destination / "PinkhaNativeHeartBuild.json")
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / "custom-heart-build.json").write_bytes(receipt_raw)
        installation = dict(status="PASS", source_run_id=args.source_run_id,
                            archive_sha256=digest(args.archive), patch_sha256=profile.patch_sha256,
                            app_source_sha=git(args.app_source, "rev-parse", "HEAD"),
                            original_build_app_sha=receipt.get("app_base_sha"), marker=profile.receipt_marker,
                            runtime_profile=profile.name, native_marker=profile.binary_marker,
                            expected_app_get_version=profile.version)
        if producer is not None:
            installation.update(
                producer=producer, inventory_sha256=profile.inventory_sha256,
                heart_build_receipt_sha256=profiles.digest_bytes(receipt_raw),
                heart_artifact_id=downloaded["artifacts"]["runtime"]["id"],
                heart_artifact_sha256=downloaded["archive_sha256"]["runtime"],
                heart_proof_artifact_id=downloaded["artifacts"]["proof"]["id"],
                heart_proof_artifact_sha256=downloaded["archive_sha256"]["proof"],
                original_fixture_log_sha256=receipt["native_attachment_fixtures"]["log_sha256"])
        (args.evidence / "heart-installation.json").write_text(
            json.dumps(installation, indent=2) + "\n", encoding="utf8")
    return installation


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("archive", "inventory", "patch", "app-source", "evidence"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--expected-app-branch", choices=APPROVED_BRANCHES,
                        default="codex/torah-native-derived-properties-20261103")
    parser.add_argument("--runtime-profile", choices=profiles.PROFILE_NAMES, default="r14")
    for name in ("producer-run", "producer-proof", "download-receipt"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    args = parser.parse_args()
    print(json.dumps(install(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
