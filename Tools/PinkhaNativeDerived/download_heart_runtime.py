"""Download and install one explicit Heart runtime; never fall back between profiles."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import attachment_runtime
from build_custom_heart import digest
import heart_runtime_profile as profiles
import install_verified_heart as installer


def command(argv, output=None, timeout=300):
    if output is None:
        subprocess.run(argv, check=True, timeout=timeout)
    else:
        with output.open("xb") as stream, output.with_suffix(output.suffix + ".stderr.log").open("x") as errors:
            subprocess.run(argv, stdout=stream, stderr=errors, check=True, timeout=timeout)


def single_artifact(response, name):
    matches = [item for item in response.get("artifacts", []) if item.get("name") == name]
    profiles.require(len(matches) == 1, "Exactly one original named artifact is required: " + name)
    return matches[0]


def extract_payload(archive, name, directory):
    with zipfile.ZipFile(archive) as zipped:
        profiles.require(zipped.namelist() == [name], "Unexpected original GitHub artifact payload")
        item = zipped.infolist()[0]
        profiles.require(not item.is_dir() and 0 < item.file_size <= 2 * 1024**3
                         and (item.external_attr >> 16) & 0o170000 != 0o120000,
                         "Runtime artifact payload is not one bounded regular file")
        destination = directory / name
        with zipped.open(item) as source, destination.open("xb") as output:
            shutil.copyfileobj(source, output)
    return destination


def fetch_corrected(args, profile):
    producer_path = args.evidence / "original-producer-run.json"
    command(["gh", "api", "repos/" + args.repository + "/actions/runs/" + args.source_run_id],
            producer_path, timeout=120)
    run = json.loads(producer_path.read_bytes())
    producer = profiles.validate_producer(run, args.source_run_id, args.repository, args.expected_app_branch)
    artifacts_path = args.evidence / "original-artifact-list.json"
    command(["gh", "api", "repos/" + args.repository + "/actions/runs/" + args.source_run_id + "/artifacts?per_page=100"],
            artifacts_path, timeout=120)
    response = json.loads(artifacts_path.read_bytes())
    profiles.require(response.get("total_count", len(response.get("artifacts", []))) <= 100,
                     "Artifact inventory requires explicit pagination before admission")
    names = dict(runtime=profile.artifact_name,
                 proof="Pinkha-T5-Attachment-Runtime-" + profile.name + "-" + args.source_run_id + "-" + producer["run_attempt"])
    downloaded = dict(status="VERIFYING", producer=producer, artifacts={}, archive_sha256={}, payload_sha256={})
    payloads = {}
    for kind, name in names.items():
        item = single_artifact(response, name)
        expected = profiles.validate_artifact(item, run, name)
        directory = args.work / kind
        directory.mkdir()
        archive = directory / "original-github-artifact.zip"
        command(["gh", "api", "repos/" + args.repository + "/actions/artifacts/" + str(item["id"]) + "/zip"],
                archive, timeout=600)
        profiles.require(digest(archive) == expected and archive.stat().st_size == item["size_in_bytes"],
                         "Downloaded original GitHub ZIP differs from its digest/size")
        payload = profile.archive_name if kind == "runtime" else "Pinkha-Native-Derived-Evidence.zip"
        payloads[kind] = extract_payload(archive, payload, directory)
        downloaded["artifacts"][kind] = item
        downloaded["archive_sha256"][kind] = expected
        downloaded["payload_sha256"][kind] = digest(payloads[kind])
    downloaded["status"] = "VERIFIED_ORIGINAL_GITHUB_ARTIFACTS"
    download_path = args.evidence / "original-runtime-download.json"
    download_path.write_text(json.dumps(downloaded, indent=2) + "\n", encoding="utf8")
    source = args.work / "source"
    source.mkdir()
    with zipfile.ZipFile(payloads["proof"]) as proof:
        paths = dict(
            patch="runtime/corrected-native-source/native-heart-integration.patch.txt",
            inventory="runtime/corrected-native-source/native-heart-integration.json")
        for field, name in paths.items():
            entries = [item for item in proof.infolist() if item.filename == name]
            profiles.require(len(entries) == 1 and not entries[0].is_dir()
                             and 0 < entries[0].file_size <= 2 * 1024**2,
                             "Original corrected source member is missing or repeated")
            path = source / ("native-heart-integration.patch" if field == "patch" else "native-heart-integration.json")
            path.write_bytes(proof.read(entries[0]))
            setattr(args, field, path)
    args.archive = payloads["runtime"]
    args.producer_run, args.producer_proof, args.download_receipt = producer_path, payloads["proof"], download_path


def execute(args):
    profiles.require(args.source_run_id.isascii() and args.source_run_id.isdigit()
                     and args.source_run_id != "0", "Explicit positive Heart producer run ID required")
    profile = profiles.select(args.runtime_profile)
    args.app_source, args.work, args.evidence = (path.resolve() for path in
                                                (args.app_source, args.work, args.evidence))
    profiles.require(not args.work.exists(), "Fresh owned Heart download directory required")
    args.work.mkdir(parents=True)
    args.evidence.mkdir(parents=True, exist_ok=True)
    if profile.name == profiles.COHERENT:
        from coherent_runtime_admission import execute as install_coherent
        installed = install_coherent(args, profile, command)
        if os.environ.get("UI27_ACCEPTANCE_LANE") in {"hanlin-selection", "miniapps-native"}:
            import sys
            sys.path.insert(0, str(args.app_source / "Tools/MiniApps"))
            from acceptance_profile import resolve_profile
            requested_lane = os.environ["UI27_ACCEPTANCE_LANE"]
            branch = subprocess.check_output(["git", "-C", str(args.app_source),
                                              "branch", "--show-current"], text=True).strip()
            if resolve_profile(args.app_source, requested_lane, branch) is not None:
                from run_native_acceptance import prepare_authenticated_dependencies
                prepare_authenticated_dependencies(args.app_source, args.evidence.parent,
                    args.work / "miniapps-producer", requested_lane,
                    args.runtime_profile, args.source_run_id)
        return installed
    if profile.name == "r14":
        # Preserve the existing original r14 route, filename and approval inputs.
        command(["gh", "run", "download", args.source_run_id, "--repo", args.repository,
                 "--name", profile.artifact_name, "--dir", str(args.work)], timeout=600)
        args.archive = args.work / profile.archive_name
        approval = args.app_source / attachment_runtime.APPROVAL_ROOT / "revision-14"
        args.patch, args.inventory = approval / "native-heart-integration.patch", approval / "native-heart-integration.json"
        args.producer_run = args.producer_proof = args.download_receipt = None
    else:
        fetch_corrected(args, profile)
    return installer.install(args)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--runtime-profile", choices=profiles.PROFILE_NAMES, default="r14")
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--expected-app-branch", required=True, choices=installer.APPROVED_BRANCHES)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"), required=not os.environ.get("GITHUB_REPOSITORY"))
    for name in ("app-source", "work", "evidence"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(execute(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
