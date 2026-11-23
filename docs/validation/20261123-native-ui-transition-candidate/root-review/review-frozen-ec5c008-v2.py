from pathlib import Path
import ast,datetime,hashlib,json,os,stat,subprocess,time
ROOT=Path('/mnt/development/projects/worktrees/anytype-wave15-native-ui-transition-candidate-20261123')
OUT=Path('/mnt/development/projects/diagnostics/native-ui-transition-root-review-20261123')
HEAD='ec5c0083e6b78948a7adb26bf3d3844215c922d3'
SOURCE='1a710285102077f8be7b3180a6685fbed1dc7cd9'
BASE='c0c1f851f80322c9f532e86505047498dfaf1adf'
APP='4b09cc5478c60c1c6728a54f2a27a115637a835b'
D=ROOT/'docs/validation/20261123-native-ui-transition-candidate'
def req(v,s):
 if not v: raise RuntimeError(s)
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*a): return subprocess.check_output(['git','--no-optional-locks','-C',str(ROOT),*a],timeout=30)
def blob(ref,p): return git('show',ref+':'+p)
def data(p): return json.loads(p.read_bytes())
def regular(p):
 s=p.lstat();req(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and p.resolve()==p,'regular_single_path')
 return p.read_bytes()
t=time.monotonic();free=os.statvfs('/mnt/development');free=free.f_bavail*free.f_frsize
req(free>=2_500_000_000+16*1024**2,'reserve')
req(git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain=v1'),'frozen_clean_head')
pinned={'control-inputs.json':'c4a4de9506103ea52e201f66556ff80729f0e2784b44a6479f83cfdbfc25fe4f','run-controls.py':'3b863337edc63270111f55fae0aad717ee36219a79865ce74c10fc59d853a564','colon-selector-source-review.json':'94e5b53cdc6d1941b2582fef3e597d37b834171d95ebc1f3491cdc69ffb0dfd5','runtime-composition.json':'e5cb2e82f324badd7d5dbc091a5d322b04a8685767b104cf3a368a2fcba88961'}
for name,digest in pinned.items():
 b=regular(D/name);req(sha(b)==digest and b==blob(HEAD,(D/name).relative_to(ROOT).as_posix()),'pinned_metadata:'+name)
manifest=data(D/'control-inputs.json');req(manifest['source_commit']==SOURCE and len(manifest['files'])==13,'manifest_scope')
observed=[]
for row in manifest['files']:
 p=ROOT/row['path'];b=regular(p)
 req(b==blob(HEAD,row['path'])==git('cat-file','blob',row['git_blob']) and sha(b)==row['sha256'] and len(b)==row['bytes'],'frozen_input:'+row['path'])
 req(stat.S_IMODE(p.lstat().st_mode)==row['physical_mode'],'input_mode')
 req(git('ls-tree',SOURCE,'--',row['path']).decode().strip()==row['git_mode']+' blob '+row['git_blob']+'\t'+row['path'],'source_tree_entry')
 if p.suffix=='.py': ast.parse(b,filename=str(p))
 observed.append({'path':row['path'],'sha256':sha(b),'bytes':len(b)})
review=data(D/'colon-selector-source-review.json');counts=[]
for row in review['rows']:
 b=regular(ROOT/row['path']).decode()
 req(sha(b.encode())==row['after_sha256'],'colon_after_hash')
 for change in reversed(row['changes']):
  req(b.count(change['after'])==1,'unique_colon_inverse')
  b=b.replace(change['after'],change['before'],1)
 req(b.encode()==blob(review['original_source'],row['path']) and sha(b.encode())==row['before_sha256'],'colon_whole_inverse')
 counts.append({'path':row['path'],'substitutions':len(row['changes'])})
inv=data(D/'test-source-inverse.json');current=regular(ROOT/inv['path']);req(sha(current)==inv['candidate_sha256'],'swift_candidate')
text=current.decode()
for h in reversed(inv['hunks']):
 req(sha(h['candidate'].encode())==h['candidate_sha256'] and sha(h['original'].encode())==h['original_sha256'],'swift_hunk_hash')
 req(text.count(h['candidate'])==1,'swift_inverse_unique')
 text=text.replace(h['candidate'],h['original'],1)
req(text.encode()==blob(BASE,inv['path'])==blob(APP,inv['path']) and sha(text.encode())==inv['original_sha256'],'swift_whole_inverse')
composition=data(D/'runtime-composition.json')
for path,row in composition['retained_direct_runtime_helpers'].items():
 b=blob(HEAD,path);req(b==blob(BASE,path) and sha(b)==row['sha256'] and len(b)==row['bytes'],'current_helper:'+path)
for path,row in composition['immutable_legacy_validators'].items():
 b=blob(APP,path);req(sha(b)==row['sha256'] and len(b)==row['bytes'],'immutable_validator:'+path)
testpath=ROOT/'Tools/AnyEnginePort/test_native_ui_transition_candidate.py'
tree=ast.parse(regular(testpath));methods=[n.name for c in tree.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
expected=[x.split('.')[-1] for x in manifest['case_ids']]
req(methods==expected and len(methods)==3,'only_three_new_methods')
req(len(manifest['loaded_python'])==3 and len(manifest['read_data'])==4,'host_scope')
req(blob(HEAD,'.github/workflows/torah-inspector-ipados27.yml')==blob(BASE,'.github/workflows/torah-inspector-ipados27.yml'),'central_untouched')
req(git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain=v1'),'after_clean_head')
report={'schema':'native-ui-transition-root-source-review/v1','status':'PASS','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewedHead':HEAD,'sourceCommit':SOURCE,'originalApp':APP,'fixedMetadata':pinned,'physicalAndGitInputs':observed,'colonWholeInverses':counts,'swiftWholeInverse':{'hunks':len(inv['hunks']),'oldWholeSHA256':inv['original_sha256'],'newWholeSHA256':inv['candidate_sha256'],'changedMethods':inv['changed_methods'],'unchangedExistingFunctions':len(inv['unchanged_existing_functions'])},'retainedCurrentHelpers':len(composition['retained_direct_runtime_helpers']),'immutableOriginalValidators':len(composition['immutable_legacy_validators']),'exactNewControlMethods':expected,'hostLoadedModules':manifest['loaded_python'],'manualReview':['new UI-only projection and one-target descriptor composition','original4b application/current controller separation','no old22 selection','actual validation return keys and provider cleanup identity contracts','bounded successful Files navigation and first-error preservation','frozen three-method wrapper source and capacity guards'],'preservedReviewAttempt1':{'readerSHA256':'8ed18190604d9a9f21e57cdb4a6f9fef7eab2891a1c18f1dde1187a5a4cfc1df','error':'Reviewer named a nonexistent central workflow path; no tests or repository writes occurred. Corrected to retained known torah-inspector-ipados27.yml.'},'sourceASTParsedWithoutImport':True,'centralWorkflowUnchanged':True,'productTests':0,'hostTests':0,'builds':0,'freeBytes':free,'elapsedSeconds':round(time.monotonic()-t,4),'scopeLimit':'Source review only; actual Apple compilation and mounted product behavior remain unproved.'}
dest=OUT/'source-review-ec5c008.json'
with dest.open('x',encoding='utf-8') as f: json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'status':'PASS','output':str(dest),'sha256':sha(dest.read_bytes()),'readerSHA256':sha(Path(__file__).read_bytes()),'elapsed':report['elapsedSeconds'],'freeBytes':free}))
