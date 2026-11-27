"""Admit original hosted products at their live producer paths, in the same job."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

from originals import require

REPOSITORY = "davidpovarsky/anytype-swift"
CONTROL_PREFIX = "Tools/PinkhaDualEngineRuntime/hosted_hanlin_uikit23/"
HOSTED_OWNER = "Tools/PinkhaDualEngineRuntime/hosted_shared_build/run.py"
HOSTED_OWNER_SHA256 = "34d9b19f4d34f8f441fc13a79bb615deb7676413cb33862d00629ed2f64871b0"
NATIVE_INPUTS = "Tools/PinkhaDualEngineRuntime/hosted_shared_build/native_inputs.py"
NATIVE_INPUTS_SHA256 = "e8aaf254140c06410813d5ab6f3b9168b71c1722dfe2ecdac8155a1bdc9d4d3c"
LOCK = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
SDK_MARKER = "Dependencies/Hanlin/.pinkha-source.json"
NATIVE_MANIFEST = "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json"
NATIVE_BINARY = "Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib"
ORIGINAL_PRODUCER = "Tools/PinkhaDualEngineRuntime/build_wave2_app16_compiler_qualified.py"
ORIGINAL_PRODUCER_SHA256 = "9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c"
UI_GENERATOR = "Tools/PinkhaNativeDerived/rerun_original_ui.py"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(path, *, directory=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
            "Original physical same-job path required: " + str(path))
    require(path.is_dir() if directory else path.is_file(), "Wrong original input kind")
    return path


def ref(path):
    path = canonical(path)
    return {"path": str(path), "sha256": sha(path)}


def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "--no-replace-objects",
                                    "-C", str(root), *args], timeout=60).decode()


def identity(root, commit, tree=None):
    root = canonical(root, directory=True)
    value = {"root": git(root, "rev-parse", "--show-toplevel").strip(),
             "commit": git(root, "rev-parse", "HEAD").strip(),
             "tree": git(root, "rev-parse", "HEAD^{tree}").strip(),
             "status": git(root, "status", "--porcelain", "--untracked-files=all")}
    require(value["root"] == str(root) and value["commit"] == commit and value["status"] == ""
            and (tree is None or value["tree"] == tree), "Immutable clean original checkout differs")
    return value


def bind_job(args, plan):
    env = os.environ
    require(env.get("GITHUB_REPOSITORY") == REPOSITORY and env.get("GITHUB_ACTIONS") == "true"
            and env.get("RUNNER_ENVIRONMENT") == "github-hosted" and env.get("RUNNER_ARCH") == "ARM64",
            "The original GitHub-hosted ARM64 job is required")
    run, attempt = env.get("GITHUB_RUN_ID", ""), env.get("GITHUB_RUN_ATTEMPT", "")
    require(re.fullmatch(r"[1-9][0-9]*", run) and re.fullmatch(r"[1-9][0-9]*", attempt)
            and env.get("GITHUB_JOB"), "Actual original run/attempt/job identity is required")
    workspace = canonical(env["GITHUB_WORKSPACE"], directory=True)
    temporary = canonical(env["RUNNER_TEMP"], directory=True)
    require(Path(args.control) == workspace / "control" and Path(args.source) == workspace / "app/source"
            and Path(args.build_root) == temporary / ("pinkha-hosted-shared-" + run + "-" + attempt)
            and Path(args.plan) == temporary / "pinkha-root-plan.json"
            and Path(args.output) == temporary / ("pinkha-hosted-hanlin-uikit23-" + run + "-" + attempt),
            "Different-job, relocated or invented producer paths are not supported")
    require(plan["controlCommit"] == env.get("GITHUB_SHA") and plan["repository"] == REPOSITORY
            and plan["readyForBuild"] is True and plan["schema"] == "pinkha-hosted-original-shared-build-plan-v1",
            "Exact root-reviewed executed hosted plan required")
    require(env.get("DEVELOPER_DIR") == plan["toolchain"]["developerDir"],
            "Runtime must use the producer's exact selected Xcode")
    return {"repository": REPOSITORY, "runID": run, "runAttempt": attempt,
            "job": env["GITHUB_JOB"], "controlCommit": env["GITHUB_SHA"],
            "workspace": str(workspace), "temporary": str(temporary),
            "developerDir": env["DEVELOPER_DIR"]}


def control_identity(control, commit):
    result = identity(control, commit)
    paths = [path for path in git(control, "ls-files", "-z", CONTROL_PREFIX).split("\0") if path]
    required = {CONTROL_PREFIX + name for name in ("run.py", "admission.py", "originals.py", "original_sources.json",
                    "profile_binding.py", "profile-dependency.json", "activation.json", "native23_receipts.py",
                    "profile.py", "profile.json", "source-inverse.json")}
    require(required.issubset(paths) and all(path.startswith(CONTROL_PREFIX) for path in paths),
            "Complete reviewed runtime controller closure required")
    result["files"] = {}
    for path in paths:
        original = subprocess.check_output(["git", "--no-replace-objects", "-C", str(control),
                                            "show", commit + ":" + path], timeout=60)
        file = canonical(Path(control) / path)
        require(file.read_bytes() == original, "Executed runtime control differs from its immutable Git blob")
        result["files"][path] = {"bytes": len(original), "sha256": hashlib.sha256(original).hexdigest()}
    require(Path(__file__).resolve() == Path(control) / CONTROL_PREFIX / "admission.py",
            "The actual runtime adapter is not in the admitted control checkout")
    return result


def load_hosted_owner(control):
    modules = []
    for name, relative, expected in (
        ("native_inputs", NATIVE_INPUTS, NATIVE_INPUTS_SHA256),
        ("core13_original_hosted_producer", HOSTED_OWNER, HOSTED_OWNER_SHA256),
    ):
        path = canonical(Path(control) / relative)
        require(sha(path) == expected and name not in sys.modules,
                "Reviewed hosted producer source changed or its module name is occupied")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    return modules[-1]


def producer_context(args, plan, originals, owner):
    gate, shared = originals.gate, originals.shared
    root, source = canonical(args.build_root, directory=True), canonical(args.source, directory=True)
    control = canonical(args.control, directory=True)
    owner.validate_plan(plan, os.environ["GITHUB_SHA"])
    source_identity = identity(source, plan["appSourceSHA"], plan["appSourceTree"])
    sdk_pin = gate.json_ref(ref(source / "Tools/Hanlin/source.json"))
    require(sha(source / "Tools/Hanlin/source.json") == plan["pins"]["sdkSourcePinSHA256"]
            and sdk_pin["revision"] == plan["hanlinRevision"]
            and sdk_pin["repository"] == "https://github.com/davidpovarsky/hanlin-ai.git"
            and sha(source / "Tools/Hanlin/prepare_sdk.py") == plan["pins"]["sdkMaterializerSHA256"]
            and sha(source / SDK_MARKER) == plan["pins"]["sdkMaterializationReceiptSHA256"]
            and sha(source / LOCK) == plan["pins"]["packageResolvedSHA256"],
            "Original canonical SDK, materializer, installed receipt or App lock differs")
    owner_proof = owner.control_identity(control, plan["controlCommit"])
    selected = owner.selected_sources(source)
    require(selected == plan["compilerInputs"]
            and owner.validate_compiler_inputs(selected) == {"native": 61, "stage1UI": 10, "native23UI": 2},
            "The exact reviewed61-native/10-Stage1 source membership, bytes and import projection differ")
    expected_plan = ref(args.plan)
    require(expected_plan["sha256"] == args.plan_sha256, "Root plan changed after admission")
    hosted = gate.json_ref(ref(root / "hosted-receipt.json"))
    build_ref = ref(root / "build16/receipt.json")
    build = gate.json_ref(build_ref)
    root_ref = ref(root / "root-derived-build-admission.json")
    root_admission = gate.json_ref(root_ref)
    require(hosted["status"] == "PASS_HOSTED_ORIGINAL_APP_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and hosted["testsExecuted"] == 0 and hosted["originalBuildReceipt"] == build_ref
            and hosted["rootPlan"] == expected_plan and hosted["controlCommit"] == plan["controlCommit"]
            and hosted["appSourceSHA"] == plan["appSourceSHA"]
            and build["status"] == gate.BUILD_STATUS and build["testsExecuted"] == 0
            and build["sourceCommit"] == plan["appSourceSHA"] and build["sourceUnchanged"] is True,
            "No original successful same-job App and complete UI producer exists")
    require(build["controlAdmission"]["admission"] == root_ref
            and root_admission["rootPlan"] == expected_plan and root_admission["readyForBuild"] is True
            and root_admission["hostedColdBuild"] is True and root_admission["appSourceSHA"] == plan["appSourceSHA"]
            and root_admission["sourceRoot"] == str(source) and root_admission["buildRoot"] == str(root)
            and root_admission["appDerived"] == str(root / "app-derived")
            and root_admission["pins"] == plan["pins"], "Original hosted source/producer admission differs")
    staging_ref, cache_ref = ref(root / "source-staging.json"), ref(root / "cold-cache-qualification.json")
    require(root_admission["sourceStaging"] == staging_ref and root_admission["cacheQualification"] == cache_ref,
            "The original hosted source/cache observations are not local to this job")
    stage, cache = gate.json_ref(staging_ref), gate.json_ref(cache_ref)
    transport_ref = ref(root / "native-transport-receipt.json")
    require(stage["status"] == "PASS_FRESH_HOSTED_SOURCE_NATIVE_AND_SDK_NOT_BUILT"
            and stage["sourceCommit"] == plan["appSourceSHA"] and stage["sourceTree"] == plan["appSourceTree"]
            and stage["sourceRoot"] == str(source) and stage["appDerived"] == str(root / "app-derived")
            and stage["compilerInputs"] == plan["compilerInputs"] and stage["rootPlan"] == expected_plan
            and stage["nativeArtifactTransport"] == transport_ref
            and root_admission["originalRetention"] == transport_ref
            and cache["status"] == "PASS_EMPTY_HOSTED_COMPILER_PATHS_NOT_BUILT"
            and cache["sourceCommit"] == plan["appSourceSHA"] and cache["stageReceiptSHA256"] == staging_ref["sha256"],
            "Original cold source/native transport/cache custody differs")
    transport = gate.json_ref(transport_ref)
    require(transport["status"] == "PASS_EXACT_ORIGINAL_NATIVE8AC_ARTIFACT_TRANSPORT_NOT_APP_ACCEPTANCE"
            and transport["artifact"] == plan["nativeArtifact"], "Original native artifact transport differs")
    native_root = canonical(root_admission["nativeMaterializationRoot"], directory=True)
    require(native_root.is_relative_to(root), "Imported native witness root escaped the original hosted build")
    producer = canonical(root / "hosted-original-producer.py")
    original = canonical(control / ORIGINAL_PRODUCER)
    require(sha(original) == ORIGINAL_PRODUCER_SHA256, "Original unexpanded producer changed")
    adapter = owner.load_adapter(control)
    expanded, inverse = owner.expand(original.read_text(), adapter, root_admission, Path(root_ref["path"]), HOSTED_OWNER_SHA256)
    require(producer.read_text() == expanded and sha(producer) == build["controllerSHA256"]
            and gate.json_ref(ref(root / "producer-full-byte-inverse.json")) == inverse,
            "Actual executed producer is not the exact reviewed original expansion")
    exit_record = gate.json_ref(ref(root / "producer-exit.json"))
    require(exit_record["exitCode"] == 0 and exit_record["producer"] == ref(producer)
            and exit_record["sourceCommit"] == plan["appSourceSHA"] and exit_record["testsExecuted"] == 0,
            "Original producer exit is missing or incomplete")
    for label in ("app", "ui"):
        step = build[label]
        require(step["exitCode"] == 0 and step["status"] == "PASS_BUILD_EXIT_0"
                and step["ownedProcessGroup"] == "ABSENT_ESRCH" and not step["cleanupErrors"]
                and step["sourceCommit"] == plan["appSourceSHA"], "A compiler phase lacks terminal owned cleanup")
        require(sha(root / "build16" / label / "process-exit.json") == step["processExitReceiptSHA256"],
                "Original compiler process-exit evidence changed")
    require(gate.json_ref(ref(root / "controls-before.json")) == owner_proof
            and gate.json_ref(ref(root / "controls-after.json")) == owner_proof,
            "Original executed build controller checkout changed")
    toolchain_ref = ref(root / "toolchain/receipt.json")
    toolchain = gate.json_ref(toolchain_ref)
    require(hosted["toolchain"] == root_admission["toolchainIntake"] == stage["toolchain"] == toolchain_ref
            and toolchain["status"] == "PASS_EXACT_ORIGINAL_TOOLCHAIN_NOT_BUILD_ACCEPTANCE"
            and toolchain["developerDir"] == plan["toolchain"]["developerDir"]
            and toolchain["machine"] == "arm64", "Original toolchain custody differs")
    return {"root": root, "source": source, "sourceIdentity": source_identity, "build": build,
            "buildRef": build_ref, "rootAdmission": root_admission, "producer": producer,
            "nativeRoot": native_root, "toolchain": toolchain, "toolchainRef": toolchain_ref,
            "planRef": expected_plan, "ownerControlProof": owner_proof}


def receipt_contract(context, output, originals, runtime, device_type):
    gate = originals.gate
    root, source, build = context["root"], context["source"], context["build"]
    base = root / "build16"
    manifest = output / "evidence/original-tools-source-manifest.json"
    originals.preparation.control_manifest(SimpleNamespace(repository=source,
        commit=context["sourceIdentity"]["commit"], output=manifest))
    product_ref = ref(base / "products-all.json")
    products = gate.json_ref(product_ref)
    descriptors = {}
    for label, target in (("app", "AnytypeTests"), ("ui", "PinkhaStage1AcceptanceUITests")):
        slot = label + "-derived"
        expected_root = root / slot / "Build/Products"
        require(products[slot]["base"] == str(expected_root), "Actual Products do not belong to this hosted producer")
        candidates = []
        for row in products[slot]["entries"]:
            if row["kind"] != "file" or not row["path"].endswith(".xctestrun"):
                continue
            try:
                originals.products.entries(expected_root / row["path"], target)
                candidates.append(row["path"])
            except (ValueError, KeyError, TypeError):
                continue
        require(len(candidates) == 1, "One actual original compiled descriptor required for " + target)
        descriptors[label] = {"slot": slot, "path": candidates[0]}
    input_paths = {
        "nativeSourceManifestSHA256": source / NATIVE_MANIFEST,
        "nativeSHA256": source / NATIVE_BINARY,
        "lockSHA256": source / LOCK,
        "sdkReceiptSHA256": source / SDK_MARKER,
        "stagingReceiptSHA256": root / "source-staging.json",
        "cacheRequalificationReceiptSHA256": root / "cold-cache-qualification.json",
    }
    require({key for key in build["inputs"] if key.endswith("SHA256")} == set(input_paths),
            "Every original input digest must have its exact live file; unknown input needs review")
    before = gate.json_ref(ref(base / "source-before.json"))
    assembly = ref(context["nativeRoot"] / "receipt.json")
    manifest_ref, lock_ref = ref(source / NATIVE_MANIFEST), ref(source / LOCK)
    contract = {
        "schema": gate.SCHEMA,
        "source": {"root": str(source), "commit": before["commit"], "tree": before["tree"],
                   "before": ref(base / "source-before.json"), "after": ref(base / "source-after.json")},
        "controls": {"root": str(source), "commit": before["commit"], "manifest": ref(manifest)},
        "build": {"receipt": context["buildRef"], "producer": ref(context["producer"]),
                  "assembly": assembly, "uiGenerator": ref(source / UI_GENERATOR),
                  "originalUICopy": ref(base / "original-ui-copy.json"),
                  "uiCompilationProof": build["uiCompilationProof"],
                  "nativeCompilationProof": build["nativeCompilationProof"],
                  "products": product_ref, "inputs": {key: ref(path) for key, path in input_paths.items()},
                  "logs": {key: ref(base / key / "original.log") for key in ("app", "ui")}},
        "descriptors": descriptors,
        "dependencyEvidence": {
            "Hanlin": [ref(source / "Tools/Hanlin/source.json"), ref(source / SDK_MARKER), ref(root / "sdk-materialization.log")],
            "Any": [manifest_ref, assembly, ref(base / "runtime-identity-after-ui.json")],
            "Heart": [manifest_ref, assembly, ref(base / "runtime-identity-after-ui.json")],
            "TorahInspectorKit": [lock_ref, ref(base / "package-checkouts-after-ui.json")],
        },
        "runtime": {"identifier": runtime["identifier"], "version": runtime["version"],
                    "build": runtime["buildversion"], "architecture": "arm64", "family": "ipad",
                    "deviceType": device_type["identifier"]},
        "toolchain": [{"argv": row["argv"], "original": {"path": row["path"], "sha256": row["sha256"]}}
                      for row in context["toolchain"]["observations"]],
    }
    require(all(row["exitCode"] == 0 for row in context["toolchain"]["observations"]),
            "Original Apple toolchain outcome missing")
    path = output / "evidence/receipt-input.json"
    originals.shared.write(path, contract)
    admitted, proof, actual_products = gate.admit(path, sha(path))
    originals.shared.write(output / "evidence/common-original-admission.json", proof)
    return admitted, proof, actual_products, ref(path)
