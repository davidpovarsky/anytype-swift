import pathlib,json,hashlib,gzip,stat,collections
root=pathlib.Path(r"C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\sdk06-tagged-45139431216-1")
out=root/"full-products-stream-audit"
def sha(b):return hashlib.sha256(b).hexdigest()
def strict(pairs):
 r={}
 for k,v in pairs:
  assert k not in r
  r[k]=v
 return r
def j(raw):return json.loads(raw,object_pairs_hook=strict)
names=["stream-audit-reader.py","run-audit.py","source-freeze.json","preexecution-setup.json","launch-start.json","stdout.log","stderr.log","launch-result.json","stream-audit.json","entry-map.json.gz"]
files={}
for name in names:
 p=out/name;s=p.stat()
 assert p.parent==out and stat.S_ISREG(s.st_mode) and s.st_size<8000000 and s.st_file_attributes&1 and not s.st_file_attributes&1024
 raw=p.read_bytes()
 files[name]={"bytes":len(raw),"sha256":sha(raw),"readonly":True,"metadata_strings":{k:str(getattr(s,k)) for k in ("st_dev","st_ino","st_mode","st_size","st_mtime_ns","st_ctime_ns","st_nlink","st_file_attributes","st_reparse_tag")}}
report=j((out/"stream-audit.json").read_bytes())
launch=j((out/"launch-result.json").read_bytes())
assert files["stream-audit.json"]["sha256"]=="5fb77b4c59aed70e608cde394e89015508d06110e36495b279b7473831242014"
assert files["launch-result.json"]["sha256"]=="18b6489c82ce6aa34abf0c637cd73abb1d33af6974feacc91a0f0e2dbf1a2482"
assert report["status"]=="PASS_EXACT_5011_MANIFEST_ENTRIES_STREAM_VERIFIED"
assert report["original_archive_metadata_identity_and_access_unchanged"] is True and report["source_inputs_unchanged"] is True
assert launch["status"]=="PASS_OWNED_STREAM_AUDIT" and launch["return_code"]==0 and launch["timed_out"] is False and launch["owned_child_pid"]==5560
manifest_bytes=(root/"bounded-original-audit/selected/sdk06-early-products/manifest.json").read_bytes()
assert sha(manifest_bytes)=="331ad15a50b7c0d815fde3b2597b63d24f4de48b206f005aecbf0316f5fe5707"
manifest=j(manifest_bytes)
with gzip.open(out/"entry-map.json.gz","rb") as f:entry_bytes=f.read(8*1024**2+1)
assert len(entry_bytes)<=8*1024**2 and sha(entry_bytes)==report["entry_map"]["uncompressed_sha256"]
entries=j(entry_bytes)
assert entries["complete"] is True and entries["manifest_total"]==entries["observed_verified_entries"]==5011
products=manifest["products"]
seen=set();regular_bytes=0;counts=collections.Counter()
for i,row in enumerate(entries["entries"],1):
 name=row["path"]
 assert name not in seen and name in products and row["ordinal"]==i and row["matches_original_manifest"] is True and row["build_origin_verified"] is False
 seen.add(name);expected=products[name];counts[row["kind"]]+=1
 assert row["kind"]==expected["kind"] and row["mode"]==expected["mode"]
 if row["kind"]=="file":
  assert row["bytes"]==expected["bytes"] and row["sha256"]==expected["sha256"];regular_bytes+=row["bytes"]
 else:assert row["bytes"]==0 and row["sha256"] is None
assert seen==set(products) and dict(counts)=={"directory":1232,"file":3779} and regular_bytes==2375184946
print(json.dumps({"status":"PASS_ORIGINAL_SMALL_RECEIPTS_AND_ENTRY_MAP","files":files,"original_stream_receipt":report,"original_launch_receipt":launch,"entry_map_reconciliation":{"entries":len(seen),"counts":dict(counts),"regular_bytes":regular_bytes,"uncompressed_bytes":len(entry_bytes),"uncompressed_sha256":sha(entry_bytes),"all_entries_match_exact_manifest":True},"source_payloads_reread":False,"archive_payloads_reread":False,"Products_extracted":False},sort_keys=True))
