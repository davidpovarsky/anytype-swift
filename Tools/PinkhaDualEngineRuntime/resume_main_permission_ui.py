"""Complete only the original App15 UI phase after exact filesystem-path qualification."""
import ast
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import stat
import sys
import time
import traceback

ROOT = pathlib.Path("/Users/m1/development/anytype-d-active-20261125/main15")
SOURCE = ROOT.parent / "main14/source"
APP_DERIVED = ROOT.parent / "main14/app-derived"
ORIGINAL = ROOT / "build15"
PRODUCER = ROOT / "control-main617/build_main_permission.py"
PRODUCER_SHA = "617b163951a9692909bef38a4991ded8c53e8c21ad9278a9564222fce1a57a68"
SOURCE_COMMIT = "379ca3568f247d2fc218ed63df24796d461713c0"
SOURCE_TREE = "5ebb21544dcc0f81a468ad8e77beff2f96a73295"
ORIGINAL_PINS = {
    "failure.json": "75479a16a539d47da9844817f9de802203003a4448cf4e359cc89f9b1d9db8e2",
    "source-before.json": "b4fd4069ed3846797bde854caef134c4c7343e475ade555f8daffc34e8a3dc38",
    "source-after.json": "b4fd4069ed3846797bde854caef134c4c7343e475ade555f8daffc34e8a3dc38",
    "input-and-resource-admission.json": "d185d8b2b08da4eb88fd4db011b051a42caa8641f70efca2c426e3904e100486",
    "dependencies-before.json": "5f1d52ee49a8605c257614912e96f3fb928349b209d659ec602a07989769eb67",
    "sdk-before.log": "bf4d876cf1c1a9fd8c665135b731c4d8e42af37bb68d669220fecc509f1612e0",
    "runtime-identity-before.json": "571f3148422dff2cf589060647e98981e337ef906d1c3a79ad8bd86de8872fa8",
    "app/result.json": "698889d0e24a775860dafd0d886b335ea047047e6eacb28ed5f83bd8a74dc167",
    "app/process-exit.json": "800c49403f2a4c21f59c6b3de1a36a0518336f95994b3a70a87cbd5d5ff68aad",
    "app/original.log": "52b8378d6e766d42360f4f9639a4f0dcd5b6da714e86475e9a19a9df21c53154",
}
FILE_LIST = APP_DERIVED / "Build/Intermediates.noindex/Anytype.build/Debug-Anytype-iphonesimulator/AnytypeTests.build/Objects-normal/arm64/AnytypeTests.SwiftFileList"
FILE_LIST_SHA = "fb4016eb5c58578cbdc64abbf51be59ec59ef9e474df203150ba0bd1c799e227"
TEST_INPUTS = {
    "TextBlockFocusLifecycleTests.swift": "74f09e8baa94bc8ab33668ceb72b9f59790d5a1b5e5a6d624b286844651190b3",
    "TextViewLinkGestureArbitrationTests.swift": "75a75277870bedb564a5015e1c1f33b17369f179db1802620016b63c563dd1fd",
}
CORE = ROOT / "source-inputs379/combined_heart_semantics_owned_outcomes.py"
CORE_SHA = "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"
STAGING_SHA = "dc0617be03813129b76a09a347c15f835611e6520f4f261825abacab16a71781"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def identity(path):
    s = path.lstat()
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size)

def read_pinned(path, expected):
    before = identity(path)
    assert stat.S_ISREG(before[2]), ("not a regular original", str(path))
    data = path.read_bytes()
    assert identity(path) == before and len(data) == before[3], ("changed during read", str(path))
    assert digest(data) == expected, ("unexpected original bytes", str(path))
    return data

def write_new(path, value):
    assert not path.exists() and not path.is_symlink(), ("output already exists", str(path))
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as f:
        f.write(data)
    return digest(data)

def verify_compiler_pair(source, list_bytes, log_bytes, name, expected_sha, source_files):
    git_path = source / "AnyTypeTests/Pinkha" / name
    compiler_path = source / "AnytypeTests/Pinkha" / name
    assert list_bytes.decode("utf-8").splitlines().count(str(compiler_path)) == 1, "compiler input must occur exactly once"
    a, b = identity(git_path), identity(compiler_path)
    assert stat.S_ISREG(a[2]) and stat.S_ISREG(b[2]), "compiler inputs must be regular files"
    assert a == b and git_path.samefile(compiler_path), "the two spellings must identify the same actual file"
    data = read_pinned(git_path, expected_sha)
    assert read_pinned(compiler_path, expected_sha) == data
    key = "AnyTypeTests/Pinkha/" + name
    assert source_files[key] == {"bytes": len(data), "sha256": expected_sha}, "original source inventory differs"
    marker = ("SwiftCompile normal arm64 " + str(compiler_path) + " (in target 'AnytypeTests' from project 'Anytype')").encode()
    assert marker in log_bytes.splitlines(), "original compiler command for this exact input is absent"
    assert identity(git_path) == a and identity(compiler_path) == b
    return {"gitPath": str(git_path), "compilerPath": str(compiler_path),
            "sha256": expected_sha, "bytes": len(data), "sameActualFile": True,
            "fileIdentity": {"device": a[0], "inode": a[1], "mode": stat.S_IMODE(a[2])},
            "exactOriginalSwiftCompileLine": marker.decode()}

def inventory(root):
    assert root.is_dir() and not root.is_symlink()
    root_id = identity(root)[:3]
    rows = []
    def visit(path):
        start = identity(path)
        kind = start[2]
        row = {"path": "." if path == root else str(path.relative_to(root)), "mode": stat.S_IMODE(kind)}
        if stat.S_ISLNK(kind):
            row.update(kind="symlink", target=os.readlink(path))
        elif stat.S_ISDIR(kind):
            row["kind"] = "directory"
        elif stat.S_ISREG(kind):
            h = hashlib.sha256()
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            row.update(kind="file", bytes=start[3], sha256=h.hexdigest())
        else:
            raise AssertionError(("unexpected product kind", str(path)))
        assert identity(path) == start, ("product changed during inventory", str(path))
        rows.append(row)
        if stat.S_ISDIR(kind):
            for child in sorted(path.iterdir(), key=lambda x: x.name):
                visit(child)
    visit(root)
    assert identity(root)[:3] == root_id
    return {"base": str(root), "rootIdentity": {"device": root_id[0], "inode": root_id[1], "mode": stat.S_IMODE(root_id[2])}, "entries": rows}

def original_sections(raw):
    tree = ast.parse(raw.decode(), filename=str(PRODUCER))
    tries = [n for n in tree.body if isinstance(n, ast.Try)]
    assert len(tries) == 1 and tree.body[-1] is tries[0]
    outer = tries[0]
    prefix = tree.body[:tree.body.index(outer)]
    settings = [n for n in outer.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "settings" for t in n.targets)]
    assert len(settings) == 1
    starts = [i for i, n in enumerate(outer.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ui_source" for t in n.targets)]
    assert len(starts) == 1
    receipt = outer.body[-1]
    assert isinstance(receipt, ast.Expr) and isinstance(receipt.value, ast.Call)
    assert isinstance(receipt.value.func, ast.Name) and receipt.value.func.id == "write"
    assert ast.literal_eval(receipt.value.args[0].right) == "receipt.json"
    ui = outer.body[starts[0]:-1]
    calls = [n for node in ui for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "run_phase"]
    assert len(calls) == 1 and ast.literal_eval(calls[0].args[0]) == "ui"
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "verify_new_test_compiler_inputs" for node in ui for n in ast.walk(node))
    return prefix, settings, ui, receipt.value.args[1]

def execute_nodes(nodes, namespace):
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(PRODUCER), "exec"), namespace)

def qualify(evidence):
    raw = read_pinned(PRODUCER, PRODUCER_SHA)
    originals = {name: read_pinned(ORIGINAL / name, sha) for name, sha in ORIGINAL_PINS.items()}
    assert not (ORIGINAL / "receipt.json").exists() and not (ORIGINAL / "ui").exists()
    failure = json.loads(originals["failure.json"])
    assert failure["status"] == "FAIL" and failure["sourceCommit"] == SOURCE_COMMIT
    assert failure["error"] == "The actual AnytypeTests compiler input list must contain both new UIKit test sources"
    before = json.loads(originals["source-before.json"])
    assert before == json.loads(originals["source-after.json"])
    assert before["commit"] == SOURCE_COMMIT and before["tree"] == SOURCE_TREE and before["status"] == ""
    app = json.loads(originals["app/result.json"])
    exited = json.loads(originals["app/process-exit.json"])
    assert app["status"] == exited["status"] == "PASS_BUILD_EXIT_0" and app["exitCode"] == exited["exitCode"] == 0
    assert app["phase"] == "app" and app["sourceCommit"] == SOURCE_COMMIT
    assert app["ownedProcessGroup"] == "ABSENT_ESRCH" and app["cleanupErrors"] == app["termination"] == []
    assert app["processExitReceiptSHA256"] == ORIGINAL_PINS["app/process-exit.json"]
    assert all(app[key] == value for key, value in exited.items())
    assert app["logSHA256"] == ORIGINAL_PINS["app/original.log"] and app["logBytes"] == len(originals["app/original.log"])
    assert b"** TEST BUILD SUCCEEDED **" in originals["app/original.log"]
    staging = json.loads(read_pinned(ROOT / "source-staging1/receipt.json", STAGING_SHA))
    assert staging["status"] == "PASS_EXACT_APP15_SOURCE_AND_NATIVE_MATERIALIZED_ORIGINALS_RETAINED"
    assert staging["sourceCommit"] == SOURCE_COMMIT and staging["sourceRoot"] == str(SOURCE) and staging["appDerived"] == str(APP_DERIVED)
    prefix, settings, ui, receipt_expr = original_sections(raw)
    namespace = {"__name__": "app15_original_ui_continuation", "__file__": str(pathlib.Path(__file__).resolve())}
    saved = sys.argv
    try:
        sys.argv = [str(PRODUCER), SOURCE_COMMIT]
        execute_nodes(prefix, namespace)
    finally:
        sys.argv = saved
    assert namespace["ROOT"] == ROOT and namespace["SOURCE"] == SOURCE and namespace["APP_DERIVED"] == APP_DERIVED
    namespace["EVIDENCE"] = evidence
    assert namespace["source_state"]() == before, "actual source differs from original App compiler inputs"
    read_pinned(CORE, CORE_SHA)
    spec = importlib.util.spec_from_file_location("app15_original_owned_outcomes_continuation", CORE)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    namespace["LIFECYCLE"] = core.Commands(evidence / "owned-builder-lifecycle", SOURCE)
    file_list = read_pinned(FILE_LIST, FILE_LIST_SHA)
    pairs = [verify_compiler_pair(SOURCE, file_list, originals["app/original.log"], name, sha, before["files"]) for name, sha in TEST_INPUTS.items()]
    qualification = {"status": "PASS_EXACT_SAME_FILE_COMPILER_INPUTS_NOT_TEST_EXECUTION", "originalFailureSHA256": ORIGINAL_PINS["failure.json"],
                     "originalAppResultSHA256": ORIGINAL_PINS["app/result.json"], "originalFileList": str(FILE_LIST),
                     "originalFileListSHA256": FILE_LIST_SHA, "sourceFiles": pairs, "testsExecuted": 0}
    write_new(evidence / "new-uikit-compiler-inputs.json", qualification)
    for name in ["source-before.json", "input-and-resource-admission.json", "dependencies-before.json", "sdk-before.log", "runtime-identity-before.json"]:
        with (evidence / name).open("xb") as f:
            f.write(originals[name])
    namespace["verify_dependencies"]("after-app")
    assert namespace["source_state"]() == before
    baseline = json.loads(originals["input-and-resource-admission.json"])
    assert namespace["sha"](SOURCE / "Dependencies/Hanlin/.pinkha-source.json") == baseline["sdkReceiptSHA256"]
    assert namespace["sha"](SOURCE / "Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib") == baseline["nativeSHA256"]
    assert json.loads((evidence / "runtime-identity-after-app.json").read_bytes()) == json.loads(originals["runtime-identity-before.json"])
    assert not (ROOT / "ui-source-build15").exists(), "original UI source was already materialized"
    assert not (evidence / "UI.xcresult").exists() and not (evidence / "ui").exists()
    product_before = inventory(APP_DERIVED / "Build/Products")
    write_new(evidence / "original-app-products-before.json", product_before)
    body = "\n".join(ast.get_source_segment(raw.decode(), n) for n in ui)
    proof = {"status": "PASS_EXACT_ORIGINAL_APP_AND_UNEXECUTED_UI_PHASE_ADMISSION",
             "sourceCommit": SOURCE_COMMIT, "originalProducer": {"path": str(PRODUCER), "sha256": PRODUCER_SHA, "gitCommit": "08ed46041a4d45164e000212eb26fd1c98fee966"},
             "originalEvidence": str(ORIGINAL), "originalPinnedFiles": ORIGINAL_PINS,
             "compilerInputQualificationSHA256": digest((evidence / "new-uikit-compiler-inputs.json").read_bytes()),
             "originalUIBodySHA256": digest(body.encode()), "originalUIStatements": len(ui),
             "uiPhaseInvocations": 0, "appPhaseInvocations": 0, "nativeBuilds": 0, "testsExecuted": 0,
             "existingAppProductEntries": len(product_before["entries"]), "stagingReceiptSHA256": STAGING_SHA}
    write_new(evidence / "admission.json", proof)
    namespace.update(before=before, baseline=baseline, appresult=app, assembly=ROOT / "native-materialization-8ac/receipt.json")
    execute_nodes(settings, namespace)
    return namespace, ui, receipt_expr, originals, product_before, proof

def recheck_originals(originals):
    for name, old in originals.items():
        assert read_pinned(ORIGINAL / name, ORIGINAL_PINS[name]) == old
    assert not (ORIGINAL / "receipt.json").exists() and not (ORIGINAL / "ui").exists()
    read_pinned(PRODUCER, PRODUCER_SHA)
    read_pinned(FILE_LIST, FILE_LIST_SHA)
    read_pinned(CORE, CORE_SHA)

def main():
    assert sys.argv[1:] in (["admit"], ["build"]), "choose one closed continuation phase"
    mode = sys.argv[1]
    evidence = ROOT / ("build15-ui-source-admission1" if mode == "admit" else "build15-ui-continuation1")
    evidence.mkdir(mode=0o700, exist_ok=False)
    namespace = None
    try:
        namespace, ui, receipt_expr, originals, product_before, proof = qualify(evidence)
        recheck_originals(originals)
        if mode == "admit":
            assert inventory(APP_DERIVED / "Build/Products") == product_before
            write_new(evidence / "result.json", dict(proof, status="PASS_ADMISSION_ONLY_NO_BUILD", controllerSHA256=digest(pathlib.Path(__file__).read_bytes())))
            return
        # This is the exact original full UI body and original run_phase, with
        # only its final success receipt delayed until independent retention gates.
        execute_nodes(ui, namespace)
        product_after = inventory(APP_DERIVED / "Build/Products")
        write_new(evidence / "original-app-products-after.json", product_after)
        assert product_before == product_after, "original successful App Products changed during UI-only build"
        recheck_originals(originals)
        assert namespace["source_state"]() == namespace["before"]
        assert json.loads((evidence / "runtime-identity-after-ui.json").read_bytes()) == json.loads(originals["runtime-identity-before.json"])
        record = eval(compile(ast.fix_missing_locations(ast.Expression(receipt_expr)), str(PRODUCER), "eval"), namespace)
        record.update(status="PASS_ORIGINAL_APP_AND_CONTINUED_COMPLETE_UI_BUILD_NOT_ACCEPTANCE",
                      protocol="pinkha-app15-original-app-ui-continuation-v1",
                      originalProducer=proof["originalProducer"], originalFailedProducerOutcomeSHA256=ORIGINAL_PINS["failure.json"],
                      originalAppResultSHA256=ORIGINAL_PINS["app/result.json"], originalAppLogSHA256=ORIGINAL_PINS["app/original.log"],
                      originalProcessExitSHA256=ORIGINAL_PINS["app/process-exit.json"], originalEvidence=str(ORIGINAL),
                      originalUIBodySHA256=proof["originalUIBodySHA256"], continuationAdmissionSHA256=digest((evidence / "admission.json").read_bytes()),
                      compilerInputQualificationSHA256=digest((evidence / "new-uikit-compiler-inputs.json").read_bytes()),
                      appBuildsThisInvocation=0, uiBuildsThisInvocation=1, nativeBuildsThisInvocation=0, testsExecuted=0,
                      originalAppProductsPreserved=True,
                      originalAppProductsBeforeSHA256=digest((evidence / "original-app-products-before.json").read_bytes()),
                      originalAppProductsAfterSHA256=digest((evidence / "original-app-products-after.json").read_bytes()))
        write_new(evidence / "receipt.json", record)
    except BaseException as exc:
        if namespace is not None:
            try:
                write_new(evidence / "source-at-failure.json", namespace["source_state"]())
            except BaseException:
                pass
        write_new(evidence / "failure.json", {"status": "FAIL_CONTINUATION", "sourceCommit": SOURCE_COMMIT,
                  "error": str(exc), "traceback": traceback.format_exc(), "time": time.time(),
                  "originalProducerOutcomeStillFAIL": ORIGINAL_PINS["failure.json"], "freeBytes": shutil.disk_usage(ROOT).free})
        raise

if __name__ == "__main__":
    main()
