#!/usr/bin/env python3
"""Correct only UI-specific absent-source-map admission; retain the original native inventory and auditor failure."""
from pathlib import Path, PurePosixPath
import hashlib,json,os,stat,tarfile,zipfile,time,shutil,collections
ROOT=Path("/mnt/development/projects/diagnostics/semantic-page-pinned-consumer-20261123/terminal-audit")
ZIP=ROOT/"artifact-14794983588.zip"
OUT=ROOT/"mounted-products-inventory"
ORIGIN="68148339c275268795360d71d519a5baf003adf8"
EXPECTED_ZIP_SHA="082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46"
RUN="45116855451"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(path,value):
 with path.open("x") as f:f.write(json.dumps(value,indent=2,sort_keys=True)+"\n")
def relative(name):
 p=PurePosixPath(name)
 assert isinstance(name,str) and name and not p.is_absolute() and "\\" not in name and "\0" not in name
 assert all(part not in ("",".","..") for part in name.split("/")) and p.as_posix()==name
 return p
class CompressedReader:
 def __init__(self,source):self.source=source;self.h=hashlib.sha256();self.count=0
 def read(self,size=-1):
  value=self.source.read(size);self.h.update(value);self.count+=len(value);return value
def one(z,label,prefix,descriptor):
 manifest_path=OUT/prefix/"manifest.json"
 manifest=json.loads(manifest_path.read_text())
 assert manifest["source_sha"]==ORIGIN and manifest["run_id"]==RUN and manifest["run_attempt"]=="1"
 assert manifest["status"]=="OBSERVED_PRODUCTS_ARCHIVED_BEFORE_ADMISSION"
 assert manifest["capture_phase"]=="AFTER_BUILD_BEFORE_ADMISSION"
 assert manifest["build_reuse_enabled"] is manifest["native_acceptance_reused"] is manifest["ui_acceptance_reused"] is False
 flags=manifest["build_flags"]
 assert any("-D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1" in v and "-D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1" in v for v in flags)
 assert "ONLY_ACTIVE_ARCH=YES" in flags and "ENABLE_TESTABILITY=YES" in flags
 rows=manifest["products"];assert 0<len(rows)<100000
 assert all(v["kind"] in ("file","directory") for v in rows.values())
 archive_name=prefix+"/BuildProducts.tar.gz";info=z.getinfo(archive_name)
 assert info.file_size==manifest["archive_bytes"] and info.file_size<=2*1024**3
 expected_descriptor_sha=sha((OUT/descriptor).read_bytes())
 seen=set();folded=set();verified={};root_descriptors=[];source_input=None;total=0
 started=time.time()
 with z.open(info) as zipped:
  incoming=CompressedReader(zipped)
  with tarfile.open(fileobj=incoming,mode="r|gz") as packed:
   for member in packed:
    assert shutil.disk_usage("/mnt/development").free>=2500000000
    name=member.name;path=relative(name)
    assert name in rows and name not in seen and name.casefold() not in folded
    assert name=="Build/PinkhaSourceInputs.json" or name=="Build/Products" or name.startswith("Build/Products/")
    seen.add(name);folded.add(name.casefold());wanted=rows[name]
    assert type(wanted.get("mode")) is int and 0<=member.mode<=0o777 and wanted["mode"]==member.mode
    if member.isdir():
     assert wanted["kind"]=="directory"
     verified[name]={"kind":"directory","mode":member.mode}
    else:
     assert member.isfile() and wanted["kind"]=="file" and wanted["bytes"]==member.size
     assert 0<=member.size<=2*1024**3
     total+=member.size;assert total<=6*1024**3
     save_source=name=="Build/PinkhaSourceInputs.json"
     save_descriptor=path.parent==PurePosixPath("Build/Products") and path.suffix==".xctestrun"
     keep=save_source or save_descriptor
     if keep:assert member.size<=64*1024**2
     chunks=[];h=hashlib.sha256();count=0
     with packed.extractfile(member) as stream:
      for chunk in iter(lambda:stream.read(1024**2),b""):
       h.update(chunk);count+=len(chunk)
       if keep:chunks.append(chunk)
     assert count==member.size and h.hexdigest()==wanted["sha256"],name
     verified[name]={"kind":"file","mode":member.mode,"bytes":count,"sha256":h.hexdigest()}
     if keep:
      raw=b"".join(chunks)
      target=OUT/(label+"-"+("source-inputs-original.json" if save_source else path.name))
      if target.exists():assert target.read_bytes()==raw
      else:
       with target.open("xb") as f:f.write(raw)
      if save_source:
       parsed=json.loads(raw)
       source_input={"archive_path":name,"saved_path":str(target),"sha256":h.hexdigest(),"bytes":count,"json_top_type":type(parsed).__name__,"json_top_keys":list(parsed)[:15] if isinstance(parsed,dict) else None}
      else:
       root_descriptors.append({"archive_path":name,"saved_path":str(target),"sha256":h.hexdigest(),"bytes":count,"matches_original_descriptor":h.hexdigest()==expected_descriptor_sha})
    if len(seen)%500==0:print(json.dumps({"scope":label,"entries_verified":len(seen),"bytes_hashed":total}),flush=True)
  while incoming.read(1024**2):pass
  assert incoming.count==manifest["archive_bytes"] and incoming.h.hexdigest()==manifest["archive_sha256"]
 assert seen==set(rows)
 assert label=="ui" and source_input is None and manifest.get("source_inputs_present") is False
 assert "Build/PinkhaSourceInputs.json" not in rows
 assert sum(d["matches_original_descriptor"] for d in root_descriptors)==1
 write(OUT/(label+"-verified-entries.json"),verified)
 report={"status":"PASS_STREAMED_ORIGINAL_PRODUCTS_BYTES","scope":label,"source_sha":ORIGIN,"run_id":RUN,"run_attempt":"1","archive_member":archive_name,"archive_sha256":manifest["archive_sha256"],"compressed_bytes":manifest["archive_bytes"],"manifest_sha256":sha(manifest_path.read_bytes()),"entries":len(seen),"kinds":dict(collections.Counter(v["kind"] for v in verified.values())),"file_bytes_hashed":total,"links":0,"every_entry_type_mode_size_and_digest_verified":True,"case_collisions":0,"outside_members":0,"original_descriptor_sha256":expected_descriptor_sha,"root_descriptors":root_descriptors,"source_inputs":source_input,"entry_proof_sha256":sha((OUT/(label+"-verified-entries.json")).read_bytes()),"full_products_restored":False,"elapsed_seconds":time.time()-started}
 write(OUT/(label+"-inventory.json"),report)
 print(json.dumps({"scope":label,"status":report["status"],"entries":len(seen),"file_bytes_hashed":total,"links":0}),flush=True)
 return report
def main():
 before=ZIP.stat();assert stat.S_ISREG(before.st_mode) and not ZIP.is_symlink() and before.st_size==703289417
 old_receipt=(OUT/"native-inventory.json").read_bytes()
 assert sha(old_receipt)=="c29ce976abee08133c34336ba77d6e5499f061fd97217e5146a28dabc610a5f7"
 native=json.loads(old_receipt);assert native["status"]=="PASS_STREAMED_ORIGINAL_PRODUCTS_BYTES"
 assert sha((OUT/"native-verified-entries.json").read_bytes())==native["entry_proof_sha256"]
 failed=(OUT/"streaming-command.json").read_bytes()
 assert sha(failed)=="774a4e5892bc8f780ab9c12a2903064be80d41a3b8e8575d60d31d3be2018571"
 failed_value=json.loads(failed);assert failed_value["returncode"]==1
 assert sha((OUT/"streaming-original.log").read_bytes())==failed_value["original_log_sha256"]
 with zipfile.ZipFile(ZIP) as z:ui=one(z,"ui","ui-runner/semantic-page154-early-products","ui-runner/original.xctestrun")
 after=ZIP.stat()
 assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
 report={"status":"PASS_NATIVE_RETAINED_AND_UI_ORIGINAL_PRODUCTS_STREAMED","outer_zip":{"path":str(ZIP),"bytes":before.st_size,"sha256":EXPECTED_ZIP_SHA,"verification_owner":"sdk_ci; prior VERIFIED_ORIGINAL_ZIP handoff and download-result.json","inode":before.st_ino,"mtime_ns":before.st_mtime_ns,"unchanged_during_ui_stream":True},"results":[native,ui],"native_retained_without_rescan":{"receipt_sha256":sha(old_receipt),"entry_proof_sha256":native["entry_proof_sha256"]},"preserved_first_auditor_failure":{"receipt_sha256":sha(failed),"log_sha256":failed_value["original_log_sha256"],"reason":"Auditor incorrectly required a source-input file in the UI archive; original manifest explicitly records absence","native_inventory_pass_unchanged":True},"inspector_sha256":sha(Path(__file__).read_bytes()),"artifact_id":14794983588,"product_tests_executed":0,"products_restored":0,"admission_written":False,"free_bytes":shutil.disk_usage("/mnt/development").free}
 write(OUT/"streaming-inventory.json",report)
 print(json.dumps({"status":report["status"],"receipt":str(OUT/"streaming-inventory.json"),"sha256":sha((OUT/"streaming-inventory.json").read_bytes()),"free_bytes":report["free_bytes"]}),flush=True)
if __name__=="__main__":main()
