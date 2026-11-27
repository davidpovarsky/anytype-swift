"""Read the actual third compiler's receipts without rewriting their schema."""
from __future__ import annotations

import json
from pathlib import Path
import types

from control import load_json, regular, require

HELPER = "Tools/PinkhaDualEngineRuntime/hosted_shared_build/native23_build.py"
HELPER_SHA256 = "9d6d8410507955d340ffc7c6fceb52477965ec8ec380255dce7d936b30fb643d"
CONTRACT = "Tools/PinkhaDualEngineRuntime/hosted_shared_build/native23_build_contract.json"
CONTRACT_SHA256 = "dc228b291736fa472c852232e09e79e27a70720ff235a762512ba4337b7d77e0"
OWNER_SHA256 = "45901e48763ed480fc9bd9789026a3fad35b44115c89f51ae7c312c433b50aa3"


def pinned(row, expected_path):
    expected_path = Path(expected_path)
    require(row == regular(expected_path), "Actual Native23 evidence reference changed: " + str(expected_path))
    return expected_path


def product_entries(inventory):
    """The original runner's non-directory view, from the verified full inventory."""
    return [{"path": name, **({key: row[key] for key in ("kind", "bytes", "sha256")}
              if row["kind"] == "file" else {"kind": "symlink", "target": row["target"]})}
            for name, row in inventory.items() if row["kind"] in ("file", "symlink")]


def admit(context, control, plan, owner, helper, common, profile):
    root, source = context["root"], context["source"]
    counts = owner.validate_compiler_inputs(plan["compilerInputs"])
    require(counts == {"native": 62, "stage1UI": 10, "native23UI": 2},
            "Exact reviewed producer membership is required for the separate two-source runner")
    output = root / "native23-ui"
    evidence = output / "evidence"
    receipt_path = evidence / "receipt.json"
    record = load_json(receipt_path)
    contract = helper.contract()
    require(regular(control / HELPER)["sha256"] == HELPER_SHA256
            and regular(control / CONTRACT)["sha256"] == CONTRACT_SHA256
            and regular(control / "Tools/PinkhaDualEngineRuntime/hosted_shared_build/run.py")["sha256"] == OWNER_SHA256,
            "Exact reviewed separate Native23 producer tuple required")
    require(plan.get("native23Compiler") == helper.declared_plan(), "Root did not admit this exact third compiler")
    require(record["schema"] == "pinkha-hosted-native23-ui-build-v1"
            and record["status"] == "PASS_ORIGINAL_NATIVE23_UI_RUNNER_BUILD_NOT_ACCEPTANCE"
            and record["sourceCommit"] == plan["appSourceSHA"]
            and record["sourceTree"] == plan["appSourceTree"]
            and record["controlCommit"] == plan["controlCommit"]
            and record["originalSharedBuildUnchanged"] is True and record["sourceUnchanged"] is True
            and record["testsExecuted"] == record["applicationBuildTargetsInThisPhase"] == record["nativeLibraryBuildsInThisPhase"] == 0
            and record["runtimeAdmission"] is False and record["releaseArchive"] is False
            and record["testFlightUploaded"] is False and not record.get("firstFailure")
            and not record.get("finalizationErrors"), "Actual separate original Native23 compiler did not pass")
    for key, path in (("contract", control / CONTRACT), ("helper", control / HELPER),
                      ("owner", control / "Tools/PinkhaDualEngineRuntime/hosted_shared_build/run.py"),
                      ("rootPlan", Path(context["planRef"]["path"]))):
        pinned(record[key], path)
    require(record["inputPins"] == plan["pins"]
            and record["nativeSourceManifestSHA256"] == plan["pins"]["nativeSourceManifestSHA256"]
            and record["resourcePolicy"] == contract["resourcePolicy"], "Original third compiler source/dependency/resource tuple differs")
    parents, build, shared_products = helper.parent_receipts(owner, root, plan, source, common)
    require(record["originalSharedBuild"] == parents and build == context["build"],
            "Third compiler must bind the actual same-job App and complete Stage1 producer")
    intake = load_json(root / "native23-source-intake.json")
    require(intake["schema"] == "pinkha-native23-compiler-inputs-v1"
            and intake["status"] == "PASS_SOURCE_INPUTS_NOT_COMPILED"
            and intake["sourceCommit"] == plan["appSourceSHA"] and intake["sourceTree"] == plan["appSourceTree"]
            and intake["sourceInputs"] == helper.source_rows(source, contract)
            and intake["output"] == str(output) and intake["resourcePolicy"] == contract["resourcePolicy"]
            and intake["testsExecuted"] == 0 and intake["runtimeAdmission"] is False
            and all(intake[name] == record[name] for name in ("contract", "helper", "rootPlan")),
            "Exact retained third compiler input preflight differs")
    before = load_json(evidence / "source-before.json")
    require(before == load_json(evidence / "source-after.json")
            == load_json(root / "build16/source-after.json"), "All three phases must use the same complete source snapshot")
    for name in ("before", "after"):
        require(load_json(evidence / ("original-shared-products-" + name + ".json")) == shared_products,
                "Original App/Stage1 products or modes changed during third compilation")
    controls = load_json(root / "controls-after.json")
    require(load_json(evidence / "controls-after.json") == controls == context["ownerControlProof"],
            "Original third phase controller identity changed")
    phase = record["compiler"]
    require(phase == load_json(evidence / "native23-ui/result.json")
            and phase["status"] == "PASS_BUILD_EXIT_0" and phase["exitCode"] == 0
            and phase["sourceCommit"] == plan["appSourceSHA"]
            and phase["ownedProcessGroup"] == "ABSENT_ESRCH"
            and not phase["cleanupErrors"] and not phase["termination"]
            and regular(evidence / "native23-ui/process-exit.json")["sha256"] == phase["processExitReceiptSHA256"],
            "Actual third compiler command/process exit is not terminal and closed")
    custody = record["ownedCompilerCustody"]
    require(custody["status"] == "ABSENT_ESRCH" and custody["pid"] == phase["pid"]
            and phase["pid"] == phase["pgid"] and type(phase["pid"]) is int and phase["pid"] > 0
            and custody["observation"]["status"] == "ABSENT_ESRCH"
            and custody["observation"]["present"] is False
            and not custody["cleanupErrors"] and not custody["termination"], "Original third compiler ownership remains unresolved")
    expected_files, transform = profile.projected_files(source)
    for name, raw in expected_files.items():
        require((output / name).read_bytes() == raw and regular(output / name)["bytes"] == len(raw),
                "Original two-source project projection changed: " + name)
    generated_before = load_json(pinned(record["generatedInputsBefore"], evidence / "generated-inputs-before.json"))
    require(generated_before == load_json(pinned(record["generatedInputsAfter"], evidence / "generated-inputs-after.json"))
            == common.inventory(output / "source"), "Generated original Swift/project/scheme bytes, modes or paths changed")
    projection = load_json(evidence / "projection.json")
    require(projection["exactOriginalProjectProjection"] == transform
            and projection["originalGenerator"] == regular(source / contract["originalProjection"]["path"])
            and projection["sourceFiles"] == contract["swiftSources"]
            and projection["applicationBuildTargets"] == projection["targetDependencies"] == projection["packageReferences"] == 0
            and projection["testsExecuted"] == 0 and projection["runtimeAdmission"] is False,
            "Only the actual original UI-only two-source projection is admitted")
    argv, argv_witness = helper.original_argv(source, output, output / "source" / contract["projectName"],
        types.SimpleNamespace(SCHEME_NAME=contract["scheme"]), contract)
    require(phase["argv"] == argv and load_json(evidence / "original-argv-declaration.json") == argv_witness,
            "Actual compiler argv must be the exact original UI-only declaration")
    compiled = load_json(pinned(record["compilerProof"], evidence / "compiler-inputs.json"))
    original_witness = contract["originalCompilerProfile"]
    witness_declarations = helper.original_functions(source / original_witness["path"], original_witness["sha256"],
        original_witness["extractedFunctions"], {"require": require, "Path": Path, "shlex": __import__("shlex")})
    log = evidence / "native23-ui/original.log"
    require(compiled["schema"] == "pinkha-original-native23-swiftc-inputs-v1"
            and compiled["status"] == "PASS_EXACT_TWO_ORIGINAL_SWIFT_COMPILER_INPUTS_NOT_TEST_EXECUTION"
            and compiled["buildLog"] == regular(log) and regular(log)["sha256"] == phase["logSHA256"]
            and regular(log)["bytes"] == phase["logBytes"] and b"** TEST BUILD SUCCEEDED **" in log.read_bytes()
            and compiled["testsExecuted"] == 0 and compiled["runtimeAdmission"] is False
            and compiled["originalCompilerWitness"] == witness_declarations
            and compiled["compiledMethodEnumerationExecuted"] is False
            and compiled["declaredLaunchMethods"] == contract["declaredOriginalLaunchMethods"]
            and compiled["declaredHistoryMethods"] == contract["declaredOriginalHistoryMethods"],
            "Actual original compiler invocation/log/source declarations differ")
    expected_compiled = {str(output / "source/UITests" / Path(name).name): row
                         for name, row in contract["swiftSources"].items()}
    require(compiled["compiledSources"] == expected_compiled and compiled["actualCompilerFileLists"],
            "Both actual original compiled Swift sources are required")
    for row in compiled["actualCompilerFileLists"]:
        original = Path(row["originalPath"])
        retained = Path(row["retained"]["path"])
        require(original.is_relative_to(output / "derived/Build/Intermediates.noindex")
                and retained.parent == evidence / "original-compiler-file-lists"
                and regular(original)["sha256"] == regular(pinned(row["retained"], retained))["sha256"],
                "Retained compiler FileList escaped or differs from its real input")
        lines = [line.strip('"') for line in retained.read_text().splitlines() if line]
        require(row["sourcePaths"] == lines and len(lines) == 2 and set(lines) == set(expected_compiled)
                and all({k: regular(Path(name))[k] for k in ("bytes", "sha256")} == expected_compiled[name] for name in lines)
                and row["compilerInvocations"] == profile.compiler_invocations(common, log, original),
                "Actual swiftc must consume exactly the two retained original source files")
    products = output / "derived/Build/Products"
    inventory = load_json(pinned(record["productInventory"], evidence / "products-with-modes.json"))
    require(record["productsRoot"] == str(products) and common.inventory(products) == inventory,
            "Actual third product bytes/modes/links changed")
    descriptor = load_json(pinned(record["compiledDescriptor"], evidence / "compiled-descriptor.json"))
    require(descriptor == helper.descriptor_proof(source, products, contract),
            "Original actual xctestrun/runner/test bundle/executable metadata differs")
    return {"schema": "pinkha-native23-same-job-compiler-admission-v1", "sourceCommit": plan["appSourceSHA"],
            "actualCompilerReceipt": regular(receipt_path), "sharedReceipt": regular(root / "build16/receipt.json"),
            "producerInputCounts": counts,
            "compiledLaunchMethodDeclarations": len(compiled["declaredLaunchMethods"]),
            "compiledHistoryMethodDeclarations": len(compiled["declaredHistoryMethods"]),
            "compilerProof": record["compilerProof"], "productInventory": record["productInventory"],
            "compiledDescriptor": record["compiledDescriptor"], "runtimeAcceptance": False}, record, inventory
