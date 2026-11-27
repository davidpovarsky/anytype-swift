#!/usr/bin/env python3
"""Create a concrete new-source input contract from original retained receipts.

The 'controls' subcommand records exact Git blobs without changing a checkout.
The 'input' subcommand references actual original build inputs; it cannot mark
an application accepted, invent compiler results or replace a producer pin.
"""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import sys

import receipt_admission as gate


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def control_manifest(args):
    commit = subprocess.check_output(["git", "-C", str(args.repository), "rev-parse", args.commit + "^{commit}"],
                                     text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(args.repository), "ls-tree", "-r", "-z", commit, "--", "Tools"])
    objects = []
    for row in tree.split(b"\0"):
        if not row:
            continue
        metadata, name = row.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        path = name.decode()
        if path.endswith(".py"):
            gate.require(kind == "blob" and mode in {"100644", "100755"}, "Controller inputs must be regular Git files")
            objects.append((path, oid))
    data = subprocess.run(["git", "-C", str(args.repository), "cat-file", "--batch"],
                          input=("".join(oid + "\n" for _, oid in objects)).encode(),
                          capture_output=True, check=True).stdout
    offset, files = 0, {}
    for name, oid in objects:
        end = data.index(b"\n", offset)
        actual_oid, kind, size = data[offset:end].decode().split()
        size = int(size); offset = end + 1
        blob = data[offset:offset + size]
        gate.require(actual_oid == oid and kind == "blob" and len(blob) == size
                     and data[offset + size:offset + size + 1] == b"\n", "Original Git blob stream differs")
        offset += size + 1
        files[name] = {"bytes": size, "sha256": hashlib.sha256(blob).hexdigest()}
    gate.require(offset == len(data) and gate.REQUIRED_CONTROLS.issubset(files),
                 "Committed controller closure is incomplete")
    value = {"schema": "pinkha.miniapps.controls-source/1", "commit": commit, "files": files}
    write(args.output, value)
    print(json.dumps({"path": str(args.output), "sha256": gate.sha256(args.output),
                      "commit": commit, "files": len(files), "applicationTests": "NOT_RUN"}))


def mapping(values, *, multiple=False):
    result = {}
    for value in values:
        name, separator, path = value.partition("=")
        gate.require(separator and name and path, "Expected NAME=/absolute/original/path")
        reference = gate.make_ref(path)
        if multiple:
            result.setdefault(name, []).append(reference)
        else:
            gate.require(name not in result, "Repeated original input: " + name)
            result[name] = reference
    return result


def has_target(path, target):
    from run_receipt_acceptance import entries
    try:
        entries(path, target)
        return True
    except (ValueError, KeyError, TypeError, plistlib.InvalidFileException):
        return False


def input_contract(args):
    from run_receipt_acceptance import entries, resolve_product, bundle_executable
    build_path = gate.canonical(args.receipt)
    base = build_path.parent
    build = json.loads(build_path.read_bytes())
    before_path = gate.canonical(args.source_before or base / "source-before.json")
    after_path = gate.canonical(args.source_after or base / "source-after.json")
    before = json.loads(before_path.read_bytes())
    products_path = gate.canonical(args.products or base / "products-all.json")
    products = json.loads(products_path.read_bytes())
    controls = json.loads(gate.canonical(args.control_manifest).read_bytes())
    descriptors = {}
    for kind, target in (("app", "AnytypeTests"), ("ui", "PinkhaStage1AcceptanceUITests")):
        slot = kind + "-derived"
        candidates = [row["path"] for row in products[slot]["entries"]
                      if row["kind"] == "file" and row["path"].endswith(".xctestrun")
                      and has_target(Path(products[slot]["base"]) / row["path"], target)]
        gate.require(len(candidates) == 1, "An exact original descriptor must be uniquely discoverable for " + target)
        descriptors[kind] = {"slot": slot, "path": candidates[0]}
    native_descriptor = Path(products["app-derived"]["base"]) / descriptors["app"]["path"]
    _, _, entry = entries(native_descriptor, "AnytypeTests")
    app = resolve_product(entry["TestHostPath"], native_descriptor.parent)
    info, _ = bundle_executable(app)
    schemes = [value for row in info.get("CFBundleURLTypes", []) for value in row.get("CFBundleURLSchemes", [])]
    gate.require("anytype" in schemes, "The original native fixture requires its real anytype URL scheme")
    value = {
        "schema": gate.SCHEMA,
        "source": {"root": str(gate.canonical(args.source, directory=True)), "commit": before["commit"],
                   "tree": before["tree"], "before": gate.make_ref(before_path), "after": gate.make_ref(after_path)},
        "controls": {"root": str(gate.canonical(args.controls, directory=True)), "commit": controls["commit"],
                     "manifest": gate.make_ref(args.control_manifest)},
        "build": {"receipt": gate.make_ref(build_path), "products": gate.make_ref(products_path),
                  "producer": gate.make_ref(args.producer), "assembly": gate.make_ref(args.assembly),
                  "uiGenerator": gate.make_ref(args.ui_generator),
                  "originalUICopy": gate.make_ref(args.original_ui_copy or base / "original-ui-copy.json"),
                  "uiCompilationProof": build["uiCompilationProof"],
                  "nativeCompilationProof": build["nativeCompilationProof"],
                  "inputs": mapping(args.build_input),
                  "logs": {"app": gate.make_ref(args.app_log), "ui": gate.make_ref(args.ui_log)}},
        "dependencyEvidence": mapping(args.dependency, multiple=True),
        "descriptors": descriptors, "bundleID": info["CFBundleIdentifier"],
        "sourceScheme": "anytype", "nativeAppGroup": args.native_app_group,
        "runtime": {"identifier": args.runtime_id, "version": args.runtime_version, "build": args.runtime_build,
                    "architecture": "arm64", "deviceType": args.device_type, "family": args.family},
        "toolchain": [
            {"argv": ["xcodebuild", "-version"], "original": gate.make_ref(args.xcode_log)},
            {"argv": ["xcrun", "swift", "--version"], "original": gate.make_ref(args.swift_log)},
            {"argv": ["xcrun", "--sdk", "iphonesimulator", "--show-sdk-build-version"],
             "original": gate.make_ref(args.sdk_build_log)},
        ],
    }
    write(args.output, value)
    digest = gate.sha256(args.output)
    # A failed admission preserves the concrete candidate and original failure.
    _, proof, _ = gate.admit(args.output, digest)
    write(args.output.with_name(args.output.stem + "-admission.json"), proof)
    print(json.dumps({"contract": str(args.output), "sha256": digest,
                      "sourceCommit": before["commit"], "controllerCommit": controls["commit"],
                      "status": proof["status"], "testsExecuted": 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    control = commands.add_parser("controls")
    control.add_argument("--repository", type=Path, required=True)
    control.add_argument("--commit", required=True)
    control.add_argument("--output", type=Path, required=True)
    control.set_defaults(function=control_manifest)
    make = commands.add_parser("input")
    for name in ("source", "controls", "control-manifest", "receipt", "app-log", "ui-log",
                 "xcode-log", "swift-log", "sdk-build-log", "producer", "assembly", "ui-generator", "output"):
        make.add_argument("--" + name, type=Path, required=True)
    for name in ("source-before", "source-after", "products", "original-ui-copy"):
        make.add_argument("--" + name, type=Path)
    make.add_argument("--build-input", action="append", default=[], required=True)
    make.add_argument("--dependency", action="append", default=[], required=True)
    for name in ("native-app-group", "runtime-id", "runtime-version", "runtime-build", "device-type"):
        make.add_argument("--" + name, required=True)
    make.add_argument("--family", choices=("ipad", "iphone"), required=True)
    make.set_defaults(function=input_contract)
    args = parser.parse_args()
    gate.require(args.output.is_absolute() and not args.output.exists(), "Fresh absolute output is required")
    args.function(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
