import pathlib,subprocess,json,hashlib,shutil,gzip
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
D=pathlib.Path('/mnt/development/projects/diagnostics/native-owned-snapshot-composition-20261123')
BASE='5fc0a95dc1f8573ff55dfcae1f4ae04c1a7cee33'
DONOR='10e924941435a486b1e4e8290399c045045ecc8e'
DONOR_BASE='e4edea19ce716280f4087f8b9571ad2b4f6f94c5'
DOC='docs/validation/20261123-native-owned-snapshot-composition'
QDOC='docs/validation/20261123-native-owned-snapshot'
CHAIN=['d6e52e3a9d6e4a8d3fc266ae0fe586cd20e3eeb2','26035ff40275693606d51978aff4b2d045c7ac0e','44e09f96353186e56ecdbefe0d0cd7e059097d9d',DONOR]
def git(*args):
 return subprocess.check_output(['git','-c','gc.auto=0','-c','user.name=davidpovarsky','-c','user.email=your-email@example.com','-C',str(W),*args],stderr=subprocess.PIPE,timeout=80)
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
def tree(ref):
 result={}
 for row in git('ls-tree','-r','-z',ref).split(b'\0'):
  if row:
   m,n=row.split(b'\t',1);result[n.decode()]=m.decode()
 return result
assert shutil.disk_usage(W).free>=2520000000
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain=v1')
assert git('rev-list','--reverse',DONOR_BASE+'..'+DONOR).decode().splitlines()==CHAIN
raw=git('show',DONOR+':'+QDOC+'/qualification.json')
assert hashlib.sha256(raw).hexdigest()=='bdb429d7e196f8faa85b7b4ef3844b942dac00dd088e76f5549dd3b3e98a8789'
q=json.loads(raw)
assert q['status']=='PASS_SCOPE_NATIVE_STORAGE_LIFETIME_ONLY'
assert q['qualified_distinct_methods']==4 and q['original_first_run_passes']==3 and q['original_first_run_failures']==1 and q['failed_only_continuation_passes']==1
assert q['old_controls_replayed']==0 and q['passed_methods_replayed']==0
assert len({r['method'] for r in q['method_receipts']})==4
assert all(q[k] is False for k in ['accountSessionACLAuthorized','filePayloadCoverageComplete','hasNativeSourceAdmission','permitsDestinationWrites','semanticIdentityCensusComplete'])
before=tree(BASE);donor=tree(DONOR);db=tree(DONOR_BASE)
changed={p for p in set(donor)|set(db) if donor.get(p)!=db.get(p)}
assert all(p.startswith(('Tools/AnyEngineValidation/native_owned_snapshot/',QDOC+'/')) for p in changed)
assert all(p not in before for p in changed)
copy_checks=[]
for name,row in q['failed_only_original_files'].items():
 if 'original_private_path' in row:
  assert row['raw_published'] is False
  continue
 p=row.get('compressed_copy',QDOC+'/failed-shutdown-attempt1/'+name)
 assert p in donor,p
 b=git('show',DONOR+':'+p)
 if 'compressed_copy' in row:
  assert len(b)==row['copy']['bytes'] and hashlib.sha256(b).hexdigest()==row['copy']['sha256']
  b=gzip.decompress(b)
 assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],p
 copy_checks.append(p)
for path,expected in [(q['fixed_source_review']['path'],q['fixed_source_review']['sha256']),(q['original_private_frames']['audit_path'],q['original_private_frames']['audit_sha256'])]:
 assert hashlib.sha256(git('show',DONOR+':'+path)).hexdigest()==expected
save(D/'intent.json',{'base':BASE,'donor':DONOR,'commits':CHAIN,'changed_paths':sorted(changed),'verified_public_original_copies':copy_checks,'tests_replayed':0,'builds':0})
git('cherry-pick',*CHAIN)
current=tree('HEAD')
assert all(current.get(p)==donor.get(p) for p in changed)
assert all(current.get(p)==row for p,row in before.items())
doc=W/DOC;doc.mkdir(parents=True)
record={'status':'QUALIFIED_NATIVE_LIFETIME_SLICE_COMPOSED','base':BASE,'donor':DONOR,'native_source':q['current_native_sha'],'donor_commits':CHAIN,'qualification_sha256':hashlib.sha256(raw).hexdigest(),'qualified_distinct_native_methods':4,'retained_original_named_passes':3,'failed_only_named_passes':1,'original_aggregate_failure_retained':True,'verified_public_original_copy_count':len(copy_checks),'all_prior_release_page_ui_sources_unchanged':True,'tests_replayed_now':0,'builds_now':0,'remaining_acceptance':q['remaining_acceptance'],'account_session_acl_semantic_file_destination_acceptance':False,'integrator_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
save(doc/'qualification.json',record)
(doc/'integrate-native-lifetime.py').write_bytes(pathlib.Path(__file__).read_bytes())
git('add','--',DOC)
git('commit','-m','Compose native lifetime evidence retaining original three plus failed-only pass')
head=git('rev-parse','HEAD').decode().strip();after=tree(head)
assert all(after.get(p)==row for p,row in before.items())
assert all(p in changed or p.startswith(DOC+'/') for p in set(after)-set(before))
assert not git('status','--porcelain=v1')
result={'status':'PASS_NATIVE_LIFETIME_SOURCE_COMPOSITION','head':head,'base':BASE,'donor':DONOR,'new_paths':len(set(after)-set(before)),'source_and_original_evidence_retained':True,'old_tests_replayed':0,'builds':0,'free_bytes':shutil.disk_usage(W).free}
save(D/'integration-result.json',result)
print(json.dumps(result))
