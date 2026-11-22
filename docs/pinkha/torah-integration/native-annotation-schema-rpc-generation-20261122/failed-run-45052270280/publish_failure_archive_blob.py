import base64,hashlib,json,pathlib,shutil,subprocess
archive=pathlib.Path(r"C:\Users\DAVID\Code\otzaria-schema-rpc-generation-observer-20261122-45052270280\generation-artifact.zip")
raw=archive.read_bytes()
assert len(raw)==866386
assert hashlib.sha256(raw).hexdigest()=="9e12af3ae19e07b06cc3ee4215d218b62e0092525921cece5c81759aac802b01"
expected=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
gh=shutil.which("gh")
assert gh
done=subprocess.run([gh,"api","--method","POST","repos/davidpovarsky/anytype-swift/git/blobs","--input","-"],input=json.dumps({"encoding":"base64","content":base64.b64encode(raw).decode()}).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
assert done.returncode==0, "GitHub blob creation failed: "+str(done.returncode)
result=json.loads(done.stdout)
assert result["sha"]==expected
receipt={"status":"EXACT_FAILURE_ARCHIVE_BLOB_STORED","repository":"davidpovarsky/anytype-swift","source":str(archive),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"git_blob":expected,"ref_changed":False}
(archive.parent/"ARCHIVE_BLOB_PUBLICATION.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt))
