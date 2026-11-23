#!/usr/bin/env python3
"""Four new boundary controls; no old controller or Apple product method is executed."""
from __future__ import annotations
import copy
import io
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import tarfile
import tempfile
import unittest
import native_ui_original_products_contract as c

FIXTURE = Path(__file__).parent / "fixtures/native-ui-original-products/PinkhaAnyNativeApp_iphonesimulator27.0-arm64.xctestrun"
APP = "4b09cc5478c60c1c6728a54f2a27a115637a835b"
PROVIDER_BASE = "846c33eac1b399f625b5d3bc6ead9ebed39c43c2"


class OriginalNativeUIProductsControls(unittest.TestCase):
    def test_two_origins_zero_builds_and_unexecuted_scope_refuse_relabeling(self):
        fixed = c.contract()
        ctx = {"controlCommit": "f" * 40, "currentRunID": "999000111", "currentRunAttempt": 1,
               "controllerSourceInputs": {}, "qualifiedProvider": {}}
        with tempfile.TemporaryDirectory(prefix="native-ui-origin-control-") as directory:
            root = Path(directory)
            control, app = root / "control", root / "app"
            control.mkdir(); app.mkdir()
            locations = {"app": app, "evidence": control / "build/any-patched-evidence",
                         "work": control / "build/native-ui-original-products",
                         "products": control / "build/any-native-app-derived/Build/Products",
                         "originals": control / "build/any-patched-evidence/original-451082",
                         "download": control / "build/native-ui-original-products/download",
                         "derived": control / "build/any-native-app-derived"}
            c.validate_paths(locations, control)
            record = {"status": "ADMITTED_ORIGINAL_NATIVE_UI_PRODUCTS", **ctx,
                      "contract": c.PROFILE, "contractSHA256": c.CONTRACT_SHA,
                      "applicationCommit": APP, "applicationCheckout": str(app),
                      "productsDirectory": str(locations["products"]), "originalArtifact": fixed["artifact"],
                      "originalFrozenBuildSHA256": fixed["metadataSHA256"]["native-shared-products.json"],
                      "originalProductOrigin": {"origin": fixed["origin"], "successfulBuildInvocation": 1,
                                               "executedCurrentMethodsAtOrigin": 0},
                      "currentApplicationBuilds": 0, "currentUIRunnerBuilds": 0,
                      "currentNativeLibraryBuilds": 0, "currentMethodsExecutedAtAdmission": 0,
                      "retainedProof": {"retainedMethodsWithOrigins": fixed["retainedMethods"],
                                        "retainedMethodCount": 22, "retainedMethodsExecutedThisRun": 0},
                      "selection": {name: list(value[2]) for name, value in c.STAGES.items()}}
            c.validate_admission_origin(record, fixed, ctx, locations)
            for key, value in (("applicationCommit", ctx["controlCommit"]), ("currentApplicationBuilds", 1),
                               ("currentUIRunnerBuilds", False), ("currentMethodsExecutedAtAdmission", 1),
                               ("applicationCheckout", str(control)), ("originalFrozenBuildSHA256", "0" * 64)):
                with self.subTest(changed=key):
                    changed = copy.deepcopy(record); changed[key] = value
                    with self.assertRaises(ValueError):
                        c.validate_admission_origin(changed, fixed, ctx, locations)
            changed = copy.deepcopy(record)
            changed["originalProductOrigin"]["origin"]["commit"] = ctx["controlCommit"]
            with self.assertRaises(ValueError):
                c.validate_admission_origin(changed, fixed, ctx, locations)
            changed = copy.deepcopy(record)
            changed["selection"]["native-ui-continuation"][0] = next(iter(fixed["retainedMethods"]))
            with self.assertRaises(ValueError):
                c.validate_admission_origin(changed, fixed, ctx, locations)
            for key, value in (("app", control / "app"), ("products", root / "foreign-products"),
                               ("evidence", app / "build/any-patched-evidence")):
                with self.subTest(path=key):
                    with self.assertRaises(ValueError):
                        c.validate_paths({**locations, key: value}, control)
            alias = root / "alias"; alias.symlink_to(locations["products"])
            with self.assertRaises(ValueError):
                c.validate_paths({**locations, "products": alias}, control)
        origin = fixed["origin"]
        run = {"id": int(origin["runID"]), "run_attempt": 1, "head_sha": APP,
               "head_branch": origin["branch"], "path": origin["workflow"], "event": "workflow_dispatch",
               "status": "completed", "conclusion": "failure",
               "repository": {"full_name": fixed["repository"]}, "head_repository": {"full_name": fixed["repository"]}}
        artifact = {"id": fixed["artifact"]["id"], "name": fixed["artifact"]["name"], "expired": False,
                    "size_in_bytes": fixed["artifact"]["bytes"], "digest": "sha256:" + fixed["artifact"]["sha256"],
                    "workflow_run": {"id": int(origin["runID"]), "head_sha": APP}}
        steps = [{"number": int(n), "name": name, "conclusion": conclusion}
                 for group, conclusion in (("originalSuccessfulSteps", "success"), ("originalUnexecutedSteps", "skipped"))
                 for n, name in fixed[group].items()]
        jobs = {"jobs": [{"id": origin["jobID"], "run_id": int(origin["runID"]), "head_sha": APP,
                          "status": "completed", "conclusion": "failure", "steps": steps}]}
        self.assertEqual(c.validate_original_api(run, artifact, jobs, fixed)["executedCurrentMethodsAtOrigin"], 0)
        for kind in ("successful-relabel", "wrong-attempt", "wrong-carrier", "already-executed"):
            with self.subTest(original=kind):
                r, a, j = copy.deepcopy(run), copy.deepcopy(artifact), copy.deepcopy(jobs)
                if kind == "successful-relabel": r["conclusion"] = "success"
                elif kind == "wrong-attempt": r["run_attempt"] = 2
                elif kind == "wrong-carrier": a["digest"] = "sha256:" + "0" * 64
                else: j["jobs"][0]["steps"][-1]["conclusion"] = "success"
                with self.assertRaises(ValueError):
                    c.validate_original_api(r, a, j, fixed)

        owned = "1A111111-2222-4333-8444-555555555555"
        self.assertTrue(c.validate_owned_device_absence({"devices": {}}, owned)["ownedDeviceAbsent"])
        foreign = {"devices": {"runtime": [{"udid": "AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE"}]}}
        self.assertEqual(c.validate_owned_device_absence(foreign, owned)["enumeratedDeviceCount"], 1)
        malformed = [{}, {"devices": None}, {"devices": []}, {"devices": {"runtime": {}}},
                     {"devices": {"runtime": [None]}}, {"devices": {"runtime": [{"udid": 4}]}},
                     {"devices": {"runtime": [{"udid": "not-a-uuid"}]}},
                     {"devices": {"runtime": [{"udid": owned.lower()}]}}]
        for inventory in malformed:
            with self.subTest(cleanup_inventory=inventory):
                with self.assertRaises(ValueError):
                    c.validate_owned_device_absence(inventory, owned)

    def test_restoration_preserves_modes_and_refuses_links_extras_missing_or_changed_bytes(self):
        with tempfile.TemporaryDirectory(prefix="native-ui-restore-control-") as directory:
            root = Path(directory)
            entries = [
                {"name": "Debug-iphonesimulator/PinkhaAnyNative.app", "kind": "directory", "mode": 0o755, "bytes": 0},
                {"name": "Debug-iphonesimulator/PinkhaAnyNative.app/PinkhaAnyNative", "kind": "file",
                 "mode": 0o755, "bytes": 12, "sha256": c.sha(b"CONTROL-ONLY")},
                {"name": "original.xctestrun", "kind": "file", "mode": 0o644, "bytes": 10,
                 "sha256": c.sha(b"descriptor")}]
            def archive(name, variant=None):
                path = root / (name + ".tar.gz")
                with tarfile.open(path, "w:gz") as stream:
                    for index, expected in enumerate(entries):
                        info = tarfile.TarInfo(expected["name"])
                        info.mode = expected["mode"]; info.size = expected["bytes"]
                        if expected["kind"] == "directory":
                            info.type = tarfile.DIRTYPE; stream.addfile(info); continue
                        value = b"CONTROL-ONLY" if index == 1 else b"descriptor"
                        if variant == "bytes" and index == 1: value = b"ALTERED-ONLY"
                        if variant == "mode" and index == 1: info.mode = 0o644
                        if variant == "link" and index == 1:
                            info.type = tarfile.SYMTYPE; info.linkname = str(root / "outside"); info.size = 0
                            stream.addfile(info); continue
                        if variant == "missing" and index == 1: continue
                        stream.addfile(info, io.BytesIO(value))
                    if variant in {"escape", "extra", "duplicate"}:
                        name = "../outside" if variant == "escape" else "unexpected" if variant == "extra" else entries[2]["name"]
                        info = tarfile.TarInfo(name); info.mode = 0o644; info.size = 1
                        stream.addfile(info, io.BytesIO(b"x"))
                return path
            products = root / "good"
            c.restore_tar(archive("good"), products, entries)
            self.assertEqual(c.verify_entries(products, entries)["originalRegularFiles"], 2)
            executable = products / entries[1]["name"]
            self.assertEqual(stat.S_IMODE(executable.stat().st_mode), 0o755)
            self.assertEqual(executable.read_bytes(), b"CONTROL-ONLY")
            with self.assertRaises(ValueError):
                c.verify_entries(products, entries, copy_sha=c.sha(b"copy"))
            copied = products / c.COPY_NAME; copied.write_bytes(b"copy")
            c.verify_entries(products, entries, copy_sha=c.sha(b"copy"))
            copied.unlink()
            executable.chmod(0o644)
            with self.assertRaises(ValueError):
                c.verify_entries(products, entries)
            executable.chmod(0o755)
            (products / "unexpected-link").symlink_to(root / "outside")
            with self.assertRaises(ValueError):
                c.verify_entries(products, entries)
            for variant in ("bytes", "mode", "link", "missing", "escape", "extra", "duplicate"):
                with self.subTest(variant=variant):
                    with self.assertRaises(ValueError):
                        c.restore_tar(archive(variant, variant), root / (variant + "-products"), entries)
            self.assertFalse((root / "outside").exists())

    def test_exact_27_2_runtime_and_original_descriptor_allow_only_one_bound_token_change(self):
        fixed = c.contract(); policy = fixed["runtime"]
        with tempfile.TemporaryDirectory(prefix="native-ui-runtime-control-") as directory:
            root = Path(directory)
            runtime_root = root / "runtime"; library = runtime_root / "usr/lib/libMainThreadChecker.dylib"
            library.parent.mkdir(parents=True); library.write_bytes(b"\xcf\xfa\xed\xfeCONTROL-ONLY")
            device = {"identifier": policy["deviceType"], "productFamily": "iPad", "name": "iPad mini (A20 Pro)",
                      "minRuntimeVersion": (27 << 16) | (2 << 8), "maxRuntimeVersion": 0xFFFFFFFF}
            runtime = {"identifier": policy["identifier"], "version": "27.2", "buildversion": "24B8117",
                       "isAvailable": True, "supportedArchitectures": ["arm64"], "runtimeRoot": str(runtime_root),
                       "supportedDeviceTypes": [dict(device)]}
            pair = c.runtime_pair({"runtimes": [runtime]}, {"devicetypes": [device]}, fixed)
            self.assertEqual(pair["selection"]["runtimeBuild"], "24B8117")
            for change in ("build", "version", "architecture", "support", "bounds", "duplicate"):
                with self.subTest(runtime=change):
                    r, d = copy.deepcopy(runtime), copy.deepcopy(device)
                    if change == "build": r["buildversion"] = "24A434"
                    elif change == "version": r["version"] = "27.0"
                    elif change == "architecture": r["supportedArchitectures"] = ["x86_64"]
                    elif change == "support": r["supportedDeviceTypes"] = []
                    elif change == "bounds": d["minRuntimeVersion"] = 28 << 16
                    with self.assertRaises(ValueError):
                        c.runtime_pair({"runtimes": [r, r] if change == "duplicate" else [r]},
                                       {"devicetypes": [d]}, fixed)
            product = root / "products"; product.mkdir()
            original = product / FIXTURE.name; original.write_bytes(FIXTURE.read_bytes())
            before = original.read_bytes()
            self.assertEqual(c.sha(before), "67228dbc1e1636b9e877d487528ea1fa37023a9a3ff8e53c8d92a94d38c897e6")
            copied = product / c.COPY_NAME
            proof = c.copied_descriptor(original, copied, runtime, fixed)
            self.assertEqual(original.read_bytes(), before)
            self.assertEqual(proof["normalization"]["original_token"], policy["originalMainThreadChecker"])
            self.assertIn("7ygB8c", proof["normalization"]["original_token"])
            current, old = plistlib.loads(copied.read_bytes()), plistlib.loads(before)
            current["PinkhaAnyNativeUITests"]["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = (
                old["PinkhaAnyNativeUITests"]["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"])
            self.assertEqual(current, old)
            copied.unlink()
            for kind in ("foreign-copy-parent", "wrong-original-hash", "wrong-token", "non-macho-current-library"):
                with self.subTest(descriptor=kind):
                    f = copy.deepcopy(fixed); target = copied
                    if kind == "foreign-copy-parent": target = root / c.COPY_NAME
                    elif kind == "wrong-original-hash": f["productArchive"]["xctestrun"][0]["sha256"] = "0" * 64
                    elif kind == "wrong-token": f["runtime"]["originalMainThreadChecker"] = "/wrong/DPYuL8/usr/lib/libMainThreadChecker.dylib"
                    else: library.write_bytes(b"NOT-A-MACHO")
                    with self.assertRaises(ValueError):
                        c.copied_descriptor(original, target, runtime, f)
                    self.assertFalse(target.exists())

    def test_fixed_commands_and_workflow_never_build_or_repeat_twenty_two_retained_methods(self):
        fixed = c.contract()
        expected = {
            "NativeLaunchTests/testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType",
            "NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen",
            "NativeLaunchTests/testSourceDragIntoNativeEditorPreservesTargetAndColdReopens",
            "NativeLaunchTests/testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen",
            "NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies",
            "NativeLaunchTests/testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen",
            "NativeHistoryTests/testSavedHebrewVersionsRemainReadOnlyAcrossCloseBackgroundAndColdReopen"}
        actual = set()
        for stage, allowance in (("native-ui-continuation", 360), ("archive-roundtrip", 1800),
                                 ("custom-type", 360), ("native-history", 1800)):
            plan = c.plan(stage, Path("/owned/Products") / c.COPY_NAME,
                          "11111111-2222-4333-8444-555555555555", Path("/owned") / (stage + ".xcresult"))
            command = plan["command"]
            self.assertEqual(command[:2], ["xcodebuild", "test-without-building"])
            self.assertTrue({"-project", "-scheme", "-derivedDataPath", "build", "build-for-testing",
                             "-resolvePackageDependencies"}.isdisjoint(command))
            self.assertEqual(command[command.index("-default-test-execution-time-allowance") + 1], str(allowance))
            self.assertEqual(command[command.index("-maximum-test-execution-time-allowance") + 1], str(allowance))
            selected = {value.removeprefix("-only-testing:PinkhaAnyNativeUITests/")
                        for value in command if value.startswith("-only-testing:")}
            self.assertEqual(selected, set(plan["methods"]))
            actual.update(selected)
        self.assertEqual(actual, expected)
        self.assertTrue(actual.isdisjoint(fixed["retainedMethods"]))
        workflow = (c.ROOT / c.WORKFLOW).read_text()
        self.assertEqual(workflow.count("CURRENT_UI_STAGE:"), 4)
        for stage in c.STAGES:
            self.assertEqual(workflow.count("CURRENT_UI_STAGE: " + stage + "\n"), 1)
        self.assertNotIn("build-for-testing", workflow)
        self.assertNotIn("swift test", workflow)
        self.assertNotIn("unittest", workflow)
        self.assertIn("timeout-minutes: 120", workflow)
        self.assertIn("subprocess.Popen(plan[\"command\"]", workflow)
        self.assertIn("steps.four.outcome == 'success' && steps.files.outcome == 'success'", workflow)
        self.assertIn("steps.custom_type.outcome == 'success'", workflow)
        central = (c.ROOT / c.CENTRAL).read_text()
        restored = central.replace("          - native-ui-original-products\n", "", 1).replace(
            "  native-ui-original-products:\n"
            "    if: ${{ inputs.route == 'native-ui-original-products' }}\n"
            "    uses: ./.github/workflows/pinkha-any-native-ui-original-products.yml\n\n", "", 1)
        original = subprocess.check_output(["git", "show", PROVIDER_BASE + ":" + c.CENTRAL],
                                           cwd=c.ROOT, timeout=30).decode()
        self.assertEqual(restored, original)
        with self.assertRaises(ValueError):
            c.plan("old-passed-methods", Path("/owned/config"), "11111111-2222-4333-8444-555555555555",
                   Path("/owned/result"))
        changed = {name: list(value[2]) for name, value in c.STAGES.items()}
        changed["native-ui-continuation"].append(next(iter(fixed["retainedMethods"])))
        with self.assertRaises(ValueError):
            c.validate_selection(changed, fixed)


if __name__ == "__main__":
    unittest.main()
