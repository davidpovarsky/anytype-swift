#!/usr/bin/env python3
"""Fixed source preflight and exec-only launch; no child manager, retry, or grant."""
import sys
sys.dont_write_bytecode = True
import hashlib
import os
from pathlib import Path
import stat

ROOT = Path("/mnt/development/projects/evidence/pinkha-wave2-sharing-role3-component-20261128")
PREPARED = ROOT / "prepared"
CALLER_SHA256 = "3ec0fd8ac7ae23a4c20e7a315c1b2ec83038dbfec98fc9f46b4ffcd6b7dab80e"
PINS = (
    ("run_shared_three_source2.py", 22367, CALLER_SHA256),
    ("owned_swift_commands_original.py", 9527, "f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56"),
    ("input-manifest.original.json", 4893, "b3d739b25605697acbf41a4ce97cd7dc0e9f125acc25e9cb774eaadab610dd66"),
    ("route-plan.original.json", 7159, "9b68fce7d225973e767f262fdabeca2aa9b0e1854d1079e7d09c60d1879c247c"),
)
if Path(__file__).resolve() != PREPARED / "launch_shared_three_source2.py" or ROOT.resolve() != ROOT:
    raise SystemExit("fixed physical launch location mismatch")
if any(value.startswith("--expected-controller-sha256") for value in sys.argv[1:]):
    raise SystemExit("caller identity is fixed by this launcher")
for relative, expected_size, expected_sha in PINS:
    path = PREPARED / relative
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or path.resolve() != path:
        raise SystemExit("physical immutable launch input required")
    raw = path.read_bytes()
    if len(raw) != expected_size or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise SystemExit("immutable launch input mismatch: " + relative)
os.chdir(ROOT)
os.execv("/usr/bin/python3", ["/usr/bin/python3", "-B", str(PREPARED / "run_shared_three_source2.py"),
                            "--expected-controller-sha256", CALLER_SHA256, *sys.argv[1:]])
