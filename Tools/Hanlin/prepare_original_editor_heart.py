"""Download one recorded original r14 artifact; retain raw producer metadata and hashes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import zipfile

from original_editor_profile import manifest, require

REPOSITORY = "davidpovarsky/anytype-swift"


def verify_metadata(run, artifact, pin):
    require(run.get("id") == pin["run_id"] and run.get("head_sha") == pin["head_sha"]
            and run.get("head_branch") == pin["head_branch"] and run.get("run_attempt") == 1
            and run.get("status") == "completed" and run.get("conclusion") == "success"
            and run.get("repository", {}).get("full_name") == REPOSITORY
            and run.get("event") == "workflow_dispatch"
            and run.get("path") == ".github/workflows/torah-inspector-ipados27.yml"
            and run.get("display_title") == "Pinkha heart-runtime \u00b7 " + pin["head_sha"],
            "Recorded original Heart producer identity/outcome differs")
    bound = artifact.get("workflow_run", {})
    require(artifact.get("id") == pin["artifact_id"] and artifact.get("name") == pin["name"]
            and artifact.get("expired") is False
            and type(artifact.get("size_in_bytes")) is int
            and artifact["size_in_bytes"] == pin["zip_bytes"]
            and artifact.get("digest") == "sha256:" + pin["zip_sha256"]
            and bound.get("id") == pin["run_id"] and bound.get("head_sha") == pin["head_sha"]
            and bound.get("head_branch") == pin["head_branch"],
            "Recorded original Heart artifact identity/digest differs")


def unpack_exact_archive(archive, destination, pin):
    require(archive.stat().st_size == pin["zip_bytes"], "Original Heart ZIP size differs")
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    require(digest == pin["zip_sha256"], "Original Heart ZIP GitHub digest differs")
    name = pin["name"] + ".tar.gz"
    with zipfile.ZipFile(archive) as zipped:
        members = zipped.infolist()
        require(len(members) == 1 and members[0].filename == name and not members[0].is_dir(),
                "Unexpected original Heart ZIP members")
        entry = members[0]
        mode = (entry.external_attr >> 16) & 0o170000
        require(mode in {0, stat.S_IFREG} and 0 < entry.file_size <= 536_870_912,
                "Unexpected original Heart archive type or size")
        target = destination / name
        require(not target.exists(), "Refusing to replace an existing Heart archive")
        with zipped.open(entry) as source, target.open("xb") as sink:
            shutil.copyfileobj(source, sink, 1024 * 1024)
        require(target.stat().st_size == entry.file_size, "Inner original Heart archive length differs")
    with target.open("rb") as source:
        inner_digest = hashlib.file_digest(source, "sha256").hexdigest()
    return {"outer_zip_sha256": digest, "inner_archive_sha256": inner_digest,
            "inner_archive_bytes": target.stat().st_size, "zip_crc_verified": True,
            "archive": str(target)}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    pin = manifest()["heart"]
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "Wrong Heart consumer repository")
    require(args.source_run_id == str(pin["run_id"]), "Unreviewed original Heart source run")
    root = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    output, evidence = args.output.resolve(), args.evidence.resolve()
    require(output.is_relative_to(root / "build") and evidence.is_relative_to(root / "build")
            and output != evidence, "Heart download must remain within owned CI build paths")
    output.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=True)
    receipt = {"status": "RUNNING", "run_id": pin["run_id"], "artifact_id": pin["artifact_id"],
               "consumer_sha": os.environ.get("GITHUB_SHA"), "ui_executed": 0}
    def write(name, data):
        (evidence / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    def api(path):
        result = subprocess.run(["gh", "api", path], check=True, capture_output=True)
        return json.loads(result.stdout)
    try:
        run = api("repos/" + REPOSITORY + "/actions/runs/" + str(pin["run_id"]))
        artifact = api("repos/" + REPOSITORY + "/actions/artifacts/" + str(pin["artifact_id"]))
        write("original-heart-producer-run.json", run)
        write("original-heart-artifact.json", artifact)
        verify_metadata(run, artifact, pin)
        archive = output / "original-heart-github-artifact.zip"
        with archive.open("xb") as sink, (evidence / "original-heart-download.stderr.log").open("wb") as error:
            subprocess.run(["gh", "api", "repos/" + REPOSITORY + "/actions/artifacts/"
                            + str(pin["artifact_id"]) + "/zip"], check=True, stdout=sink, stderr=error)
        receipt.update(unpack_exact_archive(archive, output, pin))
        receipt["status"] = "EXACT_GITHUB_ARTIFACT_VERIFIED_FRAMEWORK_INSTALL_NOT_RUN"
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        write("original-heart-download.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
