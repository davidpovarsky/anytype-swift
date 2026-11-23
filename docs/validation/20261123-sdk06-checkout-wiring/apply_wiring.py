from pathlib import Path
import ast,datetime,hashlib,json,subprocess,yaml
W=Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123');D=Path(__file__).parent
def h(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=W)
assert git('rev-parse','HEAD').decode().strip()=='9c7400758f6eeb6c3ecd818a48f189c1e33cd265'
assert not git('status','--porcelain=v1').strip()
sources={'input-helper.ts':'0bcab16b2b550f1b92c6176b5f842500febee3ae8c8051cb62a95264d40db0af','ref-helper.ts':'711c01895acdc63a9c2d94c5c632cb77f9d0ec78602de713855410c8269553fb','git-source-provider.ts':'b1bf57713d94302decc7f440a1cd7daa24f205ddf677c52debeb654a5565d1a7','git-command-manager.ts':'fbb9ebec4e1c94f9641ffe123a4e47df4ae5ec2023617f8646ce30e1d3221bcf'}
primary=[]
for name,expected in sources.items():
 b=(D/'primary'/name).read_bytes();assert h(b)==expected
 primary.append({'url':'https://raw.githubusercontent.com/actions/checkout/v4/src/'+name,'sha256':expected,'bytes':len(b)})
WF='.github/workflows/pinkha-sdk06-tagged-continuation.yml';MF='Tools/PinkhaSimulatorGate/sdk06-tagged-composition.json';HF='Tools/PinkhaSimulatorGate/sdk06_tagged_composition.py'
before={r:(W/r).read_bytes() for r in [WF,MF,HF]}
assert h(before[WF])=='fb926dea3dbda349b01aa3df4397c3abfb419d9ff3449690c8bcd2fb6b3a9365'
assert h(before[MF])=='8d30cf445a125af9da99b8f90fdc4a818bd7c9ff1f7d457f175b52256e93149c'
line='          ref: '+chr(36)+'{{ github.sha }}\n';assert before[WF].decode().count(line)==1
after={WF:before[WF].replace(line.encode(),b'')}
assert h(after[WF])=='d139154c3bd4526571f269c392a09012f691294d0e3fdcdaefb6d4c198ca8f0c'
m=json.loads(before[MF]);m['executing_workflows'][WF]=h(after[WF]);after[MF]=(json.dumps(m,indent=2)+'\n').encode()
assert h(after[MF])=='acdefbdbd9a5e10413ba7f7a7c7c0f3684a91e1b4d4851629cc0654948538879'
oldhash=h(before[MF]);newhash=h(after[MF]);assert before[HF].count(oldhash.encode())==1
after[HF]=before[HF].replace(oldhash.encode(),newhash.encode())
assert h(after[HF])=='7347998f3ba991ffa0574bb58ab8c95172dbc8aa6bda095290648bfa078ab92c'
assert after[WF].replace(b'          fetch-depth: 0\n',(line+'          fetch-depth: 0\n').encode())==before[WF]
inverse=json.loads(after[MF]);inverse['executing_workflows'][WF]=h(before[WF])
assert (json.dumps(inverse,indent=2)+'\n').encode()==before[MF]
assert after[HF].replace(newhash.encode(),oldhash.encode())==before[HF]
class Unique(yaml.BaseLoader):pass
def mapping(loader,node,deep=False):
 result={}
 for k,v in node.value:
  key=loader.construct_object(k,deep=deep)
  if key in result:raise ValueError('duplicate_yaml_key:'+key)
  result[key]=loader.construct_object(v,deep=deep)
 return result
Unique.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
new=yaml.load(after[WF],Loader=Unique);old=yaml.load(before[WF],Loader=Unique)
steps=new['jobs']['tagged-current-sdk06']['steps'];oldsteps=old['jobs']['tagged-current-sdk06']['steps']
assert len(steps)==len(oldsteps) and steps[1:]==oldsteps[1:]
assert steps[0]['uses']=='actions/checkout@v4' and steps[0]['with']=={'fetch-depth':'0','persist-credentials':'false'}
scripts=[]
for n,step in enumerate(steps):
 if 'run' in step:
  r=subprocess.run(['bash','-n'],input=step['run'].encode(),capture_output=True);assert r.returncode==0,r.stderr.decode();scripts.append(n)
compile(after[HF],str(W/HF),'exec')
prior=git('show','d254a4a1ccd9288f585ff9374088cbaf965b36b4:.github/workflows/pinkha-simulator-ui27.yml')
assert h(prior)=='9ea81f8e0394d39f507efb690428948cef592cf618e440e967160050a416c272'
identity=git('show','HEAD:Tools/PinkhaSimulatorGate/sdk06_qualified_continuation.py').decode()
guard=git('show','HEAD:Tools/PinkhaSimulatorGate/run_wave15_acceptance.py').decode()
def fn(s,name):return ast.get_source_segment(s,next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name==name))
identity_fn=fn(identity,'current_identity');guard_fn=fn(guard,'require_source_identity')
assert 'lane.require_source_identity(head, binding["source_sha"], branch, os.environ.get("GITHUB_REF"))' in identity_fn
assert 'branch in APPROVED_BRANCHES' in guard_fn and 'head == expected_sha' in guard_fn
dest=W/'docs/validation/20261123-sdk06-checkout-wiring';dest.mkdir(parents=True,exist_ok=True)
copies={}
for rel,b in before.items():
 p=dest/'qualified-originals'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 copies[rel]={'before_sha256':h(b),'after_sha256':h(after[rel]),'before_bytes':len(b),'after_bytes':len(after[rel]),'whole_file_inverse_verified':True}
for rel,b in after.items():(W/rel).write_bytes(b)
review={'status':'PASS_STATIC_EXACT_CHECKOUT_WIRING_AND_PIN_CORRECTION','source_before':'9c7400758f6eeb6c3ecd818a48f189c1e33cd265','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'primary_source_review':primary,'prior_existing_workflow_source':'d254a4a1ccd9288f585ff9374088cbaf965b36b4','prior_existing_workflow_blob':'bdaf3d19d64b7e0407b7a3e4812dfb7aeb27a1bb','exact_changes':copies,'app_checkout':'Default same-repository checkout@v4 binds both event ref and event SHA, including a targeted SHA fetch if origin branch advanced. Existing identity guard independently checks exact event SHA and approved actual local branch.','branch_guard_unchanged':True,'controller_logic_change':'Only fixed composition manifest hash constant; all helper control flow byte-identical by exact inverse.','yaml_duplicate_key_check':'PASS','bash_syntax_run_blocks':scripts,'old_new_control_methods_reexecuted':0,'apple_builds_or_methods':0,'actual_current_app_admission':'NOT_RUN','original_four_control_inputs_and_qualification':'Immutable source7f97 and retained originals; this separate static correction does not relabel or replay their execution.','fixed_tag_and_retention_manifests_unchanged':True,'prior_static_reader_failure':'First pre-mutation check searched for literal GITHUB_SHA in current_identity, which instead receives binding[source_sha] from the unchanged lifecycle. Main was verified clean at same9c740 afterwards; no source edit/build/test took place. Actual current_identity and downstream guard are now read by exact AST function scope.','source_script_sha256':h(Path(__file__).read_bytes())}
(dest/'review.json').write_text(json.dumps(review,indent=2)+'\n')
(dest/'apply_wiring.py').write_bytes(Path(__file__).read_bytes())
git('add','--sparse','--',WF,MF,HF,str(dest.relative_to(W)))
r=subprocess.run(['git','-c','user.name=davidpovarsky','-c','user.email=your-email@example.com','commit','-m','Bind SDK App checkout to the exact event branch and SHA'],cwd=W,capture_output=True,text=True)
assert r.returncode==0,r.stderr
print(json.dumps({'status':review['status'],'head':git('rev-parse','HEAD').decode().strip(),'review_sha256':h((dest/'review.json').read_bytes()),'three_whole_file_inverses':True,'primary_sources':len(primary),'shell_blocks':len(scripts),'old_tests_rerun':0}))
