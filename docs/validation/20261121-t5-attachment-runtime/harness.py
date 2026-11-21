"""Preserve actual local controller execution and exact inputs; no native execution."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

control = Path(__file__).resolve().parents[3]
evidence = Path(__file__).resolve().parent
inputs = [
    "Tools/PinkhaNativeDerived/attachment_runtime.py",
    "Tools/PinkhaNativeDerived/build_t5_r15_runtime.py",
    "Tools/PinkhaNativeDerived/test_attachment_runtime.py",
    "Tools/PinkhaNativeDerived/build_custom_heart.py",
    "Tools/PinkhaNativeDerived/run_t5_native_attachment.py",
    "Tools/PinkhaNativeDerived/run_t5_pairs_ci.py",
    "Tools/PinkhaNativeDerived/run_t5_coverage_ci.py",
    "Tools/PinkhaNativeDerived/r15_runtime_go.py",
    "docs/validation/20261119-t5-native-attachment/generated/native-heart-integration.patch",
    "docs/validation/20261119-t5-native-attachment/generated/native-heart-integration.json",
]
def hashes():
    return {name: hashlib.sha256((control / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in inputs}
before = hashes()
started = time.time()
argv = [sys.executable, "-B", str(control / "Tools/PinkhaNativeDerived/test_attachment_runtime.py")]
run = subprocess.run(argv, cwd=control, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=60)
after = hashes()
log = evidence / "controller-tests.log"
log.write_bytes(run.stdout)
passed = run.returncode == 0 and before == after and b"Ran 15 tests in " in run.stdout and run.stdout.rstrip().endswith(b"OK")
receipt = dict(status="PASS_CONTROLLER_CONTROLS" if passed else "FAIL",
               command=argv, exit_code=run.returncode, methods=15 if passed else None,
               wall_seconds=time.time() - started, platform=platform.platform(), python=sys.version,
               source_hash_normalization="Git LF text bytes", source_before=before, source_after=after,
               sources_unchanged=before == after, log_sha256=hashlib.sha256(run.stdout).hexdigest(),
               native_invocations=0, apple_runtime="NOT_RUN", simulator="NOT_RUN")
(evidence / "controller-result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf8")
print(json.dumps({k: v for k, v in receipt.items() if k not in {"source_before", "source_after", "command", "python"}}))
raise SystemExit(0 if passed else 1)
