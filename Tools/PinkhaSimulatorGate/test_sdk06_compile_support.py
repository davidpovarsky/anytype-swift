"""One new pure control for the source-derived SDK06 compile-support boundary.

All seven Swift fixtures and the failed PBX/driver evidence are originals.
Temporary directories are synthetic build paths. No Swift compiler, linker,
enumeration, simulator or product method is invoked.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import unittest

import sdk06_compile_support as support
import sdk06_component_projection as projection

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "docs/validation/20261123-sdk06-compile-support"
METHOD = "test_actual_packet_closure_map_flags_and_project_opt_in"


def fixture(name):
    rows = json.loads((HERE / "fixture-inputs.json").read_bytes())["files"]
    raw = (HERE / name).read_bytes()
    if len(raw) != rows[name]["bytes"] or hashlib.sha256(raw).hexdigest() != rows[name]["sha256"]:
        raise AssertionError("exact_compile_support_fixture_changed:" + name)
    return raw


class SDK06CompileSupportControl(unittest.TestCase):
    def test_actual_packet_closure_map_flags_and_project_opt_in(self):
        fixed, objects = support.fixed_inputs(ROOT)
        contract = projection.contract(ROOT)
        source = {name: fixture("control-data/" + row["basename"])
                  for name, row in contract["source_files"].items()}
        original_pbx = fixture("control-data/original-failed-project.pbxproj")
        comparison = json.loads(fixture("source-evidence/compile-support-comparison.json"))
        old_driver = comparison["rows"]["original-native/command-02.log"]
        loader = re.findall(r'"BUNDLE_LOADER" = ("[^"\n]+");', original_pbx.decode())
        product = re.findall(r'"SWIFT_INCLUDE_PATHS" = \(\n\s*("[^"\n]+"),', original_pbx.decode())
        self.assertEqual((len(loader), len(product)), (1, 1))
        staged = Path(json.loads(loader[0])).parent
        original_products = Path(json.loads(product[0]))
        names = [row["basename"] for row in contract["source_files"].values()]
        default, ids = projection.project_value(names, staged, original_products, contract)

        with self.subTest(scope="actual_packet_and_original_consumer_are_exact"):
            self.assertEqual((len(fixed["files"]), len(objects), len(fixed["link_proofs"])), (105, 109, 4))
            self.assertEqual((len(fixed["source_maps"]), len(fixed["derived_maps"])), (5, 13))
            self.assertEqual(sum(len(raw) for raw in objects.values()), 319378)
            self.assertEqual(fixed["original_app_source"], projection.SOURCE)
            self.assertEqual(fixed["original_package_resolved_sha256"],
                             "e1f20cfcd191832a49f3f94925aa314968d8ee9e344d6fac9a4aa30f2d90cc4f")
            self.assertEqual(old_driver["parent_sha256"],
                             "becf90b918076ddae2beb7c609461a568fcbae56f4b54c367fe3e2c0423a11e4")
            self.assertEqual(old_driver["line_number"], 24751)
            self.assertEqual(len(old_driver["explicit_module_maps"]), 18)
            def translated(path):
                if "/SourcePackages/checkouts/" in path:
                    package, tail = path.split("/SourcePackages/checkouts/", 1)[1].split("/", 1)
                    return "SourcePackages/" + package.lower() + "/" + tail
                return "GeneratedModuleMaps-iphonesimulator/" + path.rsplit("/", 1)[1]
            self.assertEqual(fixed["map_order"], list(map(translated, old_driver["explicit_module_maps"])))
            self.assertEqual(fixed["include_order"], [
                translated(path) for path in old_driver["clang_include_paths"]
                if "/SourcePackages/checkouts/" in path])
            self.assertEqual(("// !$*UTF8*$!\n" + projection.openstep(default) + "\n").encode(),
                             original_pbx)

        with tempfile.TemporaryDirectory(prefix="sdk06-compile-support-control-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            snapshot = {}
            for name, raw in source.items():
                path = root / "original-swift" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                path.chmod(0o644)
                snapshot[name] = hashlib.sha256(raw).hexdigest()
            sealed = support.materialize(ROOT, root / "support-project")
            settings = sealed.settings()
            receipt = sealed.receipt()
            original_inventory = sealed.verify()
            with self.subTest(scope="four_link_targets_and_five_source_maps_remain_pinned"):
                self.assertEqual(receipt["input_regular_files"], 105)
                for row in fixed["files"]:
                    path = sealed.root / row["path"]
                    info = path.lstat()
                    self.assertTrue(stat.S_ISREG(info.st_mode))
                    self.assertFalse(path.is_symlink())
                    self.assertEqual(info.st_nlink, 1)
                    self.assertEqual(stat.S_IMODE(info.st_mode), row["runtime_mode"])
                    self.assertEqual(path.read_bytes(), objects[row["content_blob"]])
                for row in fixed["source_maps"]:
                    self.assertEqual((sealed.root / row["path"]).read_bytes(), objects[row["git_blob"]])
                    self.assertEqual(row["provenance"], "PRESERVED_PINNED_PACKAGE_SOURCE")
                for proof in fixed["link_proofs"]:
                    relative = "SourcePackages/" + proof["identity"] + "/" + proof["link_path"]
                    self.assertEqual((sealed.root / relative).read_bytes(), objects[proof["target_blob"]])
                    self.assertEqual(objects[proof["link_blob"]].decode(), proof["link_text"])
                self.assertFalse(receipt["original_generated_maps_preserved"])
                self.assertFalse(receipt["compile_or_product_acceptance"])

            with self.subTest(scope="thirteen_new_maps_and_eighteen_explicit_flags"):
                self.assertEqual(set(settings), {"HEADER_SEARCH_PATHS", "OTHER_SWIFT_FLAGS"})
                self.assertEqual(settings["HEADER_SEARCH_PATHS"],
                                 [str(sealed.root / name) for name in fixed["include_order"]])
                self.assertEqual(settings["OTHER_SWIFT_FLAGS"], ["$(inherited)"] + [
                    part for name in fixed["map_order"]
                    for part in ("-Xcc", "-fmodule-map-file=" + str(sealed.root / name))])
                self.assertEqual(len(settings["OTHER_SWIFT_FLAGS"]), 37)
                for row in fixed["derived_maps"]:
                    expected = ("module " + row["module"] + " {\n    umbrella "
                                + json.dumps(str(sealed.root / row["umbrella"]), ensure_ascii=True)
                                + "\n    export *\n}\n").encode()
                    self.assertEqual((sealed.root / row["path"]).read_bytes(), expected)
                    self.assertEqual(row["provenance"], "NEW_DERIVED")
                    self.assertFalse(row["original_generated_bytes_preserved"])
                inventory = sealed.verify()
                self.assertEqual(sum(row[0] == "file" for row in inventory.values()), 118)
                self.assertEqual(set(inventory),
                                 set(receipt["inventory"]))

            with self.subTest(scope="only_header_settings_extend_the_original_unit_only_graph"):
                value, got_ids = projection.project_value(
                    names, staged, original_products, contract, compile_support=sealed)
                self.assertEqual(got_ids, ids)
                actual_settings = value["objects"][ids["target-config"]]["buildSettings"]
                self.assertEqual(actual_settings["TEST_HOST"], "")
                self.assertEqual(actual_settings["BUNDLE_LOADER"], str(staged / "Anytype"))
                self.assertEqual(actual_settings["OTHER_LDFLAGS"], [str(staged / "Anytype.debug.dylib")])
                inverse = copy.deepcopy(value)
                for key in settings:
                    del inverse["objects"][ids["target-config"]]["buildSettings"][key]
                self.assertEqual(inverse, default)
                targets = [row for row in value["objects"].values() if row.get("isa") == "PBXNativeTarget"]
                self.assertEqual(len(targets), 1)
                self.assertEqual(targets[0]["productType"], "com.apple.product-type.bundle.unit-test")
                self.assertEqual(targets[0]["dependencies"], [])
                self.assertEqual(targets[0]["packageProductDependencies"], [])
                self.assertEqual(value["objects"][value["rootObject"]]["packageReferences"], [])
                with self.assertRaisesRegex(ValueError, "concrete fixed compile-support"):
                    projection.project_value(names, staged, original_products, contract,
                                             compile_support=object())

            with self.subTest(scope="real_opt_in_writer_binds_all_generated_support_members"):
                old_umask = os.umask(0o022)
                try:
                    project, generated = projection.write_project(
                        ROOT, root / "original-swift", root / "integrated-project",
                        staged, original_products, with_compile_support=True)
                finally:
                    os.umask(old_umask)
                self.assertEqual(generated["compile_support"]["manifest_sha256"], support.MANIFEST_SHA)
                self.assertEqual(generated["app_build_targets"], 0)
                self.assertEqual(generated["native_library_build_targets"], 0)
                self.assertEqual(generated["package_build_targets"], 0)
                hashes = {path.relative_to(project.parent).as_posix():
                          hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in project.parent.rglob("*") if path.is_file()}
                self.assertEqual(hashes, generated["generated_files"])
                self.assertEqual(len(hashes), 128)
                self.assertEqual(sum(name.startswith("CompileSupport/") for name in hashes), 118)
                for name, wanted in snapshot.items():
                    self.assertEqual(hashlib.sha256((root / "original-swift" / name).read_bytes()).hexdigest(),
                                     wanted)
                with self.assertRaisesRegex(ValueError, "must be fresh"):
                    projection.write_project(ROOT, root / "original-swift", project.parent,
                                             staged, original_products, with_compile_support=True)

            with self.subTest(scope="corrupt_packet_refused_before_any_destination_write"):
                copied = root / "corrupt-control"
                for name in (support.MANIFEST, support.PACKET):
                    path = copied / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes((ROOT / name).read_bytes())
                packet = copied / support.PACKET
                raw = packet.read_bytes()
                packet.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                with self.assertRaisesRegex(ValueError, "source packet changed"):
                    support.materialize(copied, root / "rejected-project")
                self.assertFalse((root / "rejected-project").exists())

            changed_map = sealed.root / fixed["derived_maps"][0]["path"]
            saved_map = changed_map.read_bytes()
            with self.subTest(scope="changed_generated_map_refused"):
                try:
                    changed_map.write_bytes(saved_map + b"\n")
                    with self.assertRaisesRegex(ValueError, "exact compile-support"):
                        sealed.settings()
                finally:
                    changed_map.write_bytes(saved_map)
            with self.subTest(scope="unrecorded_extra_file_refused"):
                extra = sealed.root / "unrecorded.h"
                try:
                    extra.write_bytes(b"/* control-only extra */\n")
                    with self.assertRaisesRegex(ValueError, "exact compile-support"):
                        sealed.verify()
                finally:
                    extra.unlink()
            with self.subTest(scope="linked_input_and_linked_destination_refused"):
                outside = root / "external-control-map"
                outside.write_bytes(saved_map)
                try:
                    changed_map.unlink()
                    changed_map.symlink_to(outside)
                    with self.assertRaisesRegex(ValueError, "symbolic link"):
                        sealed.verify()
                finally:
                    changed_map.unlink()
                    changed_map.write_bytes(saved_map)
                    changed_map.chmod(0o644)
                linked = root / "linked-project"
                linked.symlink_to(sealed.root, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    support.materialize(ROOT, linked / "new-project")
                self.assertEqual(outside.read_bytes(), saved_map)
                self.assertEqual(sealed.verify(), original_inventory)

        with self.subTest(scope="old_runtime_registration_and_selection_function_bodies_unchanged"):
            prior = ast.parse(fixture("source-evidence/base-generator.py").decode())
            current = ast.parse((ROOT / "Tools/PinkhaSimulatorGate/sdk06_component_projection.py").read_text())
            selected = {"contract", "projected_sources", "require_pending_registration",
                        "descriptor_value", "scheme_bytes", "openstep", "object_id"}
            before = {node.name: ast.dump(node, include_attributes=False)
                      for node in prior.body if isinstance(node, ast.FunctionDef) and node.name in selected}
            after = {node.name: ast.dump(node, include_attributes=False)
                     for node in current.body if isinstance(node, ast.FunctionDef) and node.name in selected}
            self.assertEqual(set(before), selected)
            self.assertEqual(after, before)
