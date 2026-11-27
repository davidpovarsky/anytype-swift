"""Read-only selected-source proof after the common product admission.

This does not admit an App, its source, Native/SDK inputs or Products. Callers
must supply the nativeCompilationProof pin from the already admitted actual
producer and a literal reviewed source-hash map. The exact existing RTL
compiler-witness validator is reused without changing its function body.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
from types import SimpleNamespace

RTL_PROFILE_SHA256 = "80ebc56005110ee78615322f56b876b5b6fd4fae23975b86d249ae05ebcac8ea"
WITNESS_FUNCTIONS = ("sha", "_pinned_bytes", "source_contract")


def require(value, message):
    if not value:
        raise ValueError(message)


def verify_native_compiler_sources(app, *, source_commit, native_compilation_proof,
                                   expected_sources, rtl_profile_path):
    """Return selected AnytypeTests witnesses, never execution/acceptance credit.

    expected_sources is the caller profile's fixed {repository_path: sha256}.
    It is not a command-line or environment source override. The common
    qualifier remains responsible for the complete frozen source and producer.
    """
    app, profile = Path(app), Path(rtl_profile_path)
    require(app.is_absolute() and app.resolve() == app and app.is_dir() and not app.is_symlink(),
            "Canonical already-admitted source root required")
    require(re.fullmatch(r"[0-9a-f]{40}", source_commit or "") is not None,
            "Exact already-admitted source commit required")
    require(profile.is_absolute() and profile.resolve() == profile and profile.is_file() and not profile.is_symlink(),
            "Canonical reviewed RTL witness validator required")
    raw = profile.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == RTL_PROFILE_SHA256, "Original reviewed witness validator changed")
    require(isinstance(expected_sources, dict) and expected_sources
            and all(isinstance(path, str) and isinstance(value, str)
                    and re.fullmatch(r"[0-9a-f]{64}", value) is not None
                    for path, value in expected_sources.items()), "Explicit reviewed selected source hashes required")
    selected = dict(expected_sources)
    paths = [PurePosixPath(path) for path in selected]
    require(all(not path.is_absolute() and ".." not in path.parts and str(path) in selected
                and path.suffix == ".swift" for path in paths)
            and len({path.casefold() for path in selected}) == len(selected),
            "Unique canonical relative Swift sources required")
    git = ["git", "-C", str(app)]
    require(subprocess.check_output(git + ["rev-parse", "HEAD"], timeout=60).decode().strip() == source_commit
            and not subprocess.check_output(git + ["status", "--porcelain"], timeout=60).strip(),
            "Already-admitted source must remain the exact clean commit")
    tracked = subprocess.check_output(git + ["ls-files", "-z"], timeout=60).decode().split("\0")
    for relative, expected in selected.items():
        matches = [name for name in tracked if name.casefold() == relative.casefold()]
        path = app / relative
        require(len(matches) == 1 and path.is_file() and not path.is_symlink()
                and path.resolve().is_relative_to(app) and (app / matches[0]).samefile(path),
                "Selected source is absent, aliased or case-colliding: " + relative)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                "Reviewed selected source bytes changed: " + relative)

    text = raw.decode("utf-8")
    body = ast.parse(text).body
    functions = []
    for name in WITNESS_FUNCTIONS:
        nodes = [node for node in body if isinstance(node, ast.FunctionDef) and node.name == name]
        require(len(nodes) == 1, "Exact original witness declaration required: " + name)
        functions.append(nodes[0])

    def declared_contract(actual):
        require(Path(actual) == app, "Selected source root changed inside original witness check")
        return {"kind": "source-bound-native-compiler-selection", "source_hashes": selected}

    namespace = dict(Path=Path, hashlib=hashlib, json=json, re=re, shlex=shlex,
                     core=SimpleNamespace(require=require), TARGET="AnytypeTests", declared_contract=declared_contract)
    # These three function nodes are the exact pinned original source. No
    # top-level module body, imports, runner, selector or test body is executed.
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(profile), "exec"), namespace)
    result = namespace["source_contract"](app, source_commit=source_commit,
                                           native_compilation_proof=native_compilation_proof)
    require(result["source_hashes"] == selected and result["tests_executed"] == 0,
            "Original selected-source witness scope changed")
    return dict(result, witness_validator_sha256=RTL_PROFILE_SHA256,
                product_admission_performed=False, application_execution_performed=False)
