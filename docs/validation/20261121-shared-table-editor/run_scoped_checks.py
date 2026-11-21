"""Run only the changed pure queue suite and parse the touched UIKit adapters.

The copied source and test bytes are hashed before/after. This does not execute
UIKit, the table handler, Heart, or Any native persistence on Windows.
"""
from pathlib import Path
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "build/shared-table-scoped-checks"
PKG = OUT / "package"
EVIDENCE = ROOT / "docs/validation/20261121-shared-table-editor"
SWIFT = Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swift.exe")
SWIFTC = SWIFT.with_name("swiftc.exe")
QUEUE = "Modules/PinkhaKit/Sources/PinkhaKit/Editor/PinkhaSerialTextEditQueue.swift"
QUEUE_TESTS = "Modules/PinkhaKit/Tests/PinkhaKitTests/Editor/PinkhaSerialTextEditQueueTests.swift"
UIKIT = [
    "Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/SimpleTable/Block/TextBlock/SimpleTablesTextBlockActionHandler.swift",
    "Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockActionHandler.swift",
    "AnyTypeTests/Pinkha/SimpleTableTextPersistenceTests.swift",
]
PATHS = [QUEUE, QUEUE_TESTS, *UIKIT]
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
OUT.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)
before = {p: digest(ROOT / p) for p in PATHS}
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
parse_command = [str(SWIFTC), "-frontend", "-parse", *[str(ROOT / p) for p in PATHS]]
parsed = subprocess.run(parse_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
(EVIDENCE / "swift-parse.log").write_bytes(parsed.stdout)
if parsed.returncode:
    print(parsed.stdout.decode("utf-8", errors="replace"))
    sys.exit(parsed.returncode)
for relative, category in [(QUEUE, "Sources/PinkhaKit"), (QUEUE_TESTS, "Tests/PinkhaKitTests")]:
    target = PKG / category / Path(relative).name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / relative, target)
    assert digest(target) == before[relative]
(PKG / "Package.swift").write_text(
    '// swift-tools-version: 6.0\nimport PackageDescription\n'
    'let package = Package(name: "PinkhaKit", targets: [\n'
    '    .target(name: "PinkhaKit"),\n'
    '    .testTarget(name: "PinkhaKitTests", dependencies: ["PinkhaKit"])\n'
    '])\n', encoding="utf-8", newline="\n")
command = [str(SWIFT), "test", "--package-path", str(PKG), "--jobs", "2",
           "--filter", "PinkhaSerialTextEditQueueTests"]
log = EVIDENCE / "queue-swift-test.log"
timed_out = False
with log.open("wb") as stream:
    run = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
    try:
        run.wait(timeout=240)
    except subprocess.TimeoutExpired:
        timed_out = True
        # Stop only this explicitly created process tree; preserve partial output.
        subprocess.run(["taskkill", "/PID", str(run.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        run.wait(timeout=20)
decoded = log.read_bytes().decode("utf-8", errors="replace")
count_match = re.search(r"Test run with (\d+) tests? in .*? passed", decoded)
executed = int(count_match.group(1)) if count_match else 0
after = {p: digest(ROOT / p) for p in PATHS}
valid = run.returncode == 0 and executed == 9 and before == after
result = {
    "scope": "exact changed pure queue source and its nine original Swift Testing methods",
    "status": "PASS" if valid else "FAIL",
    "startedAt": started,
    "finishedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "headCommit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "command": command,
    "exitCode": run.returncode,
    "timedOut": timed_out,
    "executedQueueMethods": executed,
    "expectedQueueMethods": 9,
    "sourceHashes": before,
    "sourceStable": before == after,
    "logSHA256": digest(log),
    "syntaxParse": {"exitCode": parsed.returncode, "paths": PATHS,
                    "logSHA256": digest(EVIDENCE / "swift-parse.log")},
    "uikitTypecheck": "NOT_RUN",
    "tableHandlerCases": "NOT_RUN",
    "nativePersistence": "NOT_RUN",
    "unchangedUIKitSuitesRerun": False,
}
(EVIDENCE / "scoped-checks.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print("\n".join(decoded.splitlines()[-30:]))
print(json.dumps(result, indent=2))
sys.exit(0 if valid else (run.returncode or 91))
