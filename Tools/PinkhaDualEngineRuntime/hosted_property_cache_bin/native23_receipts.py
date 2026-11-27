"""Reuse the exact approved third-compiler reader; perform file reads only.

No historical Native23 runtime, configure(), account, simulator or compiler
entry is called. The unchanged source/profile/projection/FileList guards remain
required even though this profile executes only AnytypeTests methods.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

from originals import require

PREFIX = "Tools/PinkhaDualEngineRuntime/hosted_native23/"
READERS = (
    ("control", "control.py", "efc8291b7d5e7df7f3381df3ed61ba1e75cae209e8d86e8d433b187d117c19f2"),
    ("native23_inputs", "native23_inputs.py", "87276b53b378c4d305f782d5664106c76331276b78eb413795042af98e5f0a9d"),
    ("cache_bin_original_native23_reader_definitions", "run.py", "27576bb6c8ee8bebe618f05bcaee95e7c0fa21b2090d0f449e9b1593961d82fa"),
)


def load_pinned(path, name, digest, originals):
    path = Path(path)
    require(path.is_file() and path.resolve() == path and not path.is_symlink()
            and hashlib.sha256(path.read_bytes()).hexdigest() == digest and name not in sys.modules,
            "Exact approved Native23 reader source and unique module identity required")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    originals.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Native23Receipts:
    def __init__(self, control, source, context, plan, owner, originals):
        self.control, self.source = Path(control), Path(source)
        self.context, self.plan, self.owner, self.originals = context, plan, owner, originals
        loaded = [load_pinned(self.control / PREFIX / path, name, digest, originals)
                  for name, path, digest in READERS]
        self.reader_control, self.inputs, definitions = loaded
        require(definitions.CORE_ADMISSION_SHA == "fd0748fbbf7cef165e7b0a4e837473deeb56eb9efb11bf89d96ddbee2e102593"
                and definitions.CORE_ORIGINALS_SHA == "adc29fa18b2bd64dce6bca3cf6ded88ae6203246a12fa7e781229fda41b1f326",
                "Approved original shared reader lineage changed")
        self.helper = load_pinned(self.control / self.inputs.HELPER,
            "cache_bin_original_native23_compiler_helper", self.inputs.HELPER_SHA256, originals)
        self.profile, self.declarations = self.reader_control.selected_profile(self.source)
        before_modules = set(sys.modules)
        dependencies = definitions.load_profile_dependencies(self.source, self.profile)
        for name in set(sys.modules).difference(before_modules):
            module = sys.modules[name]
            path = getattr(module, "__file__", None)
            if path and Path(path).is_relative_to(self.source):
                originals.modules[name] = module
        # Original check_source/projected_files use only the unchanged shared
        # file reader and exact source qualifiers. No runtime state is bound.
        self.profile._state = {"shared": originals.shared, **dependencies}
        require(self.profile.READY_FOR_EXECUTION is False and self.profile.FUTURE_SOURCE_COMMIT is None,
                "Historical Native23 runtime must remain closed")
        self.observed = self._read()

    def _read(self):
        for _, path, digest in READERS:
            value = self.control / PREFIX / path
            require(value.resolve() == value and not value.is_symlink()
                    and hashlib.sha256(value.read_bytes()).hexdigest() == digest,
                    "Approved Native23 reader changed during same-job observation")
        self.profile.check_source(self.source)
        proof, record, inventory = self.inputs.admit(self.context, self.control, self.plan,
            self.owner, self.helper, self.originals.shared, self.profile)
        require(proof["producerInputCounts"] == {"native": 61, "stage1UI": 10, "native23UI": 2}
                and proof["runtimeAcceptance"] is False,
                "Actual61 App, 10 Stage1 and two separate Native23 compiler inputs are all required")
        return {"proof": proof, "record": record, "inventory": inventory}

    def proof(self):
        return {"actualCompiler": self.observed["proof"], "originalSourceDeclarations": self.declarations,
                "readerSources": [{"path": str(self.control / PREFIX / path), "sha256": digest}
                                  for _, path, digest in READERS],
                "native23RuntimeExecuted": False}

    def recheck(self):
        """No Git, subprocess, simulator, owner signal or process-group probe."""
        require(self._read() == self.observed,
                "Original shared and third compiler receipts/products changed during App tests")
        return self.proof()
