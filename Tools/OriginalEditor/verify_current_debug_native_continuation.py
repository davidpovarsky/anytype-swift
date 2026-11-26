"""Verify the exact current Debug simulator build and its already executed external consumer."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

CURRENT_SWIFT = "1b5fb6a68b1f8e1e61ac20ce02920e6c1fdb09e3"
ABI_SWIFT = "4c9fcd14af2ffcbd223fd8a47a0c806c88429d21"
NATIVE_COMMIT = "54ba7095178f77b5f80473581e28c226b74f6182"
NATIVE_TREE = "ccff9278b2c165eb470891e4dac41e0eca65a5e7"
ABI_SHA = "29b7e8472c9c80245c26101e716e4687cdc4c2666ad4aadf8d3543a9b94d30de"
BUILD = "build/SDK-Native-Selected-Space-Refreshed-External-Evidence"
RUNTIME = "build/SDK-Native-Selected-Space-External-Languages"
WORK = "build/SDK-Candidate-Debug-Work"
CURRENT_EXECUTION = "build/SDK-Native-Selected-Space-Drain-Evidence/local-execution.json"
ABI_EXECUTION = "build/SDK-Native-Readback-Debug-Evidence/local-execution.json"
SOURCE_OBSERVATION = "0cca110276077d42f476015f93e9dd2202ad7fc69fd9c94b7d26d90294fc01d1"
LANGUAGES = {
    "en": ("3b1dfe30d12f6a43104f2aa7e6b4187087165ebb79679b951fe74f7738ab46c9",
           "c757511f67f42b947c6133388d5480774ea1102a380e9c05966d214f16304bc7"),
    "he": ("10b1c744064bd95a65d84f17e57544211202de6445164dbac06f515304e5ade4",
           "e83dde22b80af6487f9758359b294fdca0b21ff72d6e7651ee8737de51f5f3b7"),
}


def verify(root, abi_root):
    sys.path.insert(0, str(root / "Tools/OriginalEditor"))
    from consumer_failure_capture import validate_launch
    from framework_products import original_oracles, verify_observation
    from framework_profile import git, read_manifest, sha256, source_observation
    from import_abi_input import LIB, exact_file, verify as verify_abi
    from pbx_source import require
    from product_inventory import inventory

    evidence = {}

    def read(relative, expected_sha):
        path = root / relative
        require(path.resolve(strict=True) == path and path.is_file()
                and sha256(path) == expected_sha, "Unexpected evidence bytes: " + relative)
        evidence[relative] = expected_sha
        return json.loads(path.read_bytes())

    require(root != abi_root and git(root, "rev-parse", "HEAD") == CURRENT_SWIFT
            and git(abi_root, "rev-parse", "HEAD") == ABI_SWIFT,
            "The current SDK and its exact original ABI checkout are required")
    env = dict(os.environ, OTZARIA_LOCAL_EXECUTION=str(root / CURRENT_EXECUTION),
               OTZARIA_LOCAL_EXECUTION_SHA256="0c85c186805e6a06b2ac8f864547ee3bc9920e0a0c7112fd5f0b8f6d25ca6778")
    before = read(RUNTIME + "/source-before.json", SOURCE_OBSERVATION)
    after = read(RUNTIME + "/source-after.json", SOURCE_OBSERVATION)
    require(source_observation(root, env) == before == after, "Current producer source changed")
    require(git(root, "diff", "--name-status", ABI_SWIFT, CURRENT_SWIFT).splitlines() == [
        "M\tOriginalEditorFramework/OriginalEditorLocalAnnotationRuntime.swift",
        "A\tTools/OriginalEditor/MiniApps/current_native_annotation_source_adoption.json",
        "M\tTools/OriginalEditor/framework_profile.json",
        "M\tTools/OriginalEditor/native_files_source.py",
    ], "The native source or generated input difference exceeds the reviewed closure")
    historical_identity = sha256(abi_root / ABI_EXECUTION)
    require(historical_identity == "0bb683f4b7f6eb35715610f9ed41bed57e28093d001df6ce242614d8f1e2f3d7",
            "Exact original ABI build identity changed")
    abi_path = abi_root / "build/ABI-Candidate-Evidence/ABI_INPUT.json"
    abi = verify_abi(abi_root, abi_path, ABI_SHA, {
        "head_sha": ABI_SWIFT,
        "execution_identity": {"local_execution_sha256": historical_identity},
    })
    native = abi["native_qualification"]
    require(abi["schema"] == "otzaria.original-import-local-sdk-input/3"
            and abi["status"] == "PASS" and native["source_sha"] == ABI_SWIFT
            and native["native_source_commit"] == NATIVE_COMMIT
            and native["native_source_tree"] == NATIVE_TREE,
            "Original ABI execution identity differs")
    installed = inventory(root / LIB)
    require(set(installed) == {row["path"][len(LIB) + 1:] for row in abi["lib_files"]},
            "Installed current library inventory differs")
    for row in abi["lib_files"]:
        exact_file(root, row)

    result = read(RUNTIME + "/actual-external-native-result.json",
                  "671734345dbe58658f24ee91edda2374a1cd5be04dc660edfa8401048baeff3b")
    require(result["phase"] == "COMPLETE" and result["source_sha"] == CURRENT_SWIFT
            and result["execution_identity"] == before["execution_identity"]
            and result["status"] == "ACTUAL_CURRENT_ORIGINAL_DEBUG_EXTERNAL_NATIVE_CONSUMER_PASS"
            and result["formal_sdk_release_qualification"] is False
            and result["original_framework_build"] == result["external_consumer_build"] == "PASS",
            "Original current Debug consumer did not finish")
    require(result["heart"]["original_native_execution"] == abi
            and result["heart"]["current_sdk_source"] == CURRENT_SWIFT,
            "Current external execution did not bind the verified native inputs")
    capture = read(RUNTIME + "/preflight/preflight.json",
                   "c7bfeb66514f4b6b7af125a39dc543eda7d650b92524aca281283f822be28810")
    require(capture == result["preflight"], "Original runtime preflight changed")
    ipad = capture["selected"]["ipad"]
    require(ipad["name"] == "Pinkha-UI27-" + before["run_id"] + "-ipad",
            "Original runtime device ownership differs")
    oracle = read(BUILD + "/independent-original-resource-oracles.json",
                  "dd7adb9167ae717ab15c1698130ff3dedc3b288e1169a459a921a4d5d80d8e3f")
    require(oracle == original_oracles(root, read_manifest()), "Original independent resource oracle differs")
    observations = []
    for language, (observation_sha, launch_sha) in LANGUAGES.items():
        launch = read(RUNTIME + f"/consumer-{language}-launch.command.json", launch_sha)
        require(launch["returncode"] == 0 and launch["timed_out"] is False,
                "Owned original language launch did not succeed")
        command = launch["command"]
        require(command[3].startswith("--stdout=") and command[4].startswith("--stderr="),
                "Missing captured original launch streams")
        original = command[:3] + command[5:]
        validate_launch(original, language, ipad["udid"])
        observed = read(RUNTIME + f"/consumer-{language}-observation.json", observation_sha)
        bundle = Path(observed["mainBundleURL"])
        require(bundle.name == "OriginalEditorConsumer.app"
                and bundle.parent.parent.is_relative_to(Path.home() / "Library/Developer/CoreSimulator/Devices"
                                                        / ipad["udid"] / "data/Containers/Bundle/Application"),
                "Original observation does not belong to the owned iPad app")
        observations.append(verify_observation(observed, original[7], language, bundle, oracle))
    require(observations == result["verified_runtime_observations"], "Independent language outcomes differ")

    graph = read(BUILD + "/compiler-symbolgraph-collection.json",
                 "87ccd613772fd84f9061139f9df8feaac7b4fd558fd31ce422abd9350456cdf2")
    require(graph["source_sha"] == CURRENT_SWIFT and graph["target"] == "arm64-apple-ios27.0-simulator"
            and graph["all_emitted_graphs_copied_without_filtering"] and len(graph["graphs"]) == 11,
            "Current compiler graph authority differs")
    read(BUILD + "/actual-public-surface.json", "9680501a5dc4da71402c001ec9149f194719db14eea75420dc200662c80819ad")
    read(BUILD + "/clang-declaration-export.json", "00e6811e45f4095fa57ad988325b7a8354126741c1d5212b4a40c8f9430ea628")
    distribution = read(BUILD + "/framework-distribution.json",
                        "4c776963de048a4410ce99a22c9f3a9f62c5c4c928345918b04e0f470ddf004c")
    exported = root / WORK / "distribution"
    require(exported.resolve(strict=True) == exported and result["distribution"] == str(exported)
            and not (root / WORK / "producer-derived").exists()
            and inventory(exported) == distribution["files"],
            "Current signed Debug distribution or quarantine differs")
    images = {
        name: distribution["files"][f"Frameworks/{name}.framework/{name}"]["sha256"]
        for name in ("AnytypeOriginalEditor", "ProtobufMessages")
    }
    for name in images:
        framework = exported / "Frameworks" / (name + ".framework")
        subprocess.run(["codesign", "--verify", "--strict", str(framework)], check=True, timeout=30)
    require(images == {
        "AnytypeOriginalEditor": "6a880f580c428303e8c45c5e8968fddf0bfeeb67489f5e906ced840dceeca64e",
        "ProtobufMessages": "d3699997bf1aaabb7fe1436c2da841f1b883419a8af4eb931a0d01fab1426b18",
    }, "Actual linked Debug Swift or Go image differs")

    return {
        "schema": "otzaria.exact-original-debug-native-continuation/1",
        "status": "VERIFIED_ACTUAL_ORIGINAL_DEBUG_EXTERNAL_NATIVE_CONSUMER",
        "source_sha": CURRENT_SWIFT,
        "native": {"source_sha": NATIVE_COMMIT, "tree": NATIVE_TREE,
                   "original_abi_swift_sha": ABI_SWIFT, "original_abi_sha256": ABI_SHA},
        "distribution": str(exported),
        "distribution_manifest_sha256": evidence[BUILD + "/framework-distribution.json"],
        "images": images,
        "external_observations": observations,
        "evidence_sha256": evidence,
        "release_qualification": False,
        "sdk_device_build": False,
        "editor_ui_tests": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--original-abi-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve(strict=True),
                            args.original_abi_root.resolve(strict=True)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
