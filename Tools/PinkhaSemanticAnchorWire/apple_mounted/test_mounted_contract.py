"""New strict mounted-controller controls; never launches product tests."""
import copy
import hashlib
import io
import json
from pathlib import Path
import plistlib
import tempfile
import tarfile
import time
import unittest
import mounted_contract as proof

BINDING = {"sourceSHA": "a" * 40, "runID": "45100000001", "runAttempt": "1", "nonce": "b" * 32}
APPROVED = {"consumer_sha": "a" * 40, "consumer_run": "45100000000", "consumer_attempt": "1"}
GENERATION = "11111111-2222-3333-4444-555555555555"
ANCHOR = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def varint(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128); value >>= 7
    result.append(value)
    return bytes(result)


def field(number, value):
    if isinstance(value, int): return varint(number << 3) + varint(value)
    return varint(number << 3 | 2) + varint(len(value)) + value


def marks(values):
    result = b""
    for row in values:
        extent = (field(1, row["from"]) if row["from"] else b"") + field(2, row["to"])
        mark = field(1, extent) + field(2, row["kind"])
        if row["param"]: mark += field(3, row["param"].encode())
        result += field(1, mark)
    return result


def block(name, text, values, opaque=b"opaque"):
    body = field(1, text.encode()) + (field(3, marks(values)) if values else b"")
    return field(1, name.encode()) + field(3, b"") + field(6, opaque) + field(14, body)


def b64(value):
    return proof.base64.b64encode(value).decode()


def sample():
    original = [{"from": 0, "to": 3, "kind": 3, "param": ""}]
    prefix = "pinkha-anchor://v1/c3BhY2U/b2JqZWN0/"
    marker = prefix + ANCHOR
    added = original + [{"from": 0, "to": 6, "kind": 5, "param": marker}]
    before = block("target", "Anchor", original)
    after = block("target", "Anchor", added)
    fixture = dict(BINDING, createdAt=time.time() - 978307200 - 5, preparationProcessID=100,
        accountID="account", spaceID="space", objectID="object", blockID="target", excludedBlockID="excluded",
        text="Anchor", excludedText="Unselected " + BINDING["nonce"],
        beforeBlockBase64=b64(before), excludedBlockBase64=b64(block("excluded", "Unselected " + BINDING["nonce"], [])))
    base = dict(BINDING, protocol=proof.PROTOCOL, accountID="account", spaceID="space", objectID="object",
        blockID="target", excludedBlockID="excluded", preparationProcessID=100, startedAt=time.time() - 3,
        finishedAt=time.time(), runtimeVersion=proof.native.VERSION, nativeManifestSHA256=proof.native.MANIFEST_SHA)
    native = dict(anchorID=ANCHOR, marker=marker, changeID="native-change", nativeChangeSHA256="c" * 64,
        beforeTextMarksSHA256=proof.snapshot("Anchor", original), afterTextMarksSHA256=proof.snapshot("Anchor", added))
    captured = dict(base, mode="capture", phase="PASS_CAPTURE_MOUNTED", processID=200, generation=GENERATION,
        publicationGeneration=GENERATION, preparations=2, cancellations=1, applyAttempts=1, documentPublications=1,
        selection=dict(blockID="target", location=0, length=6, visibleTextSHA256=hashlib.sha256(b"Anchor").hexdigest()),
        cancelNativeBlockSHA256=hashlib.sha256(before).hexdigest(),
        cancelledMarker=prefix + "ffffffff-bbbb-cccc-dddd-eeeeeeeeeeee", native=native,
        afterBlockBase64=b64(after), documentMarksBase64=b64(marks(added)),
        renderedLinks=[dict(marker=marker, location=0, length=6)], checks={k: True for k in proof.CAPTURE_CHECKS})
    raw = json.dumps(captured, separators=(",", ":"), sort_keys=True).encode()
    reopened = dict(base, mode="reopen", phase="PASS_COLD_REOPEN_MOUNTED", processID=300,
        generation="99999999-2222-3333-4444-555555555555", captureProcessID=200,
        preparations=0, cancellations=0, applyAttempts=0, documentPublications=0, native=native,
        afterBlockBase64=b64(after), documentMarksBase64=b64(marks(added)),
        renderedLinks=captured["renderedLinks"], captureReceiptSHA256=hashlib.sha256(raw).hexdigest(),
        checks={k: True for k in proof.REOPEN_CHECKS})
    return fixture, captured, reopened, raw


def archive(root, *, external=False):
    target = root / "BuildProducts.tar.gz"
    data = b"qualified owned binary control"
    rows = {"Build/Products": dict(kind="directory", mode=0o755),
        "Build/Products/test": dict(kind="file", mode=0o755, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()),
        "Build/Products/link": dict(kind="symlink", mode=0o777, target="/tmp/unadmitted" if external else "test")}
    with tarfile.open(target, "w:gz") as tar:
        for name, row in rows.items():
            member = tarfile.TarInfo(name); member.mode = row["mode"]
            if row["kind"] == "directory": member.type = tarfile.DIRTYPE
            elif row["kind"] == "symlink": member.type = tarfile.SYMTYPE; member.linkname = row["target"]
            else: member.size = len(data)
            tar.addfile(member, io.BytesIO(data) if row["kind"] == "file" else None)
    value = dict(status="OBSERVED_PRODUCTS_ARCHIVED_BEFORE_ADMISSION", capture_phase="AFTER_BUILD_BEFORE_ADMISSION",
        source_sha=APPROVED["consumer_sha"], run_id=APPROVED["consumer_run"], run_attempt=APPROVED["consumer_attempt"],
        build_reuse_enabled=False, native_acceptance_reused=False, ui_acceptance_reused=False, products=rows,
        build_flags=["OTHER_SWIFT_FLAGS=-D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 -D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1",
                     "ONLY_ACTIVE_ARCH=YES", "ENABLE_TESTABILITY=YES"],
        archive_sha256=proof.digest(target), archive_bytes=target.stat().st_size)
    manifest = root / "manifest.json"; proof.save(manifest, value)
    return target, manifest


class MountedControllerControls(unittest.TestCase):
    def test_original_native_selection_cancel_capture_and_distinct_cold_receipts_are_bound(self):
        values = sample()
        result = proof.observations(*values, BINDING)
        self.assertEqual(result["status"], proof.PASS)
        self.assertFalse(result["limitations"]["fullProductAcceptance"])

    def test_native_opaque_text_and_original_marks_cannot_be_changed_behind_receipt(self):
        for change in ("opaque", "original-mark", "text"):
            fixture, captured, reopened, _ = sample()
            fields = [{"from": 0, "to": 3, "kind": 3, "param": ""},
                {"from": 0, "to": 6, "kind": 5, "param": captured["native"]["marker"]}]
            if change == "original-mark": fields[0]["kind"] = 1
            raw_block = block("target", "Anchor!" if change == "text" else "Anchor", fields,
                opaque=b"changed" if change == "opaque" else b"opaque")
            captured["afterBlockBase64"] = b64(raw_block)
            raw = json.dumps(captured).encode()
            with self.subTest(change=change), self.assertRaises(ValueError):
                proof.observations(fixture, captured, reopened, raw, BINDING)

    def test_cancel_and_publication_owner_replay_or_weakened_checks_are_refused(self):
        for key, value in (("sourceSHA", "d" * 40), ("applyAttempts", 2),
                           ("documentPublications", 0), ("publicationGeneration", "0" * 36),
                           ("cancelNativeBlockSHA256", "0" * 64), ("checks", {})):
            fixture, captured, reopened, _ = sample()
            captured[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                proof.observations(fixture, captured, reopened, json.dumps(captured).encode(), BINDING)

    def test_cold_same_process_generation_mutation_or_wrong_capture_bytes_are_refused(self):
        for key, value in (("processID", 200), ("generation", GENERATION), ("applyAttempts", 1),
                           ("captureReceiptSHA256", "0" * 64), ("afterBlockBase64", b64(b"wrong"))):
            fixture, captured, reopened, raw = sample()
            reopened[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                proof.observations(fixture, captured, reopened, raw, BINDING)

    def test_copied_selector_and_binding_preserve_original_host_and_testing_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); original = root / "original.xctestrun"; destination = root / "mounted.xctestrun"
            target = dict(BlueprintName="AnytypeTests", TestBundlePath="__TESTHOST__/PlugIns/AnytypeTests.xctest",
                TestHostPath="__TESTROOT__/Debug/Anytype.app/Anytype", TestingEnvironmentVariables={"EXACT": "original"},
                EnvironmentVariables={"UNRELATED": "retained"}, OnlyTestIdentifiers=["Old/testOld"])
            original.write_bytes(plistlib.dumps({"__xctestrun_metadata__": {"FormatVersion": 2},
                "TestConfigurations": [{"TestTargets": [target]}]}))
            before = original.read_bytes()
            receipt = proof.copied_descriptor(original, destination, proof.PREP, BINDING)
            copied = plistlib.loads(destination.read_bytes())["TestConfigurations"][0]["TestTargets"][0]
            self.assertEqual(original.read_bytes(), before)
            self.assertEqual(copied["TestingEnvironmentVariables"], target["TestingEnvironmentVariables"])
            self.assertEqual(receipt["selector"], proof.PREP)
            with self.assertRaises(ValueError):
                proof.copied_descriptor(destination, root / "replayed.xctestrun", proof.PREP, BINDING)

    def test_actual_enum_and_execution_always_supply_full_only_testing_argv(self):
        for selector in (proof.PREP, proof.UI):
            for arguments in ({"enumeration": Path("enumeration.json")}, {"result": Path("actual.xcresult")}):
                command = proof.xctest_command(Path("bound.xctestrun"), "owned-device", selector, **arguments)
                self.assertEqual(command.count("-only-testing"), 1)
                self.assertEqual(command[command.index("-only-testing") + 1], selector)
                self.assertEqual(command[:2], ["xcodebuild", "test-without-building"])
                self.assertFalse(any("NativeAcceptanceTests" in value for value in command))

    def test_actual_summary_must_be_exact_owned_method_device_and_zero_skips(self):
        udid = "67621ae7-2788-4a27-b350-21d9c1d4c4e5"
        summary = dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0, result="Passed",
            devicesAndConfigurations=[{"device": dict(deviceId=udid, osVersion="27.0", osBuildNumber="24A434",
                architecture="arm64", platform="iOS Simulator")}])
        tree = {"testNodes": [{"nodeType": "Test Case", "nodeIdentifier": proof.UI + "()", "result": "Passed"}]}
        self.assertEqual(proof.exact_execution(summary, tree, udid, proof.UI)["selector"], proof.UI)
        for mode in ("skip", "foreign", "extra"):
            changed = copy.deepcopy(summary); other = copy.deepcopy(tree)
            if mode == "skip": changed["skippedTests"] = 1
            if mode == "foreign": other["testNodes"][0]["nodeIdentifier"] = proof.PREP
            if mode == "extra": other["testNodes"].append(copy.deepcopy(other["testNodes"][0]))
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                proof.exact_execution(changed, other, udid, proof.UI)

    def test_exact_archive_restores_owned_file_and_internal_link_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); packed, manifest = archive(root)
            result = proof.restore_products(packed, manifest, root / "restored", APPROVED)
            self.assertEqual(result["entries"], 3)
            self.assertEqual(result["links_separately_verified"], 1)
            self.assertEqual((root / "restored/Build/Products/link").read_bytes(), b"qualified owned binary control")
            self.assertEqual(proof.verify_restored_products(root / "restored", manifest)["original_entries_checked"], 3)
            (root / "restored/Build/Products/test").write_bytes(b"mutated after execution")
            with self.assertRaises(ValueError):
                proof.verify_restored_products(root / "restored", manifest)

    def test_external_link_and_tampered_entry_digest_are_refused(self):
        for mode in ("external", "digest"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); packed, manifest = archive(root, external=mode == "external")
                if mode == "digest":
                    value = proof.read(manifest); value["products"]["Build/Products/test"]["sha256"] = "0" * 64
                    proof.save(manifest, value)
                with self.assertRaises(ValueError):
                    proof.restore_products(packed, manifest, root / "restored", APPROVED)

    def test_duplicate_json_and_stale_fixture_never_form_admitted_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"; path.write_text('{"status":"PASS","status":"FAIL"}')
            with self.assertRaises(ValueError): proof.read(path)
        fixture, _, _, _ = sample()
        with self.assertRaises(ValueError): proof.fixture(fixture, BINDING, now=time.time() + 8000)


if __name__ == "__main__":
    unittest.main()
