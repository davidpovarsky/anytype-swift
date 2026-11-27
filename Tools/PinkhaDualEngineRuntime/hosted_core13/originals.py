"""Load pinned original Python controls; never copy or project Swift tests.

The old Mac entry points remain closed. Only the original declarations needed
by the separately admitted same-job runtime are installed here. Their source
bytes, decorators and AST bodies are retained without modification.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import copy
from enum import Enum
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from types import ModuleType, SimpleNamespace

PIN_MANIFEST_SHA256 = "9a24ccea1e7d6568727e2bb2b28e27a5926d653f6b8dfbf037ca7ed658946034"
CORE_ROOT = "Tools/CurrentAppleValidation/combined_heart_semantics/wave2/"
SHARED_PATH = "Tools/CurrentAppleValidation/combined_heart_semantics/build15/combined_heart_semantics_current.py"
HOST_PATH = CORE_ROOT + "native-core-hosted/combined_host_acceptance_app15.py"
CORE_PATH = CORE_ROOT + "native-core-hosted/native_core_hosted_profile.py"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


class Originals:
    def __init__(self, source):
        self.source = Path(source)
        require(self.source.is_absolute() and self.source.resolve() == self.source
                and self.source.is_dir(), "Exact physical original source root required")
        manifest_path = Path(__file__).with_name("original_sources.json")
        data = manifest_path.read_bytes()
        require(sha(data) == PIN_MANIFEST_SHA256, "Original control source manifest changed")
        self.manifest = json.loads(data)
        require(self.manifest["schema"] == "pinkha-hosted-core13-original-control-sources-v1",
                "Unknown original control source manifest")
        self.sources = {}
        self.proof = {"manifestSHA256": PIN_MANIFEST_SHA256,
                      "originalReviewedSource": self.manifest["reviewedSource"],
                      "files": {}, "declarations": [], "swiftTestBodiesCopied": False}
        self.modules = {}
        self.runtime_binding = None
        for relative, pin in self.manifest["files"].items():
            path = self.source / relative
            require(path.is_file() and not path.is_symlink() and path.resolve() == path,
                    "Original control source is missing or aliased: " + relative)
            raw = path.read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            require(len(raw) == pin["bytes"] and sha(raw) == pin["sha256"]
                    and blob == pin["gitBlob"], "Original control bytes changed: " + relative)
            self.sources[relative] = raw
            self.proof["files"][relative] = dict(pin)

    def _module(self, name, path, bindings=None):
        require(name not in sys.modules, "A foreign module already owns original control name: " + name)
        module = ModuleType(name)
        module.__file__ = str(self.source / path)
        module.__dict__.update({
            "ast": ast, "contextmanager": contextmanager, "copy": copy,
            "Enum": Enum, "hashlib": hashlib, "json": json, "os": os,
            "Path": Path, "PurePosixPath": PurePosixPath, "plistlib": plistlib,
            "re": re, "shutil": shutil, "signal": signal, "stat": stat,
            "subprocess": subprocess, "sys": sys, "time": time,
        })
        module.__dict__.update(bindings or {})
        sys.modules[name] = module
        self.modules[name] = module
        return module

    def full(self, name, path):
        module = self._module(name, path)
        exec(compile(self.sources[path], module.__file__, "exec"), module.__dict__)
        self.proof["declarations"].append({"path": path, "scope": "ENTIRE_ORIGINAL_MODULE",
                                           "sha256": sha(self.sources[path])})
        return module

    def selected(self, name, path, declarations, *, bindings=None, methods=None):
        text = self.sources[path].decode()
        tree = ast.parse(text)
        nodes, observations = [], []
        for wanted in declarations:
            found = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                     and node.name == wanted]
            require(len(found) == 1, "One exact original declaration required: " + wanted)
            node = found[0]
            if isinstance(node, ast.ClassDef) and methods is not None:
                selected = []
                for method in methods:
                    matching = [part for part in node.body if isinstance(part, ast.FunctionDef)
                                and part.name == method]
                    require(len(matching) == 1, "Exact original method required: " + method)
                    selected.append(matching[0])
                    observations.append(self._observation(path, text, matching[0], wanted + "." + method))
                # The original method nodes, including every decorator/default,
                # are unchanged. Only unrelated Mac/T5 entry methods are absent.
                node = copy.deepcopy(node)
                node.body = selected
            else:
                observations.append(self._observation(path, text, node, wanted))
            nodes.append(node)
        module = self._module(name, path, bindings)
        future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
        body = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
        exec(compile(body, module.__file__, "exec"), module.__dict__)
        self.proof["declarations"].extend(observations)
        return module

    @staticmethod
    def _observation(path, text, node, qualified_name):
        first = min([node.lineno, *[item.lineno for item in node.decorator_list]])
        data = "".join(text.splitlines(keepends=True)[first - 1:node.end_lineno]).encode()
        return {"path": path, "declaration": qualified_name, "firstLine": first,
                "lastLine": node.end_lineno, "bytes": len(data), "sha256": sha(data),
                "originalASTNodeUnchanged": True}

    def install(self):
        self.gate = self.full("receipt_admission", "Tools/MiniApps/receipt_admission.py")
        self.preparation = self.full("core13_original_receipt_preparation", "Tools/MiniApps/prepare_receipt_input.py")
        self.products = self.selected("core13_original_products", "Tools/MiniApps/run_receipt_acceptance.py",
            ("bundle_executable", "entries", "resolve_product"), bindings={"gate": self.gate})
        self.core_declarations = self.full("wave15_core_profile", "Tools/Hanlin/wave15_core_profile.py")
        self.host_results = self.selected("run_host_tests", "Tools/Hanlin/run_host_tests.py",
            ("HostTestProfile", "require", "test_cases", "validate_results"))
        self.enumeration = self.selected("shared_editor_existing_build", "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py",
            ("enumerated_identifiers",), bindings={"host": self.host_results})
        self.witness = self.full("native_compiler_witness", CORE_ROOT + "native_compiler_witness.py")
        self.native_core = self.full("native_core_hosted_profile", CORE_PATH)
        self.paths = self.selected("core13_original_product_paths", "Tools/CurrentAppleValidation/contracts.py",
            ("require", "product_path"))
        self.shared = self.selected("core13_original_shared", SHARED_PATH,
            ("require", "sha", "digest", "raw", "decode", "write", "write_bytes", "error",
             "inventory", "pinned", "Commands", "product_integrity", "bind_descriptor"),
            bindings={"FLOOR": 2 * 1024 ** 3, "common": self.paths})
        self.carriers = self.selected("core13_original_code_carriers", "Tools/PinkhaSimulatorGate/run_ui27.py",
            ("code_carriers",), bindings={"digest": self.shared.digest})
        self.settings = self.selected("core13_original_simulator_setting", "Tools/PinkhaSimulatorGate/t5_native_ui_r08.py",
            ("actual_setting",), bindings={"core": self.core_declarations})
        self.signals = self.selected("core13_original_signals", "Tools/Hanlin/host_command.py",
            ("CommandCancelled", "cancellation_signals"))
        bindings = {"shared": self.shared, "native_core": self.native_core,
                    "NATIVE": "AnytypeTests", "UI": "PinkhaStage1AcceptanceUITests",
                    "SUPPORT": Path("Library/Application Support")}
        for name in ("require", "raw", "decode", "write", "write_bytes", "sha", "digest"):
            bindings[name] = getattr(self.shared, name)
        self.host_functions = self.selected("core13_original_host_functions", HOST_PATH,
            ("invocation_selectors", "scoped_descriptor", "exact_enumeration",
             "host_validation_module", "observe_owned_groups"), bindings=bindings)
        bindings.update({name: getattr(self.host_functions, name) for name in
                         ("invocation_selectors", "scoped_descriptor", "exact_enumeration", "host_validation_module")})
        self.host = self.selected("core13_original_host_methods", HOST_PATH, ("Consumer",),
            methods=("__init__", "command", "container", "installed", "create", "appearance", "stage", "preserve"),
            bindings=bindings)
        self.helpers = {"run_ui27": self.carriers, "t5_native_ui_r08": self.settings}
        return self

    def configure_runtime(self, *, runtime, bundle_id):
        require(self.runtime_binding is None, "Original runtime may be bound only once before device creation")
        binding = {"RUNTIME": runtime["identifier"], "OS_VERSION": runtime["version"],
                   "OS_BUILD": runtime["buildversion"], "BUNDLE": bundle_id}
        require(all(isinstance(value, str) and value for value in binding.values()), "Incomplete observed runtime binding")
        for key, value in binding.items():
            setattr(self.shared, key, value)
        self.runtime_binding = binding
        self.proof["sameHostRuntimeBinding"] = dict(binding)

    def unchanged(self):
        for relative, raw in self.sources.items():
            path = self.source / relative
            require(path.resolve() == path and not path.is_symlink() and path.read_bytes() == raw,
                    "Loaded original control source changed: " + relative)
        if self.runtime_binding is not None:
            require({key: getattr(self.shared, key) for key in self.runtime_binding} == self.runtime_binding,
                    "Observed same-host runtime binding changed")

    def close(self):
        for name, module in reversed(list(self.modules.items())):
            if sys.modules.get(name) is module:
                del sys.modules[name]
