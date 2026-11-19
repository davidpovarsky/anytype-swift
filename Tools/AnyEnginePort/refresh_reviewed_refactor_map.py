#!/usr/bin/env python3
"""Refresh only this explicitly reviewed, task-scoped refactor map."""
from pathlib import Path
import subprocess,json
root=Path(__file__).resolve().parents[2]
base="586c98bcc17dee425664224e508fc0e8df277678"
def git(*args):return subprocess.check_output(["git","-C",str(root),*args]).decode().strip()
def blob(path):return git("hash-object","--path="+path,str(root/path))
def original(path):return git("rev-parse",base+":"+path)
entries=[]
def add(old,kind,reason,shared=(),destination=None):
 dest=destination or old
 if kind!="move" and original(old)==blob(dest):return
 entries.append({"kind":kind,"from":old,"to":dest,"baselineBlob":original(old),
     "replacementBlob":blob(dest),"reason":reason,
     "sharedSources":[{"path":p,"gitBlob":blob(p)} for p in shared],
     "validation":["Original implementation/extraction diff reviewed; exact replacement blobs pinned.",
        "Existing app test bodies are retained; import-only edits are mechanically checked.",
        "Independent source-bound package and UIKit/native gates are required; this map does not mark parity."]})
core="Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/"
moves={
"PinkhaHanlinAccountOwner":"",
"PinkhaHanlinHostAdapter":"","PinkhaHanlinReadRace":"","PinkhaHanlinNavigationLedger":"",
"PinkhaHanlinReadConsentDecision":"","PinkhaHanlinRevocationFence":"","PinkhaHanlinInvocationEnvelope":"",
"PinkhaHanlinCreatePagePlan":"Write/","PinkhaHanlinWriteJournal":"Write/","PinkhaHanlinWritePreflight":"Write/"}
for name,sub in moves.items():
 old="Anytype/Sources/Pinkha/AI/"+sub+name+".swift"
 reason = "Single shared implementation for Heart and Any; public API initializers/access and portable Crypto import only. Account owner replaces concrete weak presentation type with identical lifetime protocol."
 if name == "PinkhaHanlinWriteJournal":
  reason = "Retain original v1 reservation/effect bytes and receipt rules; add an account-bound metadata-only known-object recovery sidecar for uncertain native creations, strict reopen validation, and same-ID committed refinement. Native failures remain uncertain and never masquerade as committed."
 add(old,"move",reason, destination=core+name+".swift")
for old in [
"AnyTypeTests/Pinkha/HanlinHostAdapterTests.swift","AnyTypeTests/Pinkha/HanlinHostReadWriteTests.swift",
"AnyTypeTests/Pinkha/HanlinHostWriteTests.swift","AnyTypeTests/Pinkha/HanlinSDKConsumerTests.swift",
"Anytype/Sources/Pinkha/AI/PinkhaHanlinAuthService.swift",
"Anytype/Sources/Pinkha/AI/PinkhaHanlinNativeAccess.swift",
"Anytype/Sources/Pinkha/AI/PinkhaHanlinReadConsent.swift",
"Anytype/Sources/Pinkha/AI/Write/PinkhaHanlinCreatePageContext.swift",
"Anytype/Sources/Pinkha/Diagnostics/PinkhaHanlinNativeAcceptanceDriver.swift"]:
 add(old,"import_only","Import the extracted shared module; implementation and test bodies unchanged.")
ui="Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/"
add("Anytype/Sources/Pinkha/AI/PinkhaHanlinChatPresentation.swift","refactor",
    "Retain Heart factory, styling and diagnostic adapter; share the original canonical session/provider/send/configure/close presentation body through one mounted owner protocol.",
    [core+"PinkhaHanlinAccountOwner.swift",ui+"PinkhaHanlinChatPresentation.swift",ui+"PinkhaHanlinPresentationHost.swift"])
for name in ["PinkhaHanlinChatView","PinkhaHanlinConsentController","PinkhaHanlinStrings"]:
 add("Anytype/Sources/Pinkha/AI/"+name+".swift","refactor",
     "Keep original app aliases and share original UI/consent/localized-string implementation; only public API, injected styling and Bundle.module resource ownership change.",
     [ui+name+".swift"])
add("Anytype/Sources/Pinkha/AI/Resources/PinkhaHanlin.xcstrings","move",
    "Move exact byte-identical Hanlin localized resources into the single shared UI bundle; retain every existing translation.",
    destination=ui+"Resources/PinkhaHanlin.xcstrings")
add("Anytype/Sources/Pinkha/AI/Write/PinkhaHanlinCreatePageRunner.swift","refactor",
    "Keep Heart-specific creation and exact result checks in a thin wrapper; preserve shared reservation, timeout, cancellation and original-scope late receipts once.",
    [core+"PinkhaHanlinCreateRunner.swift"])
add("Anytype/Sources/Pinkha/AI/Write/PinkhaHanlinReadWriteHost.swift","refactor",
    "Keep UIKit/native mounting and write binding in app; extract exact router, bounded replay identity and tool contract for both native engines.",
    [core+"PinkhaHanlinHostRouter.swift",core+"PinkhaHanlinCreatePageTool.swift"])
extraction=root/"Modules/PinkhaTorahPresentation/EXTRACTION.json"
if extraction.exists():
 data=json.loads(extraction.read_text(encoding="utf-8"))
 assert data["baseline"]==base
 for item in data["paths"]:
  assert original(item["oldPath"])==item["baselineBlob"]
  add(item["oldPath"],"refactor",
      "Retain app aliases/Heart factory or protocol conformance; reuse original Torah session/search controller bodies, localization and six-state persistence contract through shared host protocols. Add active-host switching only with no open inspector/search modal so the native property sheet uses the same session instead of duplicating state.",
      [item["newPath"]])
# Only this exact branch is a newly authorized isolated consumer. All existing
# runtime source/hash, caller identity and explicit test-profile checks remain.
installer="Tools/PinkhaNativeDerived/install_verified_heart.py"
if original(installer)!=blob(installer):
 add(installer,"refactor","Add only codex/any-engine-port-20261119 to isolated consumer branches for unchanged verified Heart artifact compatibility tests; preserve all artifact/patch/source checks.")
out={"schemaVersion":1,"baselineCommit":base,
     "authorization":"User explicitly requested a new isolated branch, full native port, architectural adaptation preserving all capabilities, and end-to-end tests.",
     "purpose":"Reviewable exact extraction/provenance mapping. No statement of runtime or UI parity.",
     "changes":sorted(entries,key=lambda e:e["from"])}
path=root/"docs/any-engine-port/SOURCE_REFACTOR_MAP.json"
path.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"mappedChanges":len(entries),"path":str(path)}))
