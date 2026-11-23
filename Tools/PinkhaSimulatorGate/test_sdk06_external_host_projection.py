#!/usr/bin/env python3
"""One affected pure control: external host linkage and frozen workspace closure.

The original log and archive are evidence. Temporary files and Mac path strings
are control fixtures, not a linked test bundle, an App execution, or enumeration.
"""
from __future__ import annotations
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import stat
import tarfile
import tempfile
import unittest

import sdk06_component_projection as projection

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "docs/validation/20261123-sdk06-external-host-projection"
ORIGINALS = ROOT / "docs/validation/20261123-sdk06-component-projection/control-data"
METHOD = "test_actual_link_carriers_build_only_host_and_frozen_workspace"


def fixed_bytes(name):
    rows = json.loads((HERE / "evidence-inputs.json").read_bytes())["files"]
    raw = (HERE / name).read_bytes()
    if len(raw) != rows[name]["bytes"] or hashlib.sha256(raw).hexdigest() != rows[name]["sha256"]:
        raise AssertionError("actual_evidence_changed:" + name)
    return raw


def original_swift(name):
    rows = json.loads((ORIGINALS / "fixture-origins.json").read_bytes())["files"]
    raw = (ORIGINALS / name).read_bytes()
    if len(raw) != rows[name]["bytes"] or hashlib.sha256(raw).hexdigest() != rows[name]["sha256"]:
        raise AssertionError("actual_original_fixture_changed:" + name)
    return raw


class SDK06ExternalHostProjectionControl(unittest.TestCase):
    def test_actual_link_carriers_build_only_host_and_frozen_workspace(self):
        fixed = projection.contract(ROOT)
        source = {name: original_swift(row["basename"])
                  for name, row in fixed["source_files"].items()}
        observed = json.loads(fixed_bytes("originals/actual-source-observations.json"))
        link = json.loads(fixed_bytes("originals/original-link-observation.json"))
        argv = shlex.split(next(x["text"] for x in link["matching_lines"] if x["line"] == 30376))
        shim = Path(argv[argv.index("-bundle_loader") + 1])
        dylibs = [Path(x) for x in argv if x.endswith("/Anytype.app/Anytype.debug.dylib")]
        with self.subTest(scope="actual_successful_link_uses_original_shim_and_debug_dylib"):
            self.assertEqual(len(dylibs), 1)
            self.assertEqual(dylibs[0].parent, shim.parent)
            self.assertEqual(shim.name, "Anytype")
            self.assertNotIn("dynamic_lookup", argv)
            self.assertEqual(link["log_sha256"],
                             "becf90b918076ddae2beb7c609461a568fcbae56f4b54c367fe3e2c0423a11e4")
            self.assertEqual(observed["origin"]["run"], "45201516379")
            self.assertEqual(observed["origin"]["attempt"], 1)
            host_rows = observed["staged_host_rows"]
            self.assertEqual(set(host_rows), {"Anytype", "Anytype.debug.dylib", "Info.plist"})
            self.assertEqual(host_rows["Anytype"]["sha256"],
                             "7a4e21e07a8dd78cb22bfcb9b75c8f84ee3a74742b838e272977cdcc6d66ace2")
            self.assertEqual(host_rows["Anytype.debug.dylib"]["sha256"],
                             "7dd0c65ff55d2cb302631cd163bb2df598051197c3f01f342df6cb666daac17d")
            self.assertEqual(host_rows["Anytype"]["bytes"], 40496)
            self.assertEqual(host_rows["Anytype.debug.dylib"]["bytes"], 126639408)
            self.assertTrue(all(host_rows[x]["mode"] == 0o755
                                for x in ("Anytype", "Anytype.debug.dylib")))

        raw_tar = fixed_bytes("originals/SDK06PendingProducts.tar.gz")
        archive_rows, archive_files = {}, {}
        with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r:gz") as archive:
            for member in archive:
                self.assertNotIn(member.name, archive_rows)
                self.assertTrue(member.isdir() or member.isfile())
                self.assertTrue(member.name == "Source" or member.name.startswith("Source/"))
                self.assertFalse(set(Path(member.name).parts) & {".", ".."})
                self.assertFalse(Path(member.name).is_absolute())
                archive_rows[member.name] = {
                    "kind": "file" if member.isfile() else "directory",
                    "mode": member.mode, "bytes": member.size,
                }
                if member.isfile():
                    self.assertLessEqual(member.size, 64 * 1024)
                    archive_files[member.name] = archive.extractfile(member).read()
        self.assertEqual(len(archive_rows), 19)
        self.assertEqual(len(archive_files), 10)
        original_pbx = archive_files["Source/SDK06PendingComponents.xcodeproj/project.pbxproj"]
        host_matches = re.findall(r'"TEST_HOST" = ("[^"\n]+");', original_pbx.decode())
        product_matches = re.findall(r'"SWIFT_INCLUDE_PATHS" = \(\n\s*("[^"\n]+"),', original_pbx.decode())
        self.assertEqual((len(host_matches), len(product_matches)), (1, 1))
        staged_app = Path(json.loads(host_matches[0])).parent
        original_configuration = Path(json.loads(product_matches[0]))
        projected, _ = projection.projected_sources(source, fixed)
        current, ids = projection.project_value(list(projected), staged_app, original_configuration, fixed)
        settings = current["objects"][ids["target-config"]]["buildSettings"]
        with self.subTest(scope="only_build_host_fields_change_from_actual_failed_project"):
            self.assertEqual(settings["TEST_HOST"], "")
            self.assertEqual(settings["BUNDLE_LOADER"], str(staged_app / shim.name))
            self.assertEqual(settings["OTHER_LDFLAGS"], [str(staged_app / dylibs[0].name)])
            self.assertNotIn("dynamic_lookup", json.dumps(current))
            self.assertNotIn("allow_undefined", json.dumps(current))
            inverse = copy.deepcopy(current)
            inverse_settings = inverse["objects"][ids["target-config"]]["buildSettings"]
            inverse_settings["TEST_HOST"] = str(staged_app / "Anytype")
            inverse_settings["BUNDLE_LOADER"] = "$(TEST_HOST)"
            del inverse_settings["OTHER_LDFLAGS"]
            self.assertEqual(("// !$*UTF8*$!\n" + projection.openstep(inverse) + "\n").encode(),
                             original_pbx)
            targets = [x for x in current["objects"].values() if x.get("isa") == "PBXNativeTarget"]
            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0]["productType"], "com.apple.product-type.bundle.unit-test")
            self.assertEqual(targets[0]["dependencies"], [])
            self.assertEqual(targets[0]["packageProductDependencies"], [])
            self.assertEqual(current["objects"][current["rootObject"]]["packageReferences"], [])

        with tempfile.TemporaryDirectory(prefix="sdk06-external-host-control-") as temporary:
            root = Path(temporary).resolve()
            source_root = root / "original-swift"
            for name, raw in source.items():
                path = source_root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            destination = root / "generated-source"
            prior_umask = os.umask(0o022)
            try:
                project, receipt = projection.write_project(
                    ROOT, source_root, destination, staged_app, original_configuration)
            finally:
                os.umask(prior_umask)
            with self.subTest(scope="exact_observed_workspace_tree_is_frozen_before_build"):
                actual = {}
                for path in sorted(destination.rglob("*")):
                    self.assertFalse(path.is_symlink())
                    info = path.lstat()
                    relative = "Source/" + path.relative_to(destination).as_posix()
                    actual[relative] = {
                        "kind": "file" if path.is_file() else "directory",
                        "mode": stat.S_IMODE(info.st_mode),
                        "bytes": info.st_size if path.is_file() else 0,
                    }
                expected = {k: v for k, v in archive_rows.items() if k != "Source"}
                self.assertEqual(set(actual), set(expected))
                pbx_name = "Source/SDK06PendingComponents.xcodeproj/project.pbxproj"
                for name in expected:
                    if name == pbx_name:
                        self.assertEqual(actual[name]["kind"], expected[name]["kind"])
                        self.assertEqual(actual[name]["mode"], expected[name]["mode"])
                        continue
                    self.assertEqual(actual[name], expected[name], name)
                    if name in archive_files:
                        self.assertEqual((destination / name.removeprefix("Source/")).read_bytes(),
                                         archive_files[name], name)
                workspace = project / "project.xcworkspace"
                added = ("xcshareddata", "xcshareddata/swiftpm", "xcshareddata/swiftpm/configuration")
                self.assertEqual({p.relative_to(workspace).as_posix() for p in workspace.rglob("*")
                                  if p.is_dir()}, set(added))
                for name in added:
                    self.assertEqual(stat.S_IMODE((workspace / name).lstat().st_mode), 0o777)
                self.assertEqual(list((workspace / added[-1]).iterdir()), [])
                actual_hashes = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in destination.rglob("*") if p.is_file()}
                self.assertEqual(actual_hashes, receipt["generated_files"])
                self.assertEqual(len(actual_hashes), 10)
                self.assertEqual((project / "project.pbxproj").read_bytes(),
                                 ("// !$*UTF8*$!\n" + projection.openstep(current) + "\n").encode())
                self.assertTrue(all((source_root / name).read_bytes() == raw for name, raw in source.items()))

        with self.subTest(scope="build_only_empty_host_keeps_actual_hosted_runtime_descriptor"):
            original_raw = original_swift("normalized-native.xctestrun")
            original = plistlib.loads(original_raw)
            products_root = original_configuration.parent
            bundle = staged_app.parent.parent / "new-products/SDK06PendingTests.xctest"
            runtime = projection.descriptor_value(original, products_root, staged_app, bundle)
            target = runtime["TestConfigurations"][0]["TestTargets"][0]
            self.assertEqual(settings["TEST_HOST"], "")
            self.assertTrue(target["IsAppHostedTestBundle"])
            self.assertEqual(target["TestHostBundleIdentifier"], "io.anytype.app")
            self.assertEqual(target["TestHostPath"], str(staged_app))
            self.assertEqual(target["TestBundlePath"], str(bundle))
            self.assertIn(str(staged_app), target["DependentProductPaths"])
            self.assertIn(str(bundle), target["DependentProductPaths"])
            expected = copy.deepcopy(original)
            expected["TestConfigurations"][0]["TestTargets"] = [
                x for x in expected["TestConfigurations"][0]["TestTargets"]
                if x["BlueprintName"] == "AnytypeTests"
            ]
            def roots(node):
                if isinstance(node, dict):
                    return {k: roots(v) for k, v in node.items()}
                if isinstance(node, list):
                    return [roots(v) for v in node]
                if isinstance(node, str):
                    return node.replace("__TESTROOT__", str(products_root))
                return node
            expected = roots(expected)
            old_host = str(original_configuration / "Anytype.app")
            old_bundle = old_host + "/PlugIns/AnytypeTests.xctest"
            wanted = expected["TestConfigurations"][0]["TestTargets"][0]
            wanted["DependentProductPaths"] = [
                str(staged_app) if x == old_host else str(bundle) if x == old_bundle else x
                for x in wanted["DependentProductPaths"]
            ]
            wanted["TestHostPath"], wanted["TestBundlePath"] = str(staged_app), str(bundle)
            self.assertEqual(runtime, expected)
            self.assertEqual(original, plistlib.loads(original_raw))
