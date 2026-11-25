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


def qualify(root, source, manifest, manifest_sha, phase, run, environment, go):
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
    require(not fixture.exists(), "fresh_private_mobile_gateway_fixture_required")
    cwd.mkdir(mode=0o700, parents=True)
    fixture_source = source / "any/internal/pinkha/migrationnative/testdata/local.yml"
    expected = manifest["files"][str(fixture_source.relative_to(source))]
    require(fixture_source.is_file() and fixture_source.resolve() == fixture_source
            and digest(fixture_source) == expected["sha256"]
            and fixture_source.stat().st_size == expected["bytes"],
            "original_local_native_fixture_changed")
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
              "localNativeFixture": str(fixture_source.relative_to(source)),
              "localNativeFixtureSHA256": digest(fixture / "staging.yml"),
              "sourceFilesModified": False, "applicationAcceptanceClaimed": False}
    write(root / "mobile-gateway-receipt.json", result)
    return result
