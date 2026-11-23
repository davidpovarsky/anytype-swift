#!/usr/bin/env python3
"""Run the original RPC9 and Cancel panic control on an already composed union.

The caller owns composition, generator evidence, dependency declaration, finite
command execution, full input stability and cleanup. This module never creates a
second command owner, recompiles an admitted existing binary, or runs a generator.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import time

sys.dont_write_bytecode = True
PREFIX = "github.com/anyproto/anytype-heart"
PACKAGES = ("./core", "./core/application", "./cmd/grpcserver", "./clientlibrary/service")
GROUPS = (
    ("transport-size", "./core", (
        "TestAnnotationImportTransportRequestBoundaries",
        "TestAnnotationImportTransportExactGeneratedEncoding",
        "TestAnnotationImportTransportCompleteResponseLimit",
        "TestAnnotationImportTransportContainerAndReportLimits")),
    ("owned-cancel", "./core/application", (
        "TestOwnedAnnotationImportNegativeAdmission",
        "TestOwnedAnnotationCancellationMissIsNotDrain")),
    ("payload-logging", "./cmd/grpcserver", (
        "TestAnnotationImportPayloadPolicyExactMethods",
        "TestAnnotationImportPayloadLoggerSuppressesBothDirections",
        "TestAnnotationImportTracingKeepsOriginalSpanAndErrorWithoutPayloads")),
    ("generated-cancel-panic", "./clientlibrary/service", (
        "TestAnnotationImportCancelGeneratedPanicIsUnobservedFailure",)),
)
NATIVE_OUTPUTS = (
    "clientlibrary/service/service.pb.go", "docs/proto.md",
    "pb/changes.pb.go", "pb/commands.pb.go", "pb/events.pb.go",
    "pb/service/service.pb.go", "pb/snapshot.pb.go",
    "pkg/lib/pb/model/export_report.pb.go", "pkg/lib/pb/model/localstore.pb.go",
    "pkg/lib/pb/model/models.pb.go", "pkg/lib/pb/storage/file.pb.go",
)

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def row(path, label=None):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Expected regular input: " + str(path))
    size = path.stat().st_size
    sha = hashlib.sha256()
    blob = hashlib.sha1(b"blob " + str(size).encode() + b"\0")
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            sha.update(block)
            blob.update(block)
    require(path.stat().st_size == size, "Input changed while hashing")
    return {"path": str(path) if label is None else label, "bytes": size,
            "sha256": sha.hexdigest(), "git_blob": blob.hexdigest()}

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def checked_json(path, expected_sha):
    require(row(path)["sha256"] == expected_sha, "Pinned JSON input differs: " + str(path))
    return json.loads(Path(path).read_bytes())

def owned_path(root, value):
    root, path = Path(root).resolve(), Path(value)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    require(path != root and path.is_relative_to(root), "Owned path escapes its root")
    return path

def command_receipt(commands, receipt, evidence, *, argv=None, cwd=None):
    require(sum(item == receipt for item in commands.items) == 1,
            "Command receipt is not unique in the current shared owner")
    require(receipt["status"] == "TERMINAL"
        and receipt["returncode"] == receipt["effective_returncode"] == 0
        and receipt["timed_out"] is False and receipt["start_new_session"] is True
        and receipt["pid"] > 0 and receipt["process_group_id"] == receipt["pid"]
        and any(item.get("drained") is True for item in receipt["cleanup"])
        and receipt["child_started_unix"] >= receipt["started_unix"],
        "Shared command did not complete and drain successfully")
    if argv is not None:
        require(receipt["argv"] == argv, "Shared command argv differs")
    if cwd is not None:
        require(Path(receipt["cwd"]).resolve() == Path(cwd).resolve(), "Shared command cwd differs")
    for field in ("stdout", "stderr"):
        actual = owned_path(evidence, receipt[field])
        require(row(actual)["sha256"] == receipt[field + "_sha256"],
                "Shared command log differs: " + field)
    return receipt

def json_objects(path):
    text = Path(path).read_text()
    decoder, offset, objects = json.JSONDecoder(), 0, []
    while offset < len(text):
        while offset < len(text) and text[offset].isspace():
            offset += 1
        if offset == len(text):
            break
        item, offset = decoder.raw_decode(text, offset)
        require(isinstance(item, dict) and not item.get("Error") and not item.get("Incomplete"),
                "Actual Go declaration contains an incomplete package")
        objects.append(item)
    return objects

def dependency_coverage(heart, packages, paths):
    heart = Path(heart).resolve()
    by_name = {p["ImportPath"]: p for p in packages}
    require(len(by_name) == len(packages), "Go package declaration repeats an import path")
    top_names = {package: PREFIX + package[1:] + ".test" for package in PACKAGES}
    require(all(name in by_name for name in top_names.values()), "RPC test package omitted from declaration")
    output = []
    for rel in paths:
        target = (heart / rel).resolve()
        declaring = []
        for package in packages:
            directory = package.get("Dir")
            if not directory:
                continue
            # Test variants expose their actual selected test files in GoFiles.
            # Base-package TestGoFiles alone is not compiler coverage.
            files = package.get("GoFiles", []) + package.get("CgoFiles", [])
            if any((Path(directory) / name).resolve() == target for name in files):
                declaring.append(package["ImportPath"])
        selected = [package for package, name in top_names.items()
            if set(declaring).intersection(set(by_name[name].get("Deps", [])) | {name})]
        output.append({"path": rel, "declared_packages": sorted(declaring),
                       "declared_rpc_test_packages": selected})
    return output

def go_events(path, names, package):
    cases = {name: "NOT_RUN" for name in names}
    runs, terminal, package_terminal, subtests = {}, {}, [], {}
    events = 0
    parse_error = None
    try:
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            events += 1
            require(event.get("Package") == package, "Unexpected package in RPC JSON events")
            action, name = event.get("Action"), event.get("Test")
            require(action in {"start", "run", "pause", "cont", "pass", "fail", "skip", "output"},
                    "Unknown Go JSON action")
            if name is not None:
                top = name.split("/", 1)[0]
                require(top in cases, "Unselected test executed: " + name)
                target = terminal if name == top else subtests
                if action == "run":
                    require(name not in runs, "Test ran more than once: " + name)
                    runs[name] = 1
                    if name == top:
                        cases[top] = "STARTED_WITHOUT_TERMINAL"
                elif action in {"pass", "fail", "skip"}:
                    require(name in runs and name not in target, "Invalid repeated or unstarted terminal test")
                    target[name] = action
                    if name == top:
                        cases[top] = action.upper()
            elif action in {"pass", "fail", "skip"}:
                package_terminal.append(action)
    except (ValueError, KeyError, TypeError, AttributeError, RuntimeError) as error:
        parse_error = str(error)
    complete_runs = set(runs) == set(terminal) | set(subtests)
    return {"cases": cases, "events": events, "package_terminal": package_terminal,
            "subtest_terminals": subtests, "all_started_tests_terminal": complete_runs,
            "parse_error": parse_error,
            "pass": parse_error is None and complete_runs
                and all(value == "PASS" for value in cases.values())
                and all(value == "pass" for value in subtests.values())
                and package_terminal == ["pass"]}

def counts(cases):
    values = list(cases.values())
    return {"passes": values.count("PASS"),
            "failures": values.count("FAIL") + values.count("STARTED_WITHOUT_TERMINAL"),
            "skipped": values.count("SKIP"), "not_run": values.count("NOT_RUN")}

def execute(*, heart, work, evidence, commands, go_executable,
            control_spec_path, control_spec_sha256,
            union_manifest_path, union_manifest_sha256,
            declaration_path, declaration_stdout, declaration_command,
            generated_index_path, generated_index_sha256,
            existing_binaries=None):
    heart, work, evidence = [Path(p).resolve() for p in (heart, work, evidence)]
    go = Path(go_executable).resolve()
    helper_work, helper_evidence = work / "rpc-controls", evidence / "rpc-controls"
    helper_work.mkdir(exist_ok=False)
    helper_evidence.mkdir(exist_ok=False)
    result = {"schema": "otzaria.native-union-original-rpc-controls/1", "status": "NOT_STARTED",
        "started_unix": time.time(), "heart": str(heart),
        "union_manifest_sha256": union_manifest_sha256,
        "control_spec_sha256": control_spec_sha256,
        "generated_index_sha256": generated_index_sha256,
        "rpc9": {"cases": {name: "NOT_RUN" for _, _, names in GROUPS[:3] for name in names}},
        "cancel_panic": {"cases": {name: "NOT_RUN" for name in GROUPS[3][2]}},
        "binaries": {}, "groups": [], "compilation_invocations": 0,
        "reused_current_union_binaries": 0, "generators": 0, "swift_typechecks": 0,
        "historical_tests_replayed": 0, "mobile_abi_built": False,
        "full_union_input_stability_owner": "caller",
        "full_sdk_or_host_acceptance": False}
    frozen = {}
    try:
        spec = checked_json(control_spec_path, control_spec_sha256)
        require(spec["schema"] == "otzaria.native-union-rpc-control-inputs/1", "Control spec schema differs")
        expected = [(label, package, list(names)) for label, package, names in GROUPS]
        require([(g["label"], g["package"], g["test_names"]) for g in spec["groups"]] == expected,
                "Exact RPC9/panic selectors or package set changed")
        require(spec["generated_native_paths"] == list(NATIVE_OUTPUTS),
                "Generated output family changed")
        checked_json(union_manifest_path, union_manifest_sha256)
        generated = checked_json(generated_index_path, generated_index_sha256)["native"]
        require([r["path"] for r in generated] == list(NATIVE_OUTPUTS),
                "Actual generated native family differs")
        for path in (Path(control_spec_path), Path(union_manifest_path),
                     Path(declaration_path), Path(declaration_stdout), Path(generated_index_path), go):
            frozen[str(path)] = row(path)
        declaration = json.loads(Path(declaration_path).read_bytes())
        command_receipt(commands, declaration_command, evidence, cwd=heart)
        require(Path(declaration_stdout).resolve() == owned_path(evidence, declaration_command["stdout"]),
                "Raw Go declaration is not the current command stdout")
        argv = declaration_command["argv"]
        require(Path(argv[0]).resolve() == go and argv[1:5] == ["list", "-deps", "-test", "-json"],
                "Current declaration was not original Go list -deps -test -json")
        declared_packages = set(argv[5:])
        require(all(p in declared_packages or PREFIX + p[1:] in declared_packages for p in PACKAGES),
                "Current declaration omitted an RPC package")
        files = {str(Path(r["path"]).resolve()): r for r in declaration["files"]}
        required = {r["path"]: r["sha256"] for r in declaration["required_product_test_coverage"]}
        controls = [g["source"] for g in spec["groups"]]
        for item in controls + generated:
            require(row(heart / item["path"], item["path"]) == item,
                    "Current union source differs: " + item["path"])
            if item in controls:
                require(required.get(item["path"]) == item["sha256"],
                        "Required current-union control coverage is absent")
            if item["path"].endswith(".go"):
                actual = files.get(str((heart / item["path"]).resolve()))
                require(actual is not None and actual["sha256"] == item["sha256"]
                    and actual["bytes"] == item["bytes"], "Actual Go file declaration omits source")
        raw_packages = json_objects(declaration_stdout)
        coverage = dependency_coverage(heart, raw_packages, [r["path"] for r in controls + generated])
        for item in coverage:
            if item["path"].endswith(".go"):
                require(item["declared_rpc_test_packages"], "Go row has no selected RPC test dependency coverage")
        result["source_rows"] = controls + generated
        result["declaration"] = {"file": frozen[str(Path(declaration_path))],
            "raw_stdout": frozen[str(Path(declaration_stdout))],
            "command": declaration_command, "dependency_coverage": coverage,
            "byte_verified_non_go_paths": [r["path"] for r in generated if not r["path"].endswith(".go")]}
        supplied = {} if existing_binaries is None else existing_binaries
        require(set(supplied).issubset(PACKAGES), "Unknown reused binary package")
        for package in PACKAGES:
            if package in supplied:
                entry = supplied[package]
                require(set(entry) == {"path", "bytes", "sha256", "compile_command"},
                        "Existing binary entry shape differs")
                binary = owned_path(work, entry["path"])
                identity = row(binary)
                require(identity["bytes"] == entry["bytes"] and identity["sha256"] == entry["sha256"],
                        "Reused binary bytes differ from current compile receipt")
                compile_command = entry["compile_command"]
                result["reused_current_union_binaries"] += 1
            else:
                binary = helper_work / (package[2:].replace("/", "-") + ".test")
                argv = [str(go), "test", "-c", "-p", "2", "-o", str(binary), package]
                before = len(commands.items)
                commands.require("union-rpc-compile-" + package[2:].replace("/", "-"),
                                 argv, heart, 3600)
                require(len(commands.items) == before + 1, "Compile owner receipt count differs")
                compile_command = commands.items[-1]
                identity = row(binary)
                result["compilation_invocations"] += 1
            expected_argv = [str(go), "test", "-c", "-p", "2", "-o", str(binary), package]
            command_receipt(commands, compile_command, evidence, argv=expected_argv, cwd=heart)
            before = len(commands.items)
            info = commands.require("union-rpc-buildinfo-" + package[2:].replace("/", "-"),
                                    [str(go), "version", "-m", str(binary)], heart, 60)
            require(len(commands.items) == before + 1, "Buildinfo owner receipt count differs")
            info_receipt = command_receipt(commands, commands.items[-1], evidence, cwd=heart)
            text = info.read_text()
            require(text.splitlines()[0].endswith(": go1.26.5")
                and "\tbuild\tGOOS=darwin\n" in text and "\tbuild\tGOARCH=arm64\n" in text,
                "Actual RPC test binary toolchain/platform differs")
            result["binaries"][package] = {"identity": identity, "compile_command": compile_command,
                "buildinfo": {"file": row(info), "command": info_receipt},
                "reused_from_current_union": package in supplied}
        # Separate panic control first; it supplies no Native9 or cancellation ACK.
        for group in [spec["groups"][3], *spec["groups"][:3]]:
            package = group["package"]
            binary = result["binaries"][package]["identity"]["path"]
            names = group["test_names"]
            pattern = "^(" + "|".join(re.escape(name) for name in names) + ")$"
            argv = [str(go), "tool", "test2json", "-t", "-p", PREFIX + package[1:],
                    binary, "-test.v=test2json", "-test.count=1", "-test.timeout=240s",
                    "-test.run=" + pattern]
            before = len(commands.items)
            code, stdout, stderr = commands.run("union-rpc-tests-" + group["label"], argv, heart, 300)
            require(len(commands.items) == before + 1, "Execution owner receipt count differs")
            receipt = commands.items[-1]
            parsed = go_events(stdout, names, PREFIX + package[1:])
            category = "cancel_panic" if group["label"] == "generated-cancel-panic" else "rpc9"
            result[category]["cases"].update(parsed["cases"])
            item = {"label": group["label"], "package": package,
                    "command": receipt, "stdout": row(stdout), "stderr": row(stderr), **parsed}
            result["groups"].append(item)
            write(helper_evidence / (group["label"] + ".json"), item)
            require(code == 0 and parsed["pass"], "Union RPC control did not pass: " + group["label"])
            command_receipt(commands, receipt, evidence, argv=argv, cwd=heart)
        for item in controls + generated:
            require(row(heart / item["path"], item["path"]) == item, "RPC source changed during controls")
        for path, expected_row in frozen.items():
            require(row(path) == expected_row, "RPC declaration/tool input changed during use")
        for entry in result["binaries"].values():
            require(row(entry["identity"]["path"]) == entry["identity"], "RPC binary changed during controls")
        result["post_input_and_binary_stability"] = "PASS"
        result["generated_go_compiler_coverage"] = [
            {**item, "successfully_compiled_rpc_test_packages": item["declared_rpc_test_packages"]}
            for item in coverage if item["path"] in NATIVE_OUTPUTS and item["path"].endswith(".go")]
        result["status"] = "PASS"
        return result
    except BaseException as error:
        result.update({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)})
        raise
    finally:
        for category in ("rpc9", "cancel_panic"):
            result[category]["counts"] = counts(result[category]["cases"])
        result["finished_unix"] = time.time()
        result["shared_command_groups_drained"] = commands.owned_groups_drained
        write(helper_evidence / "RESULT.json", result)
