import hashlib, json, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding="utf-8")
root = Path("C:/Users/DAVID/Code/anytype-swift-chatgpt-t5-20261118")
kit = Path("C:/Users/DAVID/Code/TorahInspectorKit-chatgpt-t5-ui-20261118")
package = root / ".build/portable-t5-authorization"
evidence = root / "docs/validation/20261118-t5-runtime-contract"
kit_evidence = kit / "docs/validation/20261118-t5-coverage-contract"
evidence.mkdir(parents=True, exist_ok=True)
kit_evidence.mkdir(parents=True, exist_ok=True)
manifest = """// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "T5AuthorizationComponentProof", targets: [
    .target(name: "TorahInspectorCore"),
    .target(name: "PinkhaKit", dependencies: ["TorahInspectorCore"]),
    .testTarget(name: "PinkhaKitTests", dependencies: ["PinkhaKit", "TorahInspectorCore"]),
    .testTarget(name: "TorahInspectorCoreTests", dependencies: ["TorahInspectorCore"])
])
"""
(package / "Package.swift").write_text(manifest, encoding="utf-8")
(evidence / "portable-Package.swift").write_text(manifest, encoding="utf-8")
files = []
for original, destination in [
    (kit / "Sources/TorahInspectorCore", package / "Sources/TorahInspectorCore"),
    (root / "Modules/PinkhaKit/Sources/PinkhaKit", package / "Sources/PinkhaKit")
]:
    for source in original.rglob("*.swift"):
        target = destination / source.relative_to(original)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files.append((source, target))
for source in (root / "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah").glob("T5*Tests.swift"):
    # Existing cached tests and the new runtime boundary compile unchanged.
    if source.name == "T5SpaceRelatedDocumentsQueryTests.swift":
        continue
    target = package / "Tests/PinkhaKitTests" / source.name
    shutil.copyfile(source, target)
    files.append((source, target))
source = kit / "Tests/TorahInspectorCoreTests/RelatedDocumentsRefreshTests.swift"
target = package / "Tests/TorahInspectorCoreTests" / source.name
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(source, target)
files.append((source, target))
hashes = {str(source): hashlib.sha256(source.read_bytes()).hexdigest() for source, target in files}
def unchanged():
    return all(hashes[str(source)] == hashlib.sha256(source.read_bytes()).hexdigest()
               == hashlib.sha256(target.read_bytes()).hexdigest() for source, target in files)
if not unchanged():
    raise RuntimeError("Source copy mismatch")
swift = "C:/Users/DAVID/AppData/Local/Programs/Swift/Toolchains/6.3.3+Asserts/usr/bin/swift.exe"
receipts = []
for name, selection in [
    ("runtime", "T5NativeRelatedLookupCapabilityTests"),
    ("kit", "invalidatedLateResultCannotReplaceFreshRelatedDocuments|refreshedCoverageRetainsExactBlocksAndDropsThemAfterRuntimeFallback")
]:
    command = [swift, "test", "--package-path", str(package), "--jobs", "1", "--filter", selection]
    receipt = dict(status="RUNNING", platform="Windows Swift 6.3.3 exact-source component; not native Heart or Apple UI",
        started_utc=datetime.now(timezone.utc).isoformat(), command=command, source_sha256=hashes,
        anytype_base_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
        kit_base_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=kit,text=True).strip())
    path = evidence / (name + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    try:
        with (evidence / (name + ".log")).open("x", encoding="utf-8") as output:
            result = subprocess.run(command, cwd=root, stdout=output, stderr=subprocess.STDOUT, timeout=220)
        same = unchanged()
        receipt.update(status="PASS" if result.returncode == 0 and same else "FAIL",
            returncode=result.returncode, source_unchanged=same)
    except Exception as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k != "source_sha256"}))
    print((evidence / (name + ".log")).read_text(encoding="utf-8", errors="replace")[-15000:])
    if receipt["status"] != "PASS":
        raise SystemExit(1)
    receipts.append(receipt)
for name in ["kit.log", "kit.json", "portable-Package.swift"]:
    shutil.copyfile(evidence / name, kit_evidence / name)
print("Both bounded contract components passed; source hashes unchanged.")
