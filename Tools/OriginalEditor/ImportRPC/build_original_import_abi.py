#!/usr/bin/env python3
"""Build the real original Import/Cancel mobile ABI from authenticated generator output.

No generation/test is replayed. The original Heart tree is reconstructed from its
recorded original afterimages and actual generated files, then original gomobile,
gobind and iosrepack emit Lib.xcframework. An isolated iOS Simulator application
compiles/links the complete original ProtobufMessages package and typed Invocation.
No account, import, editor, Host mapping or acknowledgement is executed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import stat
import sys
import time
import zipfile

sys.dont_write_bytecode = True
PACKET = "docs/pinkha/torah-integration/native-annotation-import-rpc-generation-20261123"
HELPER_SHA = "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669"
REPOSITORY = "davidpovarsky/anytype-swift"
EXPORTS = ("ServiceAnnotationSchemaRegister", "ServiceAnnotationImport", "ServiceAnnotationImportCancel")


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def row(path, name):
    size = path.stat().st_size
    content, blob = hashlib.sha256(), hashlib.sha1(b"blob " + str(size).encode() + b"\0")
    count = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            count += len(block)
            content.update(block)
            blob.update(block)
    require(count == size and path.stat().st_size == size, "Artifact changed during inventory")
    return {"path": name, "bytes": size, "sha256": content.hexdigest(),
            "git_blob": blob.hexdigest()}


def source_inventory(root, scopes):
    rows = {}
    for scope in scopes:
        directory = root / scope
        require(directory.exists() and not directory.is_symlink(), "Expected source/link scope is absent")
        paths = [directory] if directory.is_file() else list(directory.rglob("*"))
        for path in paths:
            require(not path.is_symlink(), "Unexpected source/link symlink")
            if path.is_dir():
                continue
            require(path.is_file(), "Unexpected source/link input kind")
            name = path.relative_to(root).as_posix()
            require(name not in rows, "Overlapping source/link scope")
            rows[name] = row(path, name)
    return sorted(rows.values(), key=lambda item: item["path"])


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_name(name):
    p = PurePosixPath(name)
    require(bool(name) and str(p) == name and not p.is_absolute() and ".." not in p.parts
            and "\0" not in name and "\\" not in name, "Unsafe archive path")
    return p


def probe_project(root, package):
    root.mkdir(parents=True, exist_ok=False)
    project = root / "ImportABIProbe.xcodeproj"
    (project / "xcshareddata/xcschemes").mkdir(parents=True)
    source = """import UIKit
@_spi(OriginalEditor) import ProtobufMessages

@main
final class ImportABIProbe: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        true
    }

    func originalImport(_ request: Anytype_Rpc.Annotation.Import.Request) -> OriginalAnnotationImportCall {
        ClientCommands.annotationImport(request).retainingOriginalAnnotationImportHistory()
    }

    func originalCancellation(_ request: Anytype_Rpc.Annotation.Import.Cancel.Request) -> OriginalAnnotationImportCancellationCall {
        ClientCommands.annotationImportCancel(request).retainingOriginalAnnotationImportCancellationHistory()
    }

    func originalSchema(_ request: Anytype_Rpc.Annotation.Schema.Register.Request) -> OriginalAnnotationSchemaRegistrationCall {
        ClientCommands.annotationSchemaRegister(request).retainingOriginalAnnotationSchemaHistory()
    }
}
"""
    (root / "ImportABIProbe.swift").write_text(source)
    package_path = os.path.relpath(package, root).replace("\\", "/")
    pbx = """// !$*UTF8*$!
{
 archiveVersion = 1;
 classes = {};
 objectVersion = 56;
 objects = {
  100000000000000000000001 = {isa = PBXBuildFile; fileRef = 100000000000000000000002; };
  100000000000000000000002 = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = ImportABIProbe.swift; sourceTree = "<group>"; };
  100000000000000000000003 = {isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = ImportABIProbe.app; sourceTree = BUILT_PRODUCTS_DIR; };
  100000000000000000000004 = {isa = PBXBuildFile; productRef = 100000000000000000000014; };
  100000000000000000000005 = {isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (100000000000000000000004,); runOnlyForDeploymentPostprocessing = 0; };
  100000000000000000000006 = {isa = PBXGroup; children = (100000000000000000000002,100000000000000000000007,); sourceTree = "<group>"; };
  100000000000000000000007 = {isa = PBXGroup; children = (100000000000000000000003,); name = Products; sourceTree = "<group>"; };
  100000000000000000000008 = {isa = PBXNativeTarget; buildConfigurationList = 100000000000000000000010; buildPhases = (100000000000000000000009,100000000000000000000005,); buildRules = (); dependencies = (); name = ImportABIProbe; packageProductDependencies = (100000000000000000000014,); productName = ImportABIProbe; productReference = 100000000000000000000003; productType = "com.apple.product-type.application"; };
  100000000000000000000009 = {isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = (100000000000000000000001,); runOnlyForDeploymentPostprocessing = 0; };
  10000000000000000000000A = {isa = PBXProject; attributes = {LastUpgradeCheck = 2700; }; buildConfigurationList = 10000000000000000000000F; compatibilityVersion = "Xcode 14.0"; developmentRegion = en; hasScannedForEncodings = 0; knownRegions = (en,Base,); mainGroup = 100000000000000000000006; packageReferences = (100000000000000000000013,); productRefGroup = 100000000000000000000007; projectDirPath = ""; projectRoot = ""; targets = (100000000000000000000008,); };
  10000000000000000000000B = {isa = XCBuildConfiguration; buildSettings = {CLANG_ENABLE_MODULES = YES; SWIFT_VERSION = 6.0; IPHONEOS_DEPLOYMENT_TARGET = 17.0; SDKROOT = iphonesimulator; }; name = Debug; };
  10000000000000000000000C = {isa = XCBuildConfiguration; buildSettings = {CODE_SIGNING_ALLOWED = NO; GENERATE_INFOPLIST_FILE = YES; PRODUCT_BUNDLE_IDENTIFIER = org.otzaria.ImportABIProbe; PRODUCT_NAME = "$(TARGET_NAME)"; SWIFT_VERSION = 6.0; SWIFT_STRICT_CONCURRENCY = complete; SWIFT_OPTIMIZATION_LEVEL = "-Onone"; TARGETED_DEVICE_FAMILY = "1,2"; SUPPORTED_PLATFORMS = iphonesimulator; IPHONEOS_DEPLOYMENT_TARGET = 17.0; LD_RUNPATH_SEARCH_PATHS = "$(inherited) @executable_path/Frameworks"; }; name = Debug; };
  10000000000000000000000F = {isa = XCConfigurationList; buildConfigurations = (10000000000000000000000B,); defaultConfigurationIsVisible = 0; defaultConfigurationName = Debug; };
  100000000000000000000010 = {isa = XCConfigurationList; buildConfigurations = (10000000000000000000000C,); defaultConfigurationIsVisible = 0; defaultConfigurationName = Debug; };
  100000000000000000000013 = {isa = XCLocalSwiftPackageReference; relativePath = "__PACKAGE__"; };
  100000000000000000000014 = {isa = XCSwiftPackageProductDependency; package = 100000000000000000000013; productName = ProtobufMessages; };
 };
 rootObject = 10000000000000000000000A;
}
"""
    (project / "project.pbxproj").write_text(pbx.replace("__PACKAGE__", package_path))
    (project / "xcshareddata/xcschemes/ImportABIProbe.xcscheme").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="2700" version="1.3"><BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries><BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES"><BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="100000000000000000000008" BuildableName="ImportABIProbe.app" BlueprintName="ImportABIProbe" ReferencedContainer="container:ImportABIProbe.xcodeproj"/></BuildActionEntry></BuildActionEntries></BuildAction></Scheme>
""")
    return project


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("control-root", "control-head", "pin", "pin-sha256", "heart-input", "swift-input", "work", "evidence"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--job-deadline-unix", type=int, required=True)
    args = parser.parse_args()
    control = Path(args.control_root).resolve()
    work, evidence = (control / args.work).resolve(), (control / args.evidence).resolve()
    require(work.is_relative_to(control / "build") and evidence.is_relative_to(control / "build")
            and work != evidence and not work.is_relative_to(evidence) and not evidence.is_relative_to(work),
            "Owned ABI roots escape or overlap")
    pin_path = (control / args.pin).resolve()
    require(pin_path.is_relative_to(control) and sha(pin_path) == args.pin_sha256, "Exact ABI intake pin differs")
    pin = json.loads(pin_path.read_bytes())
    require(pin["schema"] == "otzaria.original-import-rpc-abi-build-pin/2", "Final union ABI pin schema differs")
    packet = control / PACKET
    support = load(packet / "generation_support.py", "original_import_generation_support")
    manifest, _ = support.admit_packet(packet, pin["generation_manifest_sha256"])
    required_tools = {
        "build_original_import_abi.py", "abi_qualification_inputs.py", "abi_mobile_inputs.py",
        "artifact_intake.py", "qualify_original_import_rpc.py", "compiler_inputs.py",
        "repair_cancel_schema.py", "typecheck_repaired_swift.py", "union_rpc_controls.py"}
    require({Path(entry["path"]).name for entry in pin["execution_tools"]} == required_tools
            and len(pin["execution_tools"]) == len(required_tools),
            "Complete ABI execution-tool closure is required")
    for entry in pin["execution_tools"]:
        require(entry["path"] == "Tools/OriginalEditor/ImportRPC/" + Path(entry["path"]).name,
                "ABI execution-tool path differs")
        support.check_rows(control, [entry])
    qualification = load(control / "Tools/OriginalEditor/ImportRPC/abi_qualification_inputs.py", "qualified_abi_inputs")
    mobile = load(control / "Tools/OriginalEditor/ImportRPC/abi_mobile_inputs.py", "original_mobile_input_observer")
    artifact_intake = load(control / "Tools/OriginalEditor/ImportRPC/artifact_intake.py", "authenticated_artifact_intake")
    qualifier = load(control / "Tools/OriginalEditor/ImportRPC/qualify_original_import_rpc.py", "original_rpc_qualification")
    compiler = load(control / "Tools/OriginalEditor/ImportRPC/compiler_inputs.py", "original_rpc_compiler_inputs")
    schema_repair = load(control / "Tools/OriginalEditor/ImportRPC/repair_cancel_schema.py", "reviewed_original_cancel_schema")
    retained = packet / "retained-original"
    helper = support.load_module(retained / "run_native_defaults_repair.py", "original_commands", support.COMMAND_HELPER_SHA)
    original = support.load_module(retained / "generate_original_schema_rpc.py", "original_generation", support.ORIGINAL_GENERATOR_SHA)
    heart_helper = support.load_module(retained / "build_custom_heart.py", "original_heart_build", HELPER_SHA)
    git = support.git
    evidence.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update({"GOTOOLCHAIN": "local", "GOWORK": "off", "GOENV": "off", "GOFLAGS": "-mod=readonly -p=2",
                "CGO_ENABLED": "1", "GOMAXPROCS": "2"})
    commands = helper.Commands(evidence, env, args.job_deadline_unix - 180)
    result = {"schema": "otzaria.original-import-rpc-abi/2", "status": "STARTED_NOT_ACCEPTED",
              "control_head": args.control_head, "pin_sha256": args.pin_sha256,
              "final_native_rpc_union_run": pin["final_native_rpc_union"]["run_id"],
              "final_native_rpc_union_source": pin["final_native_rpc_union"]["head_sha"],
              "changed_swift_run": pin["changed_swift_qualification"]["run_id"],
              "generator_invocations": 0, "historical_tests_replayed": 0,
              "native_import_executions": 0, "host_acknowledgements": 0,
              "production_profile_activated": False, "full_editor_compiled": False}
    owned = False
    owned_cleanup_marker = None
    def stop(signum, _frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise KeyboardInterrupt("ABI workflow interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        require(0 < args.job_deadline_unix - time.time() <= 10800, "Invalid finite ABI deadline")
        require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Darwin ARM64 required")
        require(git(control, "rev-parse", "HEAD") == args.control_head
                and not git(control, "status", "--porcelain", "--untracked-files=no"), "Exact clean control head required")
        require(commands.require("go-version", ["go", "version"], control, 30).read_text().strip()
                == "go version go1.26.5 darwin/arm64", "Original Go identity differs")
        require(commands.require("xcode-version", ["xcodebuild", "-version"], control, 30).read_text().splitlines()
                == ["Xcode 27.0", "Build version 27A266a"], "Original Xcode identity differs")
        commands.require("swift-version", ["xcrun", "swiftc", "--version"], control, 30)
        work.mkdir(parents=True, exist_ok=False)
        owned = True
        owned_cleanup_marker = (json.dumps({"control_head": args.control_head, "work": str(work)}, sort_keys=True) + "\n").encode()
        (work / ".original-rpc-owned-work.json").write_bytes(owned_cleanup_marker)
        env["GOPATH"] = str(work / "go")
        env["GOMODCACHE"] = str(work / "go/pkg/mod")
        env["GOCACHE"] = str(work / "go-build")
        (work / "tmp").mkdir()
        env["TMPDIR"] = str(work / "tmp")
        proofs = qualification.qualify_inputs(control, work, evidence, pin, commands,
            support, artifact_intake, qualifier, schema_repair)
        generated_root, original_generation_root = proofs["generated_root"], proofs["original_root"]
        outputs, generation_pin = proofs["outputs"], proofs["generation_pin"]
        union_root, union_rows = proofs["union_root"], proofs["union_rows"]
        union_manifest = proofs["union_manifest"]
        result["generation_qualification"] = proofs["generation_qualification"]
        result["changed_swift_qualification"] = proofs["changed_swift_qualification"]
        result["final_native_rpc_union"] = proofs["final_native_rpc_union"]
        tools = json.loads((generated_root / "ACTUAL_REPAIR_TOOL_EXECUTABLES.json").read_bytes())["tools"]
        go_path = Path(shutil.which("go")).resolve()
        require(row(go_path, "go") == next(item for item in tools if item["path"] == "go"),
                "Actual mobile Go compiler differs from qualified original generation")
        swiftc_path = Path(commands.require("actual-abi-swiftc-path", ["xcrun", "--find", "swiftc"], control, 30).read_text().strip()).resolve()
        require(row(swiftc_path, "swiftc") == proofs["changed_swift_qualification"]["actual_compiler_context"]["compiler_driver"],
                "Actual mobile Swift compiler differs from qualified changed Swift")
        observed_tools = [{"file": str(go_path), "identity": row(go_path, "go")},
                          {"file": str(swiftc_path), "identity": row(swiftc_path, "swiftc")}]
        sdk_context = {}
        for sdk in ("iphoneos", "iphonesimulator"):
            sdk_root = commands.require("actual-" + sdk + "-sdk", ["xcrun", "--sdk", sdk, "--show-sdk-path"], control, 30).read_text().strip()
            clang = commands.require("actual-" + sdk + "-clang", ["xcrun", "--sdk", sdk, "--find", "clang"], control, 30).read_text().strip()
            version = commands.require("actual-" + sdk + "-version", ["xcrun", "--sdk", sdk, "--show-sdk-version"], control, 30).read_text().strip()
            require(Path(clang).resolve().parent == swiftc_path.parent,
                    "Mobile C/Swift compilers are not from the same selected original toolchain")
            settings = Path(sdk_root) / "SDKSettings.plist"
            sdk_context[sdk] = {"sdk_root": sdk_root, "sdk_version": version, "clang": clang,
                                "sdk_settings": row(settings, str(settings))}
            observed_tools.append({"file": str(Path(clang).resolve()),
                                   "identity": row(Path(clang).resolve(), sdk + "-clang")})
        for name in ("lipo", "nm", "otool"):
            tool = Path(commands.require("actual-" + name + "-path", ["xcrun", "--find", name], control, 30).read_text().strip()).resolve()
            observed_tools.append({"file": str(tool), "identity": row(tool, name)})
        goroot = Path(commands.require("actual-go-root", ["go", "env", "GOROOT"], control, 30).read_text().strip()).resolve()
        write(evidence / "ACTUAL_ABI_TOOLCHAIN.json", {"executables": observed_tools, "ios_sdks": sdk_context, "goroot": str(goroot)})
        inputs = {"heart": (control / args.heart_input).resolve(), "swift": (control / args.swift_input).resolve()}
        for kind, expected in (("heart", support.HEART), ("swift", support.SWIFT)):
            require(inputs[kind].is_relative_to(control / "build") and git(inputs[kind], "rev-parse", "HEAD") == expected
                    and not git(inputs[kind], "status", "--porcelain", "--untracked-files=no"), "Immutable ABI source differs")
        heart, swift = work / "heart", work / "swift"
        commands.require("clone-original-heart", ["git", "clone", "--no-hardlinks", "--no-checkout", str(inputs["heart"]), str(heart)], control, 180)
        commands.require("checkout-original-heart", ["git", "checkout", "--detach", support.HEART], heart, 120)
        require(git(heart, "rev-parse", "HEAD^{tree}") == "3d5c0ac2b15840e71693a7a94e229bb605d5f0f6",
                "Original Heart base tree differs")
        materialized = []
        for entry in union_rows:
            source = qualification.relative(union_root / "qualified-native-source", entry["path"])
            require(row(source, entry["path"]) == entry, "Final union source body differs")
            target = support.relative_path(heart, entry["path"])
            before = row(target, entry["path"]) if target.is_file() else None
            require(not target.is_symlink(), "Original native source is an unexpected symlink")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            require(row(target, entry["path"]) == entry, "Materialized union source body differs")
            materialized.append({"path": entry["path"], "original_preimage": before, "qualified_afterimage": entry})
        commands.require("seal-qualified-native-union", ["git", "add", "--", *sorted(entry["path"] for entry in union_rows)], heart, 60)
        require(git(heart, "write-tree") == pin["native_source_tree"] and not git(heart, "diff", "--name-only"),
                "Reconstructed final qualified union Git tree differs")
        for name, digest in union_manifest["original_module_hashes"].items():
            require(sha(heart / name) == digest, "Original native module/checksum bytes differ")
        write(evidence / "MATERIALIZED_UNION_SOURCE.json", {"heart_base": support.HEART,
            "canonical_native_tree": pin["native_source_tree"], "files": materialized})
        commands.require("copy-original-swift", [
            sys.executable, "-I", str(retained / "copy_materialized_checkout.py"),
            "--source", str(inputs["swift"]), "--target", str(swift), "--expected-head", support.SWIFT,
            "--receipt", str(evidence / "SWIFT_COPY.json")], control, 180)
        install_scopes = original.SWIFT_OUTPUT_SCOPES + ["Dependencies/Middleware/protobuf",
            "Dependencies/Middleware/genmodels","Dependencies/Middleware/json"]
        present_scopes = [name for name in install_scopes if (swift / name).exists()]
        source_preimages = original.checked_tree(swift,present_scopes,git,tracked=False)
        write(evidence / "SWIFT_GENERATED_PREIMAGE_INDEX.json",
            {"swift_base":support.SWIFT,"scopes":install_scopes,"files":source_preimages,
             "absent_scopes":[name for name in install_scopes if name not in present_scopes]})
        for family in ("swift", "middleware"):
            if family == "swift":
                original.remove_owned_outputs(swift, original.SWIFT_OUTPUT_SCOPES)
            for entry in outputs[family]:
                before = qualification.relative(generated_root, "generated/candidate/swift/" + entry["path"])
                require(row(before, entry["path"]) == entry, "Actual generated Swift output identity differs")
                after = support.relative_path(swift, entry["path"])
                after.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(before, after)
        invocation = json.loads((original_generation_root / "ACTUAL_GENERATOR_INPUTS.json").read_bytes())["preserved_invocation"]
        require(row(swift / invocation["path"], invocation["path"]) == invocation, "Original typed Invocation changed")
        write(evidence / "ABI_SOURCE.json", {"heart_base": support.HEART,
            "generated_native_tree": proofs["generation_qualification"]["native_generated_tree"],
            "native_source_tree": pin["native_source_tree"], "swift_base": support.SWIFT,
            "generation_qualification": proofs["generation_qualification"],
            "changed_swift_qualification": proofs["changed_swift_qualification"],
            "final_native_rpc_union": proofs["final_native_rpc_union"],
            "original_invocation": invocation, "generated_counts": {k: len(v) for k, v in outputs.items()},
            "cancel_error_schema_transform":generation_pin["schema_transform"]})
        for arch in ("darwin-arm64", "darwin-amd64", "ios-arm64", "ios-arm64-sim", "ios-amd64"):
            destination = heart / "deps/libs" / (arch + ".tar.gz")
            destination.parent.mkdir(parents=True, exist_ok=True)
            commands.require("download-tantivy-" + arch, [
                "curl", "--fail", "--location", "--silent", "--show-error", "--connect-timeout", "20", "--max-time", "180",
                "--output", str(destination), "https://github.com/anyproto/tantivy-go/releases/download/v1.0.6/" + destination.name], heart, 190)
            pin_info = heart_helper.fetch_tantivy(heart, arch)
            write(evidence / ("TANTIVY_" + arch + ".json"), pin_info)
        link_inputs = source_inventory(heart, ["deps/libs"])
        write(evidence / "ORIGINAL_NATIVE_LINK_INPUTS.json", {"files": link_inputs})
        module_output = commands.require("original-heart-module-versions", ["go", "list", "-m", "-json", "all"], heart, 1500)
        original_modules = mobile.json_objects(module_output.read_text())
        downloaded_mobile = json.loads(commands.require("download-original-gomobile-source",
            ["go", "mod", "download", "-json", "golang.org/x/mobile"], heart, 180).read_bytes())
        require(downloaded_mobile["Path"] == "golang.org/x/mobile"
                and downloaded_mobile["Version"] == mobile.MOBILE_VERSION and not downloaded_mobile.get("Error"),
                "Original gomobile source download differs")
        module = json.loads(commands.require("actual-mobile-module", ["go", "list", "-m", "-json", "golang.org/x/mobile"], heart, 60).read_bytes())
        mobile_module = mobile.admit_mobile_module(module, env["GOMODCACHE"], row)
        write(evidence / "ORIGINAL_GOMOBILE_SOURCE.json", mobile_module)
        commands.require("verify-original-modules-before-mobile", ["go", "mod", "verify"], heart, 900)
        for tool in ("gomobile", "gobind"):
            commands.require("build-original-" + tool, ["go", "build", "-o", str(heart / "deps" / tool),
                "golang.org/x/mobile/cmd/" + tool], heart, 1200)
            commands.require("buildinfo-" + tool, ["go", "version", "-m", str(heart / "deps" / tool)], heart, 30)
        env["PATH"] = str(heart / "deps") + os.pathsep + env["PATH"]
        commands.require("original-gomobile-init", [str(heart / "deps/gomobile"), "init"], heart, 1200)
        framework = heart / "dist/ios/Lib.xcframework"
        require(not framework.exists(), "Refusing stale mobile framework")
        framework.parent.mkdir(parents=True, exist_ok=True)
        marker = "otzaria-original-import-rpc-" + pin["native_source_tree"]
        ldflags = "-X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + marker + " -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + support.HEART
        commands.require("original-gomobile-bind", [str(heart / "deps/gomobile"), "bind", "-x", "-work", "-tags",
            mobile.TAGS,
            "-ldflags", ldflags, "-target=ios", "-o", str(framework),
            "github.com/anyproto/anytype-heart/clientlibrary/service", "github.com/anyproto/anytype-heart/core"], heart, 6000)
        bind_command = commands.items[-1]
        compiled_inputs = mobile.capture(commands, bind_command, heart, work, evidence, env,
            sdk_context, original_modules, goroot, ldflags, row, write)
        commands.require("verify-original-modules-after-mobile", ["go", "mod", "verify"], heart, 900)
        commands.require("original-iosrepack", ["go", "run", "cmd/iosrepack/main.go"], heart, 600)
        slices = heart_helper.verify_framework_slices(framework, marker)
        write(evidence / "ORIGINAL_MOBILE_SLICES.json", slices)
        exports = []
        for native_slice in slices:
            binary = framework / native_slice["path"]
            same_binary = [s for s in slices if s["path"] == native_slice["path"]]
            thin = binary
            if len(same_binary) > 1:
                thin = work / ("exports-" + str(len(exports) + 1))
                commands.require("thin-export-slice-" + str(len(exports) + 1), [
                    "xcrun", "lipo", str(binary), "-thin", native_slice["architecture"], "-output", str(thin)], heart, 120)
            require(sha(thin) == native_slice["sha256"], "Actual mobile export slice changed")
            output = commands.require("exports-" + str(len(exports) + 1), ["xcrun", "nm", "-gU", str(thin)], heart, 120)
            names = {line.split()[-1] for line in output.read_text(errors="replace").splitlines() if line.split()}
            require(all("_" + symbol in names for symbol in EXPORTS), "Actual mobile slice lacks defined Import/Cancel exports")
            headers = list(binary.parent.rglob("*.h"))
            combined = "\n".join(h.read_text(errors="strict") for h in headers)
            require(all(re.search(r"\b" + symbol + r"\b", combined) for symbol in EXPORTS),
                    "Actual original mobile headers lack required declarations")
            exports.append({"binary": native_slice["path"], "architecture": native_slice["architecture"],
                            "sha256": sha(thin), "required_exports": list(EXPORTS),
                            "headers": [row(p, p.relative_to(framework).as_posix()) for p in headers]})
        write(evidence / "ACTUAL_MOBILE_EXPORTS.json", exports)
        retained_framework = evidence / "products/Lib.xcframework"
        shutil.copytree(framework, retained_framework)
        shutil.copytree(framework, swift / "Dependencies/Middleware/Lib.xcframework")
        framework_rows = [row(p, p.relative_to(retained_framework).as_posix()) for p in sorted(retained_framework.rglob("*")) if p.is_file()]
        write(evidence / "LIB_XCFRAMEWORK_INDEX.json", {"files": framework_rows, "marker": marker})
        # Original 997e Package.swift directly names the Lib binary target.
        # Dependencies/Middleware has no separate original SwiftPM manifest.
        swift_compile_scopes = ["Modules/ProtobufMessages/Package.swift", "Modules/ProtobufMessages/Sources",
                                "Dependencies/Middleware/Lib.xcframework"]
        swift_compile_inputs = source_inventory(swift, swift_compile_scopes)
        write(evidence / "ORIGINAL_SWIFT_ABI_COMPILER_INPUTS.json", {"swift_base": support.SWIFT, "files": swift_compile_inputs})
        project = probe_project(work / "consumer", swift / "Modules/ProtobufMessages")
        shutil.copytree(project.parent, evidence / "consumer-source")
        common = ["xcodebuild", "-project", str(project), "-scheme", "ImportABIProbe", "-configuration", "Debug",
                  "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", str(work / "DerivedData"),
                  "-clonedSourcePackagesDirPath", str(work / "SourcePackages"), "ARCHS=arm64", "CODE_SIGNING_ALLOWED=NO"]
        commands.require("resolve-original-protobuf-package", common + ["-resolvePackageDependencies"], project.parent, 1500)
        resolved = project / "project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        resolved_data = json.loads(resolved.read_bytes())
        pins = resolved_data.get("pins", resolved_data.get("object", {}).get("pins", []))
        require(len(pins) == 1 and pins[0].get("identity") == "swift-protobuf"
                and pins[0]["state"]["revision"] == support.PLUGIN, "Actual original SwiftProtobuf resolved source differs")
        shutil.copyfile(resolved, evidence / "ACTUAL_PACKAGE_RESOLVED.json")
        protobuf_checkout = work / "SourcePackages/checkouts/swift-protobuf"
        require(git(protobuf_checkout, "rev-parse", "HEAD") == support.PLUGIN
                and not git(protobuf_checkout, "status", "--porcelain", "--untracked-files=no"),
                "Actual consumer SwiftProtobuf checkout differs")
        protobuf_scopes = ["Package.swift", "Sources"]
        protobuf_inputs = source_inventory(protobuf_checkout, protobuf_scopes)
        write(evidence / "ORIGINAL_SWIFTPROTOBUF_COMPILER_INPUTS.json", {"source": support.PLUGIN, "files": protobuf_inputs})
        commands.require("compile-link-original-invocation-abi", common + [
            "-disableAutomaticPackageResolution", "-resultBundlePath", str(evidence / "ImportABIProbe.xcresult"), "build"], project.parent, 3600)
        product = work / "DerivedData/Build/Products/Debug-iphonesimulator/ImportABIProbe.app"
        require((product / "ImportABIProbe").is_file(), "Actual linked original Invocation consumer absent")
        shutil.copytree(product, evidence / "products/ImportABIProbe.app")
        commands.require("actual-consumer-linked-libraries", ["xcrun", "otool", "-L", str(product / "ImportABIProbe")], project.parent, 60)
        require(git(heart, "write-tree") == pin["native_source_tree"] and not git(heart, "diff", "--name-only"),
                "Actual native build modified source")
        require(row(swift / invocation["path"], invocation["path"]) == invocation, "Original Invocation changed during compilation")
        support.check_rows(heart, union_rows)
        for name, digest in union_manifest["original_module_hashes"].items():
            require(sha(heart / name) == digest, "Original native module/checksum changed during ABI build")
        for family in ("swift", "middleware"):
            support.check_rows(swift, outputs[family])
        mobile_stability = mobile.recheck(compiled_inputs, row)
        require(source_inventory(heart, ["deps/libs"]) == link_inputs, "Original native link inputs changed")
        require(source_inventory(swift, swift_compile_scopes) == swift_compile_inputs,
                "Original ProtobufMessages/Invocation/Lib compiler closure changed")
        require(git(protobuf_checkout, "rev-parse", "HEAD") == support.PLUGIN
                and not git(protobuf_checkout, "status", "--porcelain", "--untracked-files=no")
                and source_inventory(protobuf_checkout, protobuf_scopes) == protobuf_inputs,
                "Actual consumer SwiftProtobuf source changed")
        require(sha(resolved) == sha(evidence / "ACTUAL_PACKAGE_RESOLVED.json"),
                "Actual consumer dependency lock changed during build")
        require(mobile.admit_mobile_module(module, env["GOMODCACHE"], row) == mobile_module,
                "Original gomobile source changed during build")
        for tool in observed_tools:
            require(row(Path(tool["file"]), tool["identity"]["path"]) == tool["identity"],
                    "Actual ABI tool executable changed")
        for sdk in sdk_context.values():
            item = sdk["sdk_settings"]
            require(row(Path(item["path"]), item["path"]) == item, "Actual iOS SDK settings changed")
        require(git(control, "rev-parse", "HEAD") == args.control_head
                and not git(control, "status", "--porcelain", "--untracked-files=no")
                and sha(pin_path) == args.pin_sha256, "ABI control source/pin changed")
        for entry in pin["execution_tools"]:
            support.check_rows(control, [entry])
        support.admit_packet(packet, pin["generation_manifest_sha256"])
        write(evidence / "POST_ABI_INPUT_STABILITY.json", {
            "status": "PASS", "control_head": args.control_head, "pin_sha256": args.pin_sha256,
            "mobile": mobile_stability, "original_native_link_files": len(link_inputs),
            "original_swift_compiler_files": len(swift_compile_inputs),
            "original_swiftprotobuf_compiler_files": len(protobuf_inputs),
            "qualified_native_afterimages": len(union_rows),
            "qualified_generated_source_files": len(outputs["swift"]) + len(outputs["middleware"]),
            "control_tools_rechecked": len(pin["execution_tools"]), "compiler_tools_rechecked": len(observed_tools),
            "original_module_and_source_tree_unchanged": True})
        for kind, expected in (("heart", support.HEART), ("swift", support.SWIFT)):
            require(git(inputs[kind], "rev-parse", "HEAD") == expected
                    and not git(inputs[kind], "status", "--porcelain", "--untracked-files=no"), "Immutable input changed")
        installation = {
            "schema":"otzaria.original-import-rpc-abi-installation/2",
            "abi_control_head":args.control_head,
            "abi_pin_sha256":args.pin_sha256,
            "generation_qualification":proofs["generation_qualification"],
            "changed_swift_qualification":proofs["changed_swift_qualification"],
            "final_native_rpc_union":proofs["final_native_rpc_union"],
            "qualification_receipts":proofs["qualification_receipts"],
            "heart_base":support.HEART,
            "generated_native_tree":proofs["generation_qualification"]["native_generated_tree"],
            "native_source_tree":pin["native_source_tree"],"original_swift_base":support.SWIFT,
            "swift_preimage_index":row(evidence / "SWIFT_GENERATED_PREIMAGE_INDEX.json",
                                      "SWIFT_GENERATED_PREIMAGE_INDEX.json"),
            "generated_output_index":row(evidence / "GENERATED_OUTPUT_INDEX.json","GENERATED_OUTPUT_INDEX.json"),
            "lib_index":row(evidence / "LIB_XCFRAMEWORK_INDEX.json","LIB_XCFRAMEWORK_INDEX.json"),
            "mobile_slices":row(evidence / "ORIGINAL_MOBILE_SLICES.json","ORIGINAL_MOBILE_SLICES.json"),
            "mobile_exports":row(evidence / "ACTUAL_MOBILE_EXPORTS.json","ACTUAL_MOBILE_EXPORTS.json"),
            "lib_destination":"Dependencies/Middleware/Lib.xcframework",
            "lib_marker":marker,"required_defined_exports":list(EXPORTS),
            "lib_file_count":len(framework_rows),
            "lib_total_bytes":sum(r["bytes"] for r in framework_rows),
            "lib_largest_member_bytes":max(r["bytes"] for r in framework_rows),
            "full_original_protobufmessages_invocation_linked":True,
            "full_sdk_owner_typechecked":False,"native_import_replayed":False,
            "installation_scope":"Only exact generated Swift/middleware scopes and authenticated original Lib product. Complete SDK owner, Host, runtime and production acceptance remain separate."}
        write(evidence / "RPC_ABI_INSTALLATION.json",installation)
        result.update(status="PASS", native_source_tree=pin["native_source_tree"], mobile_slices=len(slices),
            original_mobile_abi_built=True, original_protobufmessages_and_invocation_linked=True,
            consumer_executed=False, source_and_invocation_unchanged=True)
    except BaseException as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        result["commands"] = len(commands.items)
        result["original_mobile_binding_invocations"] = sum(
            item["label"] == "original-gomobile-bind" and isinstance(item.get("pid"), int)
            for item in commands.items)
        result["owned_command_groups_drained"] = commands.owned_groups_drained
        if commands.owned_groups_drained and owned and work.exists():
            try:
                result["cleanup"] = compiler.remove_owned_work(work, owned_cleanup_marker)
                result["owned_work_removed"] = True
            except Exception as error:
                result.update(status="FAIL", cleanup_error=str(error), owned_work_removed=False)
        elif owned and work.exists():
            result.update(status="FAIL", owned_work_removed=False)
        result["finished_unix"] = time.time()
        write(evidence / "RESULT.json", result)
        write(evidence / "EVIDENCE_INDEX.json", {"files": [
            row(path, path.relative_to(evidence).as_posix()) for path in sorted(evidence.rglob("*"))
            if path.is_file() and path.name != "EVIDENCE_INDEX.json"],
            "scope": "Actual mobile ABI and original typed Invocation compile/link only; no native import, full SDK/editor or Host ACK."})
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
