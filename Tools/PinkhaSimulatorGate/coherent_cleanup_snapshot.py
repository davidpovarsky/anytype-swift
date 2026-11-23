"""Cleanup-only verification of a live, previously Git-admitted source map.

No persisted report can create this process-local snapshot. Normal admission
still calls the unchanged exact Git verifier; cleanup only rechecks its bytes.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import sys

from coherent_controller_sources import MAX_BATCH_BYTES, MAX_SOURCE_BYTES


def require(value, message):
    if not value:
        raise ValueError(message)


def loaded(control):
    control = Path(control).resolve()
    result = {}
    for name, module in tuple(sys.modules.items()):
        value = getattr(module, "__file__", None)
        if not value:
            continue
        raw = Path(value)
        path = raw.resolve()
        # Preserve the same repository-Python boundary as the admitted reader.
        if path.suffix != ".py" or not path.is_relative_to(control):
            continue
        require(raw.absolute() == path, "Loaded cleanup source uses an alias or symlink")
        relative = path.relative_to(control).as_posix()
        require(not any(x in relative for x in ("\n", "\r", "\0", ":")),
                "Loaded cleanup source path is ambiguous")
        result[name] = relative
    return result


def physical(control, relative):
    path = control / relative
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute()
            and path.resolve() == path and path.is_relative_to(control)
            and path.is_file() and not path.is_symlink()
            and path.stat().st_size <= MAX_SOURCE_BYTES,
            "Admitted cleanup source is missing, escaped, aliased or unbounded")
    return path.read_bytes()


@dataclass(frozen=True)
class Snapshot:
    control: Path
    source_sha: str
    identity: tuple
    files: tuple
    module_names: tuple
    required_modules: tuple

    def verify(self, identity):
        require(tuple(sorted(identity.items())) == self.identity,
                "Cleanup snapshot belongs to another live origin")
        expected = dict(self.files)
        actual = loaded(self.control)
        for name, path in self.required_modules:
            require(actual.get(name) == path, "Required canonical cleanup module is missing or foreign")
        for name, path in self.module_names:
            require(actual.get(name) == path, "Previously admitted loaded cleanup module changed")
        require(set(actual.values()) <= set(expected), "Cleanup loaded an unadmitted source")
        total = 0
        for relative, wanted in self.files:
            raw = physical(self.control, relative)
            total += len(raw)
            require(hashlib.sha256(raw).hexdigest() == wanted, "Admitted physical cleanup source changed")
        require(total <= MAX_BATCH_BYTES, "Cleanup source snapshot exceeds its admitted bound")
        return dict(status="EXACT_PRE_ADMITTED_CLEANUP_SOURCE_SNAPSHOT",
                    control_source_sha=self.source_sha, admitted_sources=len(expected),
                    loaded_source_paths=len(set(actual.values())), loaded_module_names=len(actual),
                    physical_bytes=total, git_subprocesses=0,
                    source_snapshot_sha256=self.digest())

    def digest(self):
        import json
        value = dict(control=str(self.control), source_sha=self.source_sha,
                     identity=list(self.identity), files=list(self.files),
                     module_names=list(self.module_names), required_modules=list(self.required_modules))
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def admit(control, source_sha, identity, git_admitted, previous=None, *, required_modules):
    """Called only with the just-returned exact control_sources() result."""
    control = Path(control).resolve()
    require(re.fullmatch(r"[0-9a-f]{40}", source_sha)
            and isinstance(git_admitted, dict) and 5 <= len(git_admitted) <= 256
            and all(isinstance(k, str) and isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v)
                    for k, v in git_admitted.items()),
            "Bounded exact live Git admission is required")
    require(isinstance(required_modules, dict) and required_modules
            and all(isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9_]*", name)
                    and isinstance(path, str) and path in git_admitted
                    for name, path in required_modules.items()),
            "Explicit canonical cleanup module requirements are missing")
    current = loaded(control)
    for name, path in required_modules.items():
        require(current.get(name) == path, "Required canonical cleanup module is missing or foreign")
    require(set(current.values()) == set(git_admitted), "Git admission differs from the actual loaded closure")
    pinned = dict(git_admitted)
    names = dict(current)
    if previous is not None:
        require(previous.control == control and previous.source_sha == source_sha
                and previous.identity == tuple(sorted(identity.items()))
                and previous.required_modules == tuple(sorted(required_modules.items())),
                "A cleanup snapshot cannot change its live origin")
        for path, wanted in previous.files:
            require(path in pinned and pinned[path] == wanted, "Earlier cleanup source admission was removed or changed")
        for name, path in previous.module_names:
            require(names.get(name) == path, "Earlier admitted module identity changed")
    snapshot = Snapshot(control, source_sha, tuple(sorted(identity.items())),
                        tuple(sorted(pinned.items())), tuple(sorted(names.items())),
                        tuple(sorted(required_modules.items())))
    snapshot.verify(identity)
    return snapshot
