import json, hashlib, subprocess, shutil
from pathlib import Path
from datetime import datetime, timezone
R=Path(r"C:\Users\DAVID\Code\anytype-original-annotation-metadata-20261122")
T=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122")
BASE="b854e7f3f59690134bcabdef88527b61517d5ab5"
PRODUCT="Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationNativeMetadata.swift"
ATTR="Anytype/Sources/Pinkha/Torah/Annotations/.gitattributes"
PACKET="docs/pinkha/torah-integration/production-native-metadata-20261122"
P=R/PACKET;C=P/"controls"
STATE=T/"metadata_publication_state.json"
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):
    p=subprocess.run(["git","-c","core.autocrlf=false","-C",str(R),*args],capture_output=True,timeout=90)
    if p.returncode:raise RuntimeError((args,p.returncode,p.stdout.decode("utf-8","replace"),p.stderr.decode("utf-8","replace")))
    return p.stdout
def gt(*args):return git(*args).decode("utf-8").strip()
def save(phase,**kw):
    d={"phase":phase,"at":datetime.now(timezone.utc).isoformat(),**kw}
    STATE.write_bytes((json.dumps(d,indent=2)+"\n").encode())
    print(json.dumps(d),flush=True)
assert not STATE.exists(),"Prior publication state exists; inspect instead of replay"
assert gt("rev-parse","HEAD")==BASE
assert gt("branch","--show-current")=="codex/otzaria-original-annotation-metadata-20261122"
assert not gt("diff","--name-only") and not gt("diff","--cached","--name-only")
prod=(R/PRODUCT).read_bytes()
assert len(prod)==8112 and sha(prod)=="21321e2e69bcb29dc784620dd459f1152528f117caa13695e689b6d024813dc5"
review=(T/"metadata26_root_review.json").read_bytes()
assert sha(review)=="7fb7862193f91dd2f4ba1f4ae49420f1048928bec1476954f35a2d4fb2610f8f"
reviewobj=json.loads(review)
assert reviewobj["status"]=="PASS_INDEPENDENT_SOURCE_ARTIFACT_REVIEW_NO_TEST_RERUN"
reviewcode=(T/"metadata26_root_review.py").read_bytes()
assert sha(reviewcode)==reviewobj["root_review_script_sha256"]=="930ccb8e15af04c269e9385588cfd13a505e33ae37b6106cfcbb5e8f92d3dbed"
controls_index=(C/"FILE_INDEX.json").read_bytes()
assert sha(controls_index)=="ffac49d17c87592d13594aa6574ae7d8e09609751dac90dfca17d951de8c9d92"
ci=json.loads(controls_index)
assert len(ci["files"])==69
for row in ci["files"]:
    b=(C/row["path"]).read_bytes()
    assert len(b)==row["bytes"] and sha(b)==row["sha256"]
assert not (R/ATTR).exists() and not (P/"CONTRACT.md").exists()
trees={p:gt("rev-parse",BASE+":"+p) for p in ["Modules","OriginalEditorFramework","Anytype/Resources",".github","Scripts"]}
save("VERIFIED_BEFORE_SOURCE_COMMIT",base=BASE,product_sha256=sha(prod),controls_index_sha256=sha(controls_index))
(R/ATTR).write_bytes(b"OriginalAnnotationNativeMetadata.swift -text whitespace=cr-at-eol\n")
contract=r"""# Original native annotation metadata boundary

## Implemented scope

This component adds an internal, read-only decoder of the original Google_Protobuf_Struct into the existing TorahAnnotationNativeCandidate contract. It also declares the fixed schema keys intended for a later original native registration step. The decoder is not currently wired into ObjectShow or a production creation path.

The tested product file is Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationNativeMetadata.swift: 8,112 bytes, SHA-256 21321e2e69bcb29dc784620dd459f1152528f117caa13695e689b6d024813dc5. Its tested CRLF bytes are preserved in Git by one file-specific attribute. SOURCE_BINDING.json binds the final source commit to these same bytes. This is a new downstream component; existing original product files, generated protocol definitions and the schema1 manifest are unchanged.

## Fixed descriptor and lossless storage

The protocol value is pinkha.torah.annotation/1. The original type unique key is ot-pinkhatorahannotationv1. The suffix is a fixed schema identifier, not the actual per-Space native type object ID. A later registration/readback operation must establish that actual ID.

All 17 metadata relations use the original Anytype_Model_RelationFormat.longtext. Revisions are decimal strings, so Int64 values above the exact integer range of protobuf's Double number representation remain lossless. Native registration must explicitly provide the relation format field, including its longtext raw value of zero; this descriptor alone does not register a relation or validate an existing native schema.

| Native relation key | Presence | Representation |
| --- | --- | --- |
| pinkhaTorahAnnotationProtocol | Required | Exact protocol string |
| pinkhaTorahAnnotationClassification | Required | annotation, chiddush, article, or research |
| pinkhaTorahAnnotationNamespace | Required | Existing case-sensitive scope identifier |
| pinkhaTorahAnnotationUUID | Required | Canonical Foundation UUID string |
| pinkhaTorahAnnotationCreationDestination | Required | Existing case-sensitive scope identifier |
| pinkhaTorahAnnotationCreationAccount | Required | Existing case-sensitive scope identifier |
| pinkhaTorahAnnotationCreationSpace | Required | Existing case-sensitive scope identifier |
| pinkhaTorahAnnotationCreationMessageID | Required | Canonical Foundation UUID string |
| pinkhaTorahAnnotationCreationMutationID | Required | Canonical Foundation UUID string |
| pinkhaTorahAnnotationCreationRevision | Required | Canonical positive Int64 decimal string |
| pinkhaTorahAnnotationCreationSourceDigest | Required | Existing lowercase SHA-256 digest grammar |
| pinkhaTorahAnnotationCreationPayloadDigest | Required | Existing lowercase SHA-256 digest grammar |
| pinkhaTorahAnnotationAppliedMessageID | All five applied fields or none | Canonical Foundation UUID string |
| pinkhaTorahAnnotationAppliedMutationID | All five applied fields or none | Canonical Foundation UUID string |
| pinkhaTorahAnnotationAppliedRevision | All five applied fields or none | Canonical positive Int64 decimal string |
| pinkhaTorahAnnotationAppliedSourceDigest | All five applied fields or none | Existing lowercase SHA-256 digest grammar |
| pinkhaTorahAnnotationAppliedPayloadDigest | All five applied fields or none | Existing lowercase SHA-256 digest grammar |

UUID spelling must equal Foundation's canonical uppercase, hyphenated uuidString byte for byte. A revision must consist only of ASCII digits, be in 1...Int64.max, and round-trip to the same decimal string. Signs, whitespace, leading zeroes, fractional/exponential forms, other digit scripts and overflow are rejected. Revisions never pass through Double.

The existing PinkhaKit constructors retain their identifier bounds and digest rules. This component does not add a parallel envelope format, alternate identifier codec, or a second delivery attempt identifier. The existing creation message UUID is retained as creationAttemptID.

## Native envelope and conflict observations

The native id field must be a string matching the supplied fresh root ID byte for byte. The native spaceId must match the creator Space marker. The native type field must be a list containing exactly one string, which is validated by the existing native identity contract. Successful decoding does not prove that this type ID is the correctly registered annotation schema; that qualification remains a separate original native readback obligation.

Creator destination and account values are retained even when they belong to another current scope. The existing recovery policy can therefore report a scope conflict instead of silently rewriting foreign ownership.

Recognized promoted writing classifications are retained explicitly. An unknown classification throws; it does not silently become a note or annotation. Missing isArchived and isDeleted fields decode as false; present fields must be protobuf bool values. Deleted takes precedence over archived. These are observations of the supplied native fields, not a fresh existence or liveness proof by themselves.

The five applied commitment fields are optional as a complete group. Every partial group is rejected. Present applied fields use the same strict protobuf kinds and canonical value validation as creation fields.

## Body and authority boundary

nativeSnapshotDigest is always nil. Metadata fields claiming to be snapshot or body digests cannot make it non-nil. A copied applied commitment is not evidence that the delivered rich body was written. The decoder neither changes nor consumes body/source/unknown protobuf fields.

A later production adapter must obtain a fresh original ObjectShow observation under the genuine Account/Space/source and original Owner admission rules. Schema identity, the current destination, the complete delivered body and its referenced content require their own source-bound checks. A fresh native hash alone does not establish equivalence to the intended delivery.

Any identity/body receipt and its local mapping consumption must remain within the required original held-read and synchronous admission boundary. This decoder returns a data candidate only. It creates no public grant, captured destination authority, authenticated receipt, mapping writer, COMMIT claim or ACK.

## Executed qualification and retained evidence

The single new Swift Testing invocation executed 26 cases in one suite: 26 passed, zero failed and zero skipped. The actual suite took 0.113 seconds; SwiftPM's build-and-test command took 491.659105 seconds. The former 52 policy cases and Native/UI suites were not replayed.

The suite used genuine apple/swift-protobuf at c6fe6442e6a64250495669325044052e113e990c, selected by the original b854e7f3f59690134bcabdef88527b61517d5ab5 Package.resolved. It compiled the unchanged original RelationFormat with its real SwiftProtobuf conformance, the two complete original NativeIdentity/CreateRecovery files, and the complete unchanged decoder. The tests include an actual binary protobuf round-trip, Int64 boundaries, malformed fields, all 30 partial applied-field masks, foreign scope/promotion conflicts, copied-snapshot denial, and preservation of original body/source/unknown fields.

The retained actual build closure contains 162 files: 149 exact dependency Git files, six frozen harness inputs, and seven standard SwiftPM generated files. The actual dependency plugin/tool targets are included in this closure. Fifteen compiler and Swift Testing SDK files are identified by hash.

The immutable controls/FILE_INDEX.json covers 69 payloads plus its own separate index. ROOT_REVIEW.json and ROOT_REVIEW.py record independent verification of the packet, original Git inputs, actual build graph, XML cases, raw streams, toolchain and executing binary. That verification did not execute tests.

One redundant #require warning in the test fixture is retained in the passed source. There is no product source diagnostic. The original logs and exact tested bytes were preserved rather than rewriting a passing fixture.

This is portable semantic qualification of this decoder and its selected real dependencies. Complete Apple application linking, the whole original ProtobufMessages/PinkhaKit packages, real schema registration, ObjectShow integration, native mutation, UI/device acceptance and release/signing gates remain open.

## Integration and rollback

Merge the source and evidence commits together, preserving the indexed packet bytes. Wire the component only after the independent source/selection/schema prerequisites are established and the required changed-source acceptance is available.

The component is currently unwired and performs no native or persistent mutation. Reverting its scoped source commit removes the decoder and descriptor; retain the evidence commits as history. A later production caller or schema mutation will need its own reviewed rollback and data-state contract.
"""
(P/"CONTRACT.md").write_bytes(contract.encode("utf-8"))
source_paths=[PRODUCT,ATTR,PACKET+"/CONTRACT.md"]
git("add","--",*source_paths)
assert set(gt("diff","--cached","--name-only").splitlines())==set(source_paths)
git("diff","--cached","--check")
assert sha(git("show",":"+PRODUCT))==sha(prod)
git("commit","-m","feat(otzaria): decode original native annotation metadata strictly")
source=gt("rev-parse","HEAD")
assert gt("rev-parse",source+"^")==BASE
assert sha(git("show",source+":"+PRODUCT))==sha(prod)
save("SOURCE_COMMITTED_EVIDENCE_PENDING",source_commit=source)
(P/".gitattributes").write_bytes(b"* -text whitespace=cr-at-eol\n")
(P/"ROOT_REVIEW.json").write_bytes(review)
(P/"ROOT_REVIEW.py").write_bytes(reviewcode)
binding={"schema_version":1,"source_commit":source,"source_parent":BASE,"product_path":PRODUCT,
"product_sha256":sha(prod),"product_bytes":len(prod),"committed_blob":gt("rev-parse",source+":"+PRODUCT),
"tested_bytes_equal_committed_bytes":True,"controls_index_sha256":sha(controls_index),
"root_review_sha256":sha(review),"root_review_script_sha256":sha(reviewcode),
"original_product_files_changed":0,"new_downstream_product_files":1,
"preserved_trees":trees,"tests_reexecuted_for_publication":0,"native_or_schema_mutations":0,
"at":datetime.now(timezone.utc).isoformat()}
(P/"SOURCE_BINDING.json").write_bytes((json.dumps(binding,indent=2)+"\n").encode())
payload=[]
for p in sorted(P.rglob("*")):
    if p.is_file():
        b=p.read_bytes();payload.append({"path":p.relative_to(P).as_posix(),"bytes":len(b),"sha256":sha(b)})
assert len(payload)==75,len(payload)
index={"schema_version":1,"source_commit":source,"product_sha256":sha(prod),"payload_count":len(payload),
"payload_bytes":sum(x["bytes"] for x in payload),"payloads":payload,"excluded_self":"EVIDENCE_INDEX.json"}
(P/"EVIDENCE_INDEX.json").write_bytes((json.dumps(index,indent=2)+"\n").encode())
git("add","--",PACKET)
staged=gt("diff","--cached","--name-only").splitlines()
assert all(x.startswith(PACKET+"/") for x in staged)
git("diff","--cached","--check")
for row in ci["files"]:
    assert sha(git("show",":"+PACKET+"/controls/"+row["path"]))==row["sha256"]
assert git("show",":"+PACKET+"/controls/FILE_INDEX.json")==controls_index
git("commit","-m","test(otzaria): retain 26 real protobuf metadata controls and root review")
head=gt("rev-parse","HEAD")
assert gt("rev-parse",head+"^")==source
assert not gt("status","--porcelain")
for p,t in trees.items(): assert gt("rev-parse","HEAD:"+p)==t
assert sha(git("show","HEAD:"+PRODUCT))==sha(prod)
save("SOURCE_AND_EVIDENCE_SEALED_CLEAN_READY_FOR_PUSH",head=head,source_commit=source,
product_sha256=sha(prod),packet_payloads=len(payload),packet_files=len(payload)+1,
packet_index_sha256=sha((P/"EVIDENCE_INDEX.json").read_bytes()),controls_payloads_unchanged=69,
branch=gt("branch","--show-current"),tests_reexecuted=0)
