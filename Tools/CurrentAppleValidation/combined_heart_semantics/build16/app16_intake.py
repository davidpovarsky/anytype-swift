"""Additive App16 producer intake, inserted into the pinned original E/F collector.

The original App15 intake and every execution/result validator remain unchanged.
This fragment uses the original collector's require/raw/pinned/inventory helpers.
It builds nothing and never treats collector controls as application acceptance.
"""

APP16_SOURCE = "a089ff29a5c0a7e415aac800844505f099a5561d"
APP16_TREE = "bf6aa5ec62724639a8802b9ba2b3cdaa2a6cab63"
APP16_PREVIOUS = "379ca3568f247d2fc218ed63df24796d461713c0"
APP16_ORIGINAL_BUILDER = "617b163951a9692909bef38a4991ded8c53e8c21ad9278a9564222fce1a57a68"
APP16_BUILDER = "9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c"
APP16_BUILDER_DELTA = "5e18f0a7cdb25cc30d010eb0c19819fe778cb338366763f06f76fef649189970"
APP16_STAGE_RECEIPT = "ed896be868e973f0bdd704612b641547f51b15509805d4d66b7461be88507d21"
APP16_PRESERVATION = "11ab2f45511d8b7917709c1706475538b9ea4ed228e1dc908dfa55a331cacc74"
APP16_CACHE_QUALIFICATION = "26b16e0bb4266f6f15bd445f70a4032f027c36ca6ec6c255b2e6f9608f7f7245"
APP16_FOCUS_SOURCE = "2b1d3dbe3ad8c1e6e262eeea15a99e0c292dd693118f926c893f7bf9dfc8ac0b"


def app16_function_sources(value):
    text = value.decode("utf8")
    return {node.name: ast.get_source_segment(text, node)
            for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}


def qualify_app16_producer(admission, source, receipt):
    """Require the reviewed builder inverse and its actual stage/exit evidence."""
    contract = admission.get("app16Producer")
    expected_keys = {"builder", "builderDelta", "stagingScript", "stagingInput",
                     "stagingReceipt", "preservationReceipt", "cacheQualification",
                     "phaseReceipts", "compilerInputs", "compilerFileLists"}
    require(isinstance(contract, dict) and set(contract) == expected_keys,
            "Closed App16 producer provenance is required")
    require(admission["sourceCommit"] == APP16_SOURCE
            and receipt["sourceCommit"] == APP16_SOURCE
            and receipt["status"] == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and "uiContinuation" not in admission,
            "App16 requires its own successful App and full UI build, without a historical continuation")
    builder_raw = pinned(contract["builder"])
    delta_raw = pinned(contract["builderDelta"])
    delta = decode(delta_raw)
    require(sha(builder_raw) == receipt["controllerSHA256"] == delta["candidateSHA256"] == APP16_BUILDER
            and sha(delta_raw) == APP16_BUILDER_DELTA
            and delta["originalSHA256"] == APP16_ORIGINAL_BUILDER
            and delta["sourceCommit"] == APP16_SOURCE and delta["nativeManifest"] == MANIFEST
            and delta["actualStagingReceiptSHA256"] == APP16_STAGE_RECEIPT
            and delta["cacheRequalificationReceiptSHA256"] == APP16_CACHE_QUALIFICATION
            and delta["inverseRestoresEveryOriginalByte"] is True,
            "Exact reviewed App16 builder and reversible delta are required")
    original = subprocess.check_output(
        ["git", "-C", str(source), "show", APP16_SOURCE + ":Tools/PinkhaDualEngineRuntime/build_main_permission.py"],
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"), timeout=60)
    require(sha(original) == APP16_ORIGINAL_BUILDER, "Original App15 builder Git bytes differ")
    restored = builder_raw.decode("utf8")
    require(isinstance(delta["changes"], list) and delta["changes"], "Reviewed builder inverse is empty")
    changes = []
    for change in delta["changes"]:
        require(set(change) == {"old", "new", "count", "newPositions"}
                and isinstance(change["old"], str) and isinstance(change["new"], str)
                and type(change["count"]) is int and change["count"] > 0
                and len(change["newPositions"]) == change["count"]
                and all(type(position) is int and position >= 0 for position in change["newPositions"])
                and change["newPositions"] == sorted(set(change["newPositions"])),
                "Exact builder inverse occurrence contract differs")
        changes.extend((position, position + len(change["new"]), change["new"], change["old"])
                       for position in change["newPositions"])
    changes.sort()
    require(all(left[1] <= right[0] for left, right in zip(changes, changes[1:])),
            "Builder inverse spans overlap")
    for start, end, new, old in reversed(changes):
        require(restored[start:end] == new, "Builder inverse byte position differs")
        restored = restored[:start] + old + restored[end:]
    require(restored.encode("utf8") == original, "Complete original builder inverse differs")
    before, after = app16_function_sources(original), app16_function_sources(builder_raw)
    preserved = ("run_phase", "source_state", "verify_runtime_identity", "verify_dependencies")
    require(all(before[name] == after[name] for name in preserved),
            "Original build lifecycle/source/native verification functions changed")

    stage_raw = pinned(contract["stagingReceipt"])
    preservation_raw = pinned(contract["preservationReceipt"])
    cache_raw = pinned(contract["cacheQualification"])
    stage, preservation, cache = map(decode, (stage_raw, preservation_raw, cache_raw))
    require(sha(stage_raw) == APP16_STAGE_RECEIPT
            and sha(preservation_raw) == APP16_PRESERVATION
            and sha(cache_raw) == APP16_CACHE_QUALIFICATION,
            "Actual completed stage/preservation/cache-qualification evidence differs")
    require(stage["status"] == "PASS_EXACT_APP16_SOURCE_AND_NATIVE_REUSED_ORIGINALS_RETAINED"
            and stage["sourceCommit"] == APP16_SOURCE and stage["tree"] == APP16_TREE
            and stage["priorSource"] == APP16_PREVIOUS and stage["sourceManifestSHA256"] == MANIFEST
            and stage["originalPreservationSHA256"] == APP16_PRESERVATION
            and stage["applicationBuilds"] == stage["nativeBuilds"] == stage["tests"] == 0
            and sha(pinned(contract["stagingScript"])) == stage["controllerSHA256"]
            and sha(pinned(contract["stagingInput"])) == stage["inputSHA256"],
            "Completed staging source/native/controller identity differs")
    require(preservation["status"] == "PASS_ORIGINAL_SOURCE_AND_PRODUCTS_BYTES_MODES_LINKS"
            and preservation["originalProducerSHA256"] == BUILD15_PROOF["receipt"]
            and preservation["source"] == stage["sourceRoot"],
            "App15 original source and products were not preserved by the admitted stage")
    inputs = receipt["inputs"]
    require(inputs["sourceRoot"] == stage["sourceRoot"]
            and inputs["appDerived"] == stage["appDerived"]
            and inputs["stagingReceiptSHA256"] == APP16_STAGE_RECEIPT
            and inputs["cacheRequalificationReceiptSHA256"] == APP16_CACHE_QUALIFICATION,
            "Actual producer did not use the admitted source/workspace")
    # The historical stage boolean is deliberately not accepted as proof that
    # compiler intermediates or package checkouts survived. The separate exact
    # cache qualification records their subsequent observed absence.
    qualify_app16_cache(cache, inputs)
    require(isinstance(contract["phaseReceipts"], dict)
            and set(contract["phaseReceipts"]) == {"app", "ui"},
            "Both actual producer phase receipts are required")
    for phase in ("app", "ui"):
        pins = contract["phaseReceipts"][phase]
        require(set(pins) == {"result", "processExit"}, "Closed phase receipt pins required")
        result, exited = decode(pinned(pins["result"])), decode(pinned(pins["processExit"]))
        require(result == receipt[phase]
                and all(result.get(key) == value for key, value in exited.items())
                and result["phase"] == exited["phase"] == phase
                and result["status"] == exited["status"] == "PASS_BUILD_EXIT_0"
                and result["exitCode"] == exited["exitCode"] == 0
                and result["cleanupErrors"] == result["termination"] == []
                and result["ownedProcessGroup"] == "ABSENT_ESRCH"
                and result["processExitReceiptSHA256"] == pins["processExit"]["sha256"],
                "Actual App16 phase/exit outcome is incomplete or changed")
    return {"sourceCommit": APP16_SOURCE, "tree": APP16_TREE,
            "builderSHA256": sha(builder_raw), "deltaSHA256": sha(delta_raw),
            "fullOriginalProducerInverse": True, "unchangedFunctions": list(preserved),
            "stageReceiptSHA256": sha(stage_raw), "priorApp15PreservationSHA256": sha(preservation_raw),
            "cacheRequalificationSHA256": sha(cache_raw),
            "originalStageCacheReuseClaimAccepted": False,
            "actualNativeExecutionByThisIntake": False}


def qualify_app16_cache(cache, inputs):
    require(cache["protocol"] == "app16-observed-cache-requalification-v1"
            and cache["sourceCommit"] == APP16_SOURCE
            and cache["stageReceiptSHA256"] == APP16_STAGE_RECEIPT
            and cache["stageSourceAndNativePreservationRetained"] is True
            and cache["invalidatedStageMetadata"] == ["originalIntermediatesAndPackagePathsReused"]
            and cache["originalIntermediatesAndPackagePathsReused"] is False
            and inputs["originalIntermediatesAndPackagePathsReused"] is False
            and cache["applicationBuilds"] == cache["testsExecuted"] == 0
            and cache["estimateNewAppPhaseBytes"] == inputs["phaseGrowthAllowanceBytes"]["app"] == 6 * 1024**3
            and inputs["phaseGrowthAllowanceBytes"]["ui"] == 1024**3
            and cache["emergencyFloorBytes"] == FLOOR
            and cache["concurrentGrowthAllowanceBytes"] == inputs["concurrentGrowthAllowanceBytes"] == 512 * 1024**2,
            "Original cache claim must be superseded by the exact observed absence and measured allowance")
    derived = Path(inputs["appDerived"])
    expected = {"intermediates": (derived / "Build/Intermediates.noindex", False),
                "sourcePackages": (derived / "SourcePackages", False),
                "sdkModules": (derived / "SDKExplicitPrecompiledModules", True),
                "products": (derived / "Build/Products", True)}
    require(set(cache["observedPaths"]) == set(expected), "Complete original cache qualification required")
    for name, (path, existed) in expected.items():
        require(cache["observedPaths"][name] == {"path": str(path), "exists": existed, "symlink": False},
                "Actual pre-build cache observations changed")
    # Those paths may now exist because the admitted app build completed. This
    # check binds the original observed cache state, not a post-build absence.


def qualify_app16_compiler_inputs(admission, source, receipt):
    """Bind the real compiled focus source and retain the original target checks."""
    contract = admission["app16Producer"]
    compiler = decode(pinned(contract["compilerInputs"]))
    require(compiler["status"] == "PASS_ACTUAL_COMPILED_TEST_SOURCE_INPUTS_NOT_TEST_EXECUTION"
            and compiler["testsExecuted"] == 0,
            "Actual compiler input evidence is required")
    expected = {"TextBlockFocusLifecycleTests.swift": APP16_FOCUS_SOURCE,
                "TextViewLinkGestureArbitrationTests.swift":
                    "75a75277870bedb564a5015e1c1f33b17369f179db1802620016b63c563dd1fd"}
    rows = compiler["sourceFiles"]
    require(isinstance(rows, list) and len(rows) == len(expected)
            and {Path(row["path"]).name for row in rows} == set(expected),
            "Both original required UIKit compiler inputs must be present")
    for row in rows:
        name = Path(row["path"]).name
        actual = source / "AnyTypeTests/Pinkha" / name
        require(row["path"].casefold() == ("AnyTypeTests/Pinkha/" + name).casefold()
                and row["sha256"] == expected[name] == digest(actual),
                "Actual compiler input is not the reviewed focus/gesture source")
    file_lists = contract["compilerFileLists"]
    require(isinstance(file_lists, dict) and file_lists
            and set(file_lists) == {row["path"] for row in compiler["actualCompilerFileLists"]},
            "Every actual compiler file list must be preserved")
    for row in compiler["actualCompilerFileLists"]:
        value = pinned(file_lists[row["path"]])
        require(sha(value) == row["sha256"], "Actual compiler file list changed")
        lines = [line.strip().strip('"').casefold() for line in value.decode("utf8").splitlines()]
        for name in expected:
            actual = str(Path(receipt["inputs"]["sourceRoot"]) / "AnyTypeTests/Pinkha" / name)
            require(lines.count(actual.casefold()) == 1, "Exact required UIKit compiler input is missing or duplicated")
    return {"sourceFiles": expected, "compilerInputsSHA256": contract["compilerInputs"]["sha256"],
            "actualCompilerFileLists": len(file_lists), "testsExecuted": 0}


def qualify_app16_runtime(admission, source):
    """Reuse strict runtime validation with current actual build-boundary receipts."""
    helper = source / "Tools/PinkhaDualEngineRuntime/runtime_identity.py"
    require(digest(helper) == "306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0",
            "Original strict runtime identity validator differs")
    spec = importlib.util.spec_from_file_location("app16_original_runtime_identity", helper)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    manifest = raw(source / "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json")
    require(sha(manifest) == MANIFEST, "Exact current native manifest required")
    expected = runtime.identity(manifest, "2026-11-26")
    require(expected["sourcePins"]["any"] == "8fbd1e819fb132ac0e0a848d2ddf5c5714189b81"
            and expected["heartVersion"] == VERSION,
            "Current native authoring source/date/version differs")
    consumer = runtime.qualify_consumer(
        raw(source / "Modules/ProtobufMessages/Sources/PinkhaAnyEmbeddedBridge.swift"), expected)
    values = admission.get("runtimeIdentity")
    require(isinstance(values, dict) and set(values) == {"before", "after-app", "after-ui"},
            "Every actual producer runtime identity boundary required")
    originals = [pinned(values[phase]) for phase in ("before", "after-app", "after-ui")]
    require(originals[0] == originals[1] == originals[2], "Actual before/after runtime identity proof differs")
    proof = decode(originals[0])
    require(proof["status"] == "PASS_EXACT_CONSUMER_AND_ORIGINAL_LINKER_IDENTITIES_NOT_RUNTIME_ACCEPTANCE"
            and proof["identity"] == expected and proof["consumer"] == consumer
            and proof["nativeVersionExecutedByThisCheck"] is False
            and proof["applicationBuilds"] == 0 and proof["applicationAcceptanceClaimed"] is False
            and set(proof["slices"]) == {"device", "simulator"},
            "Closed original consumer and two-slice proof differs")
    for kind, identifier in (("simulator", "ios-arm64-simulator"), ("device", "ios-arm64")):
        binary = source / "Dependencies/Middleware/Lib.xcframework" / identifier / "Lib.framework/Lib"
        require(digest(binary) == proof["slices"][kind]["binarySHA256"]
                and binary.stat().st_size == proof["slices"][kind]["binaryBytes"],
                "Materialized exact runtime slice differs")
    return {"identity": expected, "producerRuntimeProofSHA256": sha(originals[0]),
            "consumer": consumer, "nativeRuntimeExecutedByThisCheck": False}


def admit_app16_and_clone_products(admission, root, evidence, commands):
    """App16's actual same-invocation App/UI producer, with the original clone gates."""
    require(root.resolve() == root and stat.S_IMODE(root.lstat().st_mode) == 0o700,
            "Exact product clones require the existing private execution root")
    original_source = Path(admission["sourceRoot"])
    built = {}
    build_receipt = decode(pinned(admission["producerReceipt"]))
    require(build_receipt.get("status") == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and build_receipt.get("sourceCommit") == admission["sourceCommit"] == APP16_SOURCE
            and build_receipt.get("sourceUnchanged") is True and build_receipt.get("testsExecuted") == 0,
            "Successful source-bound App16 combined build required")
    producer_proof = qualify_app16_producer(admission, original_source, build_receipt)
    inputs = build_receipt["inputs"]
    require(inputs["nativeSourceManifestSHA256"] == MANIFEST and inputs["nativeSHA256"] == NATIVE_BINARY
            and inputs["lockSHA256"] == LOCK and inputs["sdkReceiptSHA256"] == SDK_RECEIPT,
            "Compiled native/SDK dependency identity differs")
    for kind in ("app", "ui"):
        step = build_receipt[kind]
        require(step["status"] == "PASS_BUILD_EXIT_0" and step["exitCode"] == 0
                and step["sourceCommit"] == admission["sourceCommit"] and step["ownedProcessGroup"] == "ABSENT_ESRCH"
                and "build-for-testing" in step["argv"]
                and all(any("-D " + flag in token for token in step["argv"]) for flag in FLAGS),
                "Actual combined build flags/outcome differ")
        log = pinned(admission["producerLogs"][kind])
        require(sha(log) == step["logSHA256"] and len(log) == step["logBytes"]
                and b"** TEST BUILD SUCCEEDED **" in log, "Original successful build stdout required")
    before_raw, after_raw = pinned(admission["sourceBefore"]), pinned(admission["sourceAfter"])
    require(decode(before_raw) == decode(after_raw), "Producer source changed during build")
    require(decode(before_raw)["tree"] == APP16_TREE, "Reviewed exact App16 source tree differs")
    write_bytes(evidence / "producer-source-before.json", before_raw)
    write_bytes(evidence / "producer-source-after.json", after_raw)
    source_proof = source_admission(original_source, admission["sourceCommit"], decode(before_raw), root / "helpers")
    source_proof["app16Producer"] = producer_proof
    source_proof["sameInvocationAppAndUI"] = qualify_app16_compiler_inputs(admission, original_source, build_receipt)
    require(digest(original_source / "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json") == MANIFEST,
            "Combined original source manifest differs")
    require(digest(original_source / "Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib") == NATIVE_BINARY,
            "Materialized native bytes differ from producer")
    require(not any(key.endswith("UIOverride") for key in admission),
            "Older product/UI pairing cannot be admitted as App16")
    source_proof["runtimeIdentity"] = qualify_app16_runtime(admission, original_source)
    ui_copy = decode(pinned(admission["originalUICopy"]))
    require(ui_copy["generatorSHA256"] == "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
            and len(ui_copy["copiedFiles"]) == 12
            and digest(original_source / "PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift")
                == "8834541f5a47da80b460ecb96b20c930813b743d94f285fc1efba8a93f65ee4d",
            "Exact same-source complete UI and reviewed Link-glyph method required")
    for copied in ui_copy["copiedFiles"]:
        require(digest(original_source / copied["path"]) == copied["sha256"], "Original complete UI source differs")
    full = decode(pinned(admission["completeProducerProducts"]))
    require(admission["completeProducerProducts"]["sha256"] == build_receipt["completeProductsInventory"]["sha256"],
            "Complete product inventory is not the actual App16 producer inventory")
    for kind in ("app", "ui"):
        declared = decode(pinned(admission["products"][kind]["manifest"]))
        files = {name: {key: value for key, value in row.items() if key != "mode"}
                 for name, row in declared.items() if row["kind"] != "directory"}
        expected = {row["path"]: {key: value for key, value in row.items() if key != "path"}
                    for row in full[kind + "-derived"]["entries"]}
        require(files == expected, "Complete product entries must equal the actual original producer")
    for kind in ("app", "ui"):
        row = admission["products"][kind]
        original = Path(row["root"])
        manifest = decode(pinned(row["manifest"]))
        require(inventory(original) == manifest, "Original producer products changed")
        destination = root / (kind + "-products")
        previous_mask = os.umask(0)
        try:
            commands.run(["cp", "-cR", str(original), str(destination)], "clone-" + kind + "-products", 180)
        finally:
            os.umask(previous_mask)
        require(inventory(destination) == manifest, "APFS retained original products differ")
        descriptor = destination / row["descriptorRelativePath"]
        require(descriptor.parent == destination and descriptor.suffix == ".xctestrun"
                and digest(descriptor) == row["descriptorSHA256"], "Original descriptor pin differs")
        built[kind] = {"products": destination, "inventory": manifest, "copies": {}, "descriptor": descriptor,
                       "originalSelection": row["originalSelection"]}
        write(evidence / (kind + "-original-products.json"), manifest)
    app = built["app"]["products"] / "Debug-Anytype-iphonesimulator/Anytype.app"
    require(plistlib.loads(raw(app / "Info.plist"))["CFBundleIdentifier"] == BUNDLE, "Actual app bundle differs")
    return source_proof, built, app


admit_app15_original_products = admit_and_clone_products


def admit_and_clone_products(admission, root, evidence, commands):
    if admission.get("sourceCommit") == APP16_SOURCE:
        return admit_app16_and_clone_products(admission, root, evidence, commands)
    require("app16Producer" not in admission, "App16 producer contract used with a different source")
    return admit_app15_original_products(admission, root, evidence, commands)
