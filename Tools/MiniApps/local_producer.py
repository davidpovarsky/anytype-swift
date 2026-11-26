"""Admit a genuine local Mac producer without inventing a GitHub run identity.

The committed consumer pin binds the complete original manifest by SHA-256.
Original build receipt/log/source identity and every extracted app entry are
checked independently. Simulator signatures do not grant device provisioning.
"""
from pathlib import Path
import hashlib
import json
import os
import plistlib
import re
import stat
import subprocess
import zipfile

from simulator_entitlements import read_simulator_entitlements


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def artifact(root, name, expected):
    require(isinstance(name, str) and Path(name).name == name and name not in {"", ".", ".."},
            "A producer evidence name escapes its original directory")
    path = root / name
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Missing or aliased original producer evidence: " + name)
    require(re.fullmatch(r"[0-9a-f]{64}", expected or "") and digest(path) == expected,
            "Original producer evidence digest differs: " + name)
    return path


def inventory(root):
    entries = {}
    root = root.resolve()
    for directory, children, files in os.walk(root, followlinks=False):
        for name in sorted(children + files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(path)
                resolved = (path.parent / target).resolve()
                require(resolved == root or root in resolved.parents,
                        "Companion link escapes its actual bundle")
                entries[relative] = {"kind": "symlink", "target": target}
            elif stat.S_ISDIR(info.st_mode):
                entries[relative] = {"kind": "directory", "mode": stat.S_IMODE(info.st_mode)}
            elif stat.S_ISREG(info.st_mode):
                entries[relative] = {"kind": "file", "sha256": digest(path),
                                     "bytes": info.st_size, "mode": stat.S_IMODE(info.st_mode)}
            else:
                raise ValueError("Unsupported companion filesystem entry")
    return entries


def validate_archive(path, app_name):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate producer archive entry")
        for member in archive.infolist():
            name = Path(member.filename)
            require(not name.is_absolute() and ".." not in name.parts and name.parts
                    and name.parts[0] == app_name, "Producer archive entry escapes its app")
            if stat.S_ISLNK(member.external_attr >> 16):
                require(member.file_size <= 4096, "Oversized producer symbolic link")
                target = Path(archive.read(member).decode("utf8"))
                require(not target.is_absolute(), "Absolute producer symbolic link")
                # Normalize syntactically before extraction, including links that
                # point outside before any later link can be inspected.
                resolved = os.path.normpath(str(name.parent / target))
                require(resolved == app_name or resolved.startswith(app_name + "/"),
                        "Producer symbolic link escapes its app")


def admit(app_source, work, evidence, pin):
    app_source, work, evidence = map(Path, (app_source, work, evidence))
    require(pin.get("execution_origin") == "local-mac" and pin.get("run_id") is None
            and not pin.get("artifact_name"), "Local producer cannot impersonate a CI run")
    require(re.fullmatch(r"[0-9a-f]{40}", pin.get("revision", "")),
            "Local producer requires a full committed source")
    require(isinstance(pin.get("local_manifest_path"), str) and pin["local_manifest_path"],
            "Local producer manifest is not yet pinned")
    manifest_path = Path(pin["local_manifest_path"])
    require(manifest_path.is_absolute() and manifest_path.parent.resolve() == manifest_path.parent,
            "Local producer manifest must have its actual absolute location")
    manifest_path = artifact(manifest_path.parent, manifest_path.name,
                             pin.get("local_manifest_sha256"))
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_bytes())
    require(manifest.get("schema_version") == 1
            and manifest.get("execution_origin") == "local-mac"
            and manifest.get("run_id") is None
            and manifest.get("producer_sha") == pin["revision"]
            and manifest.get("bundle_id") == pin["bundle_id"]
            and manifest.get("build_status") == "EXECUTED_PASS"
            and manifest.get("physical_signing_status") == "NOT_VALIDATED_BY_SIMULATOR",
            "Local compiled companion identity differs from the committed pin")
    receipt_path = artifact(root, manifest["build_receipt_name"], manifest["build_receipt_sha256"])
    build_log = artifact(root, manifest["build_log_name"], manifest["build_log_sha256"])
    receipt = json.loads(receipt_path.read_bytes())
    require(receipt.get("sha") == pin["revision"] and receipt.get("build") == "EXECUTED_PASS",
            "Original successful producer build receipt differs")
    identity_path = artifact(root, "source-identity.json", receipt.get("source_identity_sha256"))
    identity = json.loads(identity_path.read_bytes())
    require(identity == manifest.get("source_identity") and identity.get("commit") == pin["revision"]
            and isinstance(identity.get("tracked_file_sha256"), dict)
            and identity["tracked_file_sha256"]
            and all(re.fullmatch(r"[0-9a-f]{64}", sha) for sha in identity["tracked_file_sha256"].values()),
            "Actual prepared producer source identity differs")
    from local_producer_source import validate_source_identity
    source_repository = pin.get("local_source_repository")
    require(isinstance(source_repository, str) and source_repository,
            "Local producer requires its reviewed actual source repository")
    source_admission = validate_source_identity(identity, Path(source_repository), pin["revision"],
        review_spec=pin.get("local_producer_preparation"), export_directory=root,
        consumer_root=app_source)
    commands_path = root / "commands.jsonl"
    require(commands_path.is_file() and not commands_path.is_symlink(),
            "Original producer build commands are missing")
    commands = [json.loads(line) for line in commands_path.read_text().splitlines()]
    matching = [entry for entry in commands if entry.get("argv") == receipt.get("build_command")
                and entry.get("log") == build_log.name]
    require(len(matching) == 1 and matching[0].get("exit") == 0
            and matching[0].get("sha256") == digest(build_log),
            "Original xcodebuild command does not prove this successful build")
    exported_signature = manifest.get("codesign_verification", {})
    require(exported_signature.get("status") == "EXECUTED_PASS",
            "Producer export signature was not verified")
    artifact(root, exported_signature["log_name"], exported_signature["log_sha256"])
    archive = artifact(root, manifest["archive_name"], manifest["archive_sha256"])
    require(manifest.get("app_relative_path") == "HanlinMiniApps.app",
            "Unexpected original companion bundle path")
    validate_archive(archive, manifest["app_relative_path"])
    work.mkdir(parents=True, exist_ok=False)
    destination = work / "app"
    subprocess.run(["ditto", "-x", "-k", str(archive), str(destination)], check=True)
    built = destination / manifest["app_relative_path"]
    require(built.is_dir() and not built.is_symlink()
            and inventory(built) == manifest.get("app_files"),
            "Extracted complete companion bundle differs from the original build")
    info = plistlib.loads((built / "Info.plist").read_bytes())
    executable_name = info.get("CFBundleExecutable", "")
    require(Path(executable_name).name == executable_name and executable_name
            and executable_name == manifest.get("executable_name")
            and info.get("CFBundleIdentifier") == pin["bundle_id"]
            and "iPhoneSimulator" in info.get("CFBundleSupportedPlatforms", []),
            "Extracted companion is not the required actual simulator app")
    executable = built / executable_name
    require(digest(executable) == manifest["executable_sha256"], "Actual companion executable differs")
    evidence.mkdir(parents=True, exist_ok=True)
    verified = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(built)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    signature_path = evidence / "miniapps-local-codesign.log"
    signature_path.write_bytes(verified.stdout)
    verified.check_returncode()
    embedded = read_simulator_entitlements(executable)
    require("group.com.itorah.shared" in embedded["entitlements"].get(
        "com.apple.security.application-groups", []),
        "Built companion does not carry the shared simulator App Group")
    result = {"status": "VERIFIED_COMPILED_COMPANION", "app": str(built.resolve()),
              "pin": pin, "manifest": manifest, "execution_origin": "local-mac",
              "original_manifest_path": str(manifest_path),
              "original_manifest_sha256": digest(manifest_path),
              "artifact_sha256": digest(archive),
              "actual_signature_log_sha256": digest(signature_path),
              "embedded_entitlements": embedded, "source_admission": source_admission,
              "physical_sharing": "NOT_PROVEN_BY_SIMULATOR"}
    (evidence / "miniapps-producer.json").write_text(json.dumps(result, indent=2) + chr(10))
    return result
