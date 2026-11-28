#!/usr/bin/env python3
"""Fixed ordinary Bookmark result evidence merge; no build or runtime activation."""
import ast,base64,difflib,hashlib,json,os,pathlib,re,signal,sys,time
sys.dont_write_bytecode=True
OLD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-w2-bookmark-language171-source-integration.py')
OLD_SHA='3f943613f16b5adc1e686cfa41b7c3bd9632e6e83bf4f8c77ee520597dcc102f'
PREP=pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-bookmark31-result-source-preparation-20261128')
EVIDENCE=pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-bookmark31-result-source-integration-20261128')
PRIVATE=pathlib.Path('/tmp/pinkha-w3-bookmark31-result-private-index-20261128')
OUT=pathlib.Path('/tmp/pinkha-w3-bookmark31-result-source-integration-20261128.json')
GATE_OUT=pathlib.Path('/tmp/pinkha-w3-bookmark31-result-retention-20261128.json')
START='319422f27af10e2fe5b0d837bfb703a44a59c665'
START_TREE='3b33534bedc8c2b7d1e5bcccfe6cc1ccb7eb49e5'
SOURCE_TREE='cacefe6fa60f129fb897cf5157e07b4ce11e5c82'
DONORS=['1302840dd3014cb250a01f318431ee02a61f1acd']
PREFIX='docs/validation/20261128-wave3-bookmark31-result-intake'
old=OLD.read_bytes()
assert len(old)==60995 and hashlib.sha256(old).hexdigest()==OLD_SHA
O={'__name__':'pinned_original_171','__file__':str(OLD)}
exec(compile(old,str(OLD),'exec'),O)
O.update(START=START,START_TREE=START_TREE,EVIDENCE=EVIDENCE,PRIVATE=PRIVATE,MAX_SECONDS=300)
need=O['require'];read=O['read_regular'];write=O['exclusive'];enc=O['encoded'];sha=O['sha']
root=O['ROOT']
# Only the protected-leaf transition changes: all83 now already exist and stay exact.
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
exec(compile(guard_new,'fixed_current83_guard.py','exec'),O)
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
def integrate(c,r,payload,prior_raw,prior,prep_raw,native_raw):
 rows=payload['rows'];values=O['decode_rows'](rows)
 need(len(rows)==31 and all(x['status']=='A' for x in rows.values())
      and sum(x['after']['bytes']for x in rows.values())==626537,'Only31 original additions admitted')
 need(payload['start']==START and payload['startTree']==START_TREE and payload['donorTips']==DONORS
      and payload['sourceTree']==SOURCE_TREE and payload['sourceLeaves']==23668,'Source projection differs')
 need(c.git('initial-head-tree','rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[START,START_TREE]
      and c.git('initial-branch','symbolic-ref','HEAD').decode().strip()==O['REF'],'Integration base differs')
 merge_head=pathlib.Path(c.git('merge-state-path','rev-parse','--path-format=absolute','--git-path','MERGE_HEAD').decode().strip())
 need(not merge_head.exists(),'Preserve any existing merge')
 original=O['original_status'](c,'before');O['exact_remote'](c,'original-remote',START)
 index=pathlib.Path(c.git('original-index-path','rev-parse','--path-format=absolute','--git-path','index').decode().strip())
 index_state=O['optional_file_identity'](index)
 base=O['tree_leaves'](c,'complete-current-tree',START_TREE)
 need(len(base)==23637,'Current full tree count differs')
 specs=[('1302840dd3014cb250a01f318431ee02a61f1acd','90c05af6ee3cde75b85508f6f294c392e3add3e4','8e6fe6d8f47c0229853e8948edbd58ca01dd1a9e',31)]
 need(len(payload['donorLinks'])==1,'Exact one result link required')
 seen=set();oids=set()
 for i,(link,spec) in enumerate(zip(payload['donorLinks'],specs)):
  commit,tree,parent,count=spec;tag='original-donor-'+str(i+1)
  need(link['commit']==commit and link['tree']==tree and link['parents']==[parent] and len(link['files'])==count,'Original donor link differs')
  need(c.git(tag+'-identity','show','-s','--format=%H %T %P',commit).decode().split()==[commit,tree,parent],'Published donor identity differs')
  if i<2:c.git(tag+'-base-integrated','merge-base','--is-ancestor',parent,START)
  need(O['changes'](c,tag+'-full-diff',parent,commit)=={p:'A'for p in link['files']},'Unreviewed donor delta')
  leaves=O['parse_leaves'](c.git(tag+'-changed-leaves','ls-tree','-r','-z','--full-tree',tree,'--',*sorted(link['files'])))
  bodies=O['batch_blobs'](c,tag+'-whole-original-bodies',{x['after']['gitBlob']:None for x in link['files'].values()})
  for path,item in link['files'].items():
   need(path not in seen and path not in base and rows[path]['donorCommit']==commit,'Overlap or existing source')
   need(item=={'status':'A','after':rows[path]['after']},'Full source row differs')
   O['require_leaf'](leaves,path,item['after']);O['match'](bodies[item['after']['gitBlob']],item['after'])
   need(bodies[item['after']['gitBlob']]==values[path],'Full original body differs')
   O['destination_preflight'](path,None);seen.add(path)
  oids.update(bodies)
 need(seen==set(rows),'Full31 source closure differs')
 source=O['expected_leaves'](base,rows)
 guards_payload={**payload,'donorRows':rows}
 before=O['validate_guards'](c,guards_payload,base,source,prior,'before')
 O['resources']()
 c.run('create-exclusive-private-index',O['PRE']+['python3','-B','-c','import os,sys;os.mkdir(sys.argv[1],0o700)',str(PRIVATE)])
 stree=O['private_tree'](c,'complete-original31-preview',base,rows,source)
 need(stree==SOURCE_TREE,'Complete original31 union differs')
 diagnostic=check_diff(c,'source-preview-whitespace',['diff','--check','--no-renames',START,stree],set(rows))
 after=O['validate_guards'](c,guards_payload,base,source,prior,'after')
 need(before==after,'Original pins changed')
 intake={'schema':'pinkha-w3-bookmark31-result-source-intake/v1','start':START,'startTree':START_TREE,
         'normalMergeParents':[START,*DONORS],'sourceTree':SOURCE_TREE,'sourcePaths':31,
         'sourceBytes':626537,'completeSourceLeaves':23668,
         'files':{p:{k:v for k,v in row.items()if k not in ('base64','beforeBase64')}for p,row in rows.items()},
         'sourceInputSHA256':'68fdee26555e296faafff764ad84b2c33a730bb1b961589c3a21dfb569c6ba25',
         'inputPins':before,'outputPins':after,'protectedLeaves':83,'guardFiles':52,'sourceMapRows':145,
         'currentMacStage':'a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd','runtimeAcceptance':False,
         'testsExecuted':0,'compilerInvocations':0,'materializations':0,
         'originalW2Scope':'Qualified original1ff two new SwiftTesting methods plus retained four XCTest positives across two executions; no single six-test execution. Original4441 and fe4d FAIL retained',
         'sourceReadback':'All31 complete Git bodies verified. Earlier collection terminal JSON encoding FAIL preserved separately; no source/runtime command repeated.',
         'AppleNativeUIScope':'No new acceptance inferred from Linux component proof'}
 evidence={'root-source-intake.json':enc(intake),'root-integration-controller.py':read(pathlib.Path(__file__)),
           'prior132-publication.original.json':prior_raw,'source-readback-review.original.json':prep_raw,
           'original-w2-publication-receipt.json':native_raw,
           'original83-guard-derivation.json':enc({'originalControllerSHA256':OLD_SHA,'originalFunction':guard_old,
                   'currentFunction':guard_new,'wholeOriginalInverse':True,
                   'onlyChange':'Replace previous82-plus-one transition with current83 exact preservation; all source/pin/runtime checks unchanged'})}
 erows={};evals={}
 for name,raw in evidence.items():
  path=PREFIX+'/'+name;need(path not in base and path not in rows,'Evidence already exists')
  O['destination_preflight'](path,None);O['generated_evidence_is_whitespace_clean'](raw)
  erows[path]={'status':'A','before':None,'beforeBase64':None,
              'after':{'bytes':len(raw),'sha256':sha(raw),'gitBlob':O['blob'](raw),'gitMode':'100644'}}
  evals[path]=raw
 allrows={**rows,**erows};whole=O['expected_leaves'](base,allrows)
 O['write_new_objects'](c,erows,evals,oids|{v['sha']for v in base.values()if v['type']=='blob'})
 finaltree=O['private_tree'](c,'complete-final-preview',base,allrows,whole)
 check_diff(c,'complete-preview-whitespace',['diff','--check','--no-renames',START,finaltree],set(rows),diagnostic)
 need(c.git('premerge-head-tree','rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[START,START_TREE]
      and c.git('premerge-index-tree','write-tree').decode().strip()==START_TREE,'Original HEAD or index advanced')
 need(O['original_status'](c,'premerge')==original and O['optional_file_identity'](index)==index_state,'Premerge custody changed')
 O['exact_remote'](c,'premerge-remote',START)
 r.update(phase='NORMAL_ONE_DONOR_EVIDENCE_MERGE',expectedSourceTree=SOURCE_TREE,expectedTree=finaltree)
 O['resources']()
 c.git('normal-one-donor-evidence-merge','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
       'merge','--no-ff','--no-commit',*DONORS,timeout=60)
 need(read(merge_head).decode().split()==DONORS,'Normal merge parents differ')
 need(c.git('actual-donor-index-tree','write-tree').decode().strip()==SOURCE_TREE
      and O['tree_leaves'](c,'actual-donor-full-tree',SOURCE_TREE)==source,'Normal merge differs; preserve without reset')
 O['write_owned_batch'](c,'write-exclusive-root-evidence',erows,evals,{p:None for p in erows})
 c.git('stage-exact-root-evidence','add','--sparse','--',*sorted(erows))
 need(c.git('actual-complete-index-tree','write-tree').decode().strip()==finaltree,'Full staged tree differs')
 need(O['changes'](c,'actual-complete-delta',START,finaltree)=={p:'A'for p in allrows},'Unexpected changed existing source')
 need(c.git('unstaged-source-check','diff','--name-only')==b''
      and c.git('untracked-source-check','ls-files','--others','--exclude-standard','-z')==original['untracked'],'Unexpected unstaged/private changes')
 check_diff(c,'actual-index-whitespace',['diff','--cached','--check','--no-renames',START],set(rows),diagnostic)
 need(O['validate_guards'](c,guards_payload,base,whole,prior,'after')==after,'Final source guards differ')
 r['phase']='ORIGINAL145_RETENTION_GATE'
 gate_raw=O['gate_once'](c,r,'original-retention-gate',finaltree,GATE_OUT)
 need(c.git('final-precommit-head','rev-parse','HEAD').decode().strip()==START
      and c.git('final-precommit-index','write-tree').decode().strip()==finaltree,'Gate changed source state')
 need(c.git('final-precommit-untracked','ls-files','--others','--exclude-standard','-z')==original['untracked'],'Private files changed')
 message=('Integrate qualified Bookmark component result evidence\n\n'
          'Merge exact published1302840 as ordinary second parent. Retain genuine two new SwiftTesting methods and four earlier XCTest positives as separate executions, with all original failures. '
          'Preserve all existing source,83 protected leaves,52 witnesses,56 pins,145 source mappings and45 closed runtime tuples. No compiler or product tests rerun.\n')
 c.git('normal-two-parent-evidence-commit','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
       'commit','-F','-',data=message.encode(),timeout=45)
 head=c.git('final-committed-head','rev-parse','HEAD').decode().strip()
 r['head']=head
 need(c.git('final-committed-parents','show','-s','--format=%T %P',head).decode().split()==[finaltree,START,*DONORS],'Final ordinary ancestry differs')
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
 input_raw=exact_file(PREP/'source-inputs.json',983941,'68fdee26555e296faafff764ad84b2c33a730bb1b961589c3a21dfb569c6ba25')
 payload=json.loads(input_raw)
 prior_raw=exact_file(pathlib.Path('/tmp/pinkha-w3-runtime18-bookmark132-source-integration-20261128.json'),210194,'ba6af3ede1f6af1169fdc6831e72fbe1dfd620f3e175f633be446f998f2122ee')
 prior=json.loads(prior_raw);original_closed(prior,77)
 need(prior['head']==prior['normalPushReadback']==START and prior['tree']==START_TREE
      and prior['state']=='SOURCE_NORMAL_MERGE_PUBLISHED_RUNTIME_CLOSED' and prior['firstFailure']is None
      and prior['sourceRetentionPassed'] and not prior['commandCustodyBlocked'],'Actual prior publication differs')
 prep_raw=exact_file(PREP/'source-readback-review.json',87007,'0cc2d73831dfb574dc5492c25dc71218ed1cc5d56d14b2a91d9399325f7f5055')
 prep=json.loads(prep_raw);original_closed(prep,17)
 need(prep['status']=='PASS_PRIMARY_SOURCE_REVIEW_ORIGINAL_ENCODER_FAILURE_RETAINED'
      and prep['sourceReadbackQualified'] is True and prep['originalCollectionStatus']=='FAIL_TERMINAL_RECEIPT_ENCODING'
      and prep['firstFailure']is None and not prep['commandCustodyBlocked'],'Actual source readback differs')
 native_raw=exact_file(pathlib.Path('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-continuation2-result-20261128/publication-root-receipt.json'),3760,'dfec1f4060793bc15b2f38695c3a3d7c8df258558d267096ecab7a7c916246e9')
 resource=O['resources']();EVIDENCE.mkdir(mode=0o700)
 r={'schema':'pinkha-root-bookmark31-result-source-integration/v1','state':'RUNNING','startedAt':time.time(),
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
 try:integrate(c,r,payload,prior_raw,prior,prep_raw,native_raw)
 except BaseException as e:r.update(state='FAILED_PRESERVED_NO_AUTOMATIC_RESET',firstFailure={'type':type(e).__name__,'message':str(e)})
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  for sig,handler in handlers.items():signal.signal(sig,handler)
  r.update(finishedAt=time.time(),commandCustodyBlocked=c.blocked)
  write(EVIDENCE/'receipt.json',enc(r));write(OUT,enc(r))
  print(json.dumps({k:r.get(k)for k in ('state','head','tree','firstFailure','commandCustodyBlocked')}),flush=True)
 if r['firstFailure']:raise SystemExit(1)
if __name__=='__main__':main()
