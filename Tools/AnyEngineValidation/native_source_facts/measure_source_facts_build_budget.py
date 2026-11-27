#!/usr/bin/env python3
"""Metadata-only measured allowance for one incremental owned Host build.

Does not run Swift, alter cache/source/dependencies, or qualify any tests.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path("/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127")
CACHE = Path("/tmp/pinkha-w1-migration-swift-20261127")
TARGET = Path("/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127")
OUT = Path("/var/lib/pinkha-w1-functional-migration-20261127/source-facts-build-allocation1")
MIB = 1024**2
PRODUCTS = ["PinkhaAnyHost.o", "pinkha-any-host-probe", "libPinkhaAnyHost.a",
            "PinkhaAnyHostTests.so", "PinkhaAnyHostTests-test-runner"]
os.umask(0o077)
OUT.mkdir(mode=0o700, parents=True, exist_ok=False)
env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, env=env).strip()
assert head == "0925ff79df8f70be288f96ea117dbd7059e24219"
assert CACHE.is_symlink() and CACHE.resolve() == TARGET
rows = []
for name in PRODUCTS:
    path = CACHE / "out/Products/Debug-linux-aarch64" / name
    info = path.stat()
    rows.append({"path": str(path.relative_to(CACHE)), "bytes": info.st_size,
                 "allocatedBytes": info.st_blocks * 512})
total = sum(row["allocatedBytes"] for row in rows)
assert total == 178339840 and total < 176 * MIB
result = {"status": "PASS_MEASUREMENT_ONLY_NO_COMPILER_OR_NATIVE_EXECUTION", "measuredAt": time.time(),
          "sourceBaseCommit": head, "cachePath": str(CACHE), "physicalCachePath": str(TARGET),
          "affectedProductMetadata": rows, "affectedProductsAllocatedBytes": total,
          "incrementalBuildBudgetBytes": 256 * MIB,
          "developmentBudgetMiB": {"allAffectedProductReplacementUpper": 176, "objectsModulesIndex": 32,
                                   "compilerTemporary": 32, "slack": 16},
          "rootInitialHeadroomBytes": 32 * MIB, "rootControlOutputCapBytes": 16 * MIB,
          "rootRuntimeEmergencyFloorBytes": 2 * 1024**3,
          "developmentRuntimeEmergencyFloorBytes": 512 * MIB,
          "rootInitialRequiredBytes": 2 * 1024**3 + 32 * MIB,
          "developmentInitialRequiredBytes": 512 * MIB + 256 * MIB,
          "rootFreeBytes": shutil.disk_usage("/").free, "developmentFreeBytes": shutil.disk_usage(TARGET).free,
          "temporaryDirectoryPlacement": "new owned subdirectory inside physical development cache",
          "limits": ["One new Host source and three new Host test sources only; dependencies unchanged",
                     "No cache removal, full rebuild, index disable, resolution or accepted component rerun",
                     "Live storage floors and explicit owned-growth caps remain authoritative; estimate is not an acceptance result"]}
(OUT / "controller.py").write_bytes(Path(__file__).read_bytes())
path = OUT / "result.json"
path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
print(json.dumps({"status": result["status"], "result": str(path),
                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "rootFreeBytes": result["rootFreeBytes"], "developmentFreeBytes": result["developmentFreeBytes"],
                  "developmentInitialRequiredBytes": result["developmentInitialRequiredBytes"]}))
