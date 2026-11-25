import collections, hashlib, json, os
from pathlib import Path
root=Path("/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156")
context_bytes=(root/"fixture-context.json").read_bytes()
assert hashlib.sha256(context_bytes).hexdigest()=="bb03b5a06a77d8b3e85cd46bc9cedc8a497c2bb06bbcd3e47b834e13d83b934a"
context=json.loads(context_bytes); directory=root/"bundle"; raw=(directory/context["bundleManifestName"]).read_bytes()
assert hashlib.sha256(raw).hexdigest()=="cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4"
manifest=json.loads(raw); rows=[]
for row in manifest["Objects"]:
    for key in ["Snapshot","NativeJSONView"]:
        member=row[key]; path=directory/member["Path"]
        assert path.resolve().is_relative_to(directory.resolve()) and not path.is_symlink()
        data=path.read_bytes()
        assert hashlib.sha256(data).hexdigest()==member["SHA256"] and len(data)==member["Bytes"]
        if key=="NativeJSONView":
            value=json.loads(data)
            assert value["ObjectID"]==row["ObjectID"] and value["NativeType"]==row["NativeType"]
            rows.append(value)
types=[x for x in rows if x["NativeType"]==528]
relations=[x for x in rows if x["NativeType"]==521]
read_only=[x for x in relations if x["Snapshot"]["details"].get("relationReadonlyValue")==True]
used=collections.Counter(key for row in rows for key in row["Snapshot"]["details"])
readonly_usage={row["Snapshot"]["details"]["relationKey"]:used[row["Snapshot"]["details"]["relationKey"]]
    for row in read_only if used[row["Snapshot"]["details"]["relationKey"]]}
defaults=collections.Counter("absent" if "relationDefaultValue" not in row["Snapshot"]["details"] else
    "explicit-null" if row["Snapshot"]["details"]["relationDefaultValue"] is None else "explicit-value" for row in relations)
result={
 "contract":"pinkha-real156-readonly-semantic-gap-census-v1",
 "sourceContextSHA256":hashlib.sha256(context_bytes).hexdigest(),
 "sourceManifestSHA256":hashlib.sha256(raw).hexdigest(),
 "originalProducerStatus":context["customSchemaAcceptanceStatus"],
 "sourceAcceptancePromoted":False,"sourceMembersVerified":len(rows)*2,
 "nativeTypeCounts":dict(sorted(collections.Counter(str(row["NativeType"]) for row in rows).items())),
 "capturedObjects":len(rows),"nativeTrees":len(manifest["Trees"]),
 "nativeHeads":159,"nativeHeadsProof":"20261125-native-head-census/receipt.json",
 "blocks":sum(len(row["Snapshot"].get("blocks",[])) for row in rows),
 "sourceFiles":len(manifest["Files"] or []),"sourceFileReferences":len(manifest["FileReferences"] or []),
 "typeRecommendedLayoutCounts":dict(sorted(collections.Counter(str(row["Snapshot"]["details"].get("recommendedLayout")) for row in types).items())),
 "typeManualRanks":{"present":sum("orderId" in row["Snapshot"]["details"] for row in types),
     "explicitEmpty":sum(row["Snapshot"]["details"].get("orderId")=="" for row in types),
     "absent":sum("orderId" not in row["Snapshot"]["details"] for row in types)},
 "readOnlyDefinitionCount":len(read_only),"readOnlyDefinitionKeysUsedInCapturedDetails":readonly_usage,
 "propertyDefaultPresence":dict(defaults),
 "sourceGaps":len(manifest["Gaps"] or []),"resolverUnmapped":len(manifest["ResolverUnmapped"] or []),
 "bundledDefinitionsUsedCount":len(manifest["BundledDefinitionsUsed"] or []),
 "originalNilListFields":[key for key in ["Files","FileReferences","Gaps","ResolverUnmapped"] if manifest[key] is None],
 "sourceValuesAndPrivateIdentitiesOmitted":True,"newNativeCalls":0,"destinationWrites":0,
 "wholeSourceMigrationAccepted":False,
}
out=Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125/docs/validation/20261125-native-type-order")
out.mkdir(parents=True,exist_ok=True)
p=out/"original156-census.json";assert not p.exists()
p.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");os.chown(out,1001,1002);os.chown(p,1001,1002)
print(json.dumps(result));print("receiptSHA256="+hashlib.sha256(p.read_bytes()).hexdigest())
