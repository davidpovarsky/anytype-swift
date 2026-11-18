import hashlib, json, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
root = Path("C:/Users/DAVID/Code/anytype-swift-chatgpt-t5-20261118")
kit = Path("C:/Users/DAVID/Code/TorahInspectorKit-wave1-integration-20261115")
package = root / ".build/portable-t5-authorization"
evidence = root / "docs/validation/20261118-t5-r02"
evidence.mkdir(parents=True, exist_ok=True)
files = []
for source_root, destination_root in [
    (kit / "Sources/TorahInspectorCore", package / "Sources/TorahInspectorCore"),
    (root / "Modules/PinkhaKit/Sources/PinkhaKit", package / "Sources/PinkhaKit")
]:
    for source in source_root.rglob("*.swift"):
        destination = destination_root / source.relative_to(source_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        files.append((source, destination))
for name in ["T5NoteCreationFlowTests.swift", "T5BlockReachabilityTests.swift",
             "T5ExpandedRelatedTargetsTests.swift", "T5ExpandedRelatedDocumentsQueryTests.swift"]:
    source = root / "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah" / name
    destination = package / "Tests/PinkhaKitTests" / name
    shutil.copyfile(source, destination)
    files.append((source, destination))
hashes = {str(source): hashlib.sha256(source.read_bytes()).hexdigest() for source, destination in files}
def unchanged():
    return all(hashes[str(source)] == hashlib.sha256(source.read_bytes()).hexdigest()
               == hashlib.sha256(destination.read_bytes()).hexdigest() for source, destination in files)
if not unchanged():
    raise RuntimeError("Source copy mismatch")
swift = "C:/Users/DAVID/AppData/Local/Programs/Swift/Toolchains/6.3.3+Asserts/usr/bin/swift.exe"
command = [swift, "test", "--package-path", str(package), "--jobs", "1", "--filter",
           "T5(ExpandedRelatedDocumentsQuery|ExpandedRelatedTargets|BlockReachability)Tests"]
receipt = dict(status="RUNNING", started_utc=datetime.now(timezone.utc).isoformat(),
    source_base_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    changes="Uncommitted R02 query plus four exact reused files from 4cb4e5c7816ff388e021bb64c72bfbbe3bbe39f1",
    kit_source_sha="c3fbb6c8173858b26fc5b4ce8496ee09fef2b9f9",
    platform="Windows Swift 6.3.3 exact-source component; not Heart, Apple host, UI or two-client acceptance",
    command=command, source_sha256=hashes)
receipt_path = evidence / "component.json"
with receipt_path.open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, indent=2)
try:
    with (evidence / "component.log").open("x", encoding="utf-8") as output:
        result = subprocess.run(command, cwd=root, stdout=output, stderr=subprocess.STDOUT, timeout=240)
    same = unchanged()
    receipt.update(status="PASS" if result.returncode == 0 and same else "FAIL",
        returncode=result.returncode, source_unchanged=same)
except Exception as error:
    receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in receipt.items() if key != "source_sha256"}))
print((evidence / "component.log").read_text(encoding="utf-8", errors="replace")[-17000:])
raise SystemExit(0 if receipt["status"] == "PASS" else 1)
