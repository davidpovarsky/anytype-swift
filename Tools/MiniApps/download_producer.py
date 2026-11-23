"""Fetch the exact compiled companion during the workflow's existing artifact-read step."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import time
import zipfile

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def gh_json(endpoint):
    return json.loads(subprocess.check_output(["gh", "api", endpoint], text=True))

def download(app_source, work, evidence):
    app_source, work, evidence = map(Path, (app_source, work, evidence))
    pin = json.loads((app_source / "Tools/MiniApps/producer.json").read_text())
    sdk = json.loads((app_source / "Tools/Hanlin/source.json").read_text())
    require(pin["revision"] == sdk["revision"], "Companion and consumer bridge pins differ")
    work.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=True)
    repository, run_id = pin["repository"], pin["run_id"]
    deadline = time.monotonic() + 1800
    item = None
    while time.monotonic() < deadline:
        run = gh_json(f"repos/{repository}/actions/runs/{run_id}")
        require(run["head_sha"] == pin["revision"], "Companion run uses another source")
        listing = gh_json(f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100")
        matches = [entry for entry in listing["artifacts"] if entry["name"] == pin["artifact_name"] and not entry["expired"]]
        require(len(matches) <= 1, "Repeated companion artifact")
        if matches:
            item = matches[0]
            break
        if run["status"] == "completed":
            raise RuntimeError("Completed companion run did not publish the required simulator app")
        time.sleep(10)
    require(item is not None, "Companion simulator artifact is not ready")
    require(str(item["workflow_run"]["id"]) == run_id and
            item["workflow_run"]["head_sha"] == pin["revision"], "Artifact producer differs")
    archive = work / "original-artifact.zip"
    with archive.open("xb") as output:
        subprocess.run(["gh", "api", f"repos/{repository}/actions/artifacts/{item['id']}/zip"],
                       stdout=output, check=True, timeout=600)
    expected = item.get("digest", "")
    require(expected == "sha256:" + digest(archive), "GitHub companion artifact digest differs")
    with zipfile.ZipFile(archive) as zipped:
        manifests = [name for name in zipped.namelist() if name.rsplit("/", 1)[-1] == "producer-manifest.json"]
        payloads = [name for name in zipped.namelist() if name.rsplit("/", 1)[-1] == "HanlinMiniApps-simulator.zip"]
        require(len(manifests) == len(payloads) == 1, "Exact companion manifest/archive required")
        manifest = json.loads(zipped.read(manifests[0]))
        payload = work / "HanlinMiniApps-simulator.zip"
        with zipped.open(payloads[0]) as source, payload.open("xb") as target:
            shutil.copyfileobj(source, target)
    require(manifest["producer_sha"] == pin["revision"] and str(manifest["run_id"]) == run_id
            and manifest["bundle_id"] == pin["bundle_id"]
            and manifest["build_status"] == "EXECUTED_PASS", "Companion app was not built from the pinned source")
    require(digest(payload) == manifest["archive_sha256"], "Companion app archive digest differs")
    with zipfile.ZipFile(payload) as zipped:
        for member in zipped.infolist():
            path = Path(member.filename)
            require(not path.is_absolute() and ".." not in path.parts, "Unexpected companion archive path")
    destination = work / "app"
    subprocess.run(["ditto", "-x", "-k", str(payload), str(destination)], check=True)
    built = destination / manifest["app_relative_path"]
    require(built.name == "HanlinMiniApps.app" and built.is_dir() and not built.is_symlink(), "Missing actual companion app")
    info = plistlib.loads((built / "Info.plist").read_bytes())
    require(info["CFBundleIdentifier"] == pin["bundle_id"]
            and info["CFBundleExecutable"] == manifest["executable_name"], "Built companion identity differs")
    require("iPhoneSimulator" in info["CFBundleSupportedPlatforms"], "Physical app is not a simulator artifact")
    require(digest(built / info["CFBundleExecutable"]) == manifest["executable_sha256"], "Companion executable differs")
    receipt = dict(status="VERIFIED_COMPILED_COMPANION", app=str(built.resolve()), pin=pin,
                   manifest=manifest, original_run=run, original_artifact=item,
                   artifact_sha256=digest(archive), physical_sharing="NOT_PROVEN_BY_SIMULATOR")
    (evidence / "miniapps-producer.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
