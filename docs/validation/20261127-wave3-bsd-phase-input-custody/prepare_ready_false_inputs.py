"""Bind local immutable final-source evidence into ready-false warm drafts only.

No candidate module import, Git/subprocess/network call, Mac path access,
effective approval, producer expansion, staging, build or runtime operation.
The real stager must still verify the transported bundle, physical source,
actual SDK materialization, packages, resources and every original receipt.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re

WORK = Path(__file__).resolve().parents[2]
WARM = WORK / "warm-forward-8f2-source"
CONSUMER = WORK / "warm-focus-editor-runtime-source"
CODE = CONSUMER / "after/Tools/PinkhaDualEngineRuntime/warm_focus_editor"
BASELINE = "8f2c11713fb8a40ae13444104723666ffef68afe"
SDK_REVISION = "c0b118f4de28e6ca1e71219237d1ae1c7fabefd8"
SDK_TREE = "89485be6fc9db276c4359726a33b51284835b23b"
SDK_PUBLICATION_SHA256 = "c9ed7976a67792ec2d3ab3706eadd6a3071276d9f252b1c04f0e4cd01f34bdbd"
SDK_PACKAGE_INVENTORY = {"files": 1011, "sourceBytes": 39812364,
    "gitInventorySHA256": "ce82b072db824b0fbd4cdbab19a745c46349f53ee06874e23355c9c0c5058125"}
BASE = PurePosixPath("/Users/m1/development/anytype-d-active-20261125")
REQUIRED_PACKAGES = {"Packages/HanlinAgentSDK", "Packages/HanlinPlatform",
                     "Packages/HanlinPresentationSDK", "Packages/HanlinMiniAppsBridge"}
SOURCE_PINS = {
    "hanlinSourcePinSHA256": "Tools/Hanlin/source.json",
    "sdkMaterializerSHA256": "Tools/Hanlin/prepare_sdk.py",
    "packageResolvedSHA256": "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
    "page154UITestSHA256": "PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift",
    "uiGeneratorSHA256": "Tools/PinkhaNativeDerived/rerun_original_ui.py",
    "runtimeIdentityHelperSHA256": "Tools/PinkhaDualEngineRuntime/runtime_identity.py",
    "nativeSourceManifestSHA256": "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json",
}
TEMPLATES = {
    "stage": (Path(__file__).resolve().parent / "after/source-staging.unbound.json", "0f55b8154fff8c67426252cc41bd058c3509955b0587a9c3bc06b5fcec43a287"),
    "build": (Path(__file__).resolve().parent / "after/build-admission.unbound.json", "1c8db247bd115cafd305ac783a6488e9e05253fd0d259ca68e8f7b50a77f8b51"),
    "membership": (CODE / "source-membership.json", "5c4711f1b50498d9c2babcb4593795c7b14e5aa7867d6ebbeffdcb6948fc33ee"),
    "originals": (CODE / "original_sources.json", "fccdd0205c1f9047241754fe739994f7baa92def857fa8495faf3fec83abb10c"),
    "selection": (CODE / "priority-runtime-selection.closed.json", "9d4ec5c867a9d03f6d0d41d5c52c7faaafc6116e09c0c135cd3790c76940d170"),
}
TOOLCHAIN = {"xcode": ["xcodebuild", "-version"], "swift": ["xcrun", "swift", "--version"],
             "simulator-sdk": ["xcrun", "--sdk", "iphonesimulator", "--show-sdk-build-version"]}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def decode(raw):
    def unique(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def file_bytes(reference, maximum=16 * 1024**2):
    require(set(reference) == {"path", "sha256"}, "Exact local original path/hash required")
    path = Path(reference["path"])
    require(path.is_absolute() and not path.is_symlink() and path.resolve(strict=True) == path
            and path.is_file() and path.stat().st_size <= maximum, "Bounded original physical input required")
    raw = path.read_bytes()
    require(sha(raw) == reference["sha256"], "Original local input changed: " + str(path))
    return raw


def remote(value):
    require(isinstance(value, str), "An explicit root-selected Mac locator is required")
    path = PurePosixPath(value)
    require(path.is_absolute() and str(path) == value and ".." not in path.parts,
            "Canonical absolute locator spelling required; physical custody is checked only on the Mac")
    return path


def reference_at(path, raw):
    return {"path": str(path), "sha256": sha(raw)}


def bind(spec):
    require(spec["schema"] == "pinkha-forward-warm-final-source-binding-inputs-v1"
            and spec["readyForLocalBinding"] is True, "Actual final immutable source inputs are still unbound")
    templates = {name: decode(file_bytes({"path": str(path), "sha256": expected}))
                 for name, (path, expected) in TEMPLATES.items()}
    stage, build = copy.deepcopy(templates["stage"]), copy.deepcopy(templates["build"])
    sdk_publication_raw = file_bytes(spec["sdkPublicationReceipt"])
    require(len(sdk_publication_raw) == 190591 and sha(sdk_publication_raw) == SDK_PUBLICATION_SHA256,
            "The exact positive original c0b SDK publication receipt is required")
    sdk_publication = decode(sdk_publication_raw)
    require(sdk_publication["schema"] == "pinkha-root-mcp-title-window-new-ref-publication/v1"
            and sdk_publication["state"] == "PASS_SOURCE_ONLY_NEW_REF_PUBLISHED"
            and sdk_publication["candidateCommit"] == SDK_REVISION
            and sdk_publication["candidateTree"] == sdk_publication["expectedTree"] == SDK_TREE
            and sdk_publication["normalPushCompleted"] is True
            and sdk_publication["normalPushReadback"] == SDK_REVISION
            and sdk_publication["commandCustodyBlocked"] is False
            and sdk_publication["firstFailure"] is None
            and sdk_publication["originalSourceWorktreePreserved"] is True
            and sdk_publication["actualPackageByteInventory"] == SDK_PACKAGE_INVENTORY
            and all(sdk_publication[key] == 0 for key in
                    ("compilerInvocations", "materializations", "testsExecuted", "workflowDispatches")),
            "Original SDK publication facts differ; source publication is not materialization or runtime")
    source_sha, source_tree = spec["sourceCommit"], spec["sourceTree"]
    require(re.fullmatch(r"[0-9a-f]{40}", source_sha or "") and source_sha != BASELINE
            and re.fullmatch(r"[0-9a-f]{40}", source_tree or ""), "Explicit new published source/tree required")
    publication = decode(file_bytes(spec["sourcePublicationReceipt"]))
    require(publication["head"] == source_sha and publication["tree"] == source_tree
            and publication["normalPushCompleted"] is True and publication["sourceRetentionPassed"] is True
            and publication["commandCustodyBlocked"] is False and publication["firstFailure"] is None,
            "The final original publication receipt must positively identify the selected source")
    source_inventory = decode(file_bytes(spec["sourceInventory"]))
    require(source_inventory["sourceCommit"] == source_sha and source_inventory["sourceTree"] == source_tree,
            "Immutable original source inventory belongs to a different publication")
    rows = {row["path"]: row for row in source_inventory["sources"]}
    require(len(rows) == len(source_inventory["sources"]), "Duplicate original source row")
    wanted = set(templates["membership"]["native"] + templates["membership"]["ui"])
    required = wanted | set(SOURCE_PINS.values()) | set(templates["originals"]["files"])
    require(required <= set(rows), "Complete compiler/control/pin source closure required")
    source_bytes = {}
    for name in sorted(required):
        row = rows[name]
        require(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
                and row["mode"] in ("100644", "100755"), "Original Git source must be a regular blob")
        raw = file_bytes({"path": row["localPath"], "sha256": row["sha256"]}, maximum=4 * 1024**2)
        require(len(raw) == row["bytes"]
                and hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == row["gitBlob"],
                "Complete original Git blob identity differs: " + name)
        source_bytes[name] = raw
    for name, pin in templates["originals"]["files"].items():
        require(all(rows[name][key] == pin[key] for key in ("bytes", "sha256", "gitBlob")),
                "A current original runtime helper changed and needs explicit source review: " + name)
    for pin in (templates["selection"]["focus"]["source"], templates["selection"]["editor"]["source"],
                templates["selection"]["editor"]["preparationSource"]):
        require(all(rows[pin["path"]][key] == pin[key] for key in ("bytes", "sha256", "gitBlob")),
                "An original priority Swift source changed")
    sdk = decode(source_bytes[SOURCE_PINS["hanlinSourcePinSHA256"]])
    require(sdk["repository"] == "https://github.com/davidpovarsky/hanlin-ai.git"
            and sdk["revision"] == SDK_REVISION
            and set(sdk["packages"]) == REQUIRED_PACKAGES and len(sdk["packages"]) == 4,
            "Actual final four-package canonical SDK source pin differs")
    marker_raw = file_bytes(spec["expectedSDKMarker"])
    marker = decode(marker_raw)
    require(marker["revision"] == sdk["revision"] and set(marker) == {"revision", "files"}
            and isinstance(marker["files"], dict) and len(marker["files"]) == SDK_PACKAGE_INVENTORY["files"],
            "Exact expected source-derived c0b SDK marker and all1011 original files required")
    for path, value in marker["files"].items():
        relative = PurePosixPath(path)
        require(not relative.is_absolute() and ".." not in relative.parts
                and any(relative.is_relative_to(package) for package in REQUIRED_PACKAGES)
                and re.fullmatch(r"[0-9a-f]{64}", value or ""), "Unexpected SDK marker member")
    require(all(package + "/Package.swift" in marker["files"] for package in REQUIRED_PACKAGES),
            "Expected canonical package manifests are missing")
    old_lock = decode(file_bytes({"path": str(WARM / "originals/Package.baseline8f2.resolved"),
        "sha256": "e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd"}))
    lock = decode(source_bytes[SOURCE_PINS["packageResolvedSHA256"]])
    old_rows, new_rows = ({row["identity"]: row for row in item["pins"]} for item in (old_lock, lock))
    require(len(old_rows) == len(old_lock["pins"]) == len(new_rows) == len(lock["pins"]) == 56
            and set(old_rows) == set(new_rows), "Complete original56 locked identities required")
    changed = [name for name in old_rows if old_rows[name] != new_rows[name]]
    require(changed == ["torahinspectorkit"], "Only exact reviewed Kit revision may change")
    expected_kit = copy.deepcopy(old_rows["torahinspectorkit"])
    require(expected_kit["state"]["revision"] == "9058b489e9acc271b4f8ef69e2ed24648f93b4ed", "Original Kit differs")
    expected_kit["state"]["revision"] = "26beca175d64a4d34e3567f2bbb4bf308d714478"
    require(new_rows["torahinspectorkit"] == expected_kit, "Kit identity/location/state changed beyond its exact revision")

    # Literal data extraction, not an import of the new admission/controller.
    admission_raw = file_bytes({"path": str(Path(__file__).resolve().parent / "after/Tools/PinkhaDualEngineRuntime/warm_focus_editor/admission.py"),
        "sha256": "356190ae9724a0b7910983d86b41d8e096badb0b7a69023e3968d2299bba2edc"})
    native_nodes = [node for node in ast.parse(admission_raw.decode()).body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "ORIGINAL_NATIVE_PINS" for t in node.targets)]
    require(len(native_nodes) == 1, "Exact original8ac literal pin map required")
    pins = ast.literal_eval(native_nodes[0].value)
    for key, path in SOURCE_PINS.items():
        actual = sha(source_bytes[path])
        require(key not in pins or pins[key] == actual, "The intermediate original8ac source identity changed")
        pins[key] = actual
    pins["sdkMaterializationReceiptSHA256"] = sha(marker_raw)
    require(set(pins) == set(stage["pins"]) == set(build["pins"]), "Exact finite producer pin keys differ")
    mac = spec["macPaths"]
    root, inputs = remote(mac["buildRoot"]), remote(mac["inputRoot"])
    require(root.parent == BASE and root.name.startswith("main16-wave3-forward-")
            and not inputs.is_relative_to(root) and not root.is_relative_to(inputs),
            "Inputs must be outside the new absent forward build root")
    stage.update(appSourceSHA=source_sha, appSourceTree=source_tree, buildRoot=str(root),
        sdkRevision=sdk["revision"], nativeMaterializationRoot=str(remote(mac["nativeMaterializationRoot"])),
        hanlinReadOnlySourceRoot=str(remote(mac["hanlinReadOnlySourceRoot"])),
        developerDir="/Applications/Xcode.app/Contents/Developer", pins=pins)
    require(set(mac["controls"]) == set(stage["controls"]), "Every exact frozen staging control must have a locator")
    for role, row in stage["controls"].items():
        row["path"] = str(remote(mac["controls"][role]))
    require(set(spec["toolchainOriginals"]) == set(TOOLCHAIN), "Three exact original toolchain outputs required")
    stage["toolchain"]["developerDir"] = stage["developerDir"]
    for role, argv in TOOLCHAIN.items():
        row = spec["toolchainOriginals"][role]
        require(row["argv"] == argv and row["exitCode"] == 0 and row["developerDir"] == stage["developerDir"],
                "Original toolchain command/selected environment differs")
        stage["toolchain"]["expectedOutputSHA256"][role] = sha(file_bytes(row["original"]))
    bundle = Path(spec["gitBundle"]["path"])
    require(bundle.is_absolute() and bundle.resolve(strict=True) == bundle and not bundle.is_symlink()
            and bundle.is_file() and bundle.stat().st_size <= 512 * 1024**2, "Exact bounded local Git bundle required")
    with bundle.open("rb") as stream:
        header = stream.read(1024 * 1024)
        stream.seek(0)
        bundle_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    require(bundle_sha == spec["gitBundle"]["sha256"] and b"\n\n" in header, "Original complete Git bundle hash/header differs")
    header = header.split(b"\n\n", 1)[0]
    require(header.startswith((b"# v2 git bundle\n", b"# v3 git bundle\n"))
            and any(line.startswith(source_sha.encode() + b" ") for line in header.splitlines()),
            "Bundle header must advertise the exact final commit; host bundle verification remains required")
    stage["gitBundle"] = {"path": str(remote(mac["gitBundle"])), "sha256": bundle_sha}
    native, ui = templates["membership"]["native"], templates["membership"]["ui"]
    inventory = {"schema": "pinkha-forward-warm-compiler-inputs-v1", "sourceCommit": source_sha,
        "sourceTree": source_tree, "selectedNativeTestSources": native, "selectedUITestSources": ui,
        "sources": [{key: rows[name][key] for key in ("path", "bytes", "sha256", "gitBlob", "mode")}
                    for name in sorted(wanted)], "compilerExecutionClaimed": False}
    inventory_raw = encode(inventory)
    inventory_ref = reference_at(inputs / "compiler-inputs.json", inventory_raw)
    stage["compilerInputInventory"] = inventory_ref
    build.update(appSourceSHA=source_sha, buildRoot=str(root), pins=pins, nativeBuildDate="2026-11-26",
        nativeMaterializationRoot=stage["nativeMaterializationRoot"],
        selectedNativeTestSources=native, selectedUITestSources=ui)
    build["forwardWarm"]["targetSDKRevision"] = sdk["revision"]
    build["forwardWarm"]["resourceCensusControl"]["path"] = stage["controls"]["census"]["path"]
    build["compilerInputEnumeration"] = dict(inventory_ref, sourceCommit=source_sha, sourceTree=source_tree,
                                              nativeCount=61, uiSwiftCount=10)
    build_raw = encode(build)
    stage["buildAdmissionTemplate"] = reference_at(inputs / "build-admission.bound-ready-false.json", build_raw)
    require(stage["readyForStaging"] is False and build["readyForBuild"] is False
            and stage["rootWindow"]["status"] == "UNBOUND" and stage["runtimeActivation"] is False,
            "Local source binding cannot approve any host operation")
    return {"compiler-inputs.json": inventory_raw, "build-admission.bound-ready-false.json": build_raw,
            "source-staging.bound-ready-false.json": encode(stage)}, {
        "sourceCommit": source_sha, "sourceTree": source_tree, "SDKRevision": sdk["revision"],
        "sourcePublicationReceipt": spec["sourcePublicationReceipt"], "sourceInventory": spec["sourceInventory"],
        "SDKPublicationReceipt": spec["sdkPublicationReceipt"], "SDKSourceTree": SDK_TREE,
        "SDKPublishedPackageInventory": SDK_PACKAGE_INVENTORY,
        "SDKPublicationScope": "SOURCE_ONLY_NO_MATERIALIZATION_OR_COMPILER_ACCEPTANCE",
        "originalSourceRowsRehashed": len(required), "compilerSources": {"native": 61, "stage1UI": 10},
        "expectedSDKMarker": spec["expectedSDKMarker"], "expectedSDKFileCount": len(marker["files"]),
        "SDKMarkerScope": "SOURCE_EXPECTATION_ONLY_REAL_MATERIALIZATION_STILL_REQUIRED",
        "kitTransition": {"changed": changed, "unchangedPins": 55, "resolverExecuted": False},
        "bundleHash": bundle_sha, "bundleObjectsOrAncestryVerifiedHere": False,
        "actualHostPathsVerifiedHere": False, "actualCompilerProductsRequiredBeforeRuntime": True,
        "rootWindow": "UNBOUND_FRESH_ROOT_COORDINATION_AND_CENSUS_STILL_REQUIRED",
        "runtimeActivation": False, "finalSourceSDKNativeProductTuple": None,
        "candidateImports": 0, "subprocesses": 0, "networkCalls": 0, "hostActions": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--inputs-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = decode(file_bytes({"path": str(args.inputs), "sha256": args.inputs_sha256}))
    files, record = bind(spec)
    output = args.output
    require(output.is_absolute() and output.parent.resolve(strict=True) == output.parent
            and not output.exists() and not output.is_symlink(), "Fresh physical local evidence destination required")
    output.mkdir(mode=0o700)
    record.update(schema="pinkha-forward-warm-ready-false-binding-v1", status="LOCAL_SOURCE_INPUTS_BOUND_READY_FALSE",
                  inputsSHA256=args.inputs_sha256, controllerSHA256=sha(Path(__file__).read_bytes()), outputs={})
    try:
        for name, raw in files.items():
            path = output / name
            with path.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            path.chmod(0o600)
            require(path.read_bytes() == raw, "Exclusive draft readback differs")
            record["outputs"][name] = {"bytes": len(raw), "sha256": sha(raw)}
    except BaseException as error:
        record.update(status="FAIL_LOCAL_BINDING_OUTPUT", firstFailure={"type": type(error).__name__, "message": str(error)})
        try:
            with (output / "failure.json").open("xb") as stream:
                stream.write(encode(record))
        except BaseException as later:
            record["terminalReceiptFailure"] = {"type": type(later).__name__, "message": str(later)}
        print(json.dumps(record, sort_keys=True), flush=True)
        raise
    with (output / "binding-receipt.json").open("xb") as stream:
        stream.write(encode(record))
    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
