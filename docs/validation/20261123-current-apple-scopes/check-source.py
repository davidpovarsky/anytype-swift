"""Read-only source/structure qualification. Never imports repository modules."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
DOC = Path(__file__).resolve().parent
BASE = "7c506bb52c9e211e84de5feeaca549d315b2855d"
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
records = {"status": "FAIL", "base": BASE, "repositoryImports": 0, "testMethodsExecuted": 0,
           "appleBuilds": 0, "nativeBuilds": 0, "productExecutions": 0, "checks": {}, "inputs": {}}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*argv):
    return subprocess.check_output(["git", "-C", str(ROOT), *argv], env=ENV, timeout=30)

def blob(path, commit=BASE):
    return git("show", commit + ":" + path)

def parsed(path):
    raw = (ROOT / path).read_bytes()
    records["inputs"][path] = {"bytes": len(raw), "sha256": sha(raw), "mode": stat.S_IMODE((ROOT/path).stat().st_mode)}
    return ast.parse(raw.decode(), filename=path)

def value(node, names):
    if isinstance(node, ast.Name):
        return names[node.id]
    if isinstance(node, ast.Dict):
        return {value(k, names): value(v, names) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.Tuple, ast.List)):
        values = [value(v, names) for v in node.elts]
        return tuple(values) if isinstance(node, ast.Tuple) else values
    return ast.literal_eval(node)

def function(raw, name):
    text = raw.decode()
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return "\n".join(text.splitlines()[node.lineno-1:node.end_lineno]) + "\n", ast.dump(node, include_attributes=False)

def main():
    assert git("rev-parse", "HEAD").decode().strip() == BASE
    assert os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize >= 1024**3
    changed = git("diff", "--name-status", "HEAD", "--").decode().splitlines()
    assert all(row.startswith("A\t") for row in changed), changed
    records["checks"]["onlyNewPaths"] = changed
    files = sorted((ROOT / "Tools/CurrentAppleValidation").glob("*.py"))
    trees = {p.name: parsed(p.relative_to(ROOT).as_posix()) for p in files}
    constants = {}
    for node in trees["contracts.py"].body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            constants[node.targets[0].id] = value(node.value, constants)
    all_names = set()
    for key, spec in constants["PROFILES"].items():
        methods = [name for names, seconds in spec["stages"].values() for name in names]
        assert len(methods) == len(set(methods)) == 4
        assert constants["SOURCE_DRAG"] not in methods
        all_names.update(methods)
    assert constants["PROFILES"]["release-return-rtl"]["stages"]["preparation"][1] == 300
    original_budget = ast.parse(blob("Tools/PinkhaSimulatorGate/run_ui27.py").decode())
    assert any(isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
               and n.targets[0].id == "DEFAULT_METHOD_SECONDS" and ast.literal_eval(n.value) == 300
               for n in original_budget.body)
    swift = {
      "BlockActionServiceReturnFocusTests": "AnytypeTests/Pinkha/BlockActionServiceReturnFocusTests.swift",
      "PinkhaStage1AcceptancePreparationTests": "AnyTypeTests/Pinkha/PinkhaStage1AcceptancePreparationTests.swift",
      "NativeLaunchTests": "NativeApp/UITests/NativeLaunchTests.swift"}
    for name in all_names:
        suite, method = name.split("/")
        text = blob(swift[suite]).decode()
        assert len(re.findall(r"\bfunc\s+" + re.escape(method) + r"\s*\(", text)) == 1
    records["checks"]["exactSelectors"] = {k: [s["target"] + "/" + m for ns, _ in s["stages"].values() for m in ns]
                                           for k, s in constants["PROFILES"].items()}
    original = blob("Tools/AnyEngineValidation/prepared_inline_file_apple/cleanup.py")
    candidate = (ROOT / "Tools/CurrentAppleValidation/cleanup_policy.py").read_bytes()
    one, ast_one = function(original, "cleanup_owned_simulator")
    two, ast_two = function(candidate, "cleanup_owned_simulator")
    assert one == two and ast_one == ast_two
    records["checks"]["cleanupWholeFunction"] = {"originalFileSHA256": sha(original), "functionSHA256": sha(one.encode()),
                                                "exactText": True, "exactAST": True, "oldControlsExecuted": 0}
    fixed_path = ROOT / "Tools/CurrentAppleValidation/source-inputs.json"
    fixed = json.loads(fixed_path.read_bytes())
    records["inputs"][fixed_path.relative_to(ROOT).as_posix()] = {
        "bytes": fixed_path.stat().st_size, "sha256": sha(fixed_path.read_bytes()), "mode": stat.S_IMODE(fixed_path.stat().st_mode)}
    assert fixed["base"] == BASE and fixed["native"] == {"heart": constants["HEART"], "any": constants["ANY"]}
    for scope in [*fixed["productTrees"].values(), fixed["helperTrees"]]:
        for name, expected in scope.items():
            assert git("rev-parse", BASE + ":" + name).decode().strip() == expected
    for name, expected in fixed["helperInputs"].items():
        mode, kind, oid, _ = git("ls-tree", BASE, "--", name).decode().split(maxsplit=3)
        assert kind == "blob" and expected == {"gitMode": mode, "gitBlob": oid, "sha256": sha(blob(name))}
    assert fixed["retainedMethods"] == json.loads(blob("Tools/AnyEnginePort/native-ui-original-products-451082.json"))["retainedMethods"]
    assert len(fixed["retainedMethods"]) == 22 and not all_names.intersection(fixed["retainedMethods"])
    assert not git("diff", "--name-only", constants["HEART"]["source"], BASE, "--",
                   "Modules/PinkhaKit", "Modules/PinkhaHeartEngine").strip()
    native_manifest = "Tools/AnyEngineValidation/evidence/native-property-receipts-v9-source.json"
    native = json.loads(blob(native_manifest))
    for name in [native_manifest, *[str(Path(native_manifest).parent/native[k]["patch"]) for k in ("any","sdk")]]:
        assert blob(name) == blob(name, constants["ANY"]["source"])
    records["checks"]["sourceClosure"] = {
        "helperInputs": len(fixed["helperInputs"]), "moduleOrigins": len(fixed["moduleOrigins"]),
        "helperTrees": fixed["helperTrees"], "productTrees": fixed["productTrees"],
        "retained22Disjoint": True, "coherentConsumerModulesUnchanged": True, "nativeAnyInputsUnchanged": True}
    central = ".github/workflows/torah-inspector-ipados27.yml"
    raw = (ROOT / central).read_bytes()
    assert raw == blob(central) and sha(raw) == "d96361dcf11c3f81e671560e407ad43a30aeca4528b89de59290fab652c0631f"
    patch = json.loads((DOC / "central-additive-patch.json").read_bytes())
    after = raw.decode()
    for hunk in patch["semanticHunks"]:
        assert after.count(hunk["anchor"]) == 1
        after = after.replace(hunk["anchor"], hunk["anchor"] + hunk["append"])
    assert len(patch["semanticHunks"]) == 4 and sha(after.encode()) == patch["proposedAfterSHA256"]
    import yaml
    old = yaml.load(raw, Loader=yaml.BaseLoader)
    new = yaml.load(after, Loader=yaml.BaseLoader)
    route_names = ("current-release-return-rtl", "current-native-ui-failed")
    for name in route_names:
        new["on"]["workflow_dispatch"]["inputs"]["route"]["options"].remove(name)
        del new["jobs"][name]
    assert new == old
    workflows = []
    for key in ("release-return-rtl", "native-ui-failed"):
        name = ".github/workflows/pinkha-current-" + key + ".yml"
        payload = (ROOT / name).read_bytes()
        data = yaml.load(payload, Loader=yaml.BaseLoader)
        assert set(data["on"]) == {"workflow_call"} and len(data["jobs"]) == 1
        job = next(iter(data["jobs"].values()))
        assert job["runs-on"] == "xcode-27" and job["timeout-minutes"] == "150"
        steps = job["steps"]
        assert len([step for step in steps if step.get("id") == "execute"]) == 1
        assert "always()" in steps[-2]["if"] and " cleanup " in steps[-2]["run"] and steps[-2]["timeout-minutes"] == "8"
        assert steps[-1]["uses"] == "actions/upload-artifact@v4" and steps[-1]["if"] == "always()"
        for step in steps:
            if "run" in step:
                result = subprocess.run(["bash", "-n"], input=step["run"].encode(),
                                        capture_output=True, timeout=10)
                assert result.returncode == 0, result.stderr.decode()
        records["inputs"][name] = {"bytes": len(payload), "sha256": sha(payload), "mode": stat.S_IMODE((ROOT/name).stat().st_mode)}
        workflows.append(name)
    records["checks"]["workflows"] = {"currentCentralUnchanged": True, "additiveHunks": 4,
                                      "oldStructureExact": True, "workflowFiles": workflows, "shellSyntax": "PASS"}
    sdk = "Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json"
    assert (ROOT/sdk).read_bytes() == blob(sdk)
    old_sdk = json.loads(blob(sdk))
    current_sdk = json.loads(blob(sdk, "b15cd58e376461b066df7fd1639946bb8dca5848"))
    assert old_sdk["inputs"] == current_sdk["inputs"] and len(old_sdk["inputs"]) == 85
    records["checks"]["SDK85"] = {"inputRowsUnchanged": 85, "manifestPhysicalUnchanged": True,
                                   "rootSortedPreloadManifestToRetain": "6338515deb87121b0bb592a66e2abe99c3cd06dec2fa006ec6e7848604a294da"}
    records["status"] = "PASS_SOURCE_AND_SYNTAX_ONLY"

if __name__ == "__main__":
    started = time.monotonic()
    try:
        main()
    except BaseException as failure:
        records["failure"] = {"type": type(failure).__name__, "message": str(failure)}
        raise
    finally:
        records["elapsedSeconds"] = time.monotonic() - started
        path = DOC / "static-source-check.json"
        with path.open("x") as stream:
            json.dump(records, stream, indent=2, sort_keys=True)
            stream.write("\n")
