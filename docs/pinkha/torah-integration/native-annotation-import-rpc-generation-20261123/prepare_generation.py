#!/usr/bin/env python3
"""Admit the concrete new generation packet without executing a generator or native test."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    packet = (root / args.packet).resolve()
    if not packet.is_relative_to(root):
        raise RuntimeError("owned packet escapes control root")
    spec = importlib.util.spec_from_file_location("new_generator_source_admission", packet / "generation_support.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest, admission = module.admit_packet(packet, args.manifest_sha256)
    syntax = []
    for name in ("generation_support.py", "generate_original_import_rpc.py", "prepare_generation.py"):
        raw = (packet / name).read_bytes()
        ast.parse(raw, filename=name)
        syntax.append(module.row(packet / name, name))
    corresponding = []
    for entry in manifest["swift_generator_correspondence"]:
        raw = subprocess.check_output(["git", "-C", str(root), "show", module.SWIFT + ":" + entry["path"]], timeout=30)
        if len(raw) != entry["bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise RuntimeError("original generator input differs at frozen Swift base")
        corresponding.append(entry["path"])
    all_names = []
    for entry in manifest["rpc_controls"]:
        actual = re.findall(r"^func (Test\w+)\(", (packet / entry["retained"]["path"]).read_text(), re.M)
        if actual != entry["test_names"]:
            raise RuntimeError("actual prepared RPC test declarations differ")
        all_names.extend(actual)
    if len(all_names) != 9 or len(set(all_names)) != 9:
        raise RuntimeError("prepared RPC control set differs")
    _, _, previous = module.retained_qualification(packet)
    status = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"], text=True, timeout=30)
    for line in status.splitlines():
        if not line[3:].startswith(args.packet.rstrip("/") + "/"):
            raise RuntimeError("source preparation includes a path outside its declared packet")
    result = {"schema": "otzaria.original-import-generation-source-admission/1", "status": "PASS",
              "head": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True, timeout=30).strip(),
              "manifest_sha256": args.manifest_sha256, "admission": admission,
              "new_python_syntax": syntax, "original_swift_generator_paths_verified": corresponding,
              "historical_artifact_authenticated": previous, "prepared_rpc_cases": all_names,
              "generation_executed": False, "compilation_executed": False, "rpc_controls_executed": False,
              "scope": "Source closure, original input correspondence, prior artifact integrity and new script syntax only."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "manifest_sha256": args.manifest_sha256,
                      "indexed_control_inputs": admission["control_inputs"]["files"],
                      "original_generator_paths": len(corresponding), "prepared_new_cases": len(all_names),
                      "generation_executed": False, "result_sha256": module.sha(args.output)}))

if __name__ == "__main__":
    main()
