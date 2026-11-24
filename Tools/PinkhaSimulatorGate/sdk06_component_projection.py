"""Pure source/project/descriptor projection for the pending SDK06 components.

The original App and source inputs remain immutable. Generated copies blank seven
@Test attributes, add one SwiftProtobuf import, and replace two fixture convenience
constructors with the same concrete Error.init() and field assignments. Declarations,
assertion expressions, and argument values are preserved.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
import stat
from pathlib import Path
import plistlib
import re
import xml.etree.ElementTree as ET

import sdk06_compile_support as support

CONTRACT = "Tools/PinkhaSimulatorGate/sdk06-component-projection-source.json"
CONTRACT_SHA = "da40c6f62fd40f11c8cd29ff05a9c1458eda136a6d82c7ab58ea630a06cbb704"
SOURCE = "75bd6d7af18dfd511e85582ce7f994d2801b7703"
PRODUCT = "SDK06PendingTests.xctest"
SCHEME = "SDK06PendingComponents"
TARGET = "AnytypeTests"
MODE = "CURRENT_COMPONENT_TEST_BUNDLE_WITH_ORIGINAL_APP"
EDITOR = "AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift"
AUTHORITY = "AnyTypeTests/Pinkha/TorahRelatedReadAuthorityMappingTests.swift"


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def contract(control):
    raw = (Path(control) / CONTRACT).read_bytes()
    require(digest(raw) == CONTRACT_SHA, "The fixed component projection contract changed")
    value = json.loads(raw)
    require(value["source_sha"] == SOURCE and len(value["source_files"]) == 8
            and len(value["attribute_patches"]) == 7
            and len(value["selection"]["selected"]) == 23
            and len(value["selection"]["excluded"]) == 7
            and value["required_argument_cases"] == 32,
            "The finite source projection scope changed")
    return value


def projected_sources(inputs, fixed):
    require(set(inputs) == set(fixed["source_files"]), "The exact eight Swift inputs are required")
    result, observed = {}, {}
    for name, row in fixed["source_files"].items():
        raw = inputs[name]
        require(type(raw) is bytes and len(raw) == row["bytes"]
                and digest(raw) == row["sha256"], "An original Swift input changed: " + name)
        changed = bytearray(raw)
        if name == AUTHORITY:
            patch = fixed["authority_import_patch"]
            before, after = patch["before"].encode(), patch["after"].encode()
            require(patch["path"] == name and before == b"import ProtobufMessages\n"
                    and after == before + b"import SwiftProtobuf\n"
                    and raw.count(before) == 1 and b"import SwiftProtobuf" not in raw,
                    "Only the exact missing SwiftProtobuf import may be added")
            changed = bytearray(raw.replace(before, after, 1))
            require(digest(changed) == patch["projected_sha256"]
                    and bytes(changed).replace(after, before, 1) == raw,
                    "The authority import projection or complete inverse differs")
            imported = bytes(changed)
            fixture = fixed["authority_error_construction"]
            require(fixture["path"] == name and len(fixture["patches"]) == 2
                    and digest(imported) == fixture["input_sha256"],
                    "The exact two authority fixture constructions are required")
            for replacement in fixture["patches"]:
                old, new = replacement["before"].encode(), replacement["after"].encode()
                require(old != new and changed.count(old) == 1,
                        "An exact authority fixture constructor changed")
                changed = bytearray(changed.replace(old, new, 1))
            inverse = bytes(changed)
            for replacement in reversed(fixture["patches"]):
                old, new = replacement["before"].encode(), replacement["after"].encode()
                require(inverse.count(new) == 1,
                        "The authority fixture constructor inverse is ambiguous")
                inverse = inverse.replace(new, old, 1)
            require(digest(changed) == fixture["projected_sha256"] and inverse == imported,
                    "The complete authority fixture construction inverse differs")
        if name == EDITOR:
            last = 0
            for patch in fixed["attribute_patches"]:
                start = patch["offset"]
                old, new = patch["before"].encode(), patch["after"].encode()
                require(start >= last and len(old) == len(new) and raw[start:start + len(old)] == old
                        and old.startswith(b"    @Test(") and b".tags(" not in old
                        and old.count(b"@Test") == 1
                        and new == bytes(10 if c == 10 else 32 for c in old),
                        "Only the exact seven old test attributes may be blanked")
                changed[start:start + len(old)] = new
                last = start + len(old)
            require(digest(changed) == fixed["projected_editor_sha256"],
                    "The projected editor source differs")
            inverse = bytearray(changed)
            for patch in fixed["attribute_patches"]:
                start, old = patch["offset"], patch["before"].encode()
                inverse[start:start + len(old)] = old
            require(bytes(inverse) == raw, "The complete original Swift inverse differs")
        result[row["basename"]] = bytes(changed)
        observed[name] = {"original_sha256": digest(raw), "projected_sha256": digest(changed),
                          "bytes": len(raw), "projected_bytes": len(changed),
                          "function_bodies_and_arguments_unchanged": name != AUTHORITY,
                          "fixture_constructor_replacements": 2 if name == AUTHORITY else 0,
                          "declarations_assertions_and_argument_values_unchanged": True}
    require(sum(raw.count(b"@Test(") for raw in result.values()) == 23,
            "The generated sources must register exactly the pending23 tests")
    return result, observed


def require_pending_registration(test_plan, enabled, disabled, fixed):
    selected = fixed["selection"]["selected"]
    excluded = fixed["selection"]["excluded"]
    require(type(enabled) is set and type(disabled) is set
            and len(selected) == len(set(selected)) == 23
            and len(excluded) == len(set(excluded)) == 7
            and not set(selected).intersection(excluded)
            and test_plan == "AnytypeTests"
            and enabled == set(selected) and not disabled
            and not enabled.intersection(excluded),
            "The current bundle does not expose exactly23 pending registrations and zero others")


def object_id(value):
    return hashlib.sha256(value.encode()).hexdigest()[:24].upper()


RETAINED_FRAMEWORK_PRODUCTS = (
    "ProtobufMessages", "Services", "AnytypeCore",
    "SwiftProtobuf_7CEE9AB92C12BC6B_PackageProduct",
)


def retained_framework_rows(fixed):
    binding = fixed["retained_framework_links"]
    require(type(binding) is dict and set(binding) == {"protocol", "source_sha", "native_archive_sha256",
                            "original_test_link_command_sha256", "frameworks"}
            and binding["protocol"] == "sdk06-retained-framework-links-v1"
            and binding["source_sha"] == SOURCE
            and binding["native_archive_sha256"] ==
                "478d17c0517a983830410d80b1f9630e42fb09e2293a2360d91ebf887a7ed18a"
            and binding["original_test_link_command_sha256"] ==
                "2ed656a9e9ef04b24570724066927c6a509a8896c4ffc011d5d2c1512d495830",
            "The exact original framework-link lineage is required")
    rows = binding["frameworks"]
    require(type(rows) is list and len(rows) == 4 and all(type(row) is dict for row in rows)
            and tuple(row.get("product") for row in rows) == RETAINED_FRAMEWORK_PRODUCTS,
            "Only the four original package framework inputs are admitted")
    for row in rows:
        name = row["product"]
        suffix = name + ".framework/" + name
        require(set(row) == {"product", "link_relative", "runtime_relative", "install_name",
                             "link_identity", "runtime_identity"}
                and row["link_relative"] == "PackageFrameworks/" + suffix
                and row["runtime_relative"] == "Frameworks/" + suffix
                and row["install_name"] == "@rpath/" + suffix,
                "An original framework path or install name changed")
        for role in ("link_identity", "runtime_identity"):
            value = row[role]
            require(type(value) is dict and set(value) == {"bytes", "mode", "sha256"}
                    and type(value["bytes"]) is int and 0 < value["bytes"] <= 256 * 1024 * 1024
                    and type(value["mode"]) is int and value["mode"] == 0o755
                    and type(value["sha256"]) is str
                    and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]),
                    "A fixed original framework identity is malformed")
    return rows


def verify_retained_framework_links(original_products, staged_app, fixed):
    roots = {"link": Path(original_products), "runtime": Path(staged_app)}
    require(all(root.is_absolute() and root.resolve(strict=True) == root
                and root.is_dir() and not root.is_symlink()
                for root in roots.values())
            and roots["runtime"].name == "Anytype.app"
            and not roots["runtime"].is_relative_to(roots["link"]),
            "Disjoint regular original-link and staged-runtime roots are required")
    observed = []
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)
    for row in retained_framework_rows(fixed):
        result = {"product": row["product"], "install_name": row["install_name"]}
        for role, root in roots.items():
            relative = Path(row[role + "_relative"])
            path = root / relative
            parent = root
            for part in relative.parts[:-1]:
                parent = parent / part
                require(stat.S_ISDIR(parent.lstat().st_mode),
                        "A retained framework parent is not a regular directory")
            before = path.lstat()
            expected = row[role + "_identity"]
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                    and before.st_size == expected["bytes"]
                    and stat.S_IMODE(before.st_mode) == expected["mode"],
                    "An original framework file type, mode or length changed")
            handle = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(handle, "rb") as source:
                require(identity(os.fstat(source.fileno())) == identity(before),
                        "An original framework changed while opening")
                remaining, hashed = expected["bytes"], hashlib.sha256()
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    require(bool(chunk), "An original framework ended early")
                    hashed.update(chunk)
                    remaining -= len(chunk)
                require(source.read(1) == b"" and hashed.hexdigest() == expected["sha256"],
                        "An original framework byte hash changed")
                require(identity(os.fstat(source.fileno())) == identity(before)
                        and identity(path.lstat()) == identity(before),
                        "An original framework changed during verification")
            result[role] = {"relative": relative.as_posix(), **expected,
                            "device": str(before.st_dev), "inode": str(before.st_ino),
                            "mtime_ns": str(before.st_mtime_ns), "ctime_ns": str(before.st_ctime_ns)}
        result["link_runtime_byte_equal"] = result["link"]["sha256"] == result["runtime"]["sha256"]
        observed.append(result)
    return {"protocol": "sdk06-retained-framework-byte-bindings-v1", "source_sha": SOURCE,
            "frameworks": observed, "symbol_exports_inspected": False,
            "runtime_load_succeeded": False, "app_native_or_package_builds": 0}


def project_value(source_names, staged_app, original_products, fixed, *, compile_support=None,
                  with_retained_frameworks=False):
    require(sorted(source_names) == sorted(row["basename"] for row in fixed["source_files"].values()),
            "An unreviewed source entered the isolated target")
    require(all(re.fullmatch(r"[A-Za-z0-9_]+\.swift", name) for name in source_names),
            "Unsafe generated source name")
    staged_app, original_products = Path(staged_app), Path(original_products)
    require(staged_app.is_absolute() and original_products.is_absolute()
            and staged_app.name == "Anytype.app"
            and not staged_app.is_relative_to(original_products),
            "A disjoint staged original App and absolute module directory are required")
    ids = {key: object_id("sdk06-pending-" + key) for key in
           ("project", "target", "group", "products", "product", "sources", "frameworks",
            "resources", "project-config", "target-config", "project-config-list", "target-config-list")}
    objects = {}
    source_refs, build_refs = [], []
    for name in sorted(source_names):
        ref, build = object_id("source-" + name), object_id("build-" + name)
        source_refs.append(ref)
        build_refs.append(build)
        objects[ref] = {"isa": "PBXFileReference", "lastKnownFileType": "sourcecode.swift",
                        "path": "Sources/" + name, "sourceTree": "<group>"}
        objects[build] = {"isa": "PBXBuildFile", "fileRef": ref}
    objects[ids["product"]] = {"isa": "PBXFileReference", "explicitFileType": "wrapper.cfbundle",
                              "includeInIndex": 0, "path": PRODUCT, "sourceTree": "BUILT_PRODUCTS_DIR"}
    objects[ids["group"]] = {"isa": "PBXGroup", "children": source_refs + [ids["products"]],
                            "sourceTree": "<group>"}
    objects[ids["products"]] = {"isa": "PBXGroup", "children": [ids["product"]],
                               "name": "Products", "sourceTree": "<group>"}
    for name, kind, files in (("sources", "PBXSourcesBuildPhase", build_refs),
                               ("frameworks", "PBXFrameworksBuildPhase", []),
                               ("resources", "PBXResourcesBuildPhase", [])):
        objects[ids[name]] = {"isa": kind, "buildActionMask": 2147483647,
                              "files": files, "runOnlyForDeploymentPostprocessing": 0}
    settings = {
        "SDKROOT": "iphonesimulator", "SUPPORTED_PLATFORMS": "iphonesimulator",
        "IPHONEOS_DEPLOYMENT_TARGET": "27.0", "ARCHS": "arm64", "ONLY_ACTIVE_ARCH": "YES",
        "SWIFT_VERSION": "5.0", "SWIFT_STRICT_CONCURRENCY": "complete",
        "SWIFT_OPTIMIZATION_LEVEL": "-Onone", "ENABLE_TESTABILITY": "YES",
        "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "DEBUG PINKHA_NATIVE_DERIVED",
        "ENABLE_TESTING_SEARCH_PATHS": "YES", "GENERATE_INFOPLIST_FILE": "YES",
        "CODE_SIGN_STYLE": "Manual", "DEVELOPMENT_TEAM": "", "CODE_SIGN_IDENTITY": "-",
        "CODE_SIGNING_ALLOWED": "YES", "CODE_SIGNING_REQUIRED": "YES",
        "PROVISIONING_PROFILE_SPECIFIER": "", "PRODUCT_BUNDLE_IDENTIFIER": "com.AnytypeTests",
        "PRODUCT_NAME": "SDK06PendingTests", "PRODUCT_MODULE_NAME": TARGET,
        # This graph only builds the bundle; its separately preserved runtime
        # descriptor still injects it into the original staged App.
        "TEST_HOST": "", "BUNDLE_LOADER": str(staged_app / "Anytype"),
        "OTHER_LDFLAGS": [str(staged_app / "Anytype.debug.dylib")],
        "TEST_TARGET_NAME": "", "TARGETED_DEVICE_FAMILY": "1,2",
        "SUPPORTS_MACCATALYST": "NO", "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD": "NO",
        "SWIFT_INCLUDE_PATHS": [str(original_products)],
        "LIBRARY_SEARCH_PATHS": [str(original_products)],
        "FRAMEWORK_SEARCH_PATHS": [str(original_products), str(original_products / "PackageFrameworks"),
                                   str(staged_app / "Frameworks")],
        "LD_RUNPATH_SEARCH_PATHS": ["@executable_path/Frameworks", "@loader_path/Frameworks"],
        **fixed["original_swift_features"],
    }
    require(type(with_retained_frameworks) is bool, "The retained-framework opt-in must be boolean")
    if with_retained_frameworks:
        settings["OTHER_LDFLAGS"] += [str(original_products / row["link_relative"])
                                    for row in retained_framework_rows(fixed)]
    if compile_support is not None:
        require(type(compile_support) is support.FixedCompileSupport,
                "Only the concrete fixed compile-support packet is admitted")
        settings.update(compile_support.settings())
    for prefix, values in (("project", {}), ("target", settings)):
        objects[ids[prefix + "-config"]] = {"isa": "XCBuildConfiguration",
                                            "buildSettings": values, "name": "Debug-Anytype"}
        objects[ids[prefix + "-config-list"]] = {
            "isa": "XCConfigurationList", "buildConfigurations": [ids[prefix + "-config"]],
            "defaultConfigurationIsVisible": 0, "defaultConfigurationName": "Debug-Anytype"}
    objects[ids["target"]] = {
        "isa": "PBXNativeTarget", "name": TARGET, "productName": "SDK06PendingTests",
        "productType": "com.apple.product-type.bundle.unit-test", "productReference": ids["product"],
        "buildConfigurationList": ids["target-config-list"],
        "buildPhases": [ids["sources"], ids["frameworks"], ids["resources"]],
        "buildRules": [], "dependencies": [], "packageProductDependencies": [],
    }
    objects[ids["project"]] = {
        "isa": "PBXProject", "attributes": {"LastUpgradeCheck": "2700"},
        "buildConfigurationList": ids["project-config-list"], "compatibilityVersion": "Xcode 14.0",
        "developmentRegion": "en", "hasScannedForEncodings": 0, "knownRegions": ["en", "Base"],
        "mainGroup": ids["group"], "productRefGroup": ids["products"], "projectDirPath": "",
        "projectRoot": "", "targets": [ids["target"]], "packageReferences": [],
    }
    return {"archiveVersion": 1, "classes": {}, "objectVersion": 56,
            "objects": objects, "rootObject": ids["project"]}, ids


def openstep(value, depth=0):
    indent = "\t" * depth
    if isinstance(value, dict):
        return "{\n" + "".join(indent + "\t" + json.dumps(key) + " = " +
                openstep(child, depth + 1) + ";\n" for key, child in value.items()) + indent + "}"
    if isinstance(value, list):
        return "(\n" + "".join(indent + "\t" + openstep(child, depth + 1) + ",\n"
                               for child in value) + indent + ")"
    require(type(value) in (str, int), "Unsupported generated PBX value")
    return json.dumps(value, ensure_ascii=True)


def scheme_bytes(target_id):
    root = ET.Element("Scheme", {"LastUpgradeVersion": "2700", "version": "1.7"})
    build = ET.SubElement(root, "BuildAction", {"parallelizeBuildables": "NO",
                                               "buildImplicitDependencies": "NO"})
    entry = ET.SubElement(ET.SubElement(build, "BuildActionEntries"), "BuildActionEntry",
                          {"buildForTesting": "YES", "buildForRunning": "NO",
                           "buildForProfiling": "NO", "buildForArchiving": "NO", "buildForAnalyzing": "NO"})
    ref = {"BuildableIdentifier": "primary", "BlueprintIdentifier": target_id,
           "BuildableName": PRODUCT, "BlueprintName": TARGET,
           "ReferencedContainer": "container:SDK06PendingComponents.xcodeproj"}
    ET.SubElement(entry, "BuildableReference", ref)
    action = ET.SubElement(root, "TestAction", {"buildConfiguration": "Debug-Anytype",
                                               "shouldUseLaunchSchemeArgsEnv": "NO"})
    test = ET.SubElement(ET.SubElement(action, "Testables"), "TestableReference", {"skipped": "NO"})
    ET.SubElement(test, "BuildableReference", ref)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def descriptor_value(original, original_products_root, staged_app, test_bundle):
    """Keep actual original runtime settings, relocating only explicit products."""
    value = copy.deepcopy(original)
    require(value.get("__xctestrun_metadata__", {}).get("FormatVersion") == 2
            and len(value.get("TestConfigurations", [])) == 1,
            "The original native v2 descriptor is required")
    configuration = value["TestConfigurations"][0]
    require(configuration.get("IsEnabled", True) is True, "Disabled original configuration")
    targets = configuration["TestTargets"]
    selected = [target for target in targets if target.get("BlueprintName") == TARGET]
    require(len(selected) == 1 and selected[0].get("IsAppHostedTestBundle") is True
            and selected[0].get("ProductModuleName") == TARGET
            and selected[0].get("TestHostBundleIdentifier") == "io.anytype.app",
            "The actual original Anytype hosted test target is required")
    target = selected[0]
    forbidden = {"OnlyTestIdentifiers", "SkipTestIdentifiers", "OnlyTestTags", "SkipTestTags",
                 "OnlyTestingTags", "SkipTestingTags", "TagsToRun", "TagsToSkip"}
    require(not forbidden.intersection(target), "Unexpected original selection metadata")
    old_host = "__TESTROOT__/Debug-Anytype-iphonesimulator/Anytype.app"
    old_bundle = old_host + "/PlugIns/AnytypeTests.xctest"
    require(target["TestHostPath"] == old_host
            and target["TestBundlePath"] == "__TESTHOST__/PlugIns/AnytypeTests.xctest"
            and target["DependentProductPaths"].count(old_host) == 1
            and target["DependentProductPaths"].count(old_bundle) == 1,
            "The finite original host/bundle paths changed")
    original_products_root, staged_app, test_bundle = map(Path,
        (original_products_root, staged_app, test_bundle))
    require(all(path.is_absolute() for path in (original_products_root, staged_app, test_bundle))
            and not staged_app.is_relative_to(original_products_root)
            and not test_bundle.is_relative_to(original_products_root)
            and staged_app.name == "Anytype.app" and test_bundle.name == PRODUCT,
            "Projection output paths must be disjoint from original Products")
    configuration["TestTargets"] = selected

    def relocate(node):
        if isinstance(node, dict):
            return {key: relocate(child) for key, child in node.items()}
        if isinstance(node, list):
            return [relocate(child) for child in node]
        if isinstance(node, str):
            return node.replace("__TESTROOT__", str(original_products_root))
        return node
    value = relocate(value)
    target = value["TestConfigurations"][0]["TestTargets"][0]
    host_abs = old_host.replace("__TESTROOT__", str(original_products_root))
    bundle_abs = old_bundle.replace("__TESTROOT__", str(original_products_root))
    target["DependentProductPaths"] = [
        str(staged_app) if name == host_abs else str(test_bundle) if name == bundle_abs else name
        for name in target["DependentProductPaths"]]
    target["TestHostPath"], target["TestBundlePath"] = str(staged_app), str(test_bundle)
    # Other original test bundles are dependency inventory only; they are never
    # enabled targets. Current compiled enumeration must independently be23/0.
    require(len(value["TestConfigurations"][0]["TestTargets"]) == 1,
            "Unexpected enabled native target")
    return value


def write_project(control, app, destination, staged_app, original_products, *, with_compile_support=False,
                  with_retained_frameworks=False):
    require(type(with_compile_support) is bool, "The fixed compile-support opt-in must be boolean")
    fixed = contract(control)
    require(not destination.exists() and not destination.is_symlink(),
            "The component source/project root must be fresh")
    inputs = {}
    for name in fixed["source_files"]:
        path = Path(app) / name
        require(path.is_file() and not path.is_symlink(), "Original Swift source is absent")
        inputs[name] = path.read_bytes()
    sources, receipt = projected_sources(inputs, fixed)
    require(type(with_retained_frameworks) is bool, "The retained-framework opt-in must be boolean")
    framework_binding = verify_retained_framework_links(original_products, staged_app, fixed) \
        if with_retained_frameworks else None
    compile_support = support.materialize(control, destination) if with_compile_support else None
    value, ids = project_value(list(sources), staged_app, original_products, fixed,
                              compile_support=compile_support,
                              with_retained_frameworks=with_retained_frameworks)
    project = destination / "SDK06PendingComponents.xcodeproj"
    (destination / "Sources").mkdir(parents=True)
    (project / "xcshareddata/xcschemes").mkdir(parents=True)
    for name, raw in sources.items():
        (destination / "Sources" / name).write_bytes(raw)
    (project / "project.pbxproj").write_text("// !$*UTF8*$!\n" + openstep(value) + "\n")
    (project / "xcshareddata/xcschemes" / (SCHEME + ".xcscheme")).write_bytes(scheme_bytes(ids["target"]))
    # Freeze the ordinary self workspace before xcodebuild can materialize it.
    workspace = project / "project.xcworkspace"
    workspace.mkdir()
    (workspace / "contents.xcworkspacedata").write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<Workspace version="1.0"><FileRef location="self:"></FileRef></Workspace>\n')
    # Xcode materialized precisely these three empty directories in the failed
    # original build. Freeze them before the unchanged whole-tree admission.
    for relative in ("xcshareddata", "xcshareddata/swiftpm",
                     "xcshareddata/swiftpm/configuration"):
        directory = workspace / relative
        directory.mkdir(mode=0o777)
        directory.chmod(0o777)
    files = {path.relative_to(destination).as_posix(): digest(path.read_bytes())
             for path in sorted(destination.rglob("*")) if path.is_file()}
    return project, {"protocol": "sdk06-component-source-projection-v1", "source_sha": SOURCE,
                     "contract_sha256": CONTRACT_SHA, "inputs": receipt, "generated_files": files,
                     "removed_test_registrations": fixed["selection"]["excluded"],
                     "required_compiled_registrations": fixed["selection"]["selected"],
                     "function_bodies_and_arguments_unchanged": False,
                     "fixture_constructor_replacements": 2,
                     "declarations_assertions_and_argument_values_unchanged": True,
                     "original_source_modified": False, "app_build_targets": 0,
                     "native_library_build_targets": 0, "component_test_bundle_targets": 1,
                     "package_build_targets": 0, "implicit_dependencies": False,
                     **({"compile_support": compile_support.receipt()} if compile_support is not None else {}),
                     **({"retained_framework_links": framework_binding} if framework_binding is not None else {})}
