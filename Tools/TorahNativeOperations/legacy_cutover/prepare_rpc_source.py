#!/usr/bin/env python3
"""Freeze the reviewed additive RPC inputs and prove existing generated bodies remain."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUN=Path("/var/tmp/pinkha-e-cutover-current8ac-20261127")
SOURCE=RUN/"attempt2/source/heart"
FILES=[
"core/pinkha_torah_cutover_rpc.go",
"core/pinkha_torah_cutover_rpc_test.go",
"core/pinkha_torah_cutover_rpc_acceptance_test.go",
"core/pinkha_torah_cutover_crash_acceptance_test.go",
"pb/protos/pinkha_torah_cutover.proto",
"pb/protos/service/service.proto",
"pb/cutoverpb/pinkha_torah_cutover.pb.go",
"pb/cutoverpb/pinkha_torah_cutover_gomobile_aliases.go",
"pb/service/service.pb.go",
"clientlibrary/service/service.pb.go",
"clientlibrary/service/pinkha_torah_cutover_rpc_wire_test.go",
]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def row(path):return {"bytes":path.stat().st_size,"sha256":sha(path)}
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def functions(path,strip_dispatch=False):
    original=path.read_text()
    if strip_dispatch:
        for method in ["SourceRead","Read","Append","Import","AssociationAppend"]:
            name="PinkhaTorahCutover"+method
            addition='\t\tcase "'+name+'":\n\t\t\tcd = '+name+'(data)\n'
            assert original.count(addition)==1,name
            original=original.replace(addition,"")
    pattern=r'//[^\n]*|/\*[\s\S]*?\*/|\x60[^\x60]*\x60|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27'
    masked=re.sub(pattern,lambda m:" "*len(m[0]),original)
    result={}
    for match in re.finditer(r"(?m)^func\s+",masked):
        opening=match.end();parens=0
        while True:
            character=masked[opening]
            if character=="(":parens+=1
            elif character==")":parens-=1
            elif character=="{" and parens==0:break
            opening+=1
        depth=1;end=opening+1
        while depth:
            if masked[end]=="{":depth+=1
            elif masked[end]=="}":depth-=1
            end+=1
        signature=" ".join(original[match.start():opening].split())
        assert signature not in result,signature
        result[signature]=hashlib.sha256(original[match.start():end].encode()).hexdigest()
    return result
def main():
    generated=json.loads((RUN/"rpc-generation2-isolated/receipt.json").read_text())
    assert generated["status"]=="GENERATED_ISOLATED_GO_PACKAGE_NOT_NATIVE_ACCEPTANCE"
    assert generated["descriptorIdentityPreservedExceptGoPackage"] is True
    assert generated["noOriginalPBImportCycle"] is True
    for rel, expected in generated["originalPBPackageUnchanged"].items():
        assert row(SOURCE/rel)==expected,rel
        assert not (HERE/"overlay"/rel).exists(),"original pb package must have no overlay"
    for rel,expected in (generated["generatedFiles"]|generated["sourceInputs"]).items():
        assert row(HERE/"overlay"/rel)==expected,rel
    qualified=json.loads((HERE/"native-core-current8ac-qualified.json").read_text())
    for rel,expected in qualified["sourceFiles"].items():
        assert row(HERE/"overlay"/rel)==expected,rel
    audit={}
    for rel in ["pb/service/service.pb.go","clientlibrary/service/service.pb.go"]:
        old,new=functions(SOURCE/rel),functions(HERE/"overlay"/rel,strip_dispatch=rel.startswith("clientlibrary/"))
        missing=sorted(set(old)-set(new))
        changed=sorted(k for k in old if k in new and old[k]!=new[k])
        added=sorted(set(new)-set(old))
        audit[rel]={"originalFunctionCount":len(old),"newFunctionCount":len(new),
           "missingFunctions":missing,"changedExistingFunctions":changed,"addedFunctions":added,
           "onlyCommandAsyncAdditions":["PinkhaTorahCutover"+x for x in ["SourceRead","Read","Append","Import","AssociationAppend"]] if rel.startswith("clientlibrary/") else []}
        assert not missing and not changed,(rel,missing,changed)
        assert all("PinkhaTorahCutover" in x for x in added),added
    files={rel:{"before":row(SOURCE/rel) if (SOURCE/rel).exists() else None,"after":row(HERE/"overlay"/rel)} for rel in FILES}
    manifest={"protocol":"pinkha-cutover-generated-rpc-source-v1","status":"SOURCE_FROZEN_PENDING_NATIVE_ACCEPTANCE",
       "coreManifestSHA256":sha(HERE/"native-core-current8ac-qualified.json"),
       "generatorReceiptSHA256":sha(RUN/"rpc-generation2-isolated/receipt.json"),
       "generatorReceipt":str(RUN/"rpc-generation2-isolated/receipt.json"),
       "files":files,"generatedFunctionRetention":audit,
       "goPackage":generated["goPackage"],
       "descriptorIdentityPreservedExceptGoPackage":True,
       "supersededManifestSHA256":generated["supersededManifestSHA256"],
       "unchangedNativeSource":str(SOURCE.parent),
       "generatedAcceptance":False,"peerTransport":False,"appleUI":False}
    save(HERE/"rpc-source-candidate.json",manifest)
    print(json.dumps({"manifest":row(HERE/"rpc-source-candidate.json"),"files":len(files),"functionRetention":audit}))
if __name__=="__main__":main()
