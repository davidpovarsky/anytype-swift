#!/usr/bin/env python3
"""One new composed control using actual original SDK Swift/descriptor bytes.

This is pure host validation. Generated path fixtures are not an App binary,
compiled module closure, successful Xcode build, or actual XCTest enumeration.
"""
from __future__ import annotations
import base64
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
import xml.etree.ElementTree as ET

import sdk06_component_projection as projection

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/validation/20261123-sdk06-component-projection/control-data"
METHOD = "test_actual_source_projection_unit_only_graph_descriptor_and_registration"


def fixture(name):
    manifest = json.loads((FIXTURES / "fixture-origins.json").read_bytes())
    row = manifest["files"][name]
    raw = (FIXTURES / name).read_bytes()
    if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
        raise AssertionError("exact_original_fixture_changed:" + name)
    return raw


class SDK06ComponentProjectionControl(unittest.TestCase):
    def test_actual_source_projection_unit_only_graph_descriptor_and_registration(self):
        fixed = projection.contract(ROOT)
        source = {name: fixture(row["basename"]) for name, row in fixed["source_files"].items()}
        with self.subTest(scope="actual_seven_original_git_blobs_and_exact_pending_scope"):
            self.assertEqual(len(source), 7)
            self.assertEqual(fixed["source_sha"], "75bd6d7af18dfd511e85582ce7f994d2801b7703")
            self.assertEqual(set(fixed["selection"]["declarations"]),
                             set(fixed["selection"]["selected"]) | set(fixed["selection"]["excluded"]))
            self.assertFalse(set(fixed["selection"]["selected"]) & set(fixed["selection"]["excluded"]))
            self.assertEqual((len(fixed["selection"]["selected"]), len(fixed["selection"]["excluded"]),
                              fixed["required_argument_cases"]), (23, 7, 32))
            for name, raw in source.items():
                row = fixed["source_files"][name]
                git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
                self.assertEqual(git_blob, row["git_blob"])
                self.assertEqual(len(raw), row["bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"])

        projected, observations = projection.projected_sources(source, fixed)
        with self.subTest(scope="seven_metadata_only_patches_with_complete_original_inverse"):
            self.assertEqual(len(projected), 7)
            self.assertEqual(sum(raw.count(b"@Test(") for raw in projected.values()), 23)
            editor_before = source[projection.EDITOR]
            editor_after = projected[fixed["source_files"][projection.EDITOR]["basename"]]
            inverse = bytearray(editor_after)
            positions = set()
            self.assertEqual(len(fixed["attribute_patches"]), 7)
            self.assertEqual({p["method"] for p in fixed["attribute_patches"]},
                             set(fixed["selection"]["excluded"]))
            for patch in fixed["attribute_patches"]:
                start = patch["offset"]
                original, blank = patch["before"].encode(), patch["after"].encode()
                self.assertEqual(editor_before[start:start + len(original)], original)
                self.assertEqual(editor_after[start:start + len(blank)], blank)
                self.assertEqual(len(original), len(blank))
                self.assertEqual(blank, bytes(10 if x == 10 else 32 for x in original))
                self.assertFalse(positions.intersection(range(start, start + len(original))))
                positions.update(range(start, start + len(original)))
                inverse[start:start + len(original)] = original
            self.assertEqual(bytes(inverse), editor_before)
            self.assertEqual(editor_after.count(b"\n"), editor_before.count(b"\n"))
            self.assertTrue(all(a == b for i, (a, b) in enumerate(zip(editor_before, editor_after))
                                if i not in positions))
            for name, original in source.items():
                basename = fixed["source_files"][name]["basename"]
                if name != projection.EDITOR:
                    self.assertEqual(projected[basename], original)
                self.assertIs(observations[name]["function_bodies_and_arguments_unchanged"],
                              name != projection.AUTHORITY)
                self.assertEqual(observations[name]["fixture_constructor_replacements"],
                                 2 if name == projection.AUTHORITY else 0)

        corruptions = []
        missing = dict(source)
        missing.pop(next(iter(missing)))
        corruptions.append(("missing_original_source", missing, fixed))
        changed = dict(source)
        first_name = next(iter(changed))
        changed[first_name] = changed[first_name] + b"\n"
        corruptions.append(("changed_original_source", changed, fixed))
        bad_offset = copy.deepcopy(fixed)
        bad_offset["attribute_patches"][0]["offset"] += 1
        corruptions.append(("changed_attribute_offset", source, bad_offset))
        bad_projection = copy.deepcopy(fixed)
        bad_projection["projected_editor_sha256"] = "0" * 64
        corruptions.append(("changed_projected_identity", source, bad_projection))
        for name, inputs, contract in corruptions:
            with self.subTest(refusal=name):
                with self.assertRaises(ValueError):
                    projection.projected_sources(inputs, contract)

        original_archive_raw = fixture("original-native.xctestrun")
        original_descriptor_raw = fixture("normalized-native.xctestrun")
        chain = json.loads(fixture("descriptor-chain.json"))
        provenance = json.loads(fixture("descriptor-origin.json"))
        with self.subTest(scope="actual_original_to_host_normalized_descriptor_chain"):
            self.assertEqual(base64.b64decode(chain["original_bytes_base64"], validate=True), original_archive_raw)
            self.assertEqual(base64.b64decode(chain["host_bytes_base64"], validate=True), original_descriptor_raw)
            self.assertEqual(hashlib.sha256(original_archive_raw).hexdigest(), chain["original_sha256"])
            self.assertEqual(hashlib.sha256(original_descriptor_raw).hexdigest(), chain["host_sha256"])
            self.assertEqual(provenance["chain_sha256"], hashlib.sha256(fixture("descriptor-chain.json")).hexdigest())
            self.assertEqual((provenance["actual_original_run"], provenance["actual_original_attempt"],
                              provenance["actual_original_artifact"]), ("45174279596", 3, "14822034161"))
            normalized_expected = plistlib.loads(original_archive_raw)
            targets = normalized_expected["TestConfigurations"][0]["TestTargets"]
            self.assertEqual({x["BlueprintName"] for x in targets}, set(chain["normalization"]))
            for target in targets:
                change = chain["normalization"][target["BlueprintName"]]
                injected = target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"].split(":")
                self.assertEqual(injected.count(change["original_token"]), 1)
                target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = ":".join(
                    change["replacement_token"] if x == change["original_token"] else x for x in injected)
            self.assertEqual(normalized_expected, plistlib.loads(original_descriptor_raw))
        original_descriptor = plistlib.loads(original_descriptor_raw)
        original_copy = copy.deepcopy(original_descriptor)
        with tempfile.TemporaryDirectory(prefix="sdk06-projection-host-control-") as temporary:
            root = Path(temporary).resolve()
            app_source = root / "immutable-original-source"
            for name, raw in source.items():
                path = app_source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            original_root = root / "original/Build/Products"
            original_configuration = original_root / "Debug-Anytype-iphonesimulator"
            original_configuration.mkdir(parents=True)
            staged_app = root / "disjoint-host/Anytype.app"
            staged_app.mkdir(parents=True)
            destination = root / "new-component-project"
            project, generated = projection.write_project(
                ROOT, app_source, destination, staged_app, original_configuration)
            value, ids = projection.project_value(list(projected), staged_app, original_configuration, fixed)
            objects = value["objects"]
            with self.subTest(scope="one_unit_test_only_target_and_no_implicit_build_graph"):
                targets = [x for x in objects.values() if x.get("isa") == "PBXNativeTarget"]
                self.assertEqual(len(targets), 1)
                target = targets[0]
                self.assertEqual(target["productType"], "com.apple.product-type.bundle.unit-test")
                self.assertEqual(target["dependencies"], [])
                self.assertEqual(target["packageProductDependencies"], [])
                self.assertEqual(objects[value["rootObject"]]["packageReferences"], [])
                self.assertFalse(any(x.get("isa") in {"PBXTargetDependency", "PBXCopyFilesBuildPhase",
                                                     "PBXShellScriptBuildPhase"}
                                     for x in objects.values()))
                configurations = objects[target["buildConfigurationList"]]["buildConfigurations"]
                self.assertEqual(len(configurations), 1)
                settings = objects[configurations[0]]["buildSettings"]
                self.assertEqual(settings["TEST_HOST"], str(staged_app / "Anytype"))
                self.assertEqual(settings["BUNDLE_LOADER"], "$(TEST_HOST)")
                self.assertEqual(settings["PRODUCT_MODULE_NAME"], "AnytypeTests")
                self.assertEqual(settings["PRODUCT_NAME"], "SDK06PendingTests")
                self.assertEqual(settings["SWIFT_INCLUDE_PATHS"], [str(original_configuration)])
                self.assertEqual(settings["FRAMEWORK_SEARCH_PATHS"],
                                 [str(original_configuration), str(original_configuration / "PackageFrameworks"),
                                  str(staged_app / "Frameworks")])
                self.assertEqual({k: settings[k] for k in fixed["original_swift_features"]},
                                 fixed["original_swift_features"])
                phases = [objects[x] for x in target["buildPhases"]]
                self.assertEqual([x["isa"] for x in phases],
                                 ["PBXSourcesBuildPhase", "PBXFrameworksBuildPhase", "PBXResourcesBuildPhase"])
                self.assertEqual(len(phases[0]["files"]), 7)
                self.assertEqual(phases[1]["files"], [])
                self.assertEqual(phases[2]["files"], [])
                refs = [objects[objects[x]["fileRef"]]["path"] for x in phases[0]["files"]]
                self.assertEqual(set(refs), {"Sources/" + name for name in projected})
                self.assertEqual(generated["app_build_targets"], 0)
                self.assertEqual(generated["native_library_build_targets"], 0)
                self.assertEqual(generated["package_build_targets"], 0)
                self.assertEqual(generated["component_test_bundle_targets"], 1)
                self.assertFalse(generated["implicit_dependencies"])
                self.assertFalse(generated["original_source_modified"])
            with self.subTest(scope="actual_generated_source_and_single_scheme_binding"):
                actual_generated = {
                    p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in destination.rglob("*") if p.is_file()
                }
                self.assertEqual(actual_generated, generated["generated_files"])
                self.assertEqual(len(actual_generated), 10)
                workspace = ET.fromstring(
                    (project / "project.xcworkspace/contents.xcworkspacedata").read_bytes())
                self.assertEqual(workspace.tag, "Workspace")
                self.assertEqual(workspace.attrib, {"version": "1.0"})
                self.assertEqual(len(list(workspace)), 1)
                self.assertEqual(workspace.find("FileRef").attrib, {"location": "self:"})
                for name, raw in projected.items():
                    self.assertEqual((destination / "Sources" / name).read_bytes(), raw)
                scheme = ET.fromstring(
                    (project / "xcshareddata/xcschemes" / (projection.SCHEME + ".xcscheme")).read_bytes())
                build = scheme.find("BuildAction")
                self.assertEqual(build.attrib["buildImplicitDependencies"], "NO")
                self.assertEqual(build.attrib["parallelizeBuildables"], "NO")
                entries = build.findall("BuildActionEntries/BuildActionEntry")
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0].attrib["buildForTesting"], "YES")
                self.assertTrue(all(entries[0].attrib[x] == "NO" for x in (
                    "buildForRunning", "buildForProfiling", "buildForArchiving", "buildForAnalyzing")))
                tests = scheme.findall("TestAction/Testables/TestableReference")
                self.assertEqual(len(tests), 1)
                self.assertEqual(tests[0].attrib["skipped"], "NO")
                for reference in scheme.findall(".//BuildableReference"):
                    self.assertEqual(reference.attrib["BlueprintIdentifier"], ids["target"])
                    self.assertEqual(reference.attrib["BlueprintName"], "AnytypeTests")
                    self.assertEqual(reference.attrib["BuildableName"], "SDK06PendingTests.xctest")
            with self.subTest(refusal="unreviewed_project_source"):
                with self.assertRaises(ValueError):
                    projection.project_value([*projected, "Foreign.swift"], staged_app,
                                             original_configuration, fixed)
            with self.subTest(refusal="host_inside_original_products"):
                with self.assertRaises(ValueError):
                    projection.project_value(list(projected), original_configuration / "Anytype.app",
                                             original_configuration, fixed)
            with self.subTest(refusal="generated_project_reuse"):
                with self.assertRaises(ValueError):
                    projection.write_project(ROOT, app_source, destination, staged_app, original_configuration)

            test_bundle = root / "current-products/SDK06PendingTests.xctest"
            relocated = projection.descriptor_value(original_descriptor, original_root, staged_app, test_bundle)
            selected_original = [x for x in original_descriptor["TestConfigurations"][0]["TestTargets"]
                                 if x.get("BlueprintName") == "AnytypeTests"]
            self.assertEqual(len(selected_original), 1)
            original_target = selected_original[0]
            with self.subTest(scope="actual_native_descriptor_keeps_every_nonbinding_field"):
                self.assertEqual(len(relocated["TestConfigurations"]), 1)
                self.assertEqual(len(relocated["TestConfigurations"][0]["TestTargets"]), 1)
                target = relocated["TestConfigurations"][0]["TestTargets"][0]
                self.assertEqual(target["TestHostPath"], str(staged_app))
                self.assertEqual(target["TestBundlePath"], str(test_bundle))
                self.assertEqual(target["TestHostBundleIdentifier"], "io.anytype.app")
                self.assertEqual(target["ProductModuleName"], "AnytypeTests")
                self.assertTrue(target["IsAppHostedTestBundle"])
                self.assertIn(str(staged_app), target["DependentProductPaths"])
                self.assertIn(str(test_bundle), target["DependentProductPaths"])
                self.assertFalse({"OnlyTestIdentifiers", "SkipTestIdentifiers", "OnlyTestTags",
                                  "SkipTestTags", "OnlyTestingTags", "SkipTestingTags", "TagsToRun",
                                  "TagsToSkip"}.intersection(target))

                def original_roots(node):
                    if isinstance(node, dict):
                        return {k: original_roots(v) for k, v in node.items()}
                    if isinstance(node, list):
                        return [original_roots(v) for v in node]
                    if isinstance(node, str):
                        return node.replace("__TESTROOT__", str(original_root))
                    return node

                expected = copy.deepcopy(original_descriptor)
                expected["TestConfigurations"][0]["TestTargets"] = selected_original
                expected = original_roots(expected)
                expected_target = expected["TestConfigurations"][0]["TestTargets"][0]
                host = str(original_root / "Debug-Anytype-iphonesimulator/Anytype.app")
                bundle = host + "/PlugIns/AnytypeTests.xctest"
                expected_target["DependentProductPaths"] = [
                    str(staged_app) if x == host else str(test_bundle) if x == bundle else x
                    for x in expected_target["DependentProductPaths"]
                ]
                expected_target["TestHostPath"] = str(staged_app)
                expected_target["TestBundlePath"] = str(test_bundle)
                self.assertEqual(relocated, expected)
                self.assertEqual(original_descriptor, original_copy)
                self.assertEqual(fixture("normalized-native.xctestrun"), original_descriptor_raw)
                self.assertEqual(fixture("original-native.xctestrun"), original_archive_raw)
                self.assertEqual(target["TestingEnvironmentVariables"],
                                 original_roots(original_target["TestingEnvironmentVariables"]))
            descriptor_refusals = [
                ("unexpected_selector", lambda x: x["TestConfigurations"][0]["TestTargets"][0].update(
                    OnlyTestIdentifiers=["oldPassedMethod"])),
                ("disabled_configuration", lambda x: x["TestConfigurations"][0].update(IsEnabled=False)),
                ("foreign_format", lambda x: x["__xctestrun_metadata__"].update(FormatVersion=1)),
            ]
            for name, mutation in descriptor_refusals:
                with self.subTest(refusal=name):
                    # The original fixture can contain other disabled targets; bind the actual native target only.
                    bad = copy.deepcopy(original_descriptor)
                    bad["TestConfigurations"][0]["TestTargets"] = [copy.deepcopy(original_target)]
                    mutation(bad)
                    with self.assertRaises(ValueError):
                        projection.descriptor_value(bad, original_root, staged_app, test_bundle)
            with self.subTest(refusal="new_bundle_inside_original_products"):
                with self.assertRaises(ValueError):
                    projection.descriptor_value(original_descriptor, original_root, staged_app,
                                                original_root / "SDK06PendingTests.xctest")
            with self.subTest(scope="original_source_tree_unchanged"):
                for name, raw in source.items():
                    self.assertEqual((app_source / name).read_bytes(), raw)

        # These are source-derived synthetic enumeration observations for the pure guard.
        # No compiled test enumeration is performed or inferred by this host control.
        selected, excluded = set(fixed["selection"]["selected"]), set(fixed["selection"]["excluded"])
        with self.subTest(scope="exact_23_enabled_zero_disabled_registration"):
            projection.require_pending_registration("AnytypeTests", selected, set(), fixed)
        registrations = [
            ("original_30_registered", "AnytypeTests", selected | excluded, set()),
            ("one_pending_missing", "AnytypeTests", selected - {next(iter(selected))}, set()),
            ("foreign_registration", "AnytypeTests", selected | {"AnytypeTests/Foreign/test()"}, set()),
            ("disabled_old_registration", "AnytypeTests", selected, excluded),
            ("wrong_test_plan", "Anytype", selected, set()),
        ]
        for name, plan, enabled, disabled in registrations:
            with self.subTest(refusal=name):
                with self.assertRaises(ValueError):
                    projection.require_pending_registration(plan, enabled, disabled, fixed)


if __name__ == "__main__":
    unittest.main()
