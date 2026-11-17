import hashlib, json, os, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
root=Path("C:/Users/DAVID/Code/anytype-swift-chatgpt-t5-20261118")
kit=Path("C:/Users/DAVID/Code/TorahInspectorKit-wave1-integration-20261115")
package=root/".build/portable-t5-authorization"
evidence=root/"docs/validation/20261118-t5-authorization"
package.mkdir(parents=True,exist_ok=False)
evidence.mkdir(parents=True,exist_ok=False)
manifest="""// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "T5AuthorizationComponentProof",
    targets: [
        .target(name: "TorahInspectorCore"),
        .target(name: "PinkhaKit", dependencies: ["TorahInspectorCore"]),
        .testTarget(name: "PinkhaKitTests", dependencies: ["PinkhaKit", "TorahInspectorCore"])
    ]
)
"""
(package/"Package.swift").write_text(manifest,encoding="utf8")
(evidence/"portable-Package.swift").write_text(manifest,encoding="utf8")
files=[]
for source_root,destination_root in [
    (kit/"Sources/TorahInspectorCore",package/"Sources/TorahInspectorCore"),
    (root/"Modules/PinkhaKit/Sources/PinkhaKit",package/"Sources/PinkhaKit")
]:
    for source in source_root.rglob("*.swift"):
        destination=destination_root/source.relative_to(source_root)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
        files.append((source,destination))
source=root/"Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/T5NoteCreationFlowTests.swift"
destination=package/"Tests/PinkhaKitTests/T5NoteCreationFlowTests.swift"
destination.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(source,destination)
files.append((source,destination))
hashes={str(source):hashlib.sha256(source.read_bytes()).hexdigest() for source,destination in files}
for source,destination in files:
    if hashes[str(source)]!=hashlib.sha256(destination.read_bytes()).hexdigest():
        raise RuntimeError("Copy mismatch "+str(source))
swift="C:/Users/DAVID/AppData/Local/Programs/Swift/Toolchains/6.3.3+Asserts/usr/bin/swift.exe"
command=[swift,"test","--package-path",str(package),"--jobs","1","--filter","T5NoteCreationFlowTests"]
receipt=dict(status="RUNNING",started_utc=datetime.now(timezone.utc).isoformat(),
    platform="Windows Swift 6.3.3 exact-source portable PinkhaKit + TorahInspectorCore; not native Heart/Apple/UI acceptance",
    kit_source_sha="c3fbb6c8173858b26fc5b4ce8496ee09fef2b9f9",
    source_base_sha="56be32bd491ad635c3e734ffdf767b14ac073486",
    command=command,source_sha256=hashes)
receipt_path=evidence/"component.json"
receipt_path.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf8")
with (evidence/"component.log").open("w",encoding="utf8") as output:
    result=subprocess.run(command,cwd=root,stdout=output,stderr=subprocess.STDOUT,timeout=300)
unchanged=all(hashes[str(source)]==hashlib.sha256(source.read_bytes()).hexdigest()==hashlib.sha256(destination.read_bytes()).hexdigest() for source,destination in files)
receipt.update(status="PASS" if result.returncode==0 and unchanged else "FAIL",returncode=result.returncode,
    source_unchanged=unchanged,finished_utc=datetime.now(timezone.utc).isoformat())
receipt_path.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf8")
print(json.dumps({key:value for key,value in receipt.items() if key!="source_sha256"}))
print((evidence/"component.log").read_text(encoding="utf8",errors="replace")[-16000:])
raise SystemExit(0 if receipt["status"]=="PASS" else 1)
