#!/usr/bin/env python3
"""Compile gomobile's owned bridge inside the unchanged native workspace."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)

def stream_json(raw):
    decoder, values, offset = json.JSONDecoder(), [], 0
    while offset < len(raw):
        while offset < len(raw) and raw[offset].isspace():
            offset += 1
        if offset == len(raw):
            break
        value, offset = decoder.raw_decode(raw, offset)
        values.append(value)
    return values

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    real = Path(os.environ["PINKHA_DUAL_REAL_GO"])
    source = Path(os.environ["PINKHA_DUAL_SOURCE"])
    build = Path(os.environ["PINKHA_DUAL_BUILD"])
    require(real == Path("/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go")
            and source.resolve() == source and source.parent == build,
            "pinned_real_go_and_source_required")
    require(digest(source / "source-manifest.json") == os.environ["PINKHA_DUAL_MANIFEST"],
            "runtime_source_manifest_changed")
    cwd, env, argv = Path.cwd(), dict(os.environ), sys.argv[1:]
    mod = cwd / "go.mod"
    if not mod.exists() or not mod.read_text().startswith("module gobind\n"):
        os.execve(real, [str(real), *argv], env)
    require(cwd.resolve() == cwd and cwd.is_relative_to(build / "tmp")
            and cwd.name == "src-arm64" and cwd.parent.name in ("ios", "iossimulator")
            and (cwd / "gobind").is_dir(), "foreign_generated_binding_module")
    pins = {m["Path"]: m for m in stream_json(Path(os.environ["PINKHA_DUAL_GRAPH"]).read_text())}
    native = {
        "github.com/anyproto/anytype-heart": source / "heart",
        "github.com/anyproto/any": source / "any",
        "github.com/anyproto/any-sync-sdk": source / "any/.runtime-artifacts/sdk-source",
        "github.com/anyproto/any-sync": source / "sync",
    }
    require({m["Path"]: m["Dir"] for m in pins.values() if m.get("Main")}
            == {k: str(v) for k, v in native.items()}, "source_workspace_members_changed")
    effective_mod = ("module gobind\n\ngo 1.27.4\n\nrequire golang.org/x/mobile "
                     + pins["golang.org/x/mobile"]["Version"] + "\n")
    effective_work = ("go 1.27.4\n\nuse (\n"
                      + "".join("\t" + str(p) + "\n" for p in native.values())
                      + "\t" + str(cwd) + "\n)\n")
    work = cwd / ".pinkha-runtime.work"
    audit = build / "evidence/generated-modules" / uuid.uuid4().hex
    audit.mkdir(mode=0o700, parents=True)
    (audit / "gomobile-go.mod").write_bytes(mod.read_bytes())
    receipt = {"status": "FAIL", "cwd": str(cwd), "argv": argv,
               "sourceModulesModified": False, "independentGoRuntimeCount": 1,
               "nativeSourcePaths": {k: str(v) for k, v in native.items()}}
    try:
        if argv[:2] == ["mod", "tidy"]:
            require(not work.exists(), "generated_module_tidy_replay")
            tidy_env = {**env, "GOWORK": "off"}
            declarations = json.loads(subprocess.check_output(
                [str(real), "mod", "edit", "-json"], env=tidy_env, text=True))
            replacements = {x["Old"]["Path"]: x["New"] for x in declarations.get("Replace", [])}
            for name, path in native.items():
                require(replacements.get(name) == {"Path": str(path)},
                        "generated_native_replacement_changed:" + name)
            subprocess.run([str(real), "mod", "edit", "-go=1.27.4",
                            *["-require=" + name + "@v0.0.0" for name in native]],
                           env=tidy_env, check=True)
            # Keep the actual tidy output. Its standalone pruning is not the
            # compile authority: the four original modules remain main modules.
            result = subprocess.run([str(real), *argv], env=tidy_env)
            receipt["actualTidyExitCode"] = result.returncode
            (audit / "actual-tidy-go.mod").write_bytes(mod.read_bytes())
            if (cwd / "go.sum").exists():
                (audit / "actual-tidy-go.sum").write_bytes((cwd / "go.sum").read_bytes())
            require(result.returncode == 0, "actual_generated_module_tidy_failed")
            mod.write_text(effective_mod)
            with work.open("x") as output:
                output.write(effective_work)
            # A private derived workspace absorbs checksum hydration. Original
            # source go.mod/go.sum/go.work files are never edited by this shim.
            (cwd / ".pinkha-runtime.work.sum").write_bytes((source / "go.work.sum").read_bytes())
        require(mod.read_text() == effective_mod and work.read_text() == effective_work
                and not work.is_symlink(), "effective_generated_workspace_changed")
        env["GOWORK"] = str(work)
        observed_raw = subprocess.check_output([str(real), "list", "-m", "-json", "all"],
                                               env=env, text=True)
        (audit / "observed-module-graph.jsonstream").write_text(observed_raw)
        observed = {m["Path"]: m for m in stream_json(observed_raw)}
        require(set(observed) == set(pins) | {"gobind"}, "actual_generated_graph_inventory_changed")
        require(observed["gobind"].get("Main") is True and observed["gobind"].get("Dir") == str(cwd),
                "generated_bridge_not_owned_workspace_main")
        for name, expected_module in pins.items():
            actual_module = observed[name]
            if name in native:
                require(actual_module.get("Main") is True and actual_module.get("Dir") == str(native[name]),
                        "actual_native_source_changed:" + name)
            expected = expected_module.get("Replace", expected_module)
            actual = actual_module.get("Replace", actual_module)
            delta = {key: {"expected": expected.get(key), "actual": actual.get(key)}
                     for key in ("Path", "Version", "Sum", "GoModSum", "Dir")
                     if (key in ("Path", "Version") or expected.get(key) is not None)
                     and actual.get(key) != expected.get(key)}
            require(not delta, "actual_generated_dependency_changed:" + name + ":" + json.dumps(delta))
        receipt.update(status="ORIGINAL_NATIVE_GRAPH_VERIFIED_WITH_OWNED_GENERATED_BRIDGE",
                       checkedModuleCount=len(pins),
                       effectiveGoModSHA256=digest(mod), effectiveWorkspaceSHA256=digest(work),
                       observedGraphSHA256=digest(audit / "observed-module-graph.jsonstream"),
                       completeOriginalGraphPreserved=True)
    except BaseException as error:
        receipt["error"] = str(error)
        raise
    finally:
        (audit / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    if argv[:2] != ["mod", "tidy"]:
        os.execve(real, [str(real), *argv], env)

if __name__ == "__main__":
    main()
