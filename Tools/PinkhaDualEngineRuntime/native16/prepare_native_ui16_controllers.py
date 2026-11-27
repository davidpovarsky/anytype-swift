#!/usr/bin/env python3
"""Prepare additive NativeUI controllers without changing the original profiles.

No compiler or simulator is invoked. A separately reviewed exact common app
qualifier and its real successful admission are mandatory at execution.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ORIGINALS = {
    "build_prebuilt_native_ui8ac.py": "e6c4c506cf893b2dc495fdc4b76c686f09a108c9980e05d19590d92acab804f9",
    "run_prebuilt_native_ui8ac.py": "18c7cc5722a856782d454a11db11ea172c9d718cecd17cd6dc54ffcc2a256d2b",
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def functions(value):
    text = value.decode()
    return {node.name: ast.get_source_segment(text, node) for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def substitute(value, changes):
    text = value.decode()
    inverse = []
    for old, new in changes:
        require(text.count(old) == 1, "Exact original replacement must occur once")
        text = text.replace(old, new)
        positions = [m.start() for m in re.finditer(re.escape(new), text)]
        require(len(positions) == 1, "Exact replacement must have one reversible position")
        inverse.append({"old": old, "new": new, "position": positions[0]})
    restored = text
    for row in reversed(inverse):
        p = row["position"]
        require(restored[p:p + len(row["new"])] == row["new"], "Inverse position differs")
        restored = restored[:p] + row["old"] + restored[p + len(row["new"]):]
    require(restored.encode() == value, "All original controller bytes must be recoverable")
    ast.parse(text)
    return text.encode(), inverse


def prepare(original_root, profile_path, output):
    original_root, profile_path, output = map(Path, (original_root, profile_path, output))
    require(original_root.is_absolute() and original_root.resolve() == original_root
            and profile_path.is_absolute() and profile_path.resolve() == profile_path
            and not profile_path.is_symlink(), "Canonical original inputs required")
    require(output.is_absolute() and output.parent.resolve() == output.parent
            and output.parent.is_dir() and not output.exists() and not output.is_symlink(),
            "Fresh canonical controller output required")
    profile = profile_path.read_bytes()
    require(len(profile) < 128 * 1024, "Bounded NativeUI profile required")
    ast.parse(profile)
    profile_sha = sha(profile)
    loader = '''def native8ac_module():
    path = Path(__file__).resolve().with_name("native16_profile.py")
    sys.dont_write_bytecode = True
    original = path.read_bytes()
    require(hashlib.sha256(original).hexdigest() == "PROFILE_SHA",
            "exact_reviewed_shared_app_NativeUI_profile_required")
    cached = getattr(native8ac_module, "qualified", None)
    if cached is not None:
        return cached
    module = type(sys)("qualified_native16")
    module.__file__ = str(path)
    exec(compile(original, str(path), "exec"), module.__dict__)
    native8ac_module.qualified = module
    return module'''.replace("PROFILE_SHA", profile_sha)
    files = {"native16_profile.py": profile}
    receipts = {}
    for name, expected in ORIGINALS.items():
        path = original_root / name
        require(path.resolve() == path and not path.is_symlink(), "Canonical original controller required")
        original = path.read_bytes()
        require(sha(original) == expected, "Original controller bytes changed: " + name)
        original_defs = functions(original)
        arguments = ('    parser.add_argument("--shared-admission", type=Path, required=True)\n'
                     '    parser.add_argument("--shared-admission-sha256", required=True)\n'
                     '    parser.add_argument("--shared-controller-sha256", required=True)\n')
        if name.startswith("run_"):
            arguments += '    parser.add_argument("--native-ui-proof-sha256", required=True)\n'
        arguments += '    args = parser.parse_args()\n    native8ac_module().configure(args)'
        changes = [(original_defs["native8ac_module"], loader),
                   ("    args = parser.parse_args()", arguments)]
        if name.startswith("build_"):
            old = '    require(code == 0 and stopped is None, "original_native_ui_runner_build_failed")'
            changes.append((old, old + '\n    current8ac.seal_ui_build(output, record, Path(__file__).resolve())'))
        candidate, inverse = substitute(original, changes)
        after_defs = functions(candidate)
        preserved = sorted(set(original_defs) - {"native8ac_module", "main"})
        require(set(original_defs) == set(after_defs)
                and all(original_defs[key] == after_defs[key] for key in preserved),
                "Original command/descriptor/result functions changed")
        output_name = name.replace("ui8ac.py", "ui16.py")
        files[output_name] = candidate
        receipts[output_name] = {"originalSHA256": expected, "candidateSHA256": sha(candidate),
                                "changes": inverse, "unchangedDefinitions": preserved,
                                "inverseRestoresEveryOriginalByte": True}
    receipt = {
        "schema": "pinkha-nativeui-shared-app-controller-preparation-v1",
        "status": "PREPARED_NATIVEUI_CONTROLLERS_NOT_APP_OR_UI_ACCEPTANCE",
        "nativeUIProfileSHA256": profile_sha, "controllers": receipts,
        "allowedExecutionStages": ["sharing-owner", "archive"],
        "sourcePinAuthority": "Exact reviewed shared controller APP16_SOURCE plus its immutable successful producer admission",
        "sharedProducerAdmitted": False, "builds": 0, "tests": 0, "nativeCalls": 0,
        "originalProfilesModified": False,
        "nextIntegratedSource": "BLOCKED_UNTIL_SEPARATELY_REVIEWED_COMMON_QUALIFIER_AND_ACTUAL_BUILD_RECEIPT",
        "files": {name: {"bytes": len(value), "sha256": sha(value)} for name, value in files.items()},
    }
    files["nativeui16-materialization.json"] = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
    output.mkdir(mode=0o700)
    for name, value in files.items():
        with (output / name).open("xb") as stream:
            stream.write(value)
        (output / name).chmod(0o600)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-controller-root", type=Path, required=True)
    parser.add_argument("--native-ui-profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.original_controller_root, args.native_ui_profile, args.output)
    print(json.dumps({name: result[name] for name in ("status", "nativeUIProfileSHA256", "builds", "tests")}, sort_keys=True))


if __name__ == "__main__":
    main()
