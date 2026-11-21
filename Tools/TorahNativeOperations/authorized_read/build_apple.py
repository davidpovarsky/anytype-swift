#!/usr/bin/env python3
"""Build only the qualified Heart read candidate for one ARM64 iOS simulator.

The native71 and real two-process account proof are retained by exact source and
binding hashes. No native test reruns, App build, default install or activation.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import signal
import shutil
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools/TorahNativeOperations"))
sys.path.insert(0, str(ROOT / "Tools/PinkhaNativeDerived"))
import run_native_rpc as rpc
import run_account_lifecycle as process_control
from authorized_read import account, profile
import build_t5_r15_runtime as binding
import r15_runtime_go as launcher
import run_t5_pairs_ci as pair_ci
import run_t5_coverage_ci as coverage
from build_t5_r15_runtime import (prepare_mobile_dependency_seed, validate_mobile_dependency_download,
    generated_dependency_seed, prepare_generated_hydration, validate_generated_seed_graph,
    validate_generated_hydration_manifest, validate_post_tidy_manifest, validate_post_tidy_seed_graph,
    prepare_apple_bind, manifest_digest, MOBILE_SEED_HASHES, POST_TIDY_FIXTURE_SHA)

QUALIFIED_RUN = "44954793488"
QUALIFIED_SOURCE = "779c47fdb89ed1a2d99d2cf69b97ed5b93c8016b"
CANDIDATE = "69b6b3fc8616b11230cbc45ced0635f60098950a1e611a089ab73baf70550b67"
VERSION = "v0.51.7-nightly.20261014.1-pinkha-authorized-read-v1-" + CANDIDATE
ARTIFACT = "Pinkha-Heart-Authorized-Read-Simulator-v1.tar.gz"
PROOF = "docs/validation/20261121-heart-authorized-read-account-linux"
require, digest, git = rpc.require, rpc.digest, rpc.git


def qualified_generation(control: Path) -> dict:
    directory = control / PROOF
    inventory = json.loads((directory / "evidence.json").read_bytes())
    require(str(inventory["run_id"]) == QUALIFIED_RUN and inventory["app_sha"] == QUALIFIED_SOURCE
            and inventory["artifact_id"] == 14726653954
            and inventory["artifact_zip_sha256"] == "dcf8bae05d6f90d18fed26f6f7a85a271724827d1e26833a51ab7ee8b3b00630",
            "Wrong original qualified native proof")
    for name, expected in inventory["original_files_sha256"].items():
        require(digest(directory / "original" / rpc.relative(name)) == expected, "Original qualified proof bytes changed")
    receipt = json.loads((directory / "original/receipt.json").read_bytes())
    require(receipt["status"] == "PASS_AUTHORIZED_READ_NATIVE_AND_REAL_ACCOUNT"
            and receipt["app_sha"] == QUALIFIED_SOURCE and receipt["run_id"] == QUALIFIED_RUN
            and receipt["combined_component_counts"] == {"top_level_pass": 23, "terminal_pass": 71,
                 "retained_from_prior_run": 67, "executed_this_run": 4}
            and receipt["native_account_counts"] == {"pass": 2, "fail": 0, "skip": 0}
            and receipt["native_account_identity"]["candidate_sha256"] == CANDIDATE,
            "Original native completion did not qualify this candidate")
    value = json.loads((directory / "original/generation-receipt.json").read_bytes())
    require(value["status"] == "PASS_PINNED_RPC_GENERATION" and account.candidate_identity(value) == CANDIDATE,
            "Qualified native source identity changed")
    return value


def require_same_candidate(actual: dict, qualified: dict) -> None:
    for key in ["heart_sha", "source_sha256", "generated_sha256", "module_sha256", "protobuf_inputs_sha256",
                "native_read_inventory_sha256", "authorized_read_manifest_sha256", "rpc_manifest_sha256"]:
        require(actual[key] == qualified[key], "Apple candidate changed qualified input: " + key)
    require(account.candidate_identity(actual) == CANDIDATE, "Candidate identity changed")


def prepare_candidate_post_tidy_seed(work, control, heart, original, candidate):
    # Reuse only the frozen module declaration, not the r15 product identity or
    # its test claims. Actual generated scopes must still match this declaration
    # and every downloaded module checksum before a candidate archive is built.
    require(candidate == CANDIDATE, "Unqualified candidate dependency seed")
    original_sha = binding.manifest_digest(binding.normalized_native_manifest(original, heart))
    require(original_sha == binding.POST_TIDY_ORIGINAL_MANIFEST_SHA,
            "Candidate changed the frozen original native module graph")
    fixture = control / binding.POST_TIDY_FIXTURE
    require(digest(fixture) == binding.POST_TIDY_FIXTURE_SHA, "Frozen dependency declaration changed")
    text = fixture.read_text(encoding="utf8")
    expected_line = "replace " + launcher.NATIVE_MODULE + " => " + binding.POST_TIDY_PLACEHOLDER
    require(text.count(binding.POST_TIDY_PLACEHOLDER) == 1 and text.splitlines().count(expected_line) == 1,
            "Ambiguous local source replacement")
    target = work / "post-tidy-dependency-seed"; target.mkdir(exist_ok=False)
    materialized = text.replace(expected_line, "replace " + launcher.NATIVE_MODULE + " => " + json.dumps(str(heart.resolve())))
    (target / "go.mod").write_text(materialized, encoding="utf8", newline="\n")
    return target, {"strategy": "CANDIDATE_BOUND_FROZEN_MODULE_DECLARATION",
                    "candidate_sha256": candidate, "qualified_native_run": QUALIFIED_RUN,
                    "fixture_sha256": binding.POST_TIDY_FIXTURE_SHA,
                    "original_normalized_manifest_sha256": original_sha,
                    "initial_go_mod_sha256": digest(target / "go.mod"), "r15_product_evidence_relabelled": False}


def prepare_binding(control, heart, work, evidence, real_go, env, gowork, helper, run, candidate):
    run([str(real_go), "mod", "download"], "pinned-module-download", env)
    mobile_path = run([str(real_go), "list", "-m", "-json", "golang.org/x/mobile"], "mobile-selection", env)
    mobile = json.loads(mobile_path.read_text(encoding="utf8"))
    seed, mobile_dependencies = prepare_mobile_dependency_seed(work, mobile)
    seed_env = dict(env, GOWORK="off")
    download_log = run([str(real_go), "mod", "download", "-json", "all"],
                       "pinned-mobile-dependency-download", seed_env, cwd=seed)
    mobile_dependencies.update(validate_mobile_dependency_download(download_log.read_text(encoding="utf8")))
    if digest(seed / "go.mod") != MOBILE_SEED_HASHES["go.mod"]:
        raise RuntimeError("Cache hydration changed the pinned tool's module declaration")
    mobile_dependencies.update(resolved_go_sum_sha256=digest(seed / "go.sum"),
                               download_receipt_sha256=digest(download_log))
    coverage.write_receipt(evidence / "mobile-dependency-preparation.json", mobile_dependencies)
    native_graph_log = run([str(real_go), "list", "-m", "-json", "all"],
                           "original-native-graph-for-gomobile", env)
    graph_seed, graph_preparation = generated_dependency_seed(
        work, native_graph_log.read_text(encoding="utf8"), heart, mobile)
    coverage.write_receipt(evidence / "generated-original-input.json", graph_preparation)
    shutil.copyfile(graph_seed / "go.mod", evidence / "generated-original.go.mod")
    hydration = prepare_generated_hydration(work, graph_seed, graph_preparation["initial_go_mod_sha256"])
    graph_env = dict(env, GOWORK="off")
    checksum_log = run([str(real_go), "env", "-json", "GOSUMDB", "GONOSUMDB", "GOPRIVATE"],
                       "generated-graph-checksum-authority", graph_env, cwd=graph_seed)
    checksum_authority = json.loads(checksum_log.read_text(encoding="utf8"))
    if (checksum_authority.get("GOSUMDB") != "sum.golang.org"
            or any(checksum_authority.get(key) for key in ["GONOSUMDB", "GOPRIVATE"])):
        raise RuntimeError("Public generated dependencies need the standard checksum database; no bypass is added")
    initial_mod = run([str(real_go), "mod", "edit", "-json"],
                      "generated-graph-original-manifest", graph_env, cwd=graph_seed)
    manifest = launcher.canonical_manifest(json.loads(initial_mod.read_text(encoding="utf8")))
    # gomobile drops the compiler patch version and narrows workspace replacements.
    # Verify the original first, then explicitly prepare only the pinned native Go
    # requirement and reviewed genproto override in this separate mutable copy.
    scope_override = launcher.prepare_generated_module(real_go, graph_env, hydration, manifest)
    coverage.write_receipt(evidence / "generated-genproto-override.json", scope_override)
    prepared_manifest = launcher.validate_generated_preparation_receipt(scope_override, manifest)
    # go mod download may write MVS requirements even with GOFLAGS=-mod=readonly.
    # Preserve the original gomobile declarations and hydrate only this owned copy.
    graph_download = run([str(real_go), "mod", "download", "-json", "all"],
                         "generated-graph-module-download", graph_env, cwd=hydration)
    graph_env["GOPROXY"] = "off"
    graph_selection = run([str(real_go), "list", "-m", "-json", "all"],
                          "generated-graph-effective-modules", graph_env, cwd=hydration)
    hydrated_mod = run([str(real_go), "mod", "edit", "-json"],
                      "generated-graph-hydrated-manifest", graph_env, cwd=hydration)
    shutil.copyfile(hydration / "go.mod", evidence / "generated-hydrated.go.mod")
    graph = launcher.selected_graph(launcher.module_records(graph_selection.read_text(encoding="utf8")), heart)
    graph_preparation.update(validate_generated_seed_graph(
        graph, launcher.downloaded_modules(graph_download.read_text(encoding="utf8"))))
    if digest(graph_seed / "go.mod") != graph_preparation["initial_go_mod_sha256"]:
        raise RuntimeError("Generated cache hydration changed its original module declarations")
    hydration_delta = validate_generated_hydration_manifest(
        prepared_manifest, json.loads(hydrated_mod.read_text(encoding="utf8")), graph)
    selected_seed_genproto = next(item for item in launcher.module_records(graph_selection.read_text(encoding="utf8"))
                                 if item["Path"] == pair_ci.GENPROTO_PATH)
    pair_ci.validate_genproto_selection(selected_seed_genproto)
    # Tidy removes unused roots from the flattened seed and can consequently
    # select lower transitive versions. Hydrate the observed, source-bound tidy
    # declaration separately while the existing online preparation is active.
    # The real gomobile scopes still start from their original immutable input.
    post_seed, post_preparation = prepare_candidate_post_tidy_seed(work, control, heart, manifest, candidate)
    post_env = dict(env, GOWORK="off")
    post_initial_log = run([str(real_go), "mod", "edit", "-json"],
                           "post-tidy-original-manifest", post_env, cwd=post_seed)
    post_manifest = validate_post_tidy_manifest(
        json.loads(post_initial_log.read_text(encoding="utf8")), prepared_manifest, heart)
    post_download = run([str(real_go), "mod", "download", "-json", "all"],
                        "post-tidy-module-download", post_env, cwd=post_seed)
    post_env["GOPROXY"] = "off"
    post_selection = run([str(real_go), "list", "-m", "-json", "all"],
                         "post-tidy-effective-modules", post_env, cwd=post_seed)
    post_final_log = run([str(real_go), "mod", "edit", "-json"],
                        "post-tidy-hydrated-manifest", post_env, cwd=post_seed)
    if validate_post_tidy_manifest(json.loads(post_final_log.read_text(encoding="utf8")),
                                   prepared_manifest, heart) != post_manifest:
        raise RuntimeError("Online hydration changed the exact source-bound post-tidy declaration")
    post_records = launcher.module_records(post_selection.read_text(encoding="utf8"))
    post_graph = launcher.selected_graph(post_records, heart)
    post_preparation.update(validate_post_tidy_seed_graph(
        post_graph, launcher.downloaded_modules(post_download.read_text(encoding="utf8"))))
    pair_ci.validate_genproto_selection(next(item for item in post_records if item["Path"] == pair_ci.GENPROTO_PATH))
    if digest(graph_seed / "go.mod") != graph_preparation["initial_go_mod_sha256"]:
        raise RuntimeError("Post-tidy preparation changed the immutable original generated input")
    post_preparation.update(checksum_authority=checksum_authority,
                            original_manifest_sha256=digest(post_initial_log),
                            hydrated_manifest_sha256=digest(post_final_log),
                            hydrated_go_mod_sha256=digest(post_seed / "go.mod"),
                            resolved_go_sum_sha256=digest(post_seed / "go.sum"),
                            download_receipt_sha256=digest(post_download),
                            effective_graph_sha256=digest(post_selection),
                            selected_dependencies=post_graph)
    coverage.write_receipt(evidence / "post-tidy-dependency-preparation.json", post_preparation)
    graph_contract = dict(schema="pinkha-generated-module-graph-v2",
                          native_directory=str(heart), before_tidy_manifest=manifest,
                          prepared_tidy_manifest=prepared_manifest,
                          post_tidy_manifest=post_manifest,
                          post_tidy_fixture_sha256=POST_TIDY_FIXTURE_SHA,
                          input_native_graph_sha256=graph_preparation["input_native_graph_sha256"],
                          pre_tidy_selected_graph_sha256=manifest_digest(graph),
                          selected_dependencies=post_graph)
    graph_contract_path = graph_seed / "bind-contract.json"
    coverage.write_receipt(graph_contract_path, graph_contract)
    graph_contract_sha = digest(graph_contract_path)
    original_versions = graph_preparation.pop("original_versions")
    graph_preparation.update(
        checksum_authority=checksum_authority, contract_sha256=graph_contract_sha,
        original_manifest_sha256=digest(initial_mod), download_receipt_sha256=digest(graph_download),
        effective_graph_sha256=digest(graph_selection), resolved_go_sum_sha256=digest(hydration / "go.sum"),
        hydrated_go_mod_sha256=digest(hydration / "go.mod"), hydrated_manifest_sha256=digest(hydrated_mod),
        hydration_delta=hydration_delta, immutable_bind_input_preserved=True,
        generated_scope_override=scope_override,
        selected_dependencies=graph,
        selected_version_changes=[dict(path=path, original=original_versions.get(path), generated=value["version"])
                                  for path, value in graph.items() if original_versions.get(path) != value["version"]])
    coverage.write_receipt(evidence / "generated-dependency-preparation.json", graph_preparation)
    env["GOPROXY"] = "off"
    run([str(real_go), "list", "-m", "-json", "all"], "resolved-native-modules", env)
    selection_path = run([str(real_go), "list", "-m", "-json", pair_ci.GENPROTO_PATH], "genproto-selection", env)
    genproto = pair_ci.validate_genproto_selection(json.loads(selection_path.read_text(encoding="utf8")))
    tools = {}
    for tool in ["gomobile", "gobind"]:
        target = heart / "deps" / tool
        run([str(real_go), "build", "-o", str(target), "golang.org/x/mobile/cmd/" + tool],
            tool + "-compile", env)
        tool_info = run([str(real_go), "version", "-m", str(target)], tool + "-identity", env)
        tools[tool] = dict(sha256=helper.digest(target), build_info_sha256=helper.digest(tool_info))
    shim = work / "bin"
    shim.mkdir()
    shim_source = control / "Tools/PinkhaNativeDerived/r15_runtime_go.py"
    shutil.copyfile(shim_source, shim / "go")
    (shim / "go").chmod(0o755)
    temporary = work / "gomobile-tmp"
    temporary.mkdir()
    audit = evidence / "go-launcher"
    audit.mkdir()
    env.update(PATH=str(shim) + os.pathsep + str(heart / "deps") + os.pathsep + env["PATH"],
               TMPDIR=str(temporary), PINKHA_T5_REAL_GO=str(real_go), PINKHA_T5_HEART=str(heart),
               PINKHA_T5_GOWORK=str(gowork), PINKHA_T5_MOBILE_TMP=str(temporary),
               PINKHA_T5_GO_AUDIT=str(audit),
               PINKHA_T5_GENERATED_CONTRACT=str(graph_contract_path),
               PINKHA_T5_GENERATED_CONTRACT_SHA256=graph_contract_sha)
    cache_log = run([str(real_go), "env", "GOMODCACHE"], "original-module-cache", env)
    module_cache = Path(cache_log.read_text(encoding="utf8").strip())
    env, mobile_preparation = prepare_apple_bind(
        work, module_cache, heart / "deps/gobind", shutil.which("gobind", path=env["PATH"]),
        tools["gobind"]["sha256"], env)
    coverage.write_receipt(evidence / "gomobile-preparation.json", mobile_preparation)
    return dict(env=env, graph_contract=graph_contract, graph_contract_sha=graph_contract_sha,
                graph_contract_path=graph_contract_path, audit=audit, manifest=manifest,
                prepared_manifest=prepared_manifest, tools=tools, genproto=genproto,
                mobile=mobile, mobile_preparation=mobile_preparation,
                graph_preparation=graph_preparation, post_preparation=post_preparation)


def validate_generated_scopes(prepared, heart):
    verified, original = {}, {}
    for path in sorted(prepared["audit"].glob("*.json")):
        record = json.loads(path.read_text(encoding="utf8"))
        if "before_tidy_seed" in record and record.get("return_code") == 0:
            require(record.get("generated_contract_sha256") == prepared["graph_contract_sha"]
                    and record["before_tidy_seed"].get("status") == "EXACT_GENERATED_INPUT",
                    "Generated module input changed")
            override = record.get("prepared_tidy_override", {})
            require(launcher.validate_generated_preparation_receipt(override, prepared["manifest"])
                    == prepared["prepared_manifest"]
                    and override["original_go_mod_sha256"] == record["before_tidy_seed"]["go_mod_sha256"],
                    "Actual generated dependency preparation changed")
            after = record["after_tidy_modules"]
            launcher.validate_post_tidy_selection(after["selected_dependency_graph"], after["post_tidy_manifest"],
                                                  prepared["graph_contract"])
            original[record["cwd"]] = record["before_tidy_seed"]
        if "before_build_modules" in record and record.get("return_code") == 0:
            require(record.get("scope") == "generated-gobind" and record.get("selected_gowork") == "off",
                    "Generated module scope changed")
            checked = record["before_build_modules"]
            launcher.validate_post_tidy_selection(checked["selected_dependency_graph"], checked["post_tidy_manifest"],
                                                  prepared["graph_contract"])
            launcher.validate_modules(checked["native"], checked["genproto_selection"], checked["genproto_download"], heart)
            require(hashlib.sha256(checked["go_mod_text"].encode()).hexdigest() == checked["go_mod_sha256"],
                    "Generated manifest bytes changed")
            verified[record["cwd"]] = checked
    require(len(verified) == 1 and set(original) == set(verified)
            and digest(prepared["graph_contract_path"]) == prepared["graph_contract_sha"],
            "Exactly one ARM64 simulator generated scope must qualify")
    return {"original": original, "verified": verified}


def validate_simulator_framework(info, slices):
    libraries = info.get("AvailableLibraries", [])
    require(len(libraries) == 1, "Only one simulator slice is built for this proof")
    entry = libraries[0]
    require(entry.get("LibraryIdentifier") == "ios-arm64-simulator"
            and entry.get("SupportedPlatform") == "ios" and entry.get("SupportedPlatformVariant") == "simulator"
            and entry.get("SupportedArchitectures") == ["arm64"] and entry.get("LibraryPath") == "Lib.framework",
            "Wrong candidate framework destination")
    require(len(slices) == 1 and slices[0].get("path") == "ios-arm64-simulator/Lib.framework/Lib"
            and slices[0].get("architecture") == "arm64" and slices[0].get("marker") == VERSION
            and re.fullmatch(r"[0-9a-f]{64}", slices[0].get("sha256", "")), "Wrong candidate binary identity")


def execute(args, receipt, run):
    control, heart, work, evidence = args.control, args.heart_source, args.work, args.evidence
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual ARM64 Apple SDK required")
    require(git(control, "rev-parse", "HEAD") == args.expected_app_sha and not git(control, "status", "--porcelain"),
            "Exact clean control source required")
    require(git(heart, "rev-parse", "HEAD") == rpc.HEART and not git(heart, "status", "--porcelain"), "Fresh pinned Heart required")
    require(not work.exists(), "Fresh owned work directory required")
    require(shutil.disk_usage(work.parent).free >= 8 * 1024**3, "Disk reserve below 8 GiB")
    work.mkdir()
    qualified = qualified_generation(control)
    real_go = Path(shutil.which("go") or "").resolve(strict=True)
    require(subprocess.check_output([str(real_go), "version"], text=True).strip() == "go version go1.26.5 darwin/arm64",
            "Pinned Apple Go compiler required")
    xcode = run(["xcodebuild", "-version"], "xcode-version").read_text().strip()
    sdk = run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], "simulator-sdk").read_text().strip()
    require(xcode.startswith("Xcode 27") and sdk.split(".")[0] == "27", "Verified Xcode 27 simulator lane required")
    generation = {"heart_sha": rpc.HEART, "app_sha": args.expected_app_sha,
                  "run_id": receipt["run_id"], "run_attempt": receipt["run_attempt"]}
    generation_args = SimpleNamespace(control=control, heart_source=heart, work=work/"generation", evidence=evidence,
                                      rpc_profile=profile.PROFILE)
    rpc.generate(generation_args, generation, lambda command, name, cwd, env: run(command, name, env, cwd),
                 protoc_profile="darwin-universal")
    require_same_candidate(generation, qualified)
    coverage.write_receipt(evidence / "generation-receipt.json", generation)
    helper_path = control / "Tools/PinkhaNativeDerived/build_custom_heart.py"
    require(digest(helper_path) == binding.HELPER_SHA, "Reviewed native binary helper changed")
    helper = pair_ci.load_module("authorized_read_apple_binary_helpers", helper_path)
    dependencies = [helper.fetch_tantivy(heart, arch) for arch in ["darwin-arm64", "ios-arm64-sim"]]
    bind_work = work / "binding"; bind_work.mkdir()
    gowork = bind_work / "go.work"
    gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + pair_ci.GENPROTO_PATH + " => "
                     + pair_ci.GENPROTO_PATH + " " + pair_ci.GENPROTO_VERSION + "\n", encoding="utf8")
    env = dict(os.environ, CGO_ENABLED="1", GOMAXPROCS="2", GOMEMLIMIT="4096MiB", GOTOOLCHAIN="local",
               GOWORK=str(gowork), GOFLAGS="-mod=readonly")
    prepared = prepare_binding(control, heart, bind_work, evidence, real_go, env, gowork, helper, run, CANDIDATE)
    env = prepared["env"]
    framework = heart / "dist/ios/Lib.xcframework"
    require(not framework.exists(), "No stale candidate framework")
    framework.parent.mkdir(parents=True, exist_ok=True)
    ldflags = "-X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + VERSION + " -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + rpc.HEART
    run([str(heart / "deps/gomobile"), "bind", "-tags",
         "nogrpcserver gomobile nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg",
         "-ldflags", ldflags, "-target=iossimulator/arm64", "-iosversion=17.0", "-o", str(framework),
         "github.com/anyproto/anytype-heart/clientlibrary/service", "github.com/anyproto/anytype-heart/core"],
        "gomobile-bind", env, timeout=3600)
    scopes = validate_generated_scopes(prepared, heart)
    binary = framework / "ios-arm64-simulator/Lib.framework/Lib"
    require(binary.is_file(), "Missing ARM64 simulator candidate binary")
    unmerged = digest(binary)
    combined = bind_work / "Lib-with-tantivy.a"
    run(["xcrun", "libtool", "-static", "-o", str(combined), str(binary),
         str(heart / "deps/libs/ios-arm64-sim/libtantivy_go.a")], "single-simulator-tantivy-repack", env)
    require(combined.is_file(), "Missing combined candidate archive")
    shutil.copyfile(combined, binary)
    headers = list((framework / "ios-arm64-simulator/Lib.framework/Headers").glob("*.h"))
    require(any("ServicePinkhaTorahAuthorizedOperationRead" in p.read_text() for p in headers),
            "Actual generated ObjC read entry missing")
    slices = helper.verify_framework_slices(framework, VERSION)
    native_slices = helper.verify_framework_slices(framework, rpc.HEART)
    require([(x["path"], x["architecture"], x["sha256"]) for x in slices]
            == [(x["path"], x["architecture"], x["sha256"]) for x in native_slices], "Native marker differs from candidate slice")
    validate_simulator_framework(plistlib.loads((framework / "Info.plist").read_bytes()), slices)
    rpc.verify_composed_source(heart, generation["source_sha256"], set(generation["tracked_paths"]), generation["module_sha256"])
    require_same_candidate(generation, qualified_generation(control))
    require(git(control, "rev-parse", "HEAD") == args.expected_app_sha and not git(control, "status", "--porcelain"), "Control source changed")
    receipt.update(status="APPLE_SIMULATOR_FRAMEWORK_BUILT_NOT_EXECUTED", candidate_sha256=CANDIDATE,
                   expected_app_get_version=VERSION, qualified_native_run=QUALIFIED_RUN,
                   qualified_native_source=QUALIFIED_SOURCE, native_component_cases_retained=71,
                   native_account_processes_retained=2, native_tests_executed_this_run=0,
                   generated_sha256=generation["generated_sha256"], native_source_sha256=generation["source_sha256"],
                   module_sha256=generation["module_sha256"], binary_slices=slices,
                   unmerged_go_archive_sha256=unmerged, native_dependencies=dependencies,
                   actual_generated_scopes=scopes, xcode=xcode, simulator_sdk=sdk,
                   framework_files_sha256={p.relative_to(framework).as_posix(): digest(p) for p in sorted(framework.rglob("*")) if p.is_file()})
    coverage.write_receipt(framework.parent / "HeartAuthorizedReadBuild.json", receipt)
    args.artifacts.mkdir(parents=True, exist_ok=False)
    artifact = args.artifacts / ARTIFACT
    run(["tar", "-czf", str(artifact), "-C", str(framework.parent), "Lib.xcframework", "HeartAuthorizedReadBuild.json"], "package-candidate", env)
    receipt.update(artifact_name=ARTIFACT, artifact_sha256=digest(artifact))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["control", "heart-source", "work", "evidence", "artifacts"]: parser.add_argument("--"+name, required=True, type=Path)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args(argv)
    for name in ["control", "heart_source", "work", "evidence", "artifacts"]: setattr(args, name, getattr(args, name).resolve())
    require(len({args.control, args.heart_source, args.work, args.evidence, args.artifacts}) == 5, "Distinct owned paths required")
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha), "Exact source SHA required")
    args.evidence.mkdir(parents=True, exist_ok=False)
    receipt_path = args.evidence / "apple-build.json"
    receipt = {"status": "NOT_RUN_PREFLIGHT", "app_sha": args.expected_app_sha, "heart_sha": rpc.HEART,
               "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
               "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"), "commands": [], "app_capability": "OFF",
               "ios_execution": "NOT_RUN", "default_runtime_changed": False,
               "started_at": datetime.now(timezone.utc).isoformat()}
    previous_handlers = {number: signal.getsignal(number) for number in [signal.SIGTERM, signal.SIGINT]}
    cancelling = False
    def cancel(number, frame):
        nonlocal cancelling
        if not cancelling:
            cancelling = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in previous_handlers: signal.signal(number, cancel)
    def run(command, name, env=None, cwd=args.heart_source, timeout=900):
        entry = {"name": name, "argv": list(map(str, command)), "status": "RUNNING"}
        receipt["commands"].append(entry); coverage.write_receipt(receipt_path, receipt)
        try:
            entry["pid"] = process_control.run_process(list(map(str, command)), cwd, env or os.environ.copy(), args.evidence/(name+".log"), timeout)
            entry["status"] = "PASS_EXIT_0"
            return args.evidence/(name+".log")
        except BaseException:
            entry["status"] = "FAIL"; raise
        finally: coverage.write_receipt(receipt_path, receipt)
    code=1
    try:
        execute(args, receipt, run); code=0
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL", error=type(error).__name__)
        print(type(error).__name__+": "+str(error), file=sys.stderr)
    finally:
        try:
            receipt["finished_at"]=datetime.now(timezone.utc).isoformat(); coverage.write_receipt(receipt_path, receipt)
        finally:
            for number, handler in previous_handlers.items(): signal.signal(number, handler)
    return code


if __name__ == "__main__": raise SystemExit(main())
