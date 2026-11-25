"""Execute the original mobile gateway methods against the exact unified graph."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

CASES = {
    "TestPinkhaMobileManagedGateway",
    "TestPinkhaMobileGatewayPreservesStandalone",
    "TestAcquirePIDLock_MobileNoOp",
}
PACKAGE = "github.com/anyproto/any/internal/server"
STATUS = "PASS_ORIGINAL_MOBILE_GATEWAY_COMPONENTS_NOT_APP_ACCEPTANCE"


def require(value, why):
    if not value:
        raise ValueError(why)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024**2), b""):
            value.update(data)
    return value.hexdigest()


def write(path, value):
    with path.open("x") as output:
        os.chmod(path, 0o600)
        json.dump(value, output, sort_keys=True, indent=2)
        output.write("\n")


def qualify(root, source, manifest, manifest_sha, phase, run, environment, go, reuse_fixture=False):
    require("mobile" in manifest["tags"] and "gomobile" in manifest["tags"],
            "original_any_mobile_gateway_tag_required")
    if phase == "device":
        original_root = root.parent / ("pinkha-dual-native-v1-" + manifest_sha[:12] + "-simulator")
        original = original_root / "mobile-gateway-receipt.json"
        require(original.resolve() == original and original.is_file(),
                "same_source_original_gateway_proof_required")
        proof = json.loads(original.read_text())
        require(proof["status"] == STATUS and proof["sourceManifestSHA256"] == manifest_sha
                and proof["cases"] == {name: "pass" for name in CASES}
                and proof["testsExecuted"] == 3 and proof["skippedTests"] == 0
                and proof["tags"] == manifest["tags"],
                "same_source_mobile_gateway_not_qualified")
        log = original_root / "evidence" / "mobile-gateway-original-json.log"
        require(log.resolve() == log and log.is_file()
                and digest(log) == proof["originalLogSHA256"],
                "original_gateway_execution_log_changed")
        return {"originalReceipt": str(original), "originalReceiptSHA256": digest(original),
                "originalLogSHA256": digest(log), "sourceManifestSHA256": manifest_sha,
                "testsExecutedNow": 0, "reusedActualMethods": 3, "status": STATUS}

    require(phase == "simulator", "known_mobile_gateway_phase_required")
    fixture = root / "mobile-gateway-fixture"
    cwd = fixture / "internal/server"
    if reuse_fixture:
        require(fixture.resolve() == fixture and cwd.resolve() == cwd and cwd.is_dir(),
                "original_private_gateway_fixture_required")
        require({str(p.relative_to(fixture)) for p in fixture.rglob("*")
                 if p.is_file() or p.is_symlink()} == {"staging.yml"},
                "unexecuted_gateway_fixture_inventory_changed")
    else:
        require(not fixture.exists(), "fresh_private_mobile_gateway_fixture_required")
        cwd.mkdir(mode=0o700, parents=True)
    fixture_source = source / "any/internal/pinkha/migrationnative/testdata/local.yml"
    expected = manifest["files"][str(fixture_source.relative_to(source))]
    require(fixture_source.is_file() and fixture_source.resolve() == fixture_source
            and digest(fixture_source) == expected["sha256"]
            and fixture_source.stat().st_size == expected["bytes"],
            "original_local_native_fixture_changed")
    if reuse_fixture:
        require(digest(fixture / "staging.yml") == expected["sha256"],
                "original_gateway_fixture_bytes_changed")
    else:
        shutil.copyfile(fixture_source, fixture / "staging.yml")
        (fixture / "staging.yml").chmod(0o600)
    binary = root / "mobile-gateway.test"
    require(not binary.exists(), "refuse_existing_gateway_test_binary")
    selection = "^(" + "|".join(sorted(CASES)) + ")$"
    run([go, "test", "-mod=readonly", "-p=2", "-tags", " ".join(manifest["tags"]),
         "-c", "-o", binary, "./internal/server"],
        "mobile-gateway-build", source / "any", environment, 900)
    require(binary.is_file() and not binary.is_symlink(), "actual_gateway_test_binary_required")
    original = run([go, "tool", "test2json", "-p", PACKAGE, "-t", binary,
                    "-test.v=test2json", "-test.run=" + selection, "-test.count=1"],
                   "mobile-gateway-original-json", cwd, environment, 300)
    events = [json.loads(line) for line in original.read_text().splitlines() if line.strip()]
    require(all(isinstance(item, dict) and item.get("Package") == PACKAGE for item in events),
            "original_gateway_event_package_changed")
    cases = {item["Test"]: item["Action"] for item in events
             if "Test" in item and item.get("Action") in ("pass", "fail", "skip")}
    require(cases == {name: "pass" for name in CASES}
            and not any(item.get("Action") in ("fail", "skip") for item in events)
            and sum(item.get("Action") == "pass" and "Test" not in item for item in events) == 1,
            "all_three_original_mobile_gateway_methods_must_pass")
    result = {"status": STATUS, "sourceManifestSHA256": manifest_sha,
              "tags": manifest["tags"], "cases": cases, "testsExecuted": 3,
              "skippedTests": 0, "testBinarySHA256": digest(binary),
              "originalLogSHA256": digest(original),
              "originalLogPath": str(original.relative_to(root)),
              "localNativeFixture": str(fixture_source.relative_to(source)),
              "localNativeFixtureSHA256": digest(fixture / "staging.yml"),
              "sourceFilesModified": False, "applicationAcceptanceClaimed": False}
    write(root / "mobile-gateway-receipt.json", result)
    return result


def reuse_standalone(proof_root, source, manifest, manifest_sha, current_graph):
    """Reuse only original execution with the identical complete module graph."""
    proof_root = Path(proof_root)
    require(proof_root.resolve() == proof_root and proof_root.is_dir()
            and proof_root.parent == Path("/Users/m1/builds")
            and proof_root.name == "pinkha-dual-native-v1-" + manifest_sha[:12] + "-gateway",
            "exact_owned_gateway_proof_root_required")
    pointer = json.loads((proof_root / "qualified-gateway.json").read_text())
    relative = Path(pointer["originalReceipt"])
    require(pointer["sourceManifestSHA256"] == manifest_sha
            and relative.parts in (("evidence", "receipt.json"), ("evidence-resume-1", "receipt.json")),
            "qualified_original_gateway_receipt_path_required")
    receipt_path = proof_root / relative
    require(receipt_path.resolve() == receipt_path
            and digest(receipt_path) == pointer["originalReceiptSHA256"],
            "qualified_original_gateway_receipt_changed")
    evidence = receipt_path.parent
    outer = json.loads(receipt_path.read_text())
    require(outer["status"] == "PASS_STANDALONE_ORIGINAL_GATEWAY_COMPONENTS_ONLY"
            and outer["sourceManifestSHA256"] == manifest_sha
            and outer["tags"] == manifest["tags"]
            and outer["goVersion"] == "go version go1.27.4 darwin/arm64"
            and outer["sourceUnchanged"] is True
            and outer["sourceFilesVerified"] == len(manifest["files"])
            and outer["testsExecuted"] == 3 and outer["skippedTests"] == 0,
            "actual_original_gateway_phase_not_qualified")
    expected_names = ["go-version", "module-graph", "mobile-gateway-build",
                      "mobile-gateway-original-json"]
    require([x["name"] for x in outer["commands"]] == expected_names
            and all(x["exitCode"] == 0 for x in outer["commands"]),
            "complete_original_gateway_commands_required")
    for item in outer["commands"]:
        log = evidence / (item["name"] + ".log")
        require(log.resolve() == log and log.is_file()
                and digest(log) == item["logSHA256"], "gateway_original_command_changed")
        try:
            os.killpg(item["pgid"], 0)
        except ProcessLookupError:
            pass
        else:
            require(False, "original_gateway_process_still_exists")
    original_source = proof_root / "source"
    require(digest(original_source / "source-manifest.json") == manifest_sha,
            "original_gateway_manifest_changed")
    files = {str(p.relative_to(original_source)) for p in original_source.rglob("*")
             if p.is_file() or p.is_symlink()}
    require(files == set(manifest["files"]) | {"source-manifest.json"},
            "original_gateway_source_inventory_changed")
    for name, expected in manifest["files"].items():
        path = original_source / name
        require(path.resolve() == path and stat.S_ISREG(path.lstat().st_mode)
                and path.stat().st_size == expected["bytes"] and digest(path) == expected["sha256"],
                "original_gateway_source_changed:" + name)
    original = proof_root / "mobile-gateway-receipt.json"
    require(digest(original) == outer["originalGatewayReceiptSHA256"],
            "original_gateway_receipt_changed")
    proof = json.loads(original.read_text())
    require(proof["status"] == STATUS and proof["sourceManifestSHA256"] == manifest_sha
            and proof["tags"] == manifest["tags"]
            and proof["cases"] == {name: "pass" for name in CASES}
            and proof["testsExecuted"] == 3 and proof["skippedTests"] == 0
            and digest(proof_root / "mobile-gateway.test") == proof["testBinarySHA256"],
            "original_gateway_execution_changed")
    log = evidence / "mobile-gateway-original-json.log"
    require(proof["originalLogPath"] == str(log.relative_to(proof_root))
            and digest(log) == proof["originalLogSHA256"], "original_gateway_log_changed")
    events = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    cases = {x["Test"]: x["Action"] for x in events
             if "Test" in x and x.get("Action") in ("pass", "fail", "skip")}
    require(cases == {name: "pass" for name in CASES}
            and all(x.get("Package") == PACKAGE for x in events)
            and not any(x.get("Action") in ("fail", "skip") for x in events)
            and sum(x.get("Action") == "pass" and "Test" not in x for x in events) == 1,
            "all_original_gateway_outcomes_required")
    def normalized_graph(path, source_root):
        raw, decoder, rows = path.read_text(), json.JSONDecoder(), {}
        def normalize(value):
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if isinstance(value, str) and (value == str(source_root)
                                           or value.startswith(str(source_root) + "/")):
                return "$SOURCE" + value[len(str(source_root)):]
            return value
        while raw.strip():
            row, end = decoder.raw_decode(raw.lstrip())
            require(row["Path"] not in rows, "duplicate_original_graph_module")
            rows[row["Path"]] = normalize(row)
            raw = raw.lstrip()[end:]
        require(len(rows) == 760, "complete_original_module_graph_required")
        return rows
    original_graph = evidence / "module-graph.log"
    require(digest(original_graph) == outer["actualModuleGraphSHA256"],
            "gateway_original_module_graph_changed")
    before = normalized_graph(original_graph, original_source)
    after = normalized_graph(Path(current_graph), source)
    require(before == after, "gateway_and_apple_native_module_graphs_differ")
    return {"status": STATUS, "sourceManifestSHA256": manifest_sha,
            "originalReceipt": str(receipt_path), "originalReceiptSHA256": digest(receipt_path),
            "originalGatewayReceiptSHA256": digest(original),
            "originalLogSHA256": digest(log), "originalGraphSHA256": digest(original_graph),
            "currentGraphSHA256": digest(current_graph), "identicalModuleIdentities": len(before),
            "testsExecutedNow": 0, "reusedActualMethods": 3, "applicationAcceptanceClaimed": False}
