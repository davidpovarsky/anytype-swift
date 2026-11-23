import pathlib,json,hashlib,os,datetime,stat,ast,subprocess,gzip
D=pathlib.Path(__file__).parent
P=json.loads((D/'prepared-copy-and-readback-v1.json').read_bytes())
source=P['source'];destination=P['destination_readback'];copy=P['copy_receipt']
p=pathlib.Path(source['path'])
expected_metadata={key:int(value) for key,value in source['metadata'].items()}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def h(b):return hashlib.sha256(b).hexdigest()
def save(path,obj):
 b=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()
 with path.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return h(b)
def metadata(st):return {'device':st.st_dev,'inode':st.st_ino,'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'nlink':st.st_nlink,'bytes':st.st_size,'allocated':st.st_blocks*512,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}
assert p==pathlib.Path('/mnt/development/projects/diagnostics/semantic-page-pinned-consumer-20261123/terminal-audit/artifact-14794983588.zip')
assert p.resolve()==p and p.is_file() and not p.is_symlink()
assert source['status']=='SOURCE_ARCHIVE_BYTES_VERIFIED_READ_ONLY'
assert copy['status']=='PASS_IMMUTABLE_COPY_FULL_ORIGINAL_HASH' and copy['oracle_source_mutations']==0
assert destination['status']=='PASS_INDEPENDENT_FULL_DESTINATION_READBACK'
assert source['sha256']==copy['sha256']==destination['sha256']=='082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46'
assert expected_metadata['bytes']==copy['bytes']==destination['bytes']==703289417
assert destination['ntfs_file_id']==copy['ntfs_file_id']=='File ID is 0x0000000000000000001300000019eefb'
assert destination['path']==copy['destination']==r'C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\semantic-page-original-45116855451-1\original-14794983588.zip'
assert destination['owner_sid']=='S-1-5-21-2914620446-786530585-2031499938-1001'
assert destination['file_sddl']==copy['file_security']['sddl'] and destination['directory_sddl']==copy['directory_security']['sddl']
assert destination['readonly'] is True and destination['non_reparse'] is True and destination['owned_transport_absent'] is True
verified=datetime.datetime.fromisoformat(destination['verified_at'].replace('Z','+00:00'))
assert 0<=(datetime.datetime.now(datetime.timezone.utc)-verified).total_seconds()<900
peer_raw=(D/'peer/qualification.json').read_bytes()
assert h(peer_raw)==P['peer_qualification_sha256']=='7ead8e422e93af4629ed34836ba89c75d44dc837a5ead13c9302748e8b83bb72'
peer=json.loads(peer_raw)
assert peer['status']=='QUALIFIED_PROVENANCE_AND_FIXED_INPUT_DEPENDENCIES_ROOT_OWNS_COPY_AND_FINAL_RELOCATION_GATES'
assert peer['source']['path']==source['path'] and peer['source']['sha256']==source['sha256'] and peer['source']['bytes']==str(expected_metadata['bytes'])
assert peer['source']['peer_metadata_matches_root_report'] is True
assert peer['origin']['source_sha']==source['app_source']=='68148339c275268795360d71d519a5baf003adf8'
assert peer['origin']['artifact_id']==str(source['artifact_id']) and peer['origin']['run_id']==str(source['origin_run'])
assert peer['origin']['run_attempt']==str(source['origin_attempt'])
for name,proof in peer['supporting_files'].items():
 raw=(D/'peer'/name).read_bytes();assert len(raw)==proof['bytes'] and h(raw)==proof['sha256']
 if name.endswith('.gz'):
  expanded=gzip.decompress(raw);assert len(expanded)==proof['uncompressed_bytes'] and h(expanded)==proof['uncompressed_sha256']
for name,proof in peer['original_receipt_bindings'].items():
 raw=pathlib.Path(proof['path']).read_bytes();assert len(raw)==proof['bytes'] and h(raw)==proof['sha256']
main=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
assert subprocess.check_output(['git','--no-optional-locks','-C',str(main),'rev-parse','HEAD'],text=True).strip()==peer['current_controller']['git_source']=='c0c1f851f80322c9f532e86505047498dfaf1adf'
assert not subprocess.check_output(['git','--no-optional-locks','-C',str(main),'status','--porcelain=v1'],text=True).strip()
admission=main/source['pinned_admission'];admission_raw=admission.read_bytes()
assert h(admission_raw)==peer['current_controller']['admission_sha256']=='17c37d842009b23d50ab2222383c1f025242aa2e61f1828cf1bc1a346b5ed7e5'
assert subprocess.check_output(['git','--no-optional-locks','-C',str(main),'show',source['pinned_admission_source']+':'+source['pinned_admission']])==admission_raw
admitted=json.loads(admission_raw)
assert admitted['artifact_sha256']==source['sha256'] and admitted['artifact_id']==source['artifact_id'] and admitted['artifact_bytes']==expected_metadata['bytes']
assert str(admitted['consumer_run'])==str(source['origin_run']) and str(admitted['consumer_attempt'])=='1' and admitted['consumer_sha']==source['app_source']
for rel,key in [('Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py','controller_sha256'),('Tools/PinkhaSemanticAnchorWire/apple_mounted/mounted_contract.py','contract_sha256'),('.github/workflows/pinkha-semantic-page-apple-mounted.yml','workflow_sha256')]:
 assert h((main/rel).read_bytes())==peer['current_controller'][key]
assert peer['current_controller']['requires_local_Oracle_archive_path'] is False
assert peer['fixed_scope']['candidate_path_or_parent_or_basename_hits']==0 and peer['fixed_scope']['all_current_Git_hashes_equal_original_control'] is True
manifest_raw=(main/'docs/validation/20261123-semantic-mounted-kernel/control-inputs.json').read_bytes()
assert h(manifest_raw)==peer['fixed_scope']['qualified_manifest_sha256']=='3525d3bb985dbbbe4de16d34023f7df354f33ac67d659e247567f7415cd335cb'
manifest=json.loads(manifest_raw);assert len(manifest['files'])==35
for rel,proof in manifest['files'].items():assert h((main/rel).read_bytes())==proof['sha256']
before=p.stat();assert metadata(before)==expected_metadata
with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest==source['sha256'] and metadata(p.stat())==expected_metadata
prior=pathlib.Path('/mnt/development/projects/diagnostics/completed-worktree-docs-capacity-round8-20261123/root_apply_candidate_attempt2.py')
raw=prior.read_bytes();assert h(raw)=='7de4d0050ceccfe2c7ae84c11552abe0ed79b5774ee7bc1c95e59d7d239b64d4'
tree=ast.parse(raw)
scanner=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='scanner' for t in n.targets))
anc=[];pid=os.getpid()
while pid>1 and pid not in anc:
 anc.append(pid)
 try:pid=int(pathlib.Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[1])
 except (FileNotFoundError,ValueError):break
scanproc=subprocess.run(['sudo','-n','python3','-B','-c',scanner,json.dumps([str(p)]),json.dumps(anc)],capture_output=True,timeout=30)
(D/'process-scan.stdout').write_bytes(scanproc.stdout);(D/'process-scan.stderr').write_bytes(scanproc.stderr)
assert scanproc.returncode==0
scan=json.loads(scanproc.stdout)
assert scan['uid']==0 and not scan['hits'] and not scan['denied']
assert metadata(p.stat())==expected_metadata
free_before=os.statvfs(p.parent).f_bavail*os.statvfs(p.parent).f_frsize
restore='Retain the sealed private Windows original at its recorded host/path/NTFS identity. To restore Oracle materialization, verify the current destination full SHA256/size/ACL/fileID, stream it into a new temporary file beside the original Oracle path, verify full SHA256 and703289417 bytes, set mode0664 and original uid1001/gid1002 and mtime1795416720054790888ns, fsync and atomically create the original path only if absent. Never overwrite a later file. A restored inode/ctime will be new; historical original identity remains recorded here. No GitHub redownload or product rebuild is required.'
intent={'protocol':'immutable-original-archive-relocation-v1','at':now(),'operation':'REMOVE_ONLY_VERIFIED_REDUNDANT_LOCAL_ARCHIVE_COPY','source':source,'destination':destination,'destination_copy_receipt_sha256':destination['receipt_sha256'],'reader_check':scan,'peer_qualification_sha256':h(peer_raw),'current_frozen_input_dependency':'NONE_CONFIRMED_BY_PAGE35_CURRENT_GIT_FIXED_RECORDS_AND_ALL_CURRENT_OWNERS','all_project_code_git_worktrees_and_extracted_products_untouched':True,'all_archive_bytes_preserved_at_verified_destination':True,'restoration':restore}
intent_sha=save(D/'relocation-intent.json',intent)
location=p.with_name(p.name+'.location.json')
location_record={'protocol':'immutable-original-archive-location-v1','recorded_at':now(),'original_path':str(p),'original_metadata':source['metadata'],'artifact_id':14794983588,'run_id':45116855451,'source_sha':source['app_source'],'sha256':digest,'bytes':703289417,'retained_original_host':'host_7ec8382e82747448 / DAVID_AND_GOLDY','retained_original_path':destination['path'],'retained_original_ntfs_file_id':destination['ntfs_file_id'],'retained_original_owner_sid':destination['owner_sid'],'retained_original_readonly':True,'verified_readback_at':destination['verified_at'],'intent':str(D/'relocation-intent.json'),'intent_sha256':intent_sha,'completion_receipt':str(D/'relocation-receipt.json'),'restoration':restore}
location_sha=save(location,location_record)
for directory in [D,p.parent]:
 fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
assert metadata(p.stat())==expected_metadata
p.unlink()
fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
assert not p.exists() and location.is_file()
free_after=os.statvfs(p.parent).f_bavail*os.statvfs(p.parent).f_frsize
receipt={'status':'PASS_BYTE_IDENTICAL_ORIGINAL_ARCHIVE_RELOCATION','peer_qualification_sha256':h(peer_raw),'completed_at':now(),'sha256':digest,'bytes':703289417,'original_archive_preserved':True,'source':str(p),'destination':destination['path'],'destination_ntfs_file_id':destination['ntfs_file_id'],'destination_readback_sha256':destination['sha256'],'destination_owner_and_private_acl_verified':True,'local_redundant_copy_removed':True,'lost_archive_bytes':0,'allocated_bytes_recovered':before.st_blocks*512,'code_git_products_worktree_mutations':0,'old_tests_or_builds':0,'current_copy_attempt_failed':False,'prior_relocation_failures_retained':True,'reader_check_uid':scan['uid'],'reader_check_hits':len(scan['hits']),'reader_check_denied':len(scan['denied']),'location_record':str(location),'location_record_sha256':location_sha,'intent_sha256':intent_sha,'free_bytes_before':free_before,'free_bytes_after':free_after,'normal_write_reserve_bytes_unchanged':2500000000,'normal_write_reserve_available_after':free_after>=2500000000,'restoration':restore}
rh=save(D/'relocation-receipt.json',receipt)
print(json.dumps({**receipt,'receipt_sha256':rh},sort_keys=True),flush=True)
