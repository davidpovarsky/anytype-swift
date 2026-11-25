#!/usr/bin/env python3
"""Use the pinned graph in gomobile's disposable module, without changing sources."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

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

def main():
    real = Path(os.environ["PINKHA_DUAL_REAL_GO"])
    source = Path(os.environ["PINKHA_DUAL_SOURCE"])
    build = Path(os.environ["PINKHA_DUAL_BUILD"])
    require(real == Path("/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go")
            and source.resolve() == source and source.parent == build,
            "pinned_real_go_and_source_required")
    manifest_raw = (source / "source-manifest.json").read_bytes()
    require(hashlib.sha256(manifest_raw).hexdigest() == os.environ["PINKHA_DUAL_MANIFEST"],
            "runtime_source_manifest_changed")
    cwd, env, argv = Path.cwd(), dict(os.environ), sys.argv[1:]
    mod = cwd / "go.mod"
    generated = mod.exists() and mod.read_text().startswith("module gobind\n")
    if not generated:
        os.execve(real, [str(real), *argv], env)
    require(cwd.resolve() == cwd and cwd.is_relative_to(build / "tmp")
            and cwd.name == "src-arm64" and cwd.parent.name in ("ios", "iossimulator")
            and (cwd / "gobind").is_dir(), "foreign_generated_binding_module")
    env["GOWORK"] = "off"
    locals_ = {
        "github.com/anyproto/anytype-heart": source / "heart",
        "github.com/anyproto/any": source / "any",
        "github.com/anyproto/any-sync-sdk": source / "any/.runtime-artifacts/sdk-source",
        "github.com/anyproto/any-sync": source / "sync",
    }
    def query(args):
        return subprocess.check_output([str(real), *args], env=env, text=True)
    declarations = json.loads(query(["mod", "edit", "-json"]))
    require(declarations["Module"]["Path"] == "gobind", "generated_module_changed")
    replacements = {x["Old"]["Path"]: x["New"] for x in declarations.get("Replace", [])}
    for module, path in locals_.items():
        require(replacements.get(module) == {"Path": str(path)},
                "generated_native_source_replacement_changed:" + module)
    before = hashlib.sha256(mod.read_bytes()).hexdigest()
    if argv[:2] == ["mod", "tidy"]:
        # gomobile formats only the major/minor Go directive and does not add
        # requirements for workspace main modules. Seed its disposable module.
        subprocess.run([str(real), "mod", "edit", "-go=1.27.4",
                        *["-require=" + module + "@v0.0.0" for module in locals_]],
                       env=env, check=True)
        result = subprocess.run([str(real), *argv], env=env)
        if result.returncode != 0:
            raise SystemExit(result.returncode)
    pins = {m["Path"]: m for m in stream_json(Path(os.environ["PINKHA_DUAL_GRAPH"]).read_text())}
    observed = stream_json(query(["list", "-m", "-json", "all"]))
    checked = []
    for module in observed:
        name = module["Path"]
        if name == "gobind":
            continue
        if name in locals_:
            require(module.get("Replace", {}).get("Dir") == str(locals_[name]),
                    "actual_native_replacement_changed:" + name)
        else:
            require(name in pins, "unreviewed_generated_module:" + name)
            expected = pins[name].get("Replace", pins[name])
            actual = module.get("Replace", module)
            require(all(actual.get(key) == expected.get(key)
                        for key in ("Path", "Version", "Sum", "GoModSum")
                        if key in ("Path", "Version") or expected.get(key) is not None),
                    "actual_generated_dependency_changed:" + name)
        checked.append(name)
    require(set(locals_).issubset(checked), "required_native_module_missing")
    receipt = {"kind": "GOMOBILE_GENERATED_MODULE_GRAPH_VERIFIED", "cwd": str(cwd),
               "argv": argv, "originalGoModSHA256": before,
               "effectiveGoModSHA256": hashlib.sha256(mod.read_bytes()).hexdigest(),
               "nativeSourcePaths": {k: str(v) for k, v in locals_.items()},
               "checkedModuleCount": len(checked), "sourceModulesModified": False,
               "workspaceDisabledOnlyForOwnedGeneratedModule": True}
    output = build / "evidence/generated-modules"
    output.mkdir(mode=0o700, exist_ok=True)
    with (output / (uuid.uuid4().hex + ".json")).open("x") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    if argv[:2] == ["mod", "tidy"]:
        return
    os.execve(real, [str(real), *argv], env)

if __name__ == "__main__":
    main()
