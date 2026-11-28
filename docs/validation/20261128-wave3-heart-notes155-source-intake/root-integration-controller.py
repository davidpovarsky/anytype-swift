#!/usr/bin/env python3
"""Fixed Notes tool and original UI detour source merge; no build or runtime activation."""
import ast,base64,difflib,hashlib,json,os,pathlib,re,signal,sys,time
sys.dont_write_bytecode=True
OLD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-w2-bookmark-language171-source-integration.py')
OLD_SHA='3f943613f16b5adc1e686cfa41b7c3bd9632e6e83bf4f8c77ee520597dcc102f'
PREP=pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-heart-notes155-source-preparation-20261128/prepared1')
EVIDENCE=pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-heart-notes155-source-integration-20261128')
PRIVATE=pathlib.Path('/tmp/pinkha-w3-heart-notes155-private-index-20261128')
OUT=pathlib.Path('/tmp/pinkha-w3-heart-notes155-source-integration-20261128.json')
GATE_OUT=pathlib.Path('/tmp/pinkha-w3-heart-notes155-retention-20261128.json')
START='5c88cf89dd26c70c285cd7d23951b26aeb5bc2d8'
START_TREE='c16392569b2fccf488e21d0bbced8cf0cc752a5c'
SOURCE_TREE='1c66199e360afa1a9d0d0a74d4cd3111f1a04cbe'
DONOR_TREE='1c66199e360afa1a9d0d0a74d4cd3111f1a04cbe'
DONORS=['155a0c751e2158ae9b5f0e219e1331e427c22909']
PREFIX='docs/validation/20261128-wave3-heart-notes155-source-intake'
INPUT_SHA='8649d0beb047e2fa5e3f686dd830ea2410a7a60c89a5ebf1b0b68440e8194841'
PREDECESSOR_SHA='2ca569d24489ac3266b823f8d79f76ba7f991576e9c17776370b5aedc1246991'
TARGET_SDK='9af3e798212dc33b3cc7ea95a065a98c034788c6'
TARGET_KIT='414e0d3e95d53509381d233a23fcdd28ef24167a'
UI_CHANGE={"path":"PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift","before":{"bytes":34629,"sha256":"b43f97b3c1283f05b728b15cc9871bfecc1692ca55563f1e2c1f1886ecd38d5e","gitBlob":"d4a15a8c318880c379c83a8ee2631e2fd6fa7568","gitMode":"100644"},"after":{"bytes":38096,"sha256":"2a71529b40bd0ae074bd891ad6b7705cf6372c17ef499b01b00ba2312f51c1a1","gitBlob":"ca8b7cb767ec7913131be8b6346f3cd6fc2b883f","gitMode":"100644"},"pureInsertionBytes":3467,"testMethods":["testCurrentSpaceRowsAndExactBlockNavigation","testAddNoteEditOpenUnlinkAndRetainAfterRelaunch","testHebrewRelatedRowsLongTitlesAndReadOnlyNavigation"],"originalObservationSites":13,"controllerMethodSeconds":300,"controllerOuterUISeconds":900,"newTestMethods":0,"runtimeAcceptance":False,"strictHistoricalHostedT5PinUnchanged":True}
ORIGINAL_EVIDENCE_NAMES=['notes155-byte-proof.original.json', 'notes155-source-review.original.json', 'notes845-root-source-review.original.json']
old=OLD.read_bytes()
assert len(old)==60995 and hashlib.sha256(old).hexdigest()==OLD_SHA
O={'__name__':'pinned_original_171','__file__':str(OLD)}
exec(compile(old,str(OLD),'exec'),O)
O.update(START=START,START_TREE=START_TREE,EVIDENCE=EVIDENCE,PRIVATE=PRIVATE,MAX_SECONDS=300,
         SDK=TARGET_SDK,KIT=TARGET_KIT)
need=O['require'];read=O['read_regular'];write=O['exclusive'];enc=O['encoded'];sha=O['sha']
root=O['ROOT']
# Preserve the executed current83 guard with the actual published map145 identity.
guard_node=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='validate_guards')
guard_old=ast.get_source_segment(old.decode(),guard_node)
a=guard_old.index("    added_path = ");b=guard_old.index("    before, after = ",a)
guard_new=guard_old[:a]+"""    require(len(protected) == 83 and protected == guards['protectedLeaves']
            and guards['addedProtectedLeaves'] == {} and guards['protectedUpdates'] == {}
            and target_protected == protected and guards['targetProtectedCount'] == 83,
            'All83 current protected leaves must remain byte-exact; no protected additions')
"""+guard_old[b:]
need(guard_new.replace(guard_new[a:guard_new.index("    before, after = ",a)],guard_old[a:b],1)==guard_old,
     'Whole original guard inverse differs')
guard_current83=guard_new
GUARD_EDITS=[{'before': '722a41b870957cf17f9724b8dd732b7d6088bde0', 'after': '0483ab6cdf65774c5fd66332143f7e804f7932a0'}]
for edit in GUARD_EDITS:
 need(guard_new.count(edit['before'])==1,'Reviewed guard splice is not unique')
 guard_new=guard_new.replace(edit['before'],edit['after'],1)
restored_guard=guard_new
for edit in reversed(GUARD_EDITS):
 need(restored_guard.count(edit['after'])==1,'Reviewed guard inverse is not unique')
 restored_guard=restored_guard.replace(edit['after'],edit['before'],1)
need(restored_guard==guard_current83,'Complete executed current83 guard inverse differs')
exec(compile(guard_new,'fixed_current9af_414_map145_guard.py','exec'),O)
def exact_file(path,size,digest):
 raw=read(path)
 need(len(raw)==size and sha(raw)==digest,'Exact immutable input differs: '+str(path))
 return raw
def original_closed(value,count):
 need(len(value['commands'])==count,'Original command count differs')
 for c in value['commands']:
  need(c.get('originalProcessGroupAbsent')is True and c.get('cleanupSignals')==[]
       and not c.get('cleanupFailure') and not c.get('receiptFailure'),'Original command custody unresolved')
def check_diff(c,label,args,known_paths,expected=None):
 try:
  raw=c.git(label,*args)
 except RuntimeError:
  q=c.receipt['commands'][-1]
  need(q['label']==label and q.get('exitCode')==2 and q.get('originalProcessGroupAbsent')is True
       and q.get('cleanupSignals')==[] and not c.blocked and q['stderr']['bytes']==0
       and q.get('firstFailure')=={'type':'RuntimeError','message':label+' exited 2'},
       'Only exact ordinary whitespace diagnostics may be retained')
  raw=read(pathlib.Path(q['stdout']['path']))
 q=c.receipt['commands'][-1]
 need(q['exitCode']in(0,2) and q['stderr']['bytes']==0,'Unexpected Git diff error')
 text=raw.decode()
 for line in text.splitlines():
  if line.startswith('+'):continue
  m=re.fullmatch(r'(.+):([1-9][0-9]*): (trailing whitespace\.|space before tab in indent\.|new blank line at EOF\.)',line)
  need(m is not None and m.group(1)in known_paths,'Unexpected original whitespace diagnostic')
 result={'exit':q['exitCode'],'stdoutSHA256':sha(raw),'stdoutBytes':len(raw),
         'scope':'EXACT_RETAINED_ORIGINAL_EVIDENCE_DIAGNOSTICS_NOT_PASS' if q['exitCode'] else 'PASS_CLEAN_DIFF'}
 if expected is not None:need(result==expected,'Ordinary index diagnostic changed')
 c.receipt.setdefault('diffChecks',[]).append(dict(result,label=label))
 return result
def integrate(c,r,payload,prior_raw,prior,projection_raw):
 rows=payload['rows'];values=O['decode_rows'](rows)
 donor_rows=payload['donorRows'];root_rows=payload['rootRows']
 need(len(rows)==11 and rows==donor_rows and root_rows=={}
      and sum(x['status']=='A'for x in rows.values())==9
      and sum(x['status']=='M'for x in rows.values())==2
      and sum(x['after']['bytes']for x in rows.values())==100793,
      'Only the exact eleven original source paths are admitted')
 need(payload['reviewedUISourceChange']==UI_CHANGE
      and rows[UI_CHANGE['path']]['before']==UI_CHANGE['before']
      and rows[UI_CHANGE['path']]['after']==UI_CHANGE['after'],
      'Exact original UI preimage and reviewed detour input differ')
 ui_before=base64.b64decode(rows[UI_CHANGE['path']]['beforeBase64'],validate=True)
 ui_after=values[UI_CHANGE['path']]
 need(len(ui_after)-len(ui_before)==3467
      and ui_after[:10822]==ui_before[:10822]
      and ui_after[14289:]==ui_before[10822:],
      'Only the reviewed3467-byte UI insertion is admitted')
 need(payload['start']==START and payload['startTree']==START_TREE and payload['donorTips']==DONORS
      and payload['donorTree']==DONOR_TREE and payload['sourceTree']==SOURCE_TREE
      and payload['sourceLeaves']==23753 and payload['runtimeAcceptance']is False
      and payload['compilerInvocations']==payload['testsExecuted']==payload['materializations']==0,
      'Exact source-only projection differs')
 need(c.git('initial-head-tree','rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[START,START_TREE]
      and c.git('initial-branch','symbolic-ref','HEAD').decode().strip()==O['REF'],'Integration base differs')
 merge_head=pathlib.Path(c.git('merge-state-path','rev-parse','--path-format=absolute','--git-path','MERGE_HEAD').decode().strip())
 need(not merge_head.exists(),'Preserve any existing merge')
 original=O['original_status'](c,'before');O['exact_remote'](c,'original-remote',START)
 index=pathlib.Path(c.git('original-index-path','rev-parse','--path-format=absolute','--git-path','index').decode().strip())
 index_state=O['optional_file_identity'](index)
 base=O['tree_leaves'](c,'complete-current-tree',START_TREE)
 need(len(base)==23744,'Current full tree count differs')
 # Missing immutable donors are fetched through the original owned Git route only.
 availability=c.git('exact-notes-donor-local-object','cat-file','--batch-check',
                    data=''.join(sha+'\n'for sha in DONORS).encode()).decode().splitlines()
 need(len(availability)==1,'Exact donor object observation differs')
 missing=[]
 for commit,line in zip(DONORS,availability):
  parts=line.split()
  if parts==[commit,'missing']:missing.append(commit)
  else:need(len(parts)==3 and parts[0]==commit and parts[1]=='commit'
            and parts[2].isdigit() and int(parts[2])>0,'Unexpected donor object identity')
 if missing:
  c.git('fetch-exact-missing-notes-donor','fetch','--no-tags','--refmap=','origin',*missing,publish=True,timeout=60)
 specs=[('84577c91e2949aead1d3e209ae7a45488e868edf','f270a7b9701d77268f006504f7e27a852da4b083',
         'b8521ca8d9d88f62aeb8e246de2c1ae2dd798588',5),
        ('155a0c751e2158ae9b5f0e219e1331e427c22909','545d61e2c700abbb43665afafdafcef7ca7f2356',
         '84577c91e2949aead1d3e209ae7a45488e868edf',6)]
 need(len(payload['donorLinks'])==2,'Exact Notes parent and UI child links required')
 seen=set();oids=set()
 preimages=O['batch_blobs'](c,'both-current-product-preimages',
                           {x['before']['gitBlob']:None for x in rows.values()if x['before']is not None})
 for path,row in rows.items():
  O['require_leaf'](base,path,row['before'])
  previous=None if row['before']is None else base64.b64decode(row['beforeBase64'],validate=True)
  if previous is not None:
   O['match'](preimages[row['before']['gitBlob']],row['before'])
   need(preimages[row['before']['gitBlob']]==previous,'Complete current preimage differs')
  O['destination_preflight'](path,previous,may_be_sparse=True)
 for i,(link,spec)in enumerate(zip(payload['donorLinks'],specs)):
  commit,tree,parent,count=spec;tag='original-donor-'+str(i+1)
  need(link['commit']==commit and link['tree']==tree and link['parents']==[parent]
       and len(link['files'])==count,'Original donor link differs')
  need(c.git(tag+'-identity','show','-s','--format=%H %T %P',commit).decode().split()==[commit,tree,parent],
       'Published donor identity differs')
  if i==0:c.git(tag+'-base-integrated','merge-base','--is-ancestor',parent,START)
  else:need(parent==specs[i-1][0],'Exact donor ancestry link differs')
  need(O['changes'](c,tag+'-full-diff',parent,commit)
       =={p:q['status']for p,q in link['files'].items()},'Unreviewed donor delta')
  leaves=O['parse_leaves'](c.git(tag+'-changed-leaves','ls-tree','-r','-z','--full-tree',tree,'--',*sorted(link['files'])))
  need(set(leaves)==set(link['files']),'Complete original donor paths differ')
  bodies=O['batch_blobs'](c,tag+'-whole-original-bodies',{x['after']['gitBlob']:None for x in link['files'].values()})
  for path,item in link['files'].items():
   need(path not in seen and donor_rows[path]['donorCommit']==commit,'Overlapping or foreign donor source')
   need(item=={'status':rows[path]['status'],'after':rows[path]['after']},'Full source row differs')
   O['require_leaf'](leaves,path,item['after']);O['match'](bodies[item['after']['gitBlob']],item['after'])
   need(bodies[item['after']['gitBlob']]==values[path],'Full original body differs')
   seen.add(path)
  oids.update(bodies)
 need(seen==set(donor_rows) and root_rows=={},
      'Full eleven original source closure differs')
 donor_source=O['expected_leaves'](base,donor_rows)
 source=O['expected_leaves'](base,rows)
 before=O['validate_guards'](c,payload,base,source,prior,'before')
 O['resources']()
 c.run('create-exclusive-private-index',O['PRE']+['python3','-B','-c','import os,sys;os.mkdir(sys.argv[1],0o700)',str(PRIVATE)])
 stree=O['private_tree'](c,'complete-notes-source-preview',base,rows,source)
 need(donor_source==source and stree==DONOR_TREE==SOURCE_TREE,'Complete eleven-path source union differs')
 production=sorted(path for path in rows if not path.startswith('docs/'))
 c.git('production-source-whitespace','diff','--check','--no-renames',START,stree,'--',*production)
 evidence_paths={path for path in rows if path.startswith('docs/')}
 diagnostic=check_diff(c,'source-preview-whitespace',['diff','--check','--no-renames',START,stree],evidence_paths)
 after=O['validate_guards'](c,payload,base,source,prior,'after')
 need(before==payload['guardInputs']['inputPins'] and after==payload['guardInputs']['outputPins'],
      'Exact input/output pin transition differs')
 intake={'schema':'pinkha-w3-heart-notes155-source-intake/v1','start':START,'startTree':START_TREE,
         'normalMergeParents':[START,*DONORS],'donorTree':DONOR_TREE,'sourceTree':SOURCE_TREE,
         'sourcePaths':11,'sourceBytes':100793,'completeSourceLeaves':23753,
         'sourceStatusCounts':{'A':9,'M':2},
         'files':{p:{k:v for k,v in row.items()if k not in('base64','beforeBase64')}for p,row in rows.items()},
         'sourceInputSHA256':INPUT_SHA,'inputPins':before,'outputPins':after,
         'protectedLeaves':83,'reviewedProtectedUpdates':0,'guardFiles':52,'reviewedGuardUpdates':0,
         'sourceMapRows':145,'sourceMapReplacementFieldsChanged':[],
         'reviewedUISourceChange':UI_CHANGE,
         'runtimeAcceptance':False,'testsExecuted':0,'compilerInvocations':0,'materializations':0,
         'NotesScope':'Eight-byte Notes tool append after the three original tools; all other5356 host bytes remain exact. Existing Notes callbacks and current414 selector/API seam are preserved. No new optional Kit hook adoption.',
         'UIScope':'One3467-byte Notes list/open detour before original unlink; complete34629-byte predecessor restored by inverse. All three original methods,13 observation sites and existing assertions survive. New behavior NOT_RUN;300/900 limits and22/34 then preparation then4 original UI order unchanged.',
         'HistoricalAdmission':'Closed hosted_t5 original_sources retains old b43 UI and its qualify_final guard. This merge does not promote it; actual new whole-source/compiler/product admission remains pending. Shared62/10/2 membership unchanged.',
         'CurrentProductPreservation':'Current SDK9af/Kit414, all83 protected paths,52 source witnesses,145 map rows,56 main pins,45 closed runtime tuples and four untracked files remain exact.'}
 evidence={'root-source-intake.json':enc(intake),'root-integration-controller.py':read(pathlib.Path(__file__)),
           'prior-type25-sharing58-publication.original.json':prior_raw,
           'source-guard-derivation.json':enc({'originalControllerSHA256':OLD_SHA,
                'predecessorControllerSHA256':PREDECESSOR_SHA,'originalFunction':guard_old,
                'current83Function':guard_current83,'successorFunction':guard_new,
                'literalGuardOperations':GUARD_EDITS,'wholeOriginalInverse':True,
                'onlyChanges':'Bind already-published map145 whole identity and SDK9af/Kit414 constants. All83 protected and52 guard source identities,56 main pins,145 map rows and45 runtime tuples remain exact; no promotion is reapplied.'})}
 need(set(payload['evidence'])==set(ORIGINAL_EVIDENCE_NAMES),'Finite original evidence names differ')
 for name,item in payload['evidence'].items():
  raw=base64.b64decode(item['base64'],validate=True);O['match'](raw,item['after'])
  need(name not in evidence,'Evidence name overlaps');evidence[name]=raw
 need(len(evidence)==7,'Exact seven intake evidence additions required')
 erows={};evals={}
 for name,raw in evidence.items():
  path=PREFIX+'/'+name;need(path not in base and path not in rows,'Evidence already exists')
  O['destination_preflight'](path,None);O['generated_evidence_is_whitespace_clean'](raw)
  erows[path]={'status':'A','before':None,'beforeBase64':None,
              'after':{'bytes':len(raw),'sha256':sha(raw),'gitBlob':O['blob'](raw),'gitMode':'100644'}}
  evals[path]=raw
 allrows={**rows,**erows};whole=O['expected_leaves'](base,allrows)
 need(len(allrows)==18 and len(whole)==23760,'Complete18-path/23760-leaf projection differs')
 O['write_new_objects'](c,erows,evals,oids|{v['sha']for v in base.values()if v['type']=='blob'})
 finaltree=O['private_tree'](c,'complete-final-preview',base,allrows,whole)
 check_diff(c,'complete-preview-whitespace',['diff','--check','--no-renames',START,finaltree],evidence_paths,diagnostic)
 need(c.git('premerge-head-tree','rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[START,START_TREE]
      and c.git('premerge-index-tree','write-tree').decode().strip()==START_TREE,'Original HEAD or index advanced')
 need(O['original_status'](c,'premerge')==original and O['optional_file_identity'](index)==index_state,'Premerge custody changed')
 O['exact_remote'](c,'premerge-remote',START)
 r.update(phase='NORMAL_NOTES_SOURCE_MERGE',expectedDonorTree=DONOR_TREE,expectedSourceTree=SOURCE_TREE,expectedTree=finaltree)
 O['resources']()
 c.git('normal-notes-source-merge','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
       'merge','--no-ff','--no-commit',*DONORS,timeout=60)
 need(read(merge_head).decode().split()==DONORS,'Normal merge parents differ')
 need(c.git('actual-donor-index-tree','write-tree').decode().strip()==DONOR_TREE
      and O['tree_leaves'](c,'actual-donor-full-tree',DONOR_TREE)==donor_source,
      'Normal merge differs; preserve without reset')
 O['write_owned_batch'](c,'write-exact-seven-intake-files',erows,evals,{p:None for p in erows})
 c.git('stage-exact-intake-files','add','--sparse','--',*sorted(erows))
 need(c.git('actual-complete-index-tree','write-tree').decode().strip()==finaltree,'Full staged tree differs')
 need(O['changes'](c,'actual-complete-delta',START,finaltree)=={p:q['status']for p,q in allrows.items()},
      'Unexpected complete staged delta')
 need(c.git('unstaged-source-check','diff','--name-only')==b''
      and c.git('untracked-source-check','ls-files','--others','--exclude-standard','-z')==original['untracked'],
      'Unexpected unstaged/private changes')
 c.git('actual-production-whitespace','diff','--cached','--check','--no-renames',START,'--',*production)
 check_diff(c,'actual-index-whitespace',['diff','--cached','--check','--no-renames',START],evidence_paths,diagnostic)
 need(O['validate_guards'](c,payload,base,whole,prior,'after')==after,'Final source guards differ')
 r['phase']='ORIGINAL145_RETENTION_GATE'
 gate_raw=O['gate_once'](c,r,'original-retention-gate',finaltree,GATE_OUT)
 need(c.git('final-precommit-head','rev-parse','HEAD').decode().strip()==START
      and c.git('final-precommit-index','write-tree').decode().strip()==finaltree,'Gate changed source state')
 need(c.git('final-precommit-untracked','ls-files','--others','--exclude-standard','-z')==original['untracked'],'Private files changed')
 message=('Integrate Notes tool and preserved T5 UI detour source\n\n'
          'Merge exact published155a and its84577 parent while preserving all current5c88 source. '
          'Add only the Notes tool and original Notes-list/open test detour; all new UI behavior remains NOT_RUN. '
          'Preserve83 protected paths,52 witnesses,56 main pins,145 mappings and45 closed runtime tuples byte-exact, including historical T5 admission. '
          'No compiler, product tests or runtime activation; original source failures and diagnostics stay literal.\n')
 c.git('normal-two-parent-source-commit','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
       'commit','-F','-',data=message.encode(),timeout=45)
 head=c.git('final-committed-head','rev-parse','HEAD').decode().strip();r['head']=head
 need(c.git('final-committed-parents','show','-s','--format=%T %P',head).decode().split()==[finaltree,START,*DONORS],
      'Final ordinary ancestry differs')
 need(O['original_status'](c,'committed')==original and not merge_head.exists(),'Committed custody differs')
 O['exact_remote'](c,'prepush-remote',START)
 r.update(tree=finaltree,donorTips=DONORS,files=sorted(allrows),sourceRetentionPassed=True,reviewedRefactors=145,
          retentionSHA256=sha(gate_raw),inputPins=before,outputPins=after,originalUntrackedPreserved=True,
          localMergeCommits=[{'head':head,'tree':finaltree,'parents':[START,*DONORS]}])
 r['phase']='ONE_NORMAL_NONFORCE_PUSH';O['resources']()
 c.git('normal-exact-source-push','push','--porcelain','--no-follow-tags','origin',head+':'+O['REF'],publish=True,timeout=90)
 r['normalPushCompleted']=True;O['exact_remote'](c,'published-readback',head);r['normalPushReadback']=head
 need(O['original_status'](c,'published')==original,'Published worktree custody differs')
 r['state']='SOURCE_NORMAL_MERGE_PUBLISHED_RUNTIME_CLOSED'
def main():
 need(os.geteuid()==0 and sys.platform.startswith('linux'),'Existing Oracle context required')
 for name in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_CONFIG_COUNT','GIT_CONFIG_PARAMETERS'):
  need(not os.environ.get(name),'Inherited Git override not admitted')
 for p in (EVIDENCE,PRIVATE,OUT,GATE_OUT):
  O['no_symlinks'](p);need(not p.exists(),'Existing attempt must be preserved: '+str(p))
 input_raw=exact_file(PREP/'source-inputs.json',551064,INPUT_SHA)
 payload=json.loads(input_raw)
 prior_raw=exact_file(pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-type25-sharing-sdk9af-kit414-source-integration-20261128/receipt.json'),
                      245876,'f877c2f501059df1932ea551b6f178ddfa07b0648dbfda3e1186910d8ee18be1')
 prior=json.loads(prior_raw);original_closed(prior,102)
 retained=[q for q in prior['commands']if q['exitCode']!=0]
 need([q['label']for q in retained]==['source-preview-whitespace','complete-preview-whitespace','actual-index-whitespace']
      and sum(q['exitCode']==0 for q in prior['commands'])==99,'Actual prior command outcomes differ')
 for q in retained:
  need(q['exitCode']==2 and q['stdout']['bytes']==141
       and q['stdout']['sha256']=='8714fc72ee9171a6cf869dbbbbb65022209654ddeb41b2b0a543edf541f53d92'
       and q['stderr']['bytes']==0,'Only exact retained prior whitespace diagnostics are admitted')
  exact_file(pathlib.Path(q['stdout']['path']),141,q['stdout']['sha256'])
  exact_file(pathlib.Path(q['stderr']['path']),0,'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
 need(prior['head']==prior['normalPushReadback']==START and prior['tree']==START_TREE
      and prior['controllerSHA256']==PREDECESSOR_SHA and prior['normalPushCompleted']is True
      and prior['state']=='SOURCE_NORMAL_MERGE_PUBLISHED_RUNTIME_CLOSED' and prior['firstFailure']is None
      and prior['sourceRetentionPassed'] and not prior['commandCustodyBlocked'],'Actual prior publication differs')
 projection_raw=exact_file(PREP/'source-projection.json',6929,'0dbcb7031a4151e1b3427b4bcef43946ee2f5db01a814696b645bbfbcff1ea46')
 projection=json.loads(projection_raw)
 need(projection['base']['head']==START and projection['base']['tree']==START_TREE
      and projection['sourceTree']==SOURCE_TREE
      and projection['sourcePaths']==11 and projection['sourceLeaves']==23753,
      'Reviewed pure-byte projection differs')
 resource=O['resources']();EVIDENCE.mkdir(mode=0o700)
 r={'schema':'pinkha-root-heart-notes155-source-integration/v1','state':'RUNNING','startedAt':time.time(),
    'start':START,'startTree':START_TREE,'commands':[],'controllerSHA256':sha(read(pathlib.Path(__file__))),
    'sourceInputSHA256':sha(input_raw),'originalHelperSHA256':OLD_SHA,'resourceBefore':resource,
    'firstFailure':None,'runtimeAcceptance':False,'compilerInvocations':0,'testsExecuted':0,'materializations':0}
 write(EVIDENCE/'started.json',enc(r));c=O['Commands'](r)
 def interrupted(sig,frame):
  c.interrupted_signal=sig;c.blocked=True
  if not c.in_cleanup:raise TimeoutError('Source integration interrupted '+str(sig))
 handlers={sig:signal.getsignal(sig)for sig in (signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
 for sig in handlers:signal.signal(sig,interrupted)
 signal.setitimer(signal.ITIMER_REAL,300)
 try:integrate(c,r,payload,prior_raw,prior,projection_raw)
 except BaseException as e:r.update(state='FAILED_PRESERVED_NO_AUTOMATIC_RESET',firstFailure={'type':type(e).__name__,'message':str(e)})
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  for sig,handler in handlers.items():signal.signal(sig,handler)
  r.update(finishedAt=time.time(),commandCustodyBlocked=c.blocked)
  write(EVIDENCE/'receipt.json',enc(r));write(OUT,enc(r))
  print(json.dumps({k:r.get(k)for k in ('state','head','tree','firstFailure','commandCustodyBlocked')}),flush=True)
 if r['firstFailure']:raise SystemExit(1)
if __name__=='__main__':main()
