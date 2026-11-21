from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, sys
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "shared-editor-verification"
PKG = OUT / "package"
OUT.mkdir(parents=True, exist_ok=True)
paths = ["Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockViewModel.swift","Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift","AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift","Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockActionHandlerProtocol.swift","Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentConfiguration.swift","Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockActionHandler.swift","Modules/PinkhaKit/Sources/PinkhaKit/Editor/PinkhaTextInputRenderPolicy.swift","Modules/PinkhaKit/Sources/PinkhaKit/Editor/PinkhaSerialTextEditQueue.swift","Modules/PinkhaKit/Tests/PinkhaKitTests/Editor/PinkhaTextInputRenderPolicyTests.swift","Modules/PinkhaKit/Tests/PinkhaKitTests/Editor/PinkhaSerialTextEditQueueTests.swift"]
for relative in paths:
    p = ROOT / relative
    for backup in p.parent.glob(p.name + ".bak.*"):
        dest = OUT / "backups" / backup.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(backup), str(dest))
sources = [
    "Modules/PinkhaKit/Sources/PinkhaKit/Editor/PinkhaTextInputRenderPolicy.swift",
    "Modules/PinkhaKit/Sources/PinkhaKit/Editor/PinkhaSerialTextEditQueue.swift",
]
tests = [
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Editor/PinkhaTextInputRenderPolicyTests.swift",
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Editor/PinkhaSerialTextEditQueueTests.swift",
]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = {p: digest(ROOT / p) for p in paths}
for relative in sources + tests:
    src = ROOT / relative
    category = "Sources/PinkhaKit" if relative in sources else "Tests/PinkhaKitTests"
    dst = PKG / category / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    assert digest(src) == digest(dst)
(PKG / "Package.swift").write_text('''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "PinkhaKit", targets: [
    .target(name: "PinkhaKit"),
    .testTarget(name: "PinkhaKitTests", dependencies: ["PinkhaKit"])
])
''', encoding="utf-8", newline="\n")
command = ["swift", "test", "--package-path", str(PKG)]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
log = OUT / "swift-test.log"
log.write_bytes(result.stdout)
after = {p: digest(ROOT / p) for p in paths}
manifest = {
    "startedAt": started,
    "finishedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": command,
    "exitCode": result.returncode,
    "sourceHashes": before,
    "sourceStable": before == after,
    "logSHA256": digest(log),
    "scope": "Original two new shared-source suites in a dependency-free package. UIKit and native persistence not exercised."
}
(OUT / "result.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(result.stdout.decode("utf-8", errors="replace"))
print(json.dumps(manifest, indent=2))
sys.exit(result.returncode if before == after else 90)
