import pathlib,json,hashlib,subprocess,stat,os,datetime,ast
D=pathlib.Path(__file__).parent
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-page-mounted-kernel-20261123')
M=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
E=pathlib.Path('/mnt/development/projects/evidence/semantic-mounted-kernel-20261123')
N='docs/validation/20261123-semantic-mounted-kernel'
S='b217a4646dfa5cea28c8dc4f97e1cc848845e22b';F='bdaebf04a6b3938f4fffc62e8abcd96975bae46f';B='399c19b48daacdf796216b3c1883c2d1de6f5b71'
def h(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def git(w,*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(w),*args])
def textgit(w,*args):return git(w,*args).decode().strip()
assert os.statvfs(M).f_bavail*os.statvfs(M).f_frsize>=2500000000
assert textgit(W,'rev-parse','HEAD')==F and not textgit(W,'status','--porcelain=v1')
assert textgit(M,'rev-parse','HEAD')==B and not textgit(M,'status','--porcelain=v1')
Q=W/N
qraw=(Q/'qualification.json').read_bytes();q=json.loads(qraw)
assert h(qraw)=='7eca47c39ff2ce286b865139743154c1efa1121e4752a80f5ad9215403ecd155'
iraw=(Q/'evidence-index.json').read_bytes();index=json.loads(iraw)
assert h(iraw)==q['evidence_index_sha256']=='bb0832ca10538ab6e5496517df375f88ea89bacc5544082a745816347cf76628'
manifest_raw=(Q/'control-inputs.json').read_bytes();manifest=json.loads(manifest_raw)
assert h(manifest_raw)==q['manifest_sha256']=='3525d3bb985dbbbe4de16d34023f7df354f33ac67d659e247567f7415cd335cb'
audit_raw=(E/'audit1/audit.json').read_bytes();audit=json.loads(audit_raw)
assert h(audit_raw)==q['read_only_audit']['sha256']=='18703616b3a3a4c160c79673f150c64cca145d2072011701119961881c3b3708'
assert h((E/'audit1/audit.py').read_bytes())==q['read_only_audit']['reader_sha256']=='836e88c3843fa6b9e7e9c1178b6a03ec8c3577e842ad09e8cbf616493e701d26'
copied=0;guard_records=0;specs={}
for rel,v in index['files'].items():
 p=Q/rel;b=p.read_bytes()
 assert p.is_file() and not p.is_symlink() and len(b)==v['bytes'] and h(b)==v['sha256']
 assert stat.S_IMODE(p.stat().st_mode)==v['mode']
 specs[F+':'+N+'/'+rel]=b
 if 'original_path' in v:
  op=pathlib.Path(v['original_path']);assert op.is_file() and not op.is_symlink()
  assert op.read_bytes()==b and stat.S_IMODE(op.stat().st_mode)==v['mode'] and v['copy_byte_and_mode_exact'] is True
  copied+=1
 else:
  assert rel in ['audit-capacity-guard-observation.json','audit-capacity-guard-tool-output.txt']
  guard_records+=1
assert copied==28 and guard_records==2
A=E/'attempt1'
for rel,v in audit['original_files'].items():
 p=A/rel;b=p.read_bytes()
 assert len(b)==v['bytes'] and h(b)==v['sha256'] and stat.S_IMODE(p.stat().st_mode)==v['mode']
 assert (Q/'attempt1'/rel).read_bytes()==b
assert len(audit['original_files'])==20
before=(A/'source-before.json').read_bytes()
assert before==(A/'source-after.json').read_bytes() and h(before)=='f48bf50373d44f6d096e4c0f58ce2923266daa4b5f11d90f09427d03616fec56'
sources=json.loads(before)['inputs'];assert len(sources)==35 and set(sources)==set(manifest['files'])
new_paths={'Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_kernel_quiescence.py',N+'/run_control.py'}
supervisor='Tools/PinkhaSimulatorGate/run_owned_single_lane.py'
for rel,v in sources.items():
 p=W/rel;b=p.read_bytes();st=p.stat()
 actual={'bytes':len(b),'device':st.st_dev,'inode':st.st_ino,'mode':stat.S_IMODE(st.st_mode),'mtime_ns':st.st_mtime_ns,'sha256':h(b)}
 assert actual==v,rel
 mv=manifest['files'][rel];assert mv['bytes']==len(b) and mv['sha256']==h(b)
 specs[S+':'+rel]=b;specs[F+':'+rel]=b
 if rel not in new_paths and rel!=supervisor:
  assert (M/rel).read_bytes()==b,rel
  specs[B+':'+rel]=b
loaded_raw=(A/'loaded-sources-before.json').read_bytes()
for rel in ['loaded-sources-after.json','originals/actual-import-source-closure-before.json','originals/actual-import-source-closure-after.json']:
 assert (A/rel).read_bytes()==loaded_raw
loaded=json.loads(loaded_raw)
assert len(loaded)==34 and set(loaded)==set(sources)-{'Tools/PinkhaNativeDerived/package_evidence.py'}
assert h(loaded_raw)=='4d8b3e30867ebdf94db8ecfdb3859b498e8c930b89a599e1644e19a7a80a0d5b'
for rel,v in loaded.items():assert v['sha256']==sources[rel]['sha256'] and v['aliases']
old=(M/supervisor).read_bytes();new=(W/supervisor).read_bytes()
old_line=b'if cleanup_profile in ("sdk06-enumeration", "sdk06-qualified", owned.COHERENT_HEART_PROFILE):'
new_line=b'if cleanup_profile in ("sdk06-enumeration", "sdk06-qualified", owned.COHERENT_HEART_PROFILE, "semantic-page154"):'
assert old.count(old_line)==new.count(new_line)==1 and new.replace(new_line,old_line,1)==old
assert h(old)=='627c5b3dde88e11aaf89d157cf4a05152e42a7fc6ba9545fac13607cf7923d51'
assert h(new)=='5d976901b73b5bc5e519ead3a89952220d8149e710561d92acc9f36e46247414'
def kernel(raw):
 lines=raw.decode().splitlines(keepends=True);tree=ast.parse(raw)
 n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_sdk06_kernel_group_observation')
 return ''.join(lines[n.lineno-1:n.end_lineno]).encode()
assert kernel(new)==kernel(old)
test=(W/'Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_kernel_quiescence.py').read_bytes()
assert h(test)==q['unchanged_test_sha256']=='f8150ef073a21f67a7b8b08f4ffb0611855269a5d275fbaae077f7a743cdc642'
assert b'self.assertIs(captured.exception, primary["error"])' in test
docs=git(W,'ls-tree','-r','-z',F,'--',N).split(b'\0')
doccount=0
for entry in docs:
 if not entry:continue
 meta,path=entry.split(b'\t',1);mode,kind,blob=meta.split();rel=path.decode()
 assert kind==b'blob' and mode==b'100644'
 specs[F+':'+rel]=(W/rel).read_bytes();doccount+=1
assert doccount==47
p=subprocess.run(['git','--no-optional-locks','-C',str(W),'cat-file','--batch'],input=('\n'.join(specs)+'\n').encode(),capture_output=True,timeout=30)
assert p.returncode==0,p.stderr.decode()
pos=0
for spec,expected in specs.items():
 end=p.stdout.index(b'\n',pos);header=p.stdout[pos:end].split();assert len(header)==3 and header[1]==b'blob',spec
 size=int(header[2]);pos=end+1;actual=p.stdout[pos:pos+size];pos+=size
 assert p.stdout[pos:pos+1]==b'\n';pos+=1
 assert actual==expected,spec
assert pos==len(p.stdout)
result=read(A/'result.json')
assert result['source_sha']==S and result['status']=='PASS_ONE_NEW_MOUNTED_CALLER_CONTROL'
for key in ['errors','failures','skipped','new_app_or_ui_builds','old_control_methods_reexecuted','apple_commands','product_methods']:assert result[key]==0,key
method='test_actual_mounted_consumer_keeps_owned_kernel_deadline_and_first_error'
assert result['tests_run']==1 and result['selected_methods']==[method]
assert result['source_inputs_unchanged'] is True and result['loaded_sources_unchanged'] is True
events=read(A/'events.json');assert len(events)==2 and [v['event'] for v in events]==['START','PASS']
assert all(v['test']=='test_mounted_kernel_quiescence.MountedPageKernelCompositionTests.'+method for v in events)
assert events[0]['time']<events[1]['time']
log=(A/'controls.log').read_text();assert 'Ran 1 test in 0.299s' in log and log.endswith('\nOK\n')
complete=read(A/'originals/actual-complete-proof.json');ce=read(A/'originals/actual-complete/execution.json')['commands'][0]
timed=read(A/'originals/actual-timeout-proof.json');te=read(A/'originals/actual-timeout/execution.json')['commands'][0]
assert complete['kind']=='ACTUAL_OWNED_CHILD_AND_UNMODIFIED_KERNEL_QUERY' and complete['actual_pid']==complete['actual_pgid']==ce['worker_pid']==2666229
assert ce['status']=='COMPLETE' and ce['return_code']==0 and ce['owned_group_cleanup']=='TERM_THEN_KILL'
assert ce['owned_group_quiescence']==complete['quiescence']
assert complete['quiescence']['status']=='PASS' and complete['quiescence']['live_members']==0
def actual_absence(v,pid):
 assert v['pgid']==pid and v['operation']=='os.killpg' and v['signal']==0 and v['outcome']=='ABSENT_ESRCH' and v['errno']==3
 assert v['before_monotonic']<=v['after_monotonic']<=v['deadline_monotonic']
 assert 0<v['deadline_monotonic']-v['before_monotonic']<=10
actual_absence(complete['quiescence']['kernel_group_observation'],2666229)
assert timed['kind']=='ACTUAL_COMMAND_TIMEOUT_WITH_SEPARATELY_INJECTED_QUERY_ERROR'
assert timed['actual_pid']==te['worker_pid']==2666231 and te['status']=='TIMED_OUT' and te['return_code']==-15 and te['timeout_seconds']==0.2
assert te['error_type']==timed['primary_type']=='TimeoutExpired' and timed['primary_object_preserved'] is True and timed['original_projection_stays_failed'] is True
assert len(timed['injection'])==1 and timed['injection'][0]['kind']=='SYNTHETIC_KERNEL_EPERM_AFTER_ACTUAL_CLEANUP'
assert te['quiescence_failure']==timed['quiescence_failure']
assert te['quiescence_failure']['quiescence_observation']['status']=='FAIL_KERNEL_QUERY'
actual_absence(timed['independent_actual_group_absence'],2666231)
for name,pid,status in [('actual-complete',2666229,'COMPLETE'),('actual-timeout',2666231,'TIMED_OUT')]:
 basename='actual-child' if name=='actual-complete' else 'actual-timeout'
 raw=read(A/'originals'/name/(basename+'.command.json'));child=read(A/'originals'/name/(basename+'.log'))
 assert raw['worker_pid']==child['pid']==child['pgid']==pid and raw['status']==status
synthetic=read(A/'originals/synthetic-profile-observations.json')
assert len(synthetic)==2 and all(x['actual_os_observation'] is False for x in synthetic)
assert [x['observation']['status'] for x in synthetic]==['FAIL_DEADLINE','FAIL_PS_AFTER_KERNEL_GROUP_EXISTS']
assert q['actual_passed']==1 and q['actual_failed']==q['actual_skipped']==q['actual_errors']==0
report={'status':'PASS_INDEPENDENT_ORIGINAL_PAGE_CONTROL_AND_EXACT_MAIN_COMPOSITION_REVIEW','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_control':S,'sealed_source':F,'main_before':B,'qualification_sha256':h(qraw),'evidence_index_sha256':h(iraw),'original_only_audit_sha256':h(audit_raw),'root_auditor_sha256':h(pathlib.Path(__file__).read_bytes()),'source_inputs':35,'actual_loaded_sources':34,'byte_mode_exact_original_copies':copied,'preserved_guard_records':guard_records,'original_actual_files':20,'sealed_document_files':doccount,'git_object_bindings':len(specs),'all_original_inputs_physical_metadata_and_git_bound':True,'composed_main_inputs_unchanged':32,'supervisor_whole_file_inverse_to_main':True,'kernel_helper_sha256_unchanged':h(kernel(new)),'only_new_profile_semantics':'semantic-page154','old_sdk_and_coherent_profile_membership_unchanged':True,'native_app_product_or_selection_changes':0,'actual_method_passes':1,'actual_child_pids':[2666229,2666231],'actual_timely_kernel_ESRCH':2,'separately_labeled_injected_query_error':1,'separately_labeled_synthetic_refusals':2,'primary_timeout_identity':'Established by the frozen source assertion during the original sole execution; original timeout and separate query refusal preserved','new_tests_or_builds_by_root_review':0,'passing_method_replays':0,'full_Page_Apple_acceptance':'NOT_RUN','excluded_baseline_only_commits':q['baseline_only_commits_excluded_from_main'],'free_bytes':os.statvfs(M).f_bavail*os.statvfs(M).f_frsize}
out=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
with (D/'root-review.json').open('xb') as f:f.write(out);f.flush();os.fsync(f.fileno())
print(json.dumps({**report,'root_review_sha256':h(out)},sort_keys=True))
