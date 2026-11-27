#!/usr/bin/env python3
"""Run the original Native26 Properties method on the same hosted products.

This distinct successor does not open a historical Mac profile, manufacture a
compiler receipt, rebuild an app, or project Swift tests. Its tracked activation
is presently closed. The root must bind the real final source/native/compiler
tuple before any runtime plan can be selected.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import types

sys.dont_write_bytecode = True

import control
import native23_inputs
from control import exclusive, load_json, load_module, regular, require, sha

CORE = "Tools/PinkhaDualEngineRuntime/hosted_core13/"
CORE_ADMISSION_SHA = "ef6e573cb2a74a6dcb758a572c4de29137f66a847d19b5c180be31a4bb75c66a"
CORE_ORIGINALS_SHA = "adc29fa18b2bd64dce6bca3cf6ded88ae6203246a12fa7e781229fda41b1f326"
DEFAULT_DEVICE = "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB"
LEGACY_DEVELOPER = Path("/Applications/Xcode.app/Contents/Developer")
REPOSITORY = "davidpovarsky/anytype-swift"


def closed_activation():
    path = Path(__file__).with_name("activation.json")
    value = load_json(path)
    require(value.get("schema") == "pinkha-hosted-native26-properties-fixed-activation-v1"
            and value.get("readyForRuntime") is True,
            "CLOSED_NATIVE26_PROPERTIES_PENDING_ROOT_FINAL_SOURCE_NATIVE_AND_COMPILER_TUPLE")
    return value, regular(path)


def job_paths(args, plan, activation, activation_ref):
    env = os.environ
    require(env.get("GITHUB_ACTIONS") == "true" and env.get("GITHUB_REPOSITORY") == REPOSITORY
            and env.get("RUNNER_ENVIRONMENT") == "github-hosted" and env.get("RUNNER_ARCH") == "ARM64"
            and platform.system() == "Darwin" and platform.machine() == "arm64",
            "Actual original GitHub-hosted Apple ARM64 job required")
    import re
    run, attempt = env.get("GITHUB_RUN_ID", ""), env.get("GITHUB_RUN_ATTEMPT", "")
    require(re.fullmatch(r"[1-9][0-9]*", run) and re.fullmatch(r"[1-9][0-9]*", attempt)
            and env.get("GITHUB_JOB"), "Original run/attempt/job identity missing")
    workspace, temporary = Path(env["GITHUB_WORKSPACE"]), Path(env["RUNNER_TEMP"])
    require(workspace.is_dir() and workspace.resolve() == workspace
            and temporary.is_dir() and temporary.resolve() == temporary
            and args.control == workspace / "control" and args.source == workspace / "app/source"
            and args.plan == temporary / "pinkha-root-plan.json"
            and args.build_root == temporary / ("pinkha-hosted-shared-" + run + "-" + attempt)
            and args.output == args.build_root / "native26-properties-runtime",
            "No relocated, cross-host or invented producer path is admitted")
    require(plan["controlCommit"] == env.get("GITHUB_SHA") and plan["repository"] == REPOSITORY
            and env.get("DEVELOPER_DIR") == plan["toolchain"]["developerDir"],
            "Actual selected controls and producer toolchain differ")
    require(activation["producerInputTuple"] == {name: plan[name] for name in
                ("appSourceSHA", "appSourceTree", "hanlinRevision", "pins", "compilerInputs", "toolchain", "native23Compiler")}
            and activation["producerOwnerSHA256"] == native23_inputs.OWNER_SHA256
            and plan["native26PropertiesRuntime"] == {"activationSHA256": activation_ref["sha256"], "plans": activation["plans"]},
            "Only the fixed root-reviewed final tuple and finite original plans may run")
    plans = activation["plans"]
    require(isinstance(plans, list) and len(plans) == 1
            and all(set(row) == {"stage", "cell"} and row["stage"] in control.PLANS and row["cell"] is None for row in plans)
            and len({row["stage"] for row in plans}) == len(plans), "Exactly the original Native26 Properties plan required")
    # Preserve the original c249-bound run body, which explicitly selects this
    # existing Xcode path. Do not create/repoint an alias or silently use another Xcode.
    selected = Path(plan["toolchain"]["developerDir"])
    require(LEGACY_DEVELOPER.is_dir() and selected.is_dir()
            and LEGACY_DEVELOPER.resolve(strict=True) == selected.resolve(strict=True),
            "Original run's existing Xcode.app must physically equal the admitted producer Xcode; no alias is created")
    return {"repository": REPOSITORY, "runID": run, "runAttempt": attempt, "job": env["GITHUB_JOB"],
            "controlCommit": env["GITHUB_SHA"], "sourceRoot": str(args.source), "buildRoot": str(args.build_root),
            "developerDir": str(selected), "originalRunDeveloperDir": str(LEGACY_DEVELOPER),
            "resolvedDeveloperDir": str(selected.resolve(strict=True))}


def own_identity(shared, args, plan):
    value = shared.identity(args.control, plan["controlCommit"])
    rows = {}
    for relative in shared.git(args.control, "ls-files", "-z", control.PREFIX).split("\0"):
        if not relative:
            continue
        path = args.control / relative
        raw = path.read_bytes()
        original = shared.git(args.control, "show", plan["controlCommit"] + ":" + relative).encode()
        require(raw == original, "Executed separate Native23 controller differs from its Git source")
        rows[relative] = regular(path)
    required = {control.PREFIX + name for name in
                ("run.py", "control.py", "native23_inputs.py", "runtime_inverse.json", "activation.json", "source_witnesses.json")}
    require(required.issubset(rows) and Path(__file__).resolve() == args.control / control.PREFIX / "run.py",
            "Complete actual same-job controller closure required")
    value["files"] = rows
    return value


def original_shared(control_root):
    directory = control_root / CORE
    require(regular(directory / "originals.py")["sha256"] == CORE_ORIGINALS_SHA
            and "originals" not in sys.modules, "Exact original Core22 source loader required")
    sys.path.insert(0, str(directory))
    admission = load_module(directory / "admission.py", "native26_properties_original_shared_admission", CORE_ADMISSION_SHA)
    import originals
    require(Path(originals.__file__).resolve() == directory / "originals.py", "Foreign source loader is forbidden")
    return admission, originals


def load_profile_dependencies(source, profile):
    # The original AX collector imports these exact original siblings by name.
    for name, digest in (("native_styled_observations", "71c376659d34b7065d152f22c41f2ded731d4527d0231375a3e688a31e7f4f02"),
                         ("native_rtl_matrix", "58c240a703a757291822073f82d84627ac5e3fedd9a0a8daf60c961a33c384ae")):
        load_module(source / control.ORIGINAL_PREFIX / (name + ".py"), name, digest)
    return {"rtl": sys.modules["native_rtl_matrix"], "styled": sys.modules["native_styled_observations"],
            "styledRuntime": profile.styled_runtime_module(), "library": profile.library_module(),
            "accessibility": profile.accessibility_module(), "accessibilityRuntime": profile.accessibility_runtime_module()}


def actual_runtime(raw_runtimes, raw_types, stage, configuration):
    runtimes = json.loads(raw_runtimes)["runtimes"]
    device_types = json.loads(raw_types)["devicetypes"]
    selected = [row for row in runtimes if row.get("isAvailable") is True and row.get("version") == "27.0"
                and "iOS" in row.get("name", "")]
    requested = configuration["deviceType"] if configuration else DEFAULT_DEVICE
    devices = [row for row in device_types if row.get("identifier") == requested]
    require(len(selected) == len(devices) == 1, "One actual original OS27 runtime/requested installed device is required")
    runtime, device = selected[0], devices[0]
    require(isinstance(runtime.get("buildversion"), str) and runtime["buildversion"], "Actual runtime build must be observed")
    family = "ipad" if device.get("name", "").startswith("iPad") else "iphone" if device.get("name", "").startswith("iPhone") else None
    require(family is not None and (configuration is None or configuration["deviceFamily"] == family),
            "Observed device family differs from the original selected plan")
    supported = {row["identifier"] if isinstance(row, dict) else row for row in runtime.get("supportedDeviceTypes", [])}
    require(not supported or requested in supported, "Requested original device is unsupported by the actual runtime")
    return runtime, device, family


def same_family_receipt_contract(admission, context, output, originals, runtime, device, family):
    """Reuse the full original contract builder with one explicit observed family."""
    path = Path(admission.__file__)
    text = path.read_text()
    nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "receipt_contract"]
    require(len(nodes) == 1, "One original common receipt contract declaration required")
    body = ast.get_source_segment(text, nodes[0])
    before, after = '"architecture": "arm64", "family": "ipad"', '"architecture": "arm64", "family": SAME_JOB_FAMILY'
    require(body.count(before) == 1 and family in ("ipad", "iphone"), "Only the actual observed device family can specialize this contract")
    changed = body.replace(before, after)
    require(changed.replace(after, before) == body, "All original common guards must restore byte-for-byte")
    namespace = dict(admission.__dict__, SAME_JOB_FAMILY=family)
    exec(compile(changed, str(path), "exec"), namespace)
    exclusive(output / "evidence/common-family-contract-inverse.json", {"originalSource": regular(path),
        "originalDeclarationSHA256": sha(body.encode()), "candidateDeclarationSHA256": sha(changed.encode()),
        "before": before, "after": after, "observedFamily": family, "fullInverseRestoresOriginal": True})
    return namespace["receipt_contract"](context, output, originals, runtime, device)


class SameJobBridge:
    def __init__(self, args, plan, context, shared, originals, owner, helper, profile, dependencies, runtime, row):
        self.args, self.plan, self.context, self.admission = args, plan, context, shared
        self.originals, self.owner, self.helper = originals, owner, helper
        self.profile, self.dependencies, self.runtime, self.row = profile, dependencies, runtime, row
        self.configured = False
        self.commands = None
        self.lifecycle = None
        self.binding = None
        self.compiler = None
        self.compiler_record = None
        self.compiler_inventory = None
        self.runtime_contract = None
        self.runtime_values = None

    def __getattr__(self, name):
        return getattr(self.profile, name)

    def configure(self, args):
        require(not self.configured and args.stage == self.row["stage"]
                and args.source_root == self.args.source and args.main_root == self.args.build_root
                and args.main_evidence == self.args.build_root / "build16"
                and args.ui_build == self.args.build_root / "native23-ui" and args.output == self.lane
                and args.retain_owned_simulator and all(getattr(args, n, None) is None for n in self.profile.OVERLAY_ARGUMENTS),
                "Exact same-job original lane paths and isolated original account policy required")
        require(args.shared_admission == Path(self.context["planRef"]["path"])
                and args.shared_admission_sha256 == self.context["planRef"]["sha256"]
                and args.shared_controller_sha256 == regular(Path(self.admission.__file__))["sha256"]
                and args.native_ui_proof_sha256 == regular(self.args.build_root / "native23-ui/evidence/compiler-inputs.json")["sha256"],
                "Original internal invocation cannot substitute an admission/controller/compiler witness")
        p = self.profile
        configuration = p.execution_configuration(args, self.originals.shared, self.dependencies["rtl"])
        p.SOURCE = self.plan["appSourceSHA"]
        p._state = {"args": args, "shared": self.originals.shared, "admission": {"sourceRoot": str(self.args.source)},
                    **self.dependencies, "rtlCell": configuration,
                    "rtlCellSHA256": args.rtl_cell_sha256 or args.styled_cell_sha256 or args.accessibility_cell_sha256,
                    "styledCellSHA256": args.styled_cell_sha256, "rtlHelpers": None, "rtlHelperClosure": None,
                    "styledContext": None, "styledRunner": None, "styledLive": None, "styledEnvironment": None,
                    "styledOwned": None, "accessibilitySession": None}
        p.check_source(self.args.source)
        self.compiler, self.compiler_record, self.compiler_inventory = native23_inputs.admit(self.context,
            self.args.control, self.plan, self.owner, self.helper, self.originals.shared, p)
        self.configured = True

    def owned_lifecycle(self, source, root, directory):
        require(self.lifecycle is None and source == self.args.source and root == self.lane,
                "One original73bb lifecycle belongs to this exact lane")
        self.lifecycle = self.profile.owned_lifecycle(source, root, directory)
        return self.lifecycle

    def styled_owned_commands(self, run, out):
        require(self.commands is None and out == self.lane and run is self.runtime.run,
                "One unchanged original run/registry must own every lane command")
        wrapped = self.profile.styled_owned_commands(run, out)
        self.commands = self.profile._state["styledOwned"]
        return wrapped

    def qualify_runtime_inputs(self, source, evidence, record):
        # This barrier is checked before direct Git/common-admission commands,
        # in addition to the unchanged c249 guard around every original run().
        require(self.commands is not None and self.commands.closed,
                "Unresolved original c249 custody forbids all new shared-admission subprocesses")
        require(source == self.args.source and evidence == self.args.build_root / "build16"
                and record == self.context["build"], "Actual original producer inputs differ")
        if self.binding is None:
            run = self.commands.run
            _, raw_runtimes = run(["xcrun", "simctl", "list", "runtimes", "--json"], self.lane, "native23-admission-runtimes")
            _, raw_types = run(["xcrun", "simctl", "list", "devicetypes", "--json"], self.lane, "native23-admission-device-types")
            runtime, device, family = actual_runtime(raw_runtimes, raw_types, self.row["stage"], self.profile._state["rtlCell"])
            # The shared original helpers may be rebound only from actual local
            # observations before the lane creates a simulator/account.
            self.runtime_values = {"RUNTIME": runtime["identifier"], "OS_VERSION": runtime["version"],
                                   "OS_BUILD": runtime["buildversion"], "BUNDLE": "io.anytype.app"}
            for name, value in self.runtime_values.items():
                setattr(self.originals.shared, name, value)
            target = self.lane / "shared-intake"
            (target / "evidence").mkdir(mode=0o700, parents=True, exist_ok=False)
            admitted, proof, products, reference = same_family_receipt_contract(self.admission, self.context,
                target, self.originals, runtime, device, family)
            self.runtime_contract = reference
            self.binding = {"schema": "pinkha-native23-actual-hosted-shared-admission-v1",
                "sourceCommit": self.plan["appSourceSHA"], "nativeSourceManifestSHA256": self.plan["pins"]["nativeSourceManifestSHA256"],
                "sharedReceiptInput": reference, "runtime": admitted["runtime"],
                "compilerAdmission": self.compiler, "actualSharedAdmission": regular(target / "evidence/common-original-admission.json"),
                "executionHost": "actual-original-GitHub-hosted-job", "historicalMacAdmissionOpened": False}
            self.shared_proof = proof
            exclusive(self.lane / "same-job-admission.json", self.binding)
        else:
            self.admission.identity(source, self.plan["appSourceSHA"], self.plan["appSourceTree"])
            _, proof, _ = self.originals.gate.admit(Path(self.runtime_contract["path"]), self.runtime_contract["sha256"])
            require(proof == self.shared_proof, "Original shared admission changed during Native23")
        self.file_only_postflight()
        return copy.deepcopy(self.binding)

    def admit(self, source, main_record, ui_build, ui_record):
        require(self.binding is not None and source == self.args.source and main_record == self.context["build"]
                and ui_build == self.args.build_root / "native23-ui" and ui_record == self.compiler_record,
                "Native23 runtime must consume the real admitted third compiler receipt")
        return copy.deepcopy(self.compiler)

    def native23_product_entries(self, path, record):
        require(path == self.args.build_root / "native23-ui/evidence/products-with-modes.json"
                and record == self.compiler_record and load_json(path) == self.compiler_inventory,
                "Actual third compiler inventory changed")
        return native23_inputs.product_entries(self.compiler_inventory)

    def file_only_postflight(self):
        # Deliberately no git, subprocess, simctl, cleanup or group re-probe here.
        if self.runtime_values is not None:
            require({name: getattr(self.originals.shared, name) for name in self.runtime_values} == self.runtime_values,
                    "Original observed same-host runtime/bundle binding changed")
        self.originals.unchanged()
        self.profile.check_source(self.args.source)
        actual, record, inventory = native23_inputs.admit(self.context, self.args.control, self.plan,
            self.owner, self.helper, self.originals.shared, self.profile)
        require(actual == self.compiler and record == self.compiler_record and inventory == self.compiler_inventory,
                "Original three-product evidence changed during Native23")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "source", "build-root", "plan", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    activation, activation_ref = closed_activation()  # Refuse before external paths, output or any command.
    require(regular(args.plan)["sha256"] == args.plan_sha256, "Root's actual original plan changed")
    plan = load_json(args.plan)
    job = job_paths(args, plan, activation, activation_ref)
    shared, original_module = original_shared(args.control)
    controls = own_identity(shared, args, plan)
    shared.control_identity(args.control, plan["controlCommit"])
    originals = original_module.Originals(args.source).install()
    owner = shared.load_hosted_owner(args.control)
    helper = load_module(args.control / native23_inputs.HELPER, "native26_properties_actual_compiler_reader", native23_inputs.HELPER_SHA256)
    context = shared.producer_context(args, plan, originals, owner)
    witnesses = load_json(Path(__file__).with_name("source_witnesses.json"))
    for relative, expected in witnesses["appFixtureSources"].items():
        actual = regular(args.source / relative)
        require({key: actual[key] for key in ("bytes", "sha256")} == expected,
                "Original unified-App fixture/storage/engine route changed: " + relative)
    require(not args.output.exists() and not args.output.is_symlink(), "Fresh same-job runtime output required")
    args.output.mkdir(mode=0o700)
    exclusive(args.output / "intake.json", {"schema": "pinkha-hosted-native26-properties-runtime-intake-v1",
        "job": job, "rootPlan": regular(args.plan), "activation": activation_ref, "controls": controls,
        "originalSharedProducerReceipt": context["buildRef"], "sourceWitnesses": witnesses,
        "plans": activation["plans"], "testsExecuted": 0, "status": "INTAKE_NOT_RUNTIME_ACCEPTANCE"})
    summary = {"schema": "pinkha-hosted-native26-properties-runtime-v1", "status": "FAIL_OR_NOT_RUN", "job": job,
               "sourceCommit": plan["appSourceSHA"], "started": time.time(), "lanes": [],
               "declaredLaunchMethods": 26, "declaredHistoryMethods": 1, "availablePlans": list(control.PLANS),
               "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}
    first = None
    try:
        # One fresh module state per selected lane; all use the same original
        # source/products and retain their separate newly owned simulator.
        for index, row in enumerate(activation["plans"]):
            parent = args.output / (str(index).zfill(2) + "-" + row["stage"])
            parent.mkdir(mode=0o700)
            runtime, materialization = control.materialize(args.source, parent / "control")
            profile, declarations = control.selected_profile(args.source)
            if index == 0:
                dependencies = load_profile_dependencies(args.source, profile)
            bridge = SameJobBridge(args, plan, context, shared, originals, owner, helper, profile, dependencies, runtime, row)
            bridge.lane = parent / "execution"
            runtime.SAME_JOB_BRIDGE = bridge
            argv = [str(runtime.__file__), "--main-root", str(args.build_root), "--main-evidence", str(args.build_root / "build16"),
                "--source-root", str(args.source), "--ui-build", str(args.build_root / "native23-ui"),
                "--output", str(bridge.lane), "--stage", row["stage"], "--retain-owned-simulator",
                "--shared-admission", str(args.plan), "--shared-admission-sha256", args.plan_sha256,
                "--shared-controller-sha256", regular(Path(shared.__file__))["sha256"],
                "--native-ui-proof-sha256", regular(args.build_root / "native23-ui/evidence/compiler-inputs.json")["sha256"]]
            if row["cell"] is not None:
                cell = parent / "original-cell.json"
                exclusive(cell, row["cell"])
                kind = "rtl" if row["stage"] == "rtl" else "styled" if row["stage"].startswith("styled-") else "accessibility"
                argv += ["--" + kind + "-cell", str(cell), "--" + kind + "-cell-sha256", regular(cell)["sha256"]]
            exclusive(parent / "source-reuse.json", {"runtime": materialization, "originalCollectors": declarations,
                                                    "actualInternalArgv": argv})
            old_argv = sys.argv
            try:
                sys.argv = argv
                runtime.main()
            finally:
                sys.argv = old_argv
            require(bridge.commands is not None and bridge.commands.closed,
                    "No subsequent lane or subprocess is allowed after unresolved original custody")
            lane_receipt = bridge.lane / "receipt.json"
            summary["lanes"].append({"stage": row["stage"], "receipt": regular(lane_receipt),
                "status": load_json(lane_receipt)["status"]})
        summary["status"] = "PASS_SELECTED_ORIGINAL_NATIVE26_PROPERTIES_METHOD_VISUAL_REVIEW_PENDING"
    except BaseException as error:
        first = error
        summary["firstFailure"] = {"type": type(error).__name__, "reason": str(error)}
    finally:
        summary["finished"] = time.time()
        first = control.retain_native23_receipt(exclusive, args.output / "receipt.json", summary, first, [])
    if first is not None:
        # stdout is an independent original workflow log if receipt storage failed.
        print(json.dumps(summary, sort_keys=True, ensure_ascii=False, default=str), flush=True)
        raise first


if __name__ == "__main__":
    main()
