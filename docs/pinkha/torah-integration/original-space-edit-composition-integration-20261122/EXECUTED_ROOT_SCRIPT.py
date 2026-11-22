from pathlib import Path,PurePosixPath
import subprocess,json,hashlib,datetime,zipfile,io,struct,xml.etree.ElementTree as ET
repo=Path(r'C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122')
author=Path(r'C:\Users\DAVID\Code\anytype-original-authority-integration-20261122')
head='403725a24422103b3562228a64061d24d639eabf'
incoming='31d3f65c0132ec17e76b11c39d3a5e3314a7aa23'
source='4262d985ce0648f20f71fb6cc54b10f6f349eb6e'
base='d33a41338bd0a56326fd02c05977c10d1c4c7baa'
packet='docs/pinkha/torah-integration/production-space-edit-composition-20261122'
product='Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift'
proof='docs/pinkha/torah-integration/original-space-edit-composition-integration-20261122'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args,cwd=repo,timeout=45):
 p=subprocess.run(['git','-c','core.autocrlf=false',*args],cwd=cwd,capture_output=True,timeout=timeout)
 if p.returncode: raise RuntimeError('git failure '+str(args)+' '+p.stderr.decode(errors='replace')[:2000])
 return p.stdout
def textgit(*args,**kw):return git(*args,**kw).decode('utf8').strip()
def blobs(specs):
 pr=subprocess.run(['git','-c','core.autocrlf=false','cat-file','--batch'],cwd=repo,input=('\n'.join(specs)+'\n').encode(),capture_output=True,timeout=60)
 assert pr.returncode==0,pr.stderr
 stream=io.BytesIO(pr.stdout);result={}
 for spec in specs:
  header=stream.readline().decode().strip().split()
  assert len(header)==3 and header[1]=='blob',(spec,header)
  size=int(header[2]);data=stream.read(size);assert len(data)==size and stream.read(1)==b'\n'
  result[spec]=(header[0],data)
 assert stream.read()==b''
 return result
def obj(ref,path):return git('show',ref+':'+path)
def loadjson(path):return json.loads(payloads[path])
assert textgit('rev-parse','HEAD')==head
assert textgit('branch','--show-current')=='codex/otzaria-original-native-annotation-integration-20261122'
assert git('status','--porcelain')==b''
assert textgit('rev-parse','HEAD',cwd=author)==incoming and git('status','--porcelain',cwd=author)==b''
assert textgit('merge-base',head,incoming)==base
assert textgit('rev-parse',source+'^')==base
index_b=obj(incoming,packet+'/PACKET_INDEX.json')
assert sha(index_b)=='26c99ea8af9671cde01b86007482685812aa31353a2267abd39681e551c92c36'
index=json.loads(index_b);assert index['count']==86 and len(index['files'])==86 and index['source_commit']==source and index['base']==base
seen=set()
for item in index['files']:
 p=PurePosixPath(item['path']);assert not p.is_absolute() and '..' not in p.parts and '\\' not in item['path']
 assert item['path'] not in seen;seen.add(item['path'])
raw=blobs([incoming+':'+packet+'/'+x['path'] for x in index['files']]);payloads={}
for item in index['files']:
 name=item['path'];data=raw[incoming+':'+packet+'/'+name][1]
 assert len(data)==item['bytes'] and sha(data)==item['sha256'],name
 assert (author/packet/name).read_bytes()==data,name
 payloads[name]=data
tracked=set(textgit('ls-tree','-r','--name-only',incoming,'--',packet).splitlines())
assert tracked=={packet+'/'+p for p in seen}|{packet+'/PACKET_INDEX.json'}
inputs=loadjson('controls/INPUTS.json');result=loadjson('controls/RESULT.json');execution=loadjson('controls/EXECUTION.json')
assert sha(payloads['controls/INPUTS.json'])=='74a0bf1c732e7d579814c4658d1f718e3c476b0d817fbf1871c481fc490f3d07'
assert len(inputs['original_inputs'])==18 and len(inputs['compiled_inputs'])==13
originals=blobs([base+':'+i['path'] for i in inputs['original_inputs']])
for i,item in enumerate(inputs['original_inputs']):
 blob,data=originals[base+':'+item['path']]
 assert blob==item['git_blob'] and sha(data)==item['sha256'],item['path']
 assert data==payloads['controls/original-inputs/'+str(i).zfill(2)+'.swift']
for item in inputs['compiled_inputs']:
 b=payloads['controls/'+item['path']]
 assert len(b)==item['bytes'] and sha(b)==item['sha256'],item['path']
assert sha(payloads['controls/Package.swift'])==inputs['package_sha256']
assert sha(payloads['controls/Tests/CompositionControls/Controls.swift'])=='fde032b0d1bef0fbcf7f376db0b52dacfcc04b5e4dcee9b8664af133f3446877'
candidate=payloads['OWNER_CANDIDATE.swift']
assert sha(candidate)==inputs['candidate_sha256']=='bf619f8e022c99d6f7f5f8e374b7213989639502801d36b754dcd95aedae9873'
assert candidate==payloads['controls/Owner.candidate.swift']==obj(source,product)==obj(incoming,product)==(author/product).read_bytes()
assert obj(base,product)==payloads['OWNER_BASE.swift']
assert sha(payloads['SPACE_EDIT_BINDING.patch'])==inputs['candidate_patch_sha256']=='c8a2cb2f3ff3010bc1ce209aaa12bad5e82bb8cadc5954ed474cc3f1a4b849c0'
changes=textgit('diff','--name-only',base,incoming).splitlines()
assert [p for p in changes if not p.startswith('docs/')]==[product],changes
assert set(textgit('diff','--name-only',source,incoming).splitlines())<=set(p for p in changes if p.startswith('docs/'))
assert result['tests_run']==10 and result['all_inputs_unchanged'] is True and result['inputs_sha256']==sha(payloads['controls/INPUTS.json'])
xml=payloads['controls/TEST_RESULTS.xml'];assert sha(xml)==result['xunit_sha256']
root=ET.fromstring(xml);cases=root.findall('.//testcase')
names=[c.attrib['name'].removesuffix('()') for c in cases]
assert len(names)==10 and len(set(names))==10 and set(names)==set(inputs['expected_tests'])
assert not root.findall('.//failure') and not root.findall('.//error') and not root.findall('.//skipped')
assert {x['name'].removesuffix('()') for x in result['tests']}==set(names)
assert len(execution['commands'])==3
for command in execution['commands']:
 assert command['phase']=='TERMINAL' and command['returncode']==0 and command['timed_out'] is False and command['all_inputs_unchanged'] is True
 for stream in ('stdout','stderr'):
  assert sha(payloads['controls/'+command['label']+'.'+stream+'.log'])==command[stream+'_sha256']
assert execution['commands'][-1]['label']=='swift-testing-composition'
assert execution['commands'][-1]['started_at']=='2026-11-22T07:36:39.550422+00:00'
assert execution['commands'][-1]['finished_at']=='2026-11-22T07:41:33.026523+00:00'
for tool in execution['toolchain']:
 b=Path(tool['path']).read_bytes();assert len(b)==tool['bytes'] and sha(b)==tool['sha256']
archive=loadjson('controls/ACTUAL_BINARY_ARCHIVE.json')
zb=payloads['controls/actual-test-runner.zip'];assert sha(zb)==archive['sha256'] and len(zb)==archive['bytes']
with zipfile.ZipFile(io.BytesIO(zb)) as z:
 assert z.testzip() is None
 members=z.infolist();assert len(members)==1
 for info in members:
  p=PurePosixPath(info.filename);assert not p.is_absolute() and '..' not in p.parts and '\\' not in info.filename and not info.is_dir() and ((info.external_attr>>16)&0o170000)!=0o120000
 binary=z.read(members[0])
assert len(binary)==result['binary']['bytes'] and sha(binary)==result['binary']['sha256']=='17b96bc0125df3254a14fcd9c277da1c96e822f8be1a54705b5a965717a3ee2d'
assert binary[:2]==b'MZ'
pe=struct.unpack_from('<I',binary,0x3c)[0];assert binary[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',binary,pe+4)[0]==0x8664
actual_binary=Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-space-bind-20261122')/result['binary']['path']
assert actual_binary.read_bytes()==binary
assert actual_binary.name.encode() in payloads['controls/swift-testing-composition.stderr.log']
erratum=loadjson('controls/EVIDENCE_STREAM_ERRATUM.json')
assert erratum['reexecuted_commands']==0 and erratum['actual_process_exit']==0 and erratum['actual_tests']==10 and erratum['actual_failures']==0
reg=loadjson('REGISTER_PREFIX_PROOF.json')
before=obj(base,reg['path']);after=obj(incoming,reg['path'])
assert len(before)==reg['base_bytes'] and sha(before)==reg['base_sha256'] and after.startswith(before) and sha(after)==reg['after_sha256']
composition=loadjson('SOURCE_COMPOSITION.json')
for path,digest in composition['prior_component_and_shared_trees'].items():
 assert textgit('rev-parse',base+':'+path)==digest
 assert textgit('rev-parse',incoming+':'+path)==digest
 assert textgit('rev-parse',head+':'+path)==digest
preserved=['Modules','Anytype/Resources','Scripts','scripts','.github','OriginalEditorFramework','Anytype.xcodeproj',
 'Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift',
 'Anytype/Sources/ServiceLayer/SpaceStorage/SpaceViewsStorage.swift',
 'Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationNativeMetadata.swift',
 'Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationObjectReadback.swift']
preserved_before={p:textgit('rev-parse',head+':'+p) for p in preserved}
receipt={'schema':1,'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_INDEPENDENT_FROZEN_EVIDENCE_ADMISSION_NO_TEST_REPLAY','base':base,'root_premerge':head,'incoming':incoming,'source_commit':source,'packet_index_sha256':sha(index_b),'payload_count':86,'payload_bytes':sum(len(b) for b in payloads.values()),'original_git_inputs_verified':18,'compiled_inputs_verified':13,'actual_windows_pe_sha256':sha(binary),'actual_windows_pe_bytes':len(binary),'archive_crc_members':1,'actual_test_count':10,'actual_case_names':names,'xunit_sha256':sha(xml),'original_execution_started':execution['commands'][-1]['started_at'],'original_execution_finished':execution['commands'][-1]['finished_at'],'original_tool_wrapper_red_retained':True,'evidence_only_stream_erratum_verified':True,'canonical_register_prefix_preserved':True,'preserved_premerge_objects':preserved_before,'root_tests_executed':0,'native_calls':0,'limits':inputs['limits'],'executed_script_sha256':sha(Path(__file__).read_bytes())}
temp=Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122')
receipt_path=temp/'composition_root_evidence_review.json'
assert not receipt_path.exists()
receipt_path.write_bytes((json.dumps(receipt,indent=2,ensure_ascii=False)+'\n').encode())
assert textgit('rev-parse','HEAD')==head and git('status','--porcelain')==b''
git('merge','--no-ff',incoming,'-m','Merge verified original Space edit permission composition',timeout=90)
merge=textgit('rev-parse','HEAD')
assert textgit('show','-s','--format=%P',merge).split()==[head,incoming]
assert git('status','--porcelain')==b''
merged_changes=textgit('diff','--name-only',head,merge).splitlines()
assert [p for p in merged_changes if not p.startswith('docs/')]==[product]
assert obj(merge,product)==candidate and (repo/product).read_bytes()==candidate
preserved_after={p:textgit('rev-parse',merge+':'+p) for p in preserved}
assert preserved_after==preserved_before
proofdir=repo/proof;assert not proofdir.exists();proofdir.mkdir(parents=True)
(proofdir/'ROOT_REVIEW.json').write_bytes(receipt_path.read_bytes())
(proofdir/'EXECUTED_ROOT_SCRIPT.py').write_bytes(Path(__file__).read_bytes())
integration={'schema':1,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'merge_commit':merge,'merge_parents':[head,incoming],'source_commit':source,'only_product_delta':product,'product_sha256':sha(candidate),'review_sha256':sha(receipt_path.read_bytes()),'preserved_objects':preserved_after,'new_executions':0,'native_calls':0,'runtime_callers_added':0,'root_worktree':str(repo),'branch':textgit('branch','--show-current'),'incoming_packet':packet,'scope':'Original SourceBinding restriction composition with existing Participant/Space captures. No native RPC, schema creation, metadata digest, persisted receipt, writer, ACK or Apple qualification.'}
(proofdir/'INTEGRATION.json').write_bytes((json.dumps(integration,indent=2)+'\n').encode())
readme='# Original Space edit permission composition: independent integration\n\nTrue merge '+merge+' joins root '+head+' and independently verified source/evidence '+incoming+'. The only product delta is '+product+' (SHA-256 '+sha(candidate)+').\n\nRoot verified all 86 frozen payloads plus their index, 18 original immutable Git inputs, 13 compiled inputs, the actual Windows PE test runner and archived copy, CRC, raw execution streams, and ten distinct successful Swift Testing cases. The original wrapper RED and evidence-only stdout/stderr correction remain retained. No test or compiler command was rerun for this integration.\n\nThe restriction copies the original SourceBinding account, lifetime, source captures, currentness predicate, optional parent and named RPC restriction, appends actual Participant/Space captures, evaluates original SpacePermissions, and revalidates. It does not grant destination or creation authority. Existing component, generated module, resource, project, workflow, metadata and readback objects are unchanged.\n\nThe ten new cases are Windows portable component controls with explicit DI, publisher, decoded-value, document and network-configuration probes. No original native subscription, RPC, ObjectCreate, persistence receipt, identity map, ACK, Apple SDK or device runtime acceptance is claimed. Full original test scope and limits are retained in ROOT_REVIEW.json and the incoming packet.\n'
(proofdir/'README.md').write_bytes(readme.encode())
files=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(proofdir.iterdir()) if p.is_file()]
(proofdir/'FILE_INDEX.json').write_bytes((json.dumps({'schema':1,'files':files,'count':len(files)},indent=2)+'\n').encode())
git('add','--',proof);git('diff','--cached','--check')
git('commit','-m','Record independent original Space edit composition integration evidence',timeout=90)
final=textgit('rev-parse','HEAD')
assert git('status','--porcelain')==b'' and obj(final,product)==candidate
print(json.dumps({'status':'PASS','review':receipt,'integration':integration,'final_commit':final,'remote':textgit('remote','get-url','origin'),'proof':proof,'proof_index_sha256':sha((proofdir/'FILE_INDEX.json').read_bytes()),'new_test_executions':0},ensure_ascii=False))
