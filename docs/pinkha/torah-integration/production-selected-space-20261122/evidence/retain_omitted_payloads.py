import pathlib,json,hashlib,shutil,datetime
root=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-final-20261122")
old=root/"evidence-ready"
new=root/"evidence-ready-v2"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(data if isinstance(data,bytes) else data.encode("utf-8"))
def rec(p,base):return {"path":p.relative_to(base).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())}
oldindex=(old/"INDEX.json").read_bytes()
assert sha(oldindex)=="88127b17608f0e877f9f33f8e2fed9a9f25329d47f7902bb56e80b5c721473bb"
index=json.loads(oldindex)
assert index["count"]==85
for item in index["files"]:
 p=old/item["path"];assert p.stat().st_size==item["bytes"] and sha(p.read_bytes())==item["sha256"],item
assert not new.exists()
shutil.copytree(old,new)
(new/"INDEX.json").unlink()
write(new/"history"/"INDEX-88127b17.json",oldindex)
added=[]
expected={"TEST_RESULTS.xml":"008d5489b07d8be7e4634ca3b8f945fd0686e24ff43f4289eb13cdcce19d44d5","Package.swift":"6cba239977a672992c03ae5e6ed429d76e637ec3ce6f0dfb44e79989a12db067","previous-PortableDependencyProbes.swift":"f33e66619c4a5395cda45e6a7f609b7d5e6c465836eae1ae4e5dce54bdb1e16b"}
for name,digest in expected.items():
 raw=(root/name).read_bytes();assert sha(raw)==digest
 write(new/name,raw);added.append(rec(new/name,new))
for item in index["files"]:
 p=new/item["path"];assert p.stat().st_size==item["bytes"] and sha(p.read_bytes())==item["sha256"]
receipt={"schema":"original-selected-space-evidence-addition/v1","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"prior_index_sha256":sha(oldindex),"all_prior85_payloads_unchanged":True,"added_original_files":added,"reason":"Initial packaging suffix filter omitted standalone .xml and top-level .swift files; existing exact XML and Swift inputs are retained without alteration.","new_compiler_or_test_executions":0,"product_edits":0,"actual_first_wrapper_failure_retained":True}
write(new/"EVIDENCE_ADDITION.json",json.dumps(receipt,indent=2)+"\n")
write(new/"retain_omitted_payloads.py",pathlib.Path(__file__).read_bytes())
files=[rec(p,new) for p in sorted(new.rglob("*")) if p.is_file()]
write(new/"INDEX.json",json.dumps({"schema":1,"files":files,"count":len(files),"index_excludes_itself":True},indent=2)+"\n")
print(json.dumps({"status":"ADDITIVE_EVIDENCE_ONLY","proof":str(new),"payload_count":len(files),"index_sha256":sha((new/"INDEX.json").read_bytes()),"receipt_sha256":sha((new/"EVIDENCE_ADDITION.json").read_bytes()),"corrected_result_sha256":sha((new/"CORRECTED_RESULT.json").read_bytes()),"xml_sha256":sha((new/"TEST_RESULTS.xml").read_bytes()),"new_compiler_or_test_executions":0,"old_packet_unchanged":sha((old/"INDEX.json").read_bytes())==sha(oldindex)}))
