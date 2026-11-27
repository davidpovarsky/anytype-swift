"""Load pinned original Python controls; never copy or project Swift tests.

The old Mac entry points remain closed. Only the original declarations needed
by the separately admitted same-job runtime are installed here. Their source
bytes, decorators and AST bodies are retained without modification.
"""
from __future__ import annotations

import ast
import base64
from datetime import datetime, timezone
import uuid
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

PIN_MANIFEST_SHA256 = "fccdd0205c1f9047241754fe739994f7baa92def857fa8495faf3fec83abb10c"
CORE_ROOT = "Tools/CurrentAppleValidation/combined_heart_semantics/wave2/"
SHARED_PATH = "Tools/CurrentAppleValidation/combined_heart_semantics/build15/combined_heart_semantics_current.py"
HOST_PATH = CORE_ROOT + "native-renderer-hosted/combined_host_acceptance_app15.py"
CORE_PATH = CORE_ROOT + "native-renderer-hosted/native_core_hosted_profile.py"
RTL_PATH = CORE_ROOT + "rtl-current-editor-profile/rtl_hosted_profile.py"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


class StageResultWrites:
    """Preserve only the three selected original stage outcomes before receipt IO.

    The isolated Consumer namespace receives this callable. Original shared
    writes, other modules, every Consumer AST body and every command stay exact.
    A failed write cannot replace the already observed original stage cause.
    """
    def __init__(self, original_write, error_formatter, output):
        self.original_write, self.error = original_write, error_formatter
        root = Path(output) / "evidence/lanes"
        self.paths = frozenset((root / "focus-lifecycle/focus-lifecycle/result.json",
                                root / "editor/preparation/result.json",
                                root / "editor/ui/result.json"))
        self.first_failure = None
        self.io_failures = []

    def __call__(self, path, value):
        selected = Path(path) in self.paths and isinstance(value, dict)
        if selected and value.get("status") == "FAIL":
            first = value.get("firstFailure")
            if first is None and value.get("errors"):
                first = value["errors"][0]
            if self.first_failure is None and isinstance(first, dict):
                self.first_failure = copy.deepcopy(first)
        try:
            return self.original_write(path, value)
        except BaseException as error:
            if selected:
                self.io_failures.append({"path": str(path), **self.error(error)})
            raise


class Originals:
    def __init__(self, source):
        self.source = Path(source)
        require(self.source.is_absolute() and self.source.resolve() == self.source
                and self.source.is_dir(), "Exact physical original source root required")
        manifest_path = Path(__file__).with_name("original_sources.json")
        data = manifest_path.read_bytes()
        require(sha(data) == PIN_MANIFEST_SHA256, "Original control source manifest changed")
        self.manifest = json.loads(data)
        require(self.manifest["schema"] == "pinkha-warm-focus-editor-original-control-sources-v1",
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
            "base64": base64, "datetime": datetime, "timezone": timezone, "uuid": uuid,
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

    def project(self, name, path, *, bindings=None, constants=None, functions=None):
        """Select unchanged top-level original nodes with finite explicit globals.

        Imports are supplied by this isolated namespace; the functions, data
        assignments, decorators and defaults are original AST nodes. This lets
        source-only Git reads use the owned 60-second command adapter without
        globally replacing subprocess or changing an original validator body.
        """
        text = self.sources[path].decode()
        tree = ast.parse(text)
        module = self._module(name, path, bindings)
        nodes = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if functions is None or node.name in functions:
                    nodes.append(node)
                    self.proof["declarations"].append(self._observation(path, text, node, node.name))
            elif isinstance(node, ast.Assign):
                require(all(isinstance(target, ast.Name) for target in node.targets),
                        "Only exact original named module bindings are supported")
                names = {target.id for target in node.targets}
                if constants is None or names <= set(constants):
                    nodes.append(node)
                    raw = "".join(text.splitlines(keepends=True)[node.lineno - 1:node.end_lineno]).encode()
                    self.proof.setdefault("moduleAssignments", []).append({"path": path,
                        "names": sorted(names), "sha256": sha(raw), "originalASTNodeUnchanged": True})
        if functions is not None:
            require({node.name for node in nodes if isinstance(node, ast.FunctionDef)} == set(functions),
                    "Exact finite original function closure differs")
        if constants is not None:
            require({target.id for node in nodes if isinstance(node, ast.Assign) for target in node.targets}
                    == set(constants), "Exact finite original constant closure differs")
        future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
        body = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
        exec(compile(body, module.__file__, "exec"), module.__dict__)
        return module

    def install(self):
        self.gate = self.full("receipt_admission", "Tools/MiniApps/receipt_admission.py")
        self.preparation = self.full("warm_original_receipt_preparation", "Tools/MiniApps/prepare_receipt_input.py")
        self.products = self.selected("warm_original_products", "Tools/MiniApps/run_receipt_acceptance.py",
            ("bundle_executable", "entries", "resolve_product"), bindings={"gate": self.gate})
        self.core_declarations = self.full("wave15_core_profile", "Tools/Hanlin/wave15_core_profile.py")
        self.host_results = self.selected("run_host_tests", "Tools/Hanlin/run_host_tests.py",
            ("HostTestProfile", "require", "test_cases", "validate_results"))
        self.enumeration = self.selected("shared_editor_existing_build", "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py",
            ("enumerated_identifiers",), bindings={"host": self.host_results})
        self.paths = self.selected("warm_original_product_paths", "Tools/CurrentAppleValidation/contracts.py",
            ("require", "product_path"))
        self.shared = self.selected("warm_original_shared", SHARED_PATH,
            ("require", "sha", "digest", "raw", "decode", "write", "write_bytes", "error",
             "inventory", "pinned", "Commands", "product_integrity", "bind_descriptor"),
            bindings={"FLOOR": 2 * 1024 ** 3, "common": self.paths,
                "MANIFEST": "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b",
                "VERSION": "pinkha-dual-runtime-v1-8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"})
        self.results = self.selected("warm_original_method_results", "Tools/PinkhaSimulatorGate/validate_release.py",
            ("require", "method_results"))
        self.carriers = self.project("warm_original_ui_helpers", "Tools/PinkhaSimulatorGate/run_ui27.py",
            constants=("SMOKE", "DEFAULT_METHOD_SECONDS", "PROPERTIES_METHOD_SECONDS", "LONG_PROPERTIES_METHODS"),
            functions=("code_carriers", "selection_time_budget"),
            bindings={"digest": self.shared.digest, "method_results": self.results.method_results})
        self.settings = self.selected("warm_original_simulator_setting", "Tools/PinkhaSimulatorGate/t5_native_ui_r08.py",
            ("actual_setting",), bindings={"core": self.core_declarations})
        self.signals = self.selected("warm_original_signals", "Tools/Hanlin/host_command.py",
            ("CommandCancelled", "cancellation_signals"))
        self.ui_results = self.selected("warm_original_ui_results", "Tools/PinkhaSimulatorGate/t5_native_ui_evidence.py",
            ("require", "validate_selection"))
        self.host_functions = self.selected("warm_original_owned_observer", HOST_PATH,
            ("observe_owned_groups",), bindings={"shared": self.shared})
        return self

    def install_runtime(self, commands):
        from profile_binding import BoundSourceQueries, UnselectedRoute
        require(commands.is_open and not hasattr(self, "focus"), "One open original runtime binding required")
        queries = BoundSourceQueries(self.source, commands, self)
        self.focus = self.project("focus_lifecycle_profile", CORE_ROOT.replace("wave2/", "build16/") + "focus_lifecycle_profile.py",
            bindings={"host": self.host_results, "core": self.core_declarations,
                      "existing": self.enumeration, "subprocess": queries})
        unused = UnselectedRoute()
        self.wave15 = self.project("warm_original_wave15", "Tools/PinkhaSimulatorGate/run_wave15_acceptance.py",
            constants=("LANES", "HANLIN_LANES", "EDITOR_DEVICE_PREFERENCES_TIMEOUT_SECONDS"),
            functions=("require", "preparation_environment", "nonempty", "fixture_environment",
                       "validate_device_language", "source_methods"),
            bindings={"shared": self.carriers, "hanlin": unused, "hanlin_selection": unused})
        self.startup_profile = self.project("torah_ui_profile", CORE_ROOT + "torah-future/torah_ui_profile.py",
            bindings={"subprocess": queries})
        self.startup = self.project("torah_ui_consumer", CORE_ROOT + "torah_ui_consumer.py",
            bindings={"profile": self.startup_profile})
        bindings = {"shared": self.shared, "native_core": SimpleNamespace(HOSTED_LANES=frozenset()),
                    "torah_ui": self.startup, "NATIVE": "AnytypeTests", "UI": "PinkhaStage1AcceptanceUITests",
                    "SUPPORT": Path("Library/Application Support"),
                    "SWITCH": "PinkhaStage1AcceptanceUITests/testUnifiedEngineSwitchRetainsHeartDocumentAndColdReopen"}
        for name in ("require", "raw", "decode", "write", "write_bytes", "sha", "digest"):
            bindings[name] = getattr(self.shared, name)
        self.host_functions = self.selected("warm_original_host_functions", HOST_PATH,
            ("invocation_selectors", "scoped_descriptor", "exact_enumeration", "result_selection",
             "host_validation_module", "observe_owned_groups"), bindings=bindings)
        bindings.update({name: getattr(self.host_functions, name) for name in
            ("invocation_selectors", "scoped_descriptor", "exact_enumeration", "result_selection", "host_validation_module")})
        self.stage_result_writes = StageResultWrites(self.shared.write, self.shared.error, commands.cwd)
        bindings["write"] = self.stage_result_writes
        self.host = self.selected("warm_original_host_methods", HOST_PATH, ("Consumer",),
            methods=("__init__", "command", "container", "installed", "create", "appearance", "stage",
                     "read_private", "preserve", "wave"), bindings=bindings)
        self.helpers = {"run_ui27": self.carriers, "t5_native_ui_r08": self.settings,
                        "run_wave15_acceptance": self.wave15, "t5_native_ui_evidence": self.ui_results,
                        "type_preservation": unused, "focus_lifecycle_profile": self.focus}
        self.proof["finiteRuntimeBinding"] = {"lanes": ["focus-lifecycle", "editor"],
            "separateCoreRTLOrNativeUIInvoked": False, "sourceQueries": "original owned60s command barrier",
            "otherWave15Branches": "not selected; an accidental unsupported helper access fails closed"}
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
