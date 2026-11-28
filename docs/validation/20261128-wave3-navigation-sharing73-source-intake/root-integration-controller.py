#!/usr/bin/env python3
"""Fixed C30/navigation and member-role source merge; no build or runtime activation."""
import ast,base64,difflib,hashlib,json,os,pathlib,re,signal,sys,time
sys.dont_write_bytecode=True
OLD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-w2-bookmark-language171-source-integration.py')
OLD_SHA='3f943613f16b5adc1e686cfa41b7c3bd9632e6e83bf4f8c77ee520597dcc102f'
PREP=pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-navigation-sharing73-source-preparation-20261128/prepared1')
EVIDENCE=pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-navigation-sharing73-source-integration-20261128')
PRIVATE=pathlib.Path('/tmp/pinkha-w3-navigation-sharing73-private-index-20261128')
OUT=pathlib.Path('/tmp/pinkha-w3-navigation-sharing73-source-integration-20261128.json')
GATE_OUT=pathlib.Path('/tmp/pinkha-w3-navigation-sharing73-retention-20261128.json')
START='1ae5f762cd42c3c4500c553a17014e343440ce0f'
START_TREE='d1ede3887556e0670b34a20cc74e689b55899191'
SOURCE_TREE='ffc588498a01632e76ea1a937331ec27fd41abeb'
DONOR_TREE='ffc588498a01632e76ea1a937331ec27fd41abeb'
DONORS=['d1b04526825ad10b07c59313727629cec35f9559','80bd7636bb53391d8350a7ef39810e0b2cd9b733']
PREFIX='docs/validation/20261128-wave3-navigation-sharing73-source-intake'
INPUT_SHA='23f00ac836ee697ac82b7943b8bb743a95363660b2010449da414106c02f7668'
PREDECESSOR_SHA='cf18d1201f4492296a824e11d3b11cb2e71281290ba178ed1c554bcaf86297a3'
PRIOR_CONTROLLER_SHA='09705f8877ebd2a0a568982f38851ae6fdae53c38ef0b3b93842e342abb0ab6c'
TARGET_SDK='9af3e798212dc33b3cc7ea95a065a98c034788c6'
TARGET_KIT='414e0d3e95d53509381d233a23fcdd28ef24167a'
ORIGINAL_EVIDENCE_NAMES=["navigation-d1b-source-review.original.json","navigation-d1b-original-results-proof.original.json","navigation-d1b-dependency-proof.original.json","navigation-d1b-http-full-inverse.original.json","navigation-d1b-root-review.original.json","catalog30-root-review.original.json","catalog30-dependency-peer.original.json","sharing80-root-review.original.json","source-composition-proof.original.json"]
old=OLD.read_bytes()
assert len(old)==60995 and hashlib.sha256(old).hexdigest()==OLD_SHA
O={'__name__':'pinned_original_171','__file__':str(OLD)}
exec(compile(old,str(OLD),'exec'),O)
O.update(START=START,START_TREE=START_TREE,EVIDENCE=EVIDENCE,PRIVATE=PRIVATE,MAX_SECONDS=300,
         SDK=TARGET_SDK,KIT=TARGET_KIT)
need=O['require'];read=O['read_regular'];write=O['exclusive'];enc=O['encoded'];sha=O['sha']
root=O['ROOT']
# Preserve the executed83-leaf guard with the actual published146-row map.
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
GUARD_EDITS=[{"before":"guards['originalRetentionRows'] == 145","after":"guards['originalRetentionRows'] == 146"},{"before":"guards['expectedRetentionRows'] == 145","after":"guards['expectedRetentionRows'] == 146"},{"before":"The complete original145-row source map","after":"The complete original146-row source map"},{"before":"len(json.loads(map_raw)['changes']) == 145","after":"len(json.loads(map_raw)['changes']) == 146"},{"before":"722a41b870957cf17f9724b8dd732b7d6088bde0","after":"87b7d48812dfab3e49955da6009c2c617fdd1c75"},{"before":"Actual published map145 including row110","after":"Actual published map146 including Notes host"},{"before":"'reviewedRefactors': 145","after":"'reviewedRefactors': 146"},{"before":"Selected original Kit26 changed","after":"Selected current Kit414 source changed"}]
for edit in GUARD_EDITS:
 need(guard_new.count(edit['before'])==1,'Reviewed guard splice is not unique')
 guard_new=guard_new.replace(edit['before'],edit['after'],1)
restored_guard=guard_new
for edit in reversed(GUARD_EDITS):
 need(restored_guard.count(edit['after'])==1,'Reviewed guard inverse is not unique')
 restored_guard=restored_guard.replace(edit['after'],edit['before'],1)
need(restored_guard==guard_current83,'Complete executed current83 guard inverse differs')
exec(compile(guard_new,'fixed_current9af_414_map146_guard.py','exec'),O)
gate_node=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='gate_once')
gate_old=ast.get_source_segment(old.decode(),gate_node)
gate_new=gate_old
GATE_EDITS=[{'before':"len(result['reviewedRefactors']) == 145",'after':"len(result['reviewedRefactors']) == 146"},
            {'before':'Original145 retention gate did not pass','after':'Original146 retention gate did not pass'},
            {'before':"'reviewedRefactors':145",'after':"'reviewedRefactors':146"}]
for edit in GATE_EDITS:
 need(gate_new.count(edit['before'])==1,'Original gate admission count splice differs')
 gate_new=gate_new.replace(edit['before'],edit['after'],1)
gate_restored=gate_new
for edit in reversed(GATE_EDITS):
 need(gate_restored.count(edit['after'])==1,'Original gate admission inverse differs')
 gate_restored=gate_restored.replace(edit['after'],edit['before'],1)
need(gate_restored==gate_old,'Entire original gate admission inverse differs')
exec(compile(gate_new,'original_gate_same_algorithm_current146_count.py','exec'),O)
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
 need(len(rows)==73 and rows==donor_rows and root_rows=={}
      and sum(x['status']=='A'for x in rows.values())==67
      and sum(x['status']=='M'for x in rows.values())==6
      and sum(x['after']['bytes']for x in rows.values())==1228315,
      'Only the exact73 original source paths are admitted')
 need(payload['start']==START and payload['startTree']==START_TREE and payload['donorTips']==DONORS
      and payload['donorTree']==DONOR_TREE and payload['sourceTree']==SOURCE_TREE
      and payload['sourceLeaves']==23834 and payload['runtimeAcceptance']is False
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
 need(len(base)==23767,'Current full tree count differs')
 # Missing immutable donors are fetched through the original owned Git route only.
 availability=c.git('exact-navigation-sharing-donors-local-object','cat-file','--batch-check',
                    data=''.join(sha+'\n'for sha in DONORS).encode()).decode().splitlines()
 need(len(availability)==2,'Exact donor object observation differs')
 missing=[]
 for commit,line in zip(DONORS,availability):
  parts=line.split()
  if parts==[commit,'missing']:missing.append(commit)
  else:need(len(parts)==3 and parts[0]==commit and parts[1]=='commit'
            and parts[2].isdigit() and int(parts[2])>0,'Unexpected donor object identity')
 if missing:
  c.git('fetch-exact-missing-navigation-sharing-donors','fetch','--no-tags','--refmap=','origin',*missing,publish=True,timeout=60)
 specs=[('0b8f03a13d332fc44ed89fc9d6389658d6cfc5e0','c8fd677a851fb466a9c8f6b62f97564151387df3',
         'e6fedfdbc7390a5a4e934726806c952319ba4238',30),
        ('d1b04526825ad10b07c59313727629cec35f9559','b0140be8a4d53766a7e4a221e037b00e9d4c3bb2',
         '0b8f03a13d332fc44ed89fc9d6389658d6cfc5e0',27),
        ('80bd7636bb53391d8350a7ef39810e0b2cd9b733','aa886f51c746cfcedd71557b803618e4d2b614cd',
         '6ade3661c261e66c987b7017a6181bdfcebc1d58',16)]
 need(len(payload['donorLinks'])==3,'Exact C30/navigation and Sharing ancestry links required')
 seen=set();oids=set()
 preimages=O['batch_blobs'](c,'all-six-current-source-preimages',
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
  if i==1:need(parent==specs[0][0],'Exact C30-to-navigation ancestry link differs')
  else:c.git(tag+'-base-integrated','merge-base','--is-ancestor',parent,START)
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
      'Full73 original source closure differs')
 donor_source=O['expected_leaves'](base,donor_rows)
 source=O['expected_leaves'](base,rows)
 before=O['validate_guards'](c,payload,base,source,prior,'before')
 O['resources']()
 c.run('create-exclusive-private-index',O['PRE']+['python3','-B','-c','import os,sys;os.mkdir(sys.argv[1],0o700)',str(PRIVATE)])
 stree=O['private_tree'](c,'complete-navigation-sharing-source-preview',base,rows,source)
 need(donor_source==source and stree==DONOR_TREE==SOURCE_TREE,'Complete73-path source union differs')
 production=sorted(path for path in rows if not path.startswith('docs/'))
 c.git('production-source-whitespace','diff','--check','--no-renames',START,stree,'--',*production)
 evidence_paths={path for path in rows if path.startswith('docs/')}
 diagnostic=check_diff(c,'source-preview-whitespace',['diff','--check','--no-renames',START,stree],evidence_paths)
 after=O['validate_guards'](c,payload,base,source,prior,'after')
 need(before==payload['guardInputs']['inputPins'] and after==payload['guardInputs']['outputPins'],
      'Exact input/output pin transition differs')
 intake={'schema':'pinkha-w3-navigation-sharing73-source-intake/v1','start':START,'startTree':START_TREE,
         'normalMergeParents':[START,*DONORS],'donorTree':DONOR_TREE,'sourceTree':SOURCE_TREE,
         'sourcePaths':73,'sourceBytes':1228315,'completeSourceLeaves':23834,
         'sourceStatusCounts':{'A':67,'M':6},
         'files':{p:{k:v for k,v in row.items()if k not in('base64','beforeBase64')}for p,row in rows.items()},
         'sourceInputSHA256':INPUT_SHA,'inputPins':before,'outputPins':after,
         'protectedLeaves':83,'reviewedProtectedUpdates':0,'guardFiles':52,'reviewedGuardUpdates':0,
         'sourceMapRows':146,'sourceMapReplacementFieldsChanged':[],
         'runtimeAcceptance':False,'testsExecuted':0,'compilerInvocations':0,'materializations':0,
         'NavigationScope':'Complete original C30 parent and d1b child source. Original26 qualification is23 unchanged retained methods plus3 actual corrected methods; both earlier failures remain literal. No current App, Apple or N24 acceptance. W1 owns authoritative expectedNetworkID; W2 owns its separate caller. No route activation on8ac.',
         'SharingScope':'Exact original per-member capability projection with five unrun methods. Existing account/owner and native authority remain; no new atomicity, ACK convergence or Apple acceptance claim.',
         'HistoricalAdmission':'Current closed Native26, hosted_t5 and warm controls stay byte-exact. No current product result or source fixture is relabeled.',
         'CurrentProductPreservation':'Current ObjectCreator/PropertyStore, Notes UI, SDK9af/Kit414,83 protected paths,52 source witnesses,146 map rows,56 main pins,45 closed tuples and four untracked files remain exact.'}
 evidence={'root-source-intake.json':enc(intake),'root-integration-controller.py':read(pathlib.Path(__file__)),
           'prior-notes146-publication.original.json':prior_raw,
           'source-guard-derivation.json':enc({'originalControllerSHA256':OLD_SHA,
                'predecessorControllerSHA256':PREDECESSOR_SHA,'priorPublicationControllerSHA256':PRIOR_CONTROLLER_SHA,
                'originalFunction':guard_old,
                'current83Function':guard_current83,'successorFunction':guard_new,
                'literalGuardOperations':GUARD_EDITS,'wholeOriginalInverse':True,
                'originalGateAdmission':gate_old,'currentGateAdmission':gate_new,'literalGateCountOperations':GATE_EDITS,
                'onlyChanges':'Bind already-published map146 whole identity and count; preserve the original retention algorithm. All83 protected and52 guard source identities, SDK9af/Kit414,56 main pins and45 runtime tuples remain exact; no source promotion is reapplied.'})}
 need(set(payload['evidence'])==set(ORIGINAL_EVIDENCE_NAMES),'Finite original evidence names differ')
 for name,item in payload['evidence'].items():
  raw=base64.b64decode(item['base64'],validate=True);O['match'](raw,item['after'])
  need(name not in evidence,'Evidence name overlaps');evidence[name]=raw
 need(len(evidence)==13,'Exact13 intake evidence additions required')
 erows={};evals={}
 for name,raw in evidence.items():
  path=PREFIX+'/'+name;need(path not in base and path not in rows,'Evidence already exists')
  O['destination_preflight'](path,None);O['generated_evidence_is_whitespace_clean'](raw)
  erows[path]={'status':'A','before':None,'beforeBase64':None,
              'after':{'bytes':len(raw),'sha256':sha(raw),'gitBlob':O['blob'](raw),'gitMode':'100644'}}
  evals[path]=raw
 allrows={**rows,**erows};whole=O['expected_leaves'](base,allrows)
 need(len(allrows)==86 and len(whole)==23847,'Complete86-path/23847-leaf projection differs')
 O['write_new_objects'](c,erows,evals,oids|{v['sha']for v in base.values()if v['type']=='blob'})
 finaltree=O['private_tree'](c,'complete-final-preview',base,allrows,whole)
 check_diff(c,'complete-preview-whitespace',['diff','--check','--no-renames',START,finaltree],evidence_paths,diagnostic)
 need(c.git('premerge-head-tree','rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[START,START_TREE]
      and c.git('premerge-index-tree','write-tree').decode().strip()==START_TREE,'Original HEAD or index advanced')
 need(O['original_status'](c,'premerge')==original and O['optional_file_identity'](index)==index_state,'Premerge custody changed')
 O['exact_remote'](c,'premerge-remote',START)
 r.update(phase='NORMAL_NAVIGATION_SHARING_SOURCE_MERGE',expectedDonorTree=DONOR_TREE,expectedSourceTree=SOURCE_TREE,expectedTree=finaltree)
 O['resources']()
 c.git('normal-navigation-sharing-source-merge','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
       'merge','--no-ff','--no-commit',*DONORS,timeout=60)
 need(read(merge_head).decode().split()==DONORS,'Normal merge parents differ')
 need(c.git('actual-donor-index-tree','write-tree').decode().strip()==DONOR_TREE
      and O['tree_leaves'](c,'actual-donor-full-tree',DONOR_TREE)==donor_source,
      'Normal merge differs; preserve without reset')
 O['write_owned_batch'](c,'write-exact-thirteen-intake-files',erows,evals,{p:None for p in erows})
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
 r['phase']='ORIGINAL146_RETENTION_GATE'
 gate_raw=O['gate_once'](c,r,'original-retention-gate',finaltree,GATE_OUT)
 need(c.git('final-precommit-head','rev-parse','HEAD').decode().strip()==START
      and c.git('final-precommit-index','write-tree').decode().strip()==finaltree,'Gate changed source state')
 need(c.git('final-precommit-untracked','ls-files','--others','--exclude-standard','-z')==original['untracked'],'Private files changed')
 message=('Integrate original navigation catalog and member-role source\n\n'
          'Merge exact published d1b with C30 ancestry and Sharing80 while preserving all current1ae source. '
          'Retain original26 component evidence as23 unchanged plus3 actual corrected methods and preserve both failures. '
          'Sharing five new methods and all current App, Apple and N24 acceptance remain pending; native routes stay closed. '
          'Preserve83 protected paths,52 witnesses,56 main pins,146 mappings,45 closed tuples and current Notes/Store/ObjectCreator whole bytes. '
          'No compiler, product tests, source extraction or runtime activation.\n')
 c.git('normal-three-parent-source-commit','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
       'commit','-F','-',data=message.encode(),timeout=45)
 head=c.git('final-committed-head','rev-parse','HEAD').decode().strip();r['head']=head
 need(c.git('final-committed-parents','show','-s','--format=%T %P',head).decode().split()==[finaltree,START,*DONORS],
      'Final ordinary ancestry differs')
 need(O['original_status'](c,'committed')==original and not merge_head.exists(),'Committed custody differs')
 O['exact_remote'](c,'prepush-remote',START)
 r.update(tree=finaltree,donorTips=DONORS,files=sorted(allrows),sourceRetentionPassed=True,reviewedRefactors=146,
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
 input_raw=exact_file(PREP/'source-inputs.json',4096284,INPUT_SHA)
 payload=json.loads(input_raw)
 prior_raw=exact_file(pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-notes-map146-continuation-20261128/receipt.json'),
                      200053,'136ae5aa5ef21d67345c647584af05b8adcb5dd23ba179a40fcb24b7e04186e8')
 prior=json.loads(prior_raw);original_closed(prior,70)
 need(all(q['exitCode']==0 for q in prior['commands']),'Actual prior70 command outcomes differ')
 need(prior['schema']=='pinkha-root-notes-map146-continuation/v1'
      and prior['head']==prior['normalPushReadback']==START and prior['tree']==START_TREE
      and prior['controllerSHA256']==PRIOR_CONTROLLER_SHA and prior['normalPushCompleted']is True
      and prior['state']=='SOURCE_PENDING_TWO_PARENT_MERGE_CONTINUED_AND_PUBLISHED_RUNTIME_CLOSED'
      and prior['firstFailure']is None and prior['sourceRetentionPassed']
      and prior['reviewedRefactors']==146 and not prior['commandCustodyBlocked']
      and prior['originalFailedGatePreserved']is True and prior['originalMergeContinued']is True
      and prior['originalUntrackedPreserved']is True
      and prior['runtimeAcceptance']is False
      and prior['compilerInvocations']==prior['testsExecuted']==prior['materializations']==0,
      'Actual prior publication and preserved original failure differ')
 exact_file(pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-notes-map146-continuation-20261128/command-054-original146-retention-gate.stdout'),
            51524,'1cde871db5d5ec1e56b37b1299a4f27ad8f83e4954d7954ab01edcb1708cf653')
 projection_raw=exact_file(PREP/'source-projection.json',21734,'dfa62ec2333d360907ccb1b1c2469ff5aa745ab3d739d946d5e0be2f35f2a850')
 projection=json.loads(projection_raw)
 need(projection['base']['head']==START and projection['base']['tree']==START_TREE
      and projection['sourceTree']==SOURCE_TREE
      and projection['sourcePaths']==73 and projection['sourceLeaves']==23834,
      'Reviewed pure-byte projection differs')
 resource=O['resources']();EVIDENCE.mkdir(mode=0o700)
 r={'schema':'pinkha-root-navigation-sharing73-source-integration/v1','state':'RUNNING','startedAt':time.time(),
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
