import pathlib,hashlib,json,gzip,tarfile,stat
A=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-projected-graph-attempt1")
def get(n,h):
 b=(A/n).read_bytes();assert hashlib.sha256(b).hexdigest()==h;return b
ib=get("ram-inventory.json.gz","7e71cc6913fd3728768b3a793a9b8f7d056c9b3f37679af989fefb208fe398de")
inv=json.loads(gzip.decompress(ib));ap=A/"ram-originals.tar.gz"
assert hashlib.sha256(ap.read_bytes()).hexdigest()=="dc557d7ff904e8bd1fed9a536ceb834334ef2310128a9fa4a0094c4bb3ce7154"
expected={k:("file",v) for k,v in inv["files"].items()};expected.update({k:("directory",v) for k,v in inv["directories"].items()})
seen=set();size=0;g=[]
with ap.open("rb") as original:
 with gzip.GzipFile(fileobj=original,mode="rb") as z:
  with tarfile.open(fileobj=z,mode="r|") as tar:
   for m in tar:
    assert m.name in expected and m.name not in seen
    q=pathlib.PurePosixPath(m.name);assert not q.is_absolute() and ".." not in q.parts and q.as_posix()==m.name
    kind,v=expected[m.name]
    assert m.uid==int(v["st_uid"]) and m.gid==int(v["st_gid"]) and m.mode==stat.S_IMODE(int(v["st_mode"]))
    if kind=="directory":assert m.isdir() and m.size==0
    else:
     assert m.isreg() and m.size==int(v["st_size"])
     f=tar.extractfile(m);assert f is not None;h=hashlib.sha256();count=0
     with f:
      for b in iter(lambda:f.read(65536),b""):h.update(b);count+=len(b)
     assert count==m.size and h.hexdigest()==v["sha256"];size+=count
     if v["classification"]=="validated_generated_test_main":
      p=A/"generated-test-main"/(v["sha256"]+".go");b=p.read_bytes()
      assert len(b)==count and hashlib.sha256(b).hexdigest()==v["sha256"]
      g.append({"ram_member":m.name,"preserved_path":str(p),"bytes":len(b),"sha256":v["sha256"]})
    seen.add(m.name)
  tail=0
  while True:
   b=z.read(65536)
   if not b:break
   assert not any(b);tail+=len(b)
assert seen==set(expected)
priv=[];observations=[]
for p in sorted(A.glob("*.json")):
 v=json.loads(p.read_bytes())
 if "cleanup_privilege" in v:
  c=v["cleanup_privilege"];assert c["restored"] and c["ordinary_after"]==c["ordinary_before"]
  assert c["ordinary_before"]["uids"]==[1001,1001,0] and c["during_cleanup"]["uids"]==[1001,0,0]
  assert v.get("cleanup_error") is None and v.get("owned_group_absent") is True
  priv.append({"path":p.name,"pid":v.get("pid"),"pgid":v.get("pgid"),"restored":True,"primary_error":v.get("primary_error")})
print(json.dumps({"archive_readback":"PASS","members":len(seen),"files":len(inv["files"]),"directories":len(inv["directories"]),"payload_bytes":size,"gzip_eof":True,"padding_zero":True,"generated":g,"privilege_receipts":priv,"all_owned_receipts_restored":len(priv),"no_payload_extraction":True},sort_keys=True))
