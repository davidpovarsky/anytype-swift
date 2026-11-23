"""Restore one fixed original SDK06 native build without rebuilding that App.

Current controller identity, the failed original build origin, and the first
UI-only build have separate receipts. No archive label qualifies a product test.
"""
from __future__ import annotations

import base64
import copy
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import sdk06_original_native_descriptors as generated_descriptors

PROTOCOL = "sdk06-original-native-continuation-v1"
ROOT = Path(__file__).resolve().parents[2]
ADMISSION = "Tools/PinkhaSimulatorGate/sdk06-original-native-45139431216-1.json"
ADMISSION_SHA256 = "1bbba8e7578e9ba4c56d4074c45690ca592e098c89578637a4c603bbd792e9c6"
SOURCE = "75bd6d7af18dfd511e85582ce7f994d2801b7703"
RUN = "45139431216"
ATTEMPT = "1"
REPOSITORY = "davidpovarsky/anytype-swift"
PROFILE = "sdk06-qualified"
RUNTIME_PROFILE = "r15-attachment-authorized-current-read-v1"
PRODUCER_RUN = "45091223011"
_SEAL = object()


def require(value, message):
    if not value:
        raise ValueError(message)


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def read(path, maximum=16 * 1024**2):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum,
            "A bounded original regular JSON file is required")
    return json.loads(path.read_bytes())


def save(path, value, *, original=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    with path.open("xb" if original else "wb") as output:
        output.write(raw)


def relative(name):
    require(isinstance(name, str) and name and "\\" not in name and "\x00" not in name,
            "Invalid archive/source member")
    value = PurePosixPath(name)
    require(not value.is_absolute() and str(value) == name and
            all(part not in {"", ".", ".."} and ":" not in part for part in value.parts),
            "Archive/source member escapes its exact root")
    return value


def regular(root, name):
    value = relative(name)
    path = root.joinpath(*value.parts)
    current = root
    for part in value.parts:
        current = current / part
        require(not current.is_symlink(), "A source/product path traverses a link")
    require(path.is_file() and path.resolve().is_relative_to(root.resolve()),
            "Source/product regular file is absent")
    return path


def manifest(control):
    raw = regular(control, ADMISSION).read_bytes()
    require(digest_bytes(raw) == ADMISSION_SHA256, "The fixed original-native admission changed")
    value = json.loads(raw)
    require(value.get("protocol") == PROTOCOL and value.get("original_source_sha") == SOURCE
            and value.get("original_run_id") == RUN and value.get("original_run_attempt") == ATTEMPT
            and value.get("original_workflow_conclusion") == "failure"
            and value.get("original_product_tests_executed") == 0,
            "Original build identity must retain its actual failure and zero product methods")
    return value


def verify_api(run, artifact, contract):
    require(type(run.get("id")) is int and run["id"] == int(RUN)
            and type(run.get("run_attempt")) is int and run["run_attempt"] == int(ATTEMPT)
            and run.get("head_sha") == SOURCE and run.get("head_branch") == contract["original_branch"]
            and run.get("event") == "workflow_dispatch" and run.get("status") == "completed"
            and run.get("conclusion") == "failure"
            and run.get("repository", {}).get("full_name") == REPOSITORY
            and run.get("path") == ".github/workflows/torah-inspector-ipados27.yml",
            "Original failed workflow identity differs")
    expected = contract["artifact"]
    require(type(artifact.get("id")) is int and artifact["id"] == expected["id"]
            and artifact.get("name") == expected["name"]
            and artifact.get("size_in_bytes") == expected["bytes"]
            and artifact.get("digest") == "sha256:" + expected["sha256"]
            and artifact.get("expired") is False
            and artifact.get("workflow_run", {}).get("id") == int(RUN)
            and artifact["workflow_run"].get("head_sha") == SOURCE
            and artifact["workflow_run"].get("head_branch") == contract["original_branch"],
            "The exact original artifact is unavailable or belongs to another source")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(path, *, redirect=False):
    token = os.environ.get("GH_TOKEN", "")
    require(token and "\n" not in token, "Current workflow read token is required")
    request = urllib.request.Request("https://api.github.com/repos/" + REPOSITORY + path,
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": PROTOCOL})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=60) as response:
            require(not redirect and response.status == 200, "Unexpected original API status")
            raw = response.read(4 * 1024**2 + 1)
            require(len(raw) <= 4 * 1024**2, "Oversized original API metadata")
            return raw
    except urllib.error.HTTPError as error:
        require(redirect and error.code == 302, "Original API request failed")
        location = error.headers.get("Location", "")
        parsed = urllib.parse.urlsplit(location)
        require(parsed.scheme == "https" and parsed.hostname
                and (parsed.hostname.endswith(".blob.core.windows.net")
                     or parsed.hostname.endswith(".githubusercontent.com")),
                "Unexpected original artifact storage endpoint")
        return location  # Memory only; never save or print an authenticated redirect.


def download_original(control, work, evidence, contract):
    require(not work.exists() and not work.is_symlink(), "Fresh original-native work directory required")
    work.mkdir(parents=True)
    audit = evidence / "original-native-api"
    audit.mkdir(parents=True, exist_ok=False)
    run_raw = api("/actions/runs/" + RUN + "/attempts/" + ATTEMPT)
    artifact_raw = api("/actions/artifacts/" + str(contract["artifact"]["id"]))
    (audit / "run.json").write_bytes(run_raw)
    (audit / "artifact.json").write_bytes(artifact_raw)
    verify_api(json.loads(run_raw), json.loads(artifact_raw), contract)
    expected = contract["artifact"]
    destination = work / "original-artifact.zip"
    partial = work / "original-artifact.zip.partial"
    require(shutil.disk_usage(work).free >= expected["bytes"] + contract["restoration_disk_bytes"] + 2_500_000_000,
            "Insufficient owned disk for exact restoration and reserve")
    address = api("/actions/artifacts/" + str(expected["id"]) + "/zip", redirect=True)
    started = time.monotonic()
    count, hasher = 0, hashlib.sha256()
    receipt = {"protocol": PROTOCOL, "status": "DOWNLOADING", "artifact": expected,
               "original_run_id": RUN, "original_source_sha": SOURCE}
    try:
        # The storage request deliberately carries no GitHub Authorization header.
        with urllib.request.urlopen(urllib.request.Request(address,
                headers={"Accept-Encoding": "identity"}), timeout=60) as source, partial.open("xb") as output:
            require(source.status == 200
                    and source.headers.get("Content-Encoding", "identity") == "identity",
                    "Unexpected original artifact body encoding/status")
            length = source.headers.get("Content-Length")
            require(length is None or int(length) == expected["bytes"], "Original artifact size header differs")
            while True:
                require(time.monotonic() - started <= 1200, "Original artifact download deadline exceeded")
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                require(count <= expected["bytes"], "Original artifact exceeded its API-bound size")
                output.write(chunk)
                hasher.update(chunk)
            output.flush()
            os.fsync(output.fileno())
        require(count == expected["bytes"] and hasher.hexdigest() == expected["sha256"],
                "Original artifact size or full SHA differs")
        partial.rename(destination)
        destination.chmod(0o444)
        receipt.update(status="EXACT_ORIGINAL_ARCHIVE_VERIFIED", bytes=count, sha256=hasher.hexdigest())
    except BaseException as error:
        receipt.update(status="FAIL_ORIGINAL_PARTIAL_PRESERVED", error_type=type(error).__name__,
                       # Network errors may contain signed URLs; preserve only their class here.
                       failure_scope="ORIGINAL_API_OR_BODY_INTEGRITY")
        raise RuntimeError("Original archive acquisition failed; bounded receipt preserved") from None
    finally:
        receipt["bytes_observed"] = count
        save(audit / "download.json", receipt, original=True)
    return destination


def copy_member(archive, name, destination, expected, maximum):
    member = archive.getinfo(name)
    require(member.filename == name and not member.is_dir() and not member.flag_bits & 1
            and not stat.S_ISLNK(member.external_attr >> 16)
            and member.file_size == expected["bytes"] <= maximum,
            "Unexpected fixed original ZIP member")
    require(not destination.exists() and not destination.is_symlink(), "Refuse stale original member output")
    destination.parent.mkdir(parents=True, exist_ok=True)
    hasher, count = hashlib.sha256(), 0
    with archive.open(member) as source, destination.open("xb") as output:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            require(count <= expected["bytes"], "Original member exceeds its bound")
            hasher.update(chunk)
            output.write(chunk)
    require(count == expected["bytes"] and hasher.hexdigest() == expected["sha256"],
            "Original ZIP member bytes differ")
    return {"path": str(destination), "bytes": count, "sha256": hasher.hexdigest()}


def validate_product_manifest(value, contract):
    expected = contract["native_archive"]
    require(value.get("source_sha") == SOURCE and value.get("run_id") == RUN
            and value.get("run_attempt") == ATTEMPT
            and value.get("status") == "OBSERVED_PRODUCTS_ARCHIVED_BEFORE_ADMISSION"
            and value.get("archive_bytes") == expected["bytes"]
            and value.get("archive_sha256") == expected["sha256"]
            and value.get("build_flags") == contract["native_build_flags"]
            and value.get("source_inputs_present") is True
            and all(value.get(key) is False for key in
                    ("build_reuse_enabled", "every_entry_build_origin_verified",
                     "native_acceptance_reused", "ui_acceptance_reused")),
            "The original archive receipt cannot be relabelled as build/test acceptance")
    entries = value.get("products", {})
    require(len(entries) == expected["entries"]
            and sum(row.get("kind") == "file" for row in entries.values()) == expected["files"]
            and sum(row.get("kind") == "directory" for row in entries.values()) == expected["directories"],
            "Original native product inventory differs")
    for name, row in entries.items():
        relative(name)
        require(name.startswith("Build/") and row.get("kind") in {"file", "directory"}
                and type(row.get("mode")) is int and 0 <= row["mode"] <= 0o777,
                "Unsupported original product entry")
    for name, row in contract["native_carriers"].items():
        require(entries.get(name) == row, "Original native executable or descriptor identity differs")
    return entries


def git_tree(app):
    raw = subprocess.check_output(["git", "-C", str(app), "ls-tree", "-r", "-z", SOURCE], timeout=30)
    result = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        meta, name = entry.split(b"\t", 1)
        mode, kind, object_id = meta.decode().split()
        path = name.decode("utf-8")
        require(kind == "blob" and mode in {"100644", "100755"}, "Unexpected original tracked entry")
        relative(path)
        require(path not in result, "Duplicate original tracked source")
        result[path] = {"git_mode": mode, "git_blob": object_id}
    return result


def fingerprint(path):
    value = path.lstat()
    require(stat.S_ISREG(value.st_mode), "A bound regular source/product became non-regular")
    return {"bytes": value.st_size, "mode": stat.S_IMODE(value.st_mode),
            "device": str(value.st_dev), "inode": str(value.st_ino), "mtime_ns": str(value.st_mtime_ns)}


def verify_app_source(app, source_inputs, contract, *, hashes=True):
    require(subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"],
            text=True, timeout=30).strip() == SOURCE, "The original immutable App checkout differs")
    require(not subprocess.check_output(["git", "-C", str(app), "status", "--porcelain",
            "--untracked-files=no"], text=True, timeout=30), "Original tracked App source is dirty")
    require(source_inputs.get("source_sha") == SOURCE, "Original native source map belongs to another App")
    inputs = source_inputs.get("inputs", {})
    tree = git_tree(app)
    require(len(tree) == contract["tracked_source_count"]
            and set(inputs) == set(tree) | set(contract["original_untracked_framework_inputs"]),
            "The exact original tracked and auxiliary source inventories differ")
    for name, expected in contract["original_untracked_framework_inputs"].items():
        require(inputs[name]["sha256"] == expected, "Original framework source origin differs")
    observations = {}
    for name, row in tree.items():
        path = regular(app, name)
        value = fingerprint(path)
        require(bool(value["mode"] & 0o111) == (row["git_mode"] == "100755"),
                "Original source executable mode differs")
        if hashes:
            require(sha(path) == inputs[name]["sha256"], "Original tracked source bytes differ: " + name)
        observations[name] = {**row, **value, "sha256": inputs[name]["sha256"]}
    return observations


def verify_original_execution(value, contract):
    require(value.get("source_sha") == SOURCE and value.get("run_id") == RUN
            and value.get("run_attempt") == ATTEMPT and value.get("status") == "FAIL"
            and value.get("phase") == "SHARED_EDITOR_COMPONENTS"
            and value.get("native_build_succeeded") is True
            and value.get("current_controller_sources_unchanged") is True
            and value.get("native_build_flags") == contract["native_build_flags"]
            and value.get("shared_editor_components", {}).get("phase") == "ENUMERATION_PRECHECK"
            and value.get("shared_editor_components", {}).get("status") == "FAIL"
            and value.get("text_native_acknowledgement", {}).get("status") == "NOT_RUN"
            and "preparation" not in value and "ui" not in value,
            "The original failed selection/native build boundary differs")
    require(value.get("runtime_installation", {}).get("source_run_id") == PRODUCER_RUN
            and value["runtime_installation"].get("runtime_profile") == RUNTIME_PROFILE,
            "Original native framework producer/profile differs")


def restore_original(control, app, work, evidence, derived, contract):
    from sdk06_enumeration_probe import extract_products
    archive = work / "original-artifact.zip"
    require(archive.stat().st_size == contract["artifact"]["bytes"]
            and sha(archive) == contract["artifact"]["sha256"], "The original archive changed before restore")
    originals = evidence / "original-native"
    originals.mkdir(parents=True, exist_ok=False)
    inner_path = work / "original-evidence.zip"
    with zipfile.ZipFile(archive) as outer:
        require(len(outer.infolist()) == 1, "Unexpected outer original archive inventory")
        copy_member(outer, contract["inner_archive"]["path"], inner_path,
                    contract["inner_archive"], contract["inner_archive"]["bytes"])
    with zipfile.ZipFile(inner_path) as inner:
        names = [item.filename for item in inner.infolist()]
        require(len(names) == contract["inner_member_count"] and len(names) == len(set(names))
                and len(names) == len({name.casefold() for name in names}), "Original inner ZIP inventory differs")
        for name in names:
            relative(name)
        for name, expected in contract["metadata_members"].items():
            copy_member(inner, name, originals / name, expected, 8 * 1024**2)
        tar_path = work / "original-native-products.tar.gz"
        copy_member(inner, contract["native_archive"]["path"], tar_path,
                    contract["native_archive"], contract["native_archive"]["bytes"])
    product_manifest = read(originals / contract["native_archive"]["manifest_path"])
    entries = validate_product_manifest(product_manifest, contract)
    execution = read(originals / "execution.json")
    verify_original_execution(execution, contract)
    source_map = read(originals / "compiled-products/source-inputs.json")
    source_before = verify_app_source(app, source_map, contract)
    low_level = extract_products(tar_path, derived, product_manifest)
    require(low_level["entries"] == len(entries), "Actual restoration omitted original entries")
    structural_parents = generated_descriptors.original_tree(derived, entries)
    require(sha(regular(derived, "Build/PinkhaSourceInputs.json")) ==
            contract["metadata_members"]["compiled-products/source-inputs.json"]["sha256"],
            "Embedded original build source map differs")
    products = {name: fingerprint(regular(derived, name)) for name, row in entries.items()
                if row["kind"] == "file"}
    heart = regular(app, "Dependencies/Middleware/PinkhaNativeHeartBuild.json") if (
        app / "Dependencies/Middleware/PinkhaNativeHeartBuild.json").exists() else None
    require(heart is None, "Fresh original App must not contain an unadmitted Heart build receipt")
    target = app / "Dependencies/Middleware/PinkhaNativeHeartBuild.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as output:
        output.write((originals / "heart/custom-heart-build.json").read_bytes())
    heart_evidence = evidence / "heart"
    heart_evidence.mkdir(exist_ok=False)
    with (heart_evidence / "heart-installation.json").open("xb") as output:
        output.write((originals / "heart/heart-installation.json").read_bytes())
    receipt = {
        "protocol": PROTOCOL, "status": "ORIGINAL_NATIVE_BYTES_RESTORED_SELECTION_NOT_RUN",
        "original_source_sha": SOURCE, "original_run_id": RUN, "original_run_attempt": ATTEMPT,
        "artifact": contract["artifact"], "native_archive": contract["native_archive"],
        "low_level_restore_observation": low_level,
        "structural_parent_directories": structural_parents,
        "original_workflow_conclusion": "failure", "original_product_tests_executed": 0,
        "native_builds_this_run": 0, "ui_builds_this_run": 0,
        "source_fingerprints": source_before, "product_fingerprints": products,
        "original_untracked_framework_source_recreated": False,
        "original_untracked_framework_inputs": contract["original_untracked_framework_inputs"],
        "selector_qualified": False, "sdk06_accepted": False,
        "archive_entry_build_origin_claim": False,
    }
    save(evidence / "original-native-restoration.json", receipt, original=True)
    return receipt


def normalize_descriptor(derived, evidence, runtime, contract):
    import sdk06_enumeration_probe as normalizer
    original = regular(derived, contract["descriptor"]["path"])
    require(sha(original) == contract["descriptor"]["sha256"], "Original native descriptor differs")
    host = original.with_name("UI27-original-sdk06-host.xctestrun")
    require(not host.exists() and not host.is_symlink(), "Host-normalized descriptor must be fresh")
    raw = original.read_bytes()
    value = plistlib.loads(raw)
    require(value.get("__xctestrun_metadata__", {}).get("FormatVersion") == 2
            and len(value.get("TestConfigurations", [])) == 1, "Original descriptor shape differs")
    observations = {}
    for target in value["TestConfigurations"][0]["TestTargets"]:
        observations[target["BlueprintName"]] = normalizer.normalize_runtime_injection(
            target, runtime, expected_original_token=contract["descriptor"]["main_thread_checker_token"])
    with host.open("xb") as output:
        plistlib.dump(value, output, sort_keys=False)
    require(original.read_bytes() == raw, "Original descriptor was modified")
    result = {
        "original_path": str(original), "original_sha256": digest_bytes(raw),
        "host_path": str(host), "host_sha256": sha(host),
        "original_bytes_base64": base64.b64encode(raw).decode("ascii"),
        "host_bytes_base64": base64.b64encode(host.read_bytes()).decode("ascii"),
        "normalization": observations,
        "change_scope": "EXACT_ORIGINAL_MAIN_THREAD_CHECKER_TOKEN_ONLY_IN_HOST_COPY",
    }
    save(evidence / "original-native-descriptor-chain.json", result, original=True)
    return result


@dataclass(frozen=True)
class SDK06OriginalNativeContext:
    control: Path
    app: Path
    work: Path
    evidence: Path
    derived: Path
    binding_json: str
    restoration_json: str
    descriptor_json: str
    device_json: str
    _seal: object = field(repr=False)
    _generated_descriptors: dict = field(default_factory=dict, repr=False, compare=False)

    @property
    def execution_binding(self):
        return json.loads(self.binding_json)

    @property
    def descriptor_binding(self):
        return json.loads(self.descriptor_json)

    @property
    def device(self):
        return json.loads(self.device_json)

    @property
    def native_configuration(self):
        return Path(self.descriptor_binding["host_path"])

    @property
    def tag_contract(self):
        value = manifest(self.control)
        data = regular(self.app, value["tag_contract"]["path"]).read_bytes()
        require(digest_bytes(data) == value["tag_contract"]["sha256"], "Original tag declarations changed")
        return json.loads(data)

    def origin_reference(self):
        value = manifest(self.control)
        return {"mode": "ORIGINAL_NATIVE_PRODUCTS_EXACT_RESTORATION",
                "original_source_sha": SOURCE, "original_run_id": RUN, "original_run_attempt": ATTEMPT,
                "original_artifact_id": value["artifact"]["id"],
                "original_artifact_sha256": value["artifact"]["sha256"],
                "original_native_archive_sha256": value["native_archive"]["sha256"],
                "original_descriptor_sha256": value["descriptor"]["sha256"],
                "original_workflow_conclusion": "failure", "original_product_tests_executed": 0}

    def record_fields(self):
        return {"build_mode": "ORIGINAL_NATIVE_PRODUCTS_EXACT_RESTORATION",
                "controller_source_sha": self.execution_binding["source_sha"],
                "original_native_origin": self.origin_reference(),
                "original_native_build_succeeded": True, "native_builds_this_run": 0,
                "native_acceptance_reused": False, "ui_acceptance_reused": False}

    def verify_descriptor_binding(self):
        value = self.descriptor_binding
        require(sha(Path(value["original_path"])) == value["original_sha256"]
                and sha(Path(value["host_path"])) == value["host_sha256"],
                "An original or normalized descriptor changed")
        require(digest_bytes(base64.b64decode(value["original_bytes_base64"], validate=True)) ==
                value["original_sha256"]
                and digest_bytes(base64.b64decode(value["host_bytes_base64"], validate=True)) ==
                value["host_sha256"], "Descriptor original byte proof differs")

    def verify_current(self, *, full=False, _pending_descriptor=None):
        from sdk06_original_native_continuation import verify_controller
        require(self._seal is _SEAL and self.control == ROOT and self.app != self.control,
                "Unsealed original-native source context")
        verify_controller(self.control, self.execution_binding)
        contract = manifest(self.control)
        saved = read(self.evidence / "original-native-restoration.json")
        require(saved == json.loads(self.restoration_json), "Restoration receipt changed")
        require(subprocess.check_output(["git", "-C", str(self.app), "rev-parse", "HEAD"],
                text=True, timeout=30).strip() == SOURCE, "Original App source moved")
        for name, row in contract["metadata_members"].items():
            path = regular(self.evidence / "original-native", name)
            require(path.stat().st_size == row["bytes"] and sha(path) == row["sha256"],
                    "An original source/build receipt changed")
        entries = read(self.evidence / "original-native" / contract["native_archive"]["manifest_path"])["products"]
        additions = generated_descriptors.verify(self.derived, entries,
            saved["structural_parent_directories"], self.evidence, self.execution_binding,
            pending=_pending_descriptor)
        require(additions == self._generated_descriptors, "Admitted descriptor addition ledger changed")
        for name, row in entries.items():
            if row["kind"] == "directory":
                path = self.derived / relative(name)
                require(path.is_dir() and not path.is_symlink()
                        and stat.S_IMODE(path.lstat().st_mode) == row["mode"],
                        "An original product directory changed")
        for name, expected in saved["source_fingerprints"].items():
            path = regular(self.app, name)
            observed = fingerprint(path)
            require(observed == {key: expected[key] for key in observed},
                    "Original tracked App metadata changed: " + name)
            if full:
                require(sha(path) == expected["sha256"], "Original tracked App bytes changed")
        for name, expected in saved["product_fingerprints"].items():
            path = regular(self.derived, name)
            require(fingerprint(path) == expected, "An original native product changed: " + name)
            if full:
                require(sha(path) == entries[name]["sha256"], "An original native product's bytes changed")
        require(sha(regular(self.app, "Dependencies/Middleware/PinkhaNativeHeartBuild.json")) ==
                contract["metadata_members"]["heart/custom-heart-build.json"]["sha256"],
                "Original native runtime receipt changed")
        self.verify_descriptor_binding()
        return contract

    def register_generated_descriptor(self, path, purpose):
        contract = self.verify_current(_pending_descriptor=(path, purpose))
        entries = read(self.evidence / "original-native" / contract["native_archive"]["manifest_path"])["products"]
        row = generated_descriptors.register(self.derived, entries,
            json.loads(self.restoration_json)["structural_parent_directories"],
            self.evidence, self.execution_binding, path, purpose)
        self._generated_descriptors[row["path"]] = row
        self.verify_current()
        return row

    def validate_execution_identity(self, app, preflight):
        self.verify_current()
        require(Path(app).resolve() == self.app
                and all(preflight.get(name) == value for name, value in self.execution_binding.items())
                and preflight.get("selected", {}).get("ipad") == self.device,
                "Current owned preflight or original App origin differs")

    def verify_native_build(self, app, head, identity, flags, configuration):
        contract = self.verify_current()
        require(Path(app).resolve() == self.app and head == SOURCE
                and flags == contract["native_build_flags"] and configuration == "Debug-Anytype",
                "Original native build configuration or source differs")
        execution = read(self.evidence / "original-native/execution.json")
        require(identity["hashes"] == execution["candidate_input_hashes"],
                "The exact original App candidate closure differs")

    def verify_kit(self):
        contract = manifest(self.control)
        row = contract["package_lock"]
        data = regular(self.app, row["path"]).read_bytes()
        require(len(data) == row["bytes"] and digest_bytes(data) == row["sha256"],
                "Original App package lock changed")
        lock = json.loads(data)
        require(next(pin["state"]["revision"] for pin in lock["pins"]
                     if pin["identity"] == "torahinspectorkit") == contract["kit_sha"],
                "Original Kit pin differs")
        execution = read(self.evidence / "original-native/execution.json")
        require(execution.get("kit_sha") == contract["kit_sha"], "Original actual Kit observation differs")
        return {"status": "ORIGINAL_BUILD_KIT_AND_EXACT_LOCK_BOUND",
                "kit_sha": contract["kit_sha"], "sourcepackages_checkout_recreated": False,
                "original_execution_sha256": contract["metadata_members"]["execution.json"]["sha256"]}

    def build_first_ui(self, base, flags, methods, ui_derived, shared):
        contract = self.verify_current(full=True)
        require(ui_derived == self.derived.with_name(self.derived.name + "-ui")
                and not ui_derived.exists() and not ui_derived.is_symlink(),
                "The first UI-only build requires a fresh separate output directory")
        require(base == ["xcodebuild", "build-for-testing", "-configuration", "Debug-Anytype",
                "-destination", "platform=iOS Simulator,id=" + self.device["udid"],
                "-parallel-testing-enabled", "NO"]
                and flags == contract["native_build_flags"] and methods == contract["ui_methods"],
                "Unexpected first UI-only build command scope")
        import shared_editor_existing_build as component
        components = read(self.evidence / "shared-editor-components/execution.json")
        require(components.get("status") == component.PASS_STATUS
                and components.get("build_mode") == "ORIGINAL_NATIVE_PRODUCTS_EXACT_RESTORATION"
                and components.get("original_native_origin") == self.origin_reference()
                and components.get("actual", {}).get("actual_method_count") == 23
                and components.get("actual", {}).get("declared_case_count") == 32,
                "All pending component methods and argument cases must pass before UI build")
        ack = read(self.evidence / "text-native-ack/result.json")
        preparation = read(self.evidence / "preparation/result.json")
        require(all(value.get("status") == "PASS" and value.get("passed") == count
                    and value.get("failed") == value.get("skipped") == 0
                    for value, count in ((ack, 7), (preparation, 1))),
                "The current native acknowledgement and preparation must pass before UI build")
        intent = self.evidence / "first-ui-only-build.json"
        require(not intent.exists(), "A first UI build attempt cannot be repeated")
        save(intent, {"status": "ATTEMPT_STARTED", "native_builds_this_run": 0,
                      "ui_builds_this_run": 1, "original_native_origin": self.origin_reference()},
             original=True)
        project = shared.ui_only_project(self.app)
        require(sha(project / "project.pbxproj") == contract["ui_only_project_sha256"],
                "Generated UI-only target/dependency graph changed")
        scheme = ET.parse(project / "xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme").getroot()
        references = list(scheme.iter("BuildableReference"))
        require(scheme.find("BuildAction").get("buildImplicitDependencies") == "NO"
                and references and all(node.get("BlueprintName") == "PinkhaStage1AcceptanceUITests"
                and node.get("ReferencedContainer") == "container:PinkhaPrebuiltUI.xcodeproj"
                for node in references), "UI-only scheme can reach an unadmitted App target")
        command = [*base, "-project", str(project), "-scheme", "PinkhaPrebuiltUI",
                   "-derivedDataPath", str(ui_derived),
                   *["-only-testing:PinkhaStage1AcceptanceUITests/" + method for method in methods], *flags]
        shared.command(command, self.app, self.evidence)
        self.verify_current(full=True)
        result = {"status": "FIRST_UI_ONLY_BUILD_SUCCEEDED", "command": command,
                  "native_builds_this_run": 0, "ui_builds_this_run": 1,
                  "ui_source_sha": SOURCE, "controller_source_sha": self.execution_binding["source_sha"],
                  "native_products_unchanged": True, "original_native_origin": self.origin_reference()}
        save(self.evidence / "first-ui-only-build-result.json", result, original=True)
        return result

    def run_selection(self, app, configuration, blueprint, udid, selections, environment, evidence, prefix, app_path=None):
        import run_ui27 as shared
        self.verify_current()
        require(Path(app).resolve() == self.app and udid == self.device["udid"],
                "Restored SDK selection must use its original App and current owned UUID")
        if blueprint == "AnytypeTests":
            require(configuration == self.native_configuration and app_path is None,
                    "Native selection must use the exact host-normalized original descriptor")
        else:
            require(blueprint == "PinkhaStage1AcceptanceUITests"
                    and configuration.is_relative_to(self.derived.with_name(self.derived.name + "-ui"))
                    and (self.evidence / "first-ui-only-build-result.json").is_file(),
                    "UI selection requires its first distinct current UI-only build")
        if blueprint == "AnytypeTests":
            import sdk06_original_native_selection as original_selection
            import text_native_ack
            from run_wave15_acceptance import LANES
            require((prefix == "text-native-ack" and selections == text_native_ack.METHODS)
                    or (prefix == "prepare" and selections == [LANES["hanlin-native"]["preparation"]]),
                    "Only the pending exact native ack or preparation selection is permitted")
            result = original_selection.run_selection(app, configuration, blueprint, udid, selections,
                environment, evidence, prefix, app_path,
                register_descriptor=self.register_generated_descriptor)
        else:
            result = shared.run_selection(app, configuration, blueprint, udid, selections,
                                          environment, evidence, prefix, app_path)
        self.verify_current()
        result.update(original_native_origin=self.origin_reference(),
                      controller_source_sha=self.execution_binding["source_sha"],
                      build_mode=("ORIGINAL_NATIVE_PRODUCTS_EXACT_RESTORATION"
                                  if blueprint == "AnytypeTests" else "FIRST_CURRENT_UI_ONLY_BUILD"))
        shared.write(evidence / "result.json", result)
        return result


def load_context(control, app, work, evidence, derived, binding):
    contract = manifest(control)
    restored = read(evidence / "original-native-restoration.json")
    require(restored.get("status") == "ORIGINAL_NATIVE_BYTES_RESTORED_SELECTION_NOT_RUN"
            and restored.get("original_source_sha") == SOURCE
            and restored.get("artifact") == contract["artifact"]
            and restored.get("native_archive") == contract["native_archive"],
            "Exact current physical restoration is missing")
    preflight = read(evidence / "preflight/preflight.json")
    require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN"
            and all(preflight.get(key) == value for key, value in binding.items()),
            "Current owned SDK preflight is missing")
    device = preflight["selected"]["ipad"]
    descriptor = normalize_descriptor(derived, evidence, device["runtime"], contract)
    result = SDK06OriginalNativeContext(control, app, work, evidence, derived,
        json.dumps(binding, sort_keys=True), json.dumps(restored, sort_keys=True),
        json.dumps(descriptor, sort_keys=True), json.dumps(device, sort_keys=True), _SEAL)
    result.register_generated_descriptor(result.native_configuration, "host-normalization")
    result.verify_current(full=True)
    return result
