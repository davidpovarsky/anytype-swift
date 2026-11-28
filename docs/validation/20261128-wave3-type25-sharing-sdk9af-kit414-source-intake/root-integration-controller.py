#!/usr/bin/env python3
"""Fixed Type25, sharing and reviewed SDK/Kit source merge; no build or runtime activation."""
import ast,base64,difflib,hashlib,json,os,pathlib,re,signal,sys,time
sys.dont_write_bytecode=True
OLD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-w2-bookmark-language171-source-integration.py')
OLD_SHA='3f943613f16b5adc1e686cfa41b7c3bd9632e6e83bf4f8c77ee520597dcc102f'
PREP=pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-type25-sharing-sdk9af-kit414-source-preparation-20261128/prepared1')
EVIDENCE=pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-type25-sharing-sdk9af-kit414-source-integration-20261128')
PRIVATE=pathlib.Path('/tmp/pinkha-w3-type25-sharing-sdk9af-kit414-private-index-20261128')
OUT=pathlib.Path('/tmp/pinkha-w3-type25-sharing-sdk9af-kit414-source-integration-20261128.json')
GATE_OUT=pathlib.Path('/tmp/pinkha-w3-type25-sharing-sdk9af-kit414-retention-20261128.json')
START='b8521ca8d9d88f62aeb8e246de2c1ae2dd798588'
START_TREE='1875b474c3930e2f9388f9fd5b26d35536eee163'
SOURCE_TREE='6cbd59fb65260acb304d824ede40a8894fde66fc'
DONOR_TREE='c44253764445205802f3c25a54c15ca756e0d70a'
DONORS=['6ade3661c261e66c987b7017a6181bdfcebc1d58', 'e6fedfdbc7390a5a4e934726806c952319ba4238']
PREFIX='docs/validation/20261128-wave3-type25-sharing-sdk9af-kit414-source-intake'
INPUT_SHA='5298ffbeef937c338769655c30d1653ed7adc617019f04d2831498c5ea7c07c0'
PREDECESSOR_SHA='7f678b3716bb2015fb90bb53d43909c877d772c3e988c7d914b7f616678082ad'
TARGET_SDK='9af3e798212dc33b3cc7ea95a065a98c034788c6'
TARGET_KIT='414e0d3e95d53509381d233a23fcdd28ef24167a'
ROOT_PIN_PATHS=['Anytype.xcodeproj/project.pbxproj', 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved', 'Modules/PinkhaAnyHanlin/Package.resolved', 'Modules/PinkhaAnyHost/Package.resolved', 'Modules/PinkhaAnyIntegration/Package.resolved', 'Modules/PinkhaAnyNative/Package.swift', 'Modules/PinkhaAnyUI/Package.resolved', 'Modules/PinkhaAnyUI/Package.swift', 'Modules/PinkhaKit/Package.swift', 'Modules/PinkhaTorahPresentation/Package.resolved', 'Modules/PinkhaTorahPresentation/Package.swift', 'Tools/Hanlin/source.json', 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json']
EXACT_MAP_UPDATES=[{'after': '381a166034fa6b7948fd2f2e35d8b3eb880c8093', 'before': 'e558479f8e34e2f98971cbd2970fc3328100804c', 'field': 'replacementBlob', 'index': 59}, {'after': '179a63c9df96500fe72bdbee4fcc52949b3ab4a2', 'before': 'a39f3f506f8279c5acca6f74e7c7140710af9c65', 'field': 'replacementBlob', 'index': 102}]
ORIGINAL_EVIDENCE_NAMES=['sdk9af-kit414-pin-handoff.original.json', 'sdk9af-kit414-pin-inverses.original.json', 'sdk9af-kit414-pin-proof.original.json', 'sharing23-root-source-review.original.json', 'type25-current-dependency-api-proof.original.json', 'type25-intake-handoff.original.json', 'type25-source-review.original.json']
old=OLD.read_bytes()
assert len(old)==60995 and hashlib.sha256(old).hexdigest()==OLD_SHA
O={'__name__':'pinned_original_171','__file__':str(OLD)}
exec(compile(old,str(OLD),'exec'),O)
O.update(START=START,START_TREE=START_TREE,EVIDENCE=EVIDENCE,PRIVATE=PRIVATE,MAX_SECONDS=300,
         TARGET_SDK=TARGET_SDK,TARGET_KIT=TARGET_KIT,ROOT_PIN_PATHS=ROOT_PIN_PATHS,EXACT_MAP_UPDATES=EXACT_MAP_UPDATES)
need=O['require'];read=O['read_regular'];write=O['exclusive'];enc=O['encoded'];sha=O['sha']
root=O['ROOT']
# Preserve the executed current83 guard, then apply only the six reviewed source pin/map splices.
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
GUARD_EDITS=[{'before': "    require(stage in ('before', 'after') and guards['originalRetentionRows'] == 145\n            and guards['expectedRetentionRows'] == 145 and guards['sourceMapUpdates'] == []\n            and guards['sourceMapAppendedRows'] == [], 'The complete original145-row source map must remain unchanged')\n", 'after': "    require(stage in ('before', 'after') and guards['originalRetentionRows'] == 145\n            and guards['expectedRetentionRows'] == 145\n            and guards['sourceMapUpdates'] == EXACT_MAP_UPDATES\n            and guards['sourceMapAppendedRows'] == [],\n            'Only the two reviewed replacementBlob fields may change in the original145-row map')\n    root_rows = payload['rootRows']\n    require(set(root_rows) == set(ROOT_PIN_PATHS) and len(root_rows) == 13\n            and all(row['status'] == 'M' for row in root_rows.values()),\n            'Only the exact thirteen reviewed SDK9af/Kit414 source replacements are admitted')\n"}, {'before': "    require(len(protected) == 83 and protected == guards['protectedLeaves']\n            and guards['addedProtectedLeaves'] == {} and guards['protectedUpdates'] == {}\n            and target_protected == protected and guards['targetProtectedCount'] == 83,\n            'All83 current protected leaves must remain byte-exact; no protected additions')\n", 'after': "    updates = {path: {'before': before_leaves[path],\n                     'after': {'mode': row['after']['gitMode'], 'type': 'blob', 'sha': row['after']['gitBlob']}}\n               for path, row in root_rows.items()}\n    require(len(protected) == 83 and protected == guards['protectedLeaves']\n            and set(updates) <= set(protected) and guards['addedProtectedLeaves'] == {}\n            and guards['protectedUpdates'] == updates and guards['targetProtectedCount'] == 83\n            and target_protected == {**protected, **{path: row['after'] for path, row in updates.items()}},\n            'All83 protected paths remain; only thirteen exact reviewed whole identities may change')\n"}, {'before': "    require(len(before) == len(after) == 52 and before == after and guards['reviewedGuardUpdates'] == {}\n            and guards['addedClosedActivation'] == [] and guards['historicalNative26StorePromotionReapplied'] is False,\n            'All52 current source witnesses must remain exact; no earlier promotion may be reapplied')\n    values = batch_blobs(commands, 'guard-' + stage + '-original-files',\n                         {row['gitBlob']: None for row in before.values()})\n    for path, identity in before.items():\n        require_leaf(before_leaves, path, identity)\n        require_leaf(target_leaves, path, identity)\n        require(path not in payload['donorRows'], 'Current source guard overlaps a new donor')\n        match(values[identity['gitBlob']], identity)\n", 'after': "    changed_guards = {path: {'before': before[path], 'after': row['after']}\n                      for path, row in root_rows.items() if path in before}\n    require(len(before) == len(after) == 52 and len(changed_guards) == 3\n            and set(changed_guards) == {MAP_PATH, 'Tools/Hanlin/source.json',\n                'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'}\n            and guards['reviewedGuardUpdates'] == changed_guards\n            and after == {**before, **{path: row['after'] for path, row in changed_guards.items()}}\n            and guards['addedClosedActivation'] == [] and guards['historicalNative26StorePromotionReapplied'] is False,\n            'Retain all52 witnesses with only the three exact pin/map identity replacements')\n    values = batch_blobs(commands, 'guard-' + stage + '-original-files',\n                         {row['gitBlob']: None for row in before.values()})\n    for path, identity in before.items():\n        require_leaf(before_leaves, path, identity)\n        require_leaf(target_leaves, path, after[path])\n        require(path not in payload['donorRows'], 'Current source guard overlaps a new donor')\n        match(values[identity['gitBlob']], identity)\n        if path in changed_guards:\n            row = root_rows[path]\n            require(row['before'] == identity, 'Reviewed source guard preimage differs')\n            raw = base64.b64decode(row['base64'], validate=True)\n            match(raw, row['after'])\n            values[row['after']['gitBlob']] = raw\n"}, {'before': "    map_raw = values[before[MAP_PATH]['gitBlob']]\n    require(len(json.loads(map_raw)['changes']) == 145\n            and before[MAP_PATH]['gitBlob'] == '722a41b870957cf17f9724b8dd732b7d6088bde0',\n            'Actual published map145 including row110 must remain byte-exact')\n", 'after': '    map_raw = values[before[MAP_PATH][\'gitBlob\']]\n    require(len(json.loads(map_raw)[\'changes\']) == 145\n            and before[MAP_PATH][\'gitBlob\'] == \'722a41b870957cf17f9724b8dd732b7d6088bde0\',\n            \'Actual published map145 preimage differs\')\n    promoted_map = map_raw\n    before_map = json.loads(map_raw)\n    for update in EXACT_MAP_UPDATES:\n        require(before_map[\'changes\'][update[\'index\']][\'replacementBlob\'] == update[\'before\'],\n                \'Exact source-map replacement position differs\')\n        old_value = (\'"replacementBlob": "\' + update[\'before\'] + \'"\').encode()\n        new_value = (\'"replacementBlob": "\' + update[\'after\'] + \'"\').encode()\n        require(promoted_map.count(old_value) == 1, \'Source-map replacement is not unique\')\n        promoted_map = promoted_map.replace(old_value, new_value, 1)\n    require(values[after[MAP_PATH][\'gitBlob\']] == promoted_map\n            and after[MAP_PATH][\'gitBlob\'] == \'0483ab6cdf65774c5fd66332143f7e804f7932a0\',\n            \'Only rows59/102 replacementBlob may change; all history/formatting stays exact\')\n'}, {'before': "    sdk = json.loads(values[before['Tools/Hanlin/source.json']['gitBlob']])\n    lock_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'\n    pins = json.loads(values[before[lock_path]['gitBlob']])['pins']\n    require(sdk['revision'] == SDK == guards['sdkRevision'] and pins == prior['outputPins']['allPackagePins']\n            and pins == guards['inputPins']['allPackagePins'] and len(pins) == 56,\n            'Original SDK or56 selected main package pins changed')\n    require([pin['state']['revision'] for pin in pins if pin['identity'].casefold() == 'torahinspectorkit'] == [KIT],\n            'Selected original Kit26 changed')\n", 'after': "    lock_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'\n    original_sdk = json.loads(values[before['Tools/Hanlin/source.json']['gitBlob']])\n    promoted_sdk = json.loads(values[after['Tools/Hanlin/source.json']['gitBlob']])\n    input_pins = json.loads(values[before[lock_path]['gitBlob']])['pins']\n    output_pins = json.loads(values[after[lock_path]['gitBlob']])['pins']\n    require(original_sdk['revision'] == SDK == guards['sdkRevisionBefore']\n            and promoted_sdk == {**original_sdk, 'revision': TARGET_SDK}\n            and promoted_sdk['revision'] == guards['sdkRevision']\n            and input_pins == prior['outputPins']['allPackagePins']\n            and input_pins == guards['inputPins']['allPackagePins'] and len(input_pins) == 56,\n            'Original SDK/main56-pin closure or exact SDK9af successor differs')\n    require([pin['state']['revision'] for pin in input_pins if pin['identity'].casefold() == 'torahinspectorkit'] == [KIT]\n            and guards['selectedKitRevisionBefore'] == KIT and guards['selectedKitRevision'] == TARGET_KIT,\n            'Original Kit26 or selected Kit414 source differs')\n    expected_pins = [{**pin, 'state': {**pin['state'], 'revision': TARGET_KIT}}\n                     if pin['identity'].casefold() == 'torahinspectorkit' else pin for pin in input_pins]\n    require(output_pins == expected_pins and len(output_pins) == 56,\n            'Only the sole main TorahInspectorKit revision may change')\n    pins = input_pins if stage == 'before' else output_pins\n"}, {'before': "    result = {'sdk': SDK, 'allPackagePins': pins, 'reviewedRefactors': 145,\n              'closedActivation': activation, 'sourceOnly': True}\n    require(result == prior['outputPins'] == guards['inputPins'] == guards['outputPins'],\n            'Original source-only pins and closed-runtime tuple differ')\n", 'after': "    expected_input = prior['outputPins']\n    expected_output = {**expected_input, 'sdk': TARGET_SDK, 'allPackagePins': expected_pins}\n    require(guards['inputPins'] == expected_input and guards['outputPins'] == expected_output,\n            'Exact reviewed input/output pins differ')\n    result = {'sdk': SDK if stage == 'before' else TARGET_SDK, 'allPackagePins': pins,\n              'reviewedRefactors': 145, 'closedActivation': activation, 'sourceOnly': True}\n    require(result == (expected_input if stage == 'before' else expected_output),\n            'Original source-only pins or closed-runtime tuple differ')\n"}]
for edit in GUARD_EDITS:
 need(guard_new.count(edit['before'])==1,'Reviewed guard splice is not unique')
 guard_new=guard_new.replace(edit['before'],edit['after'],1)
restored_guard=guard_new
for edit in reversed(GUARD_EDITS):
 need(restored_guard.count(edit['after'])==1,'Reviewed guard inverse is not unique')
 restored_guard=restored_guard.replace(edit['after'],edit['before'],1)
need(restored_guard==guard_current83,'Complete executed current83 guard inverse differs')
exec(compile(guard_new,'fixed_reviewed_sdk9af_kit414_guard.py','exec'),O)
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
def integrate(c,r,payload,prior_raw,prior,projection_raw,locators_raw):
 rows=payload['rows'];values=O['decode_rows'](rows)
 donor_rows=payload['donorRows'];root_rows=payload['rootRows']
 need(len(rows)==58 and len(donor_rows)==45 and len(root_rows)==13
      and set(rows)==set(donor_rows)|set(root_rows) and not(set(donor_rows)&set(root_rows))
      and all(rows[p]==q for p,q in {**donor_rows,**root_rows}.items())
      and sum(x['status']=='A'for x in rows.values())==44
      and sum(x['status']=='M'for x in rows.values())==14
      and sum(x['after']['bytes']for x in rows.values())==2054010,
      'Only the exact 58 disjoint original source paths are admitted')
 need(payload['start']==START and payload['startTree']==START_TREE and payload['donorTips']==DONORS
      and payload['donorTree']==DONOR_TREE and payload['sourceTree']==SOURCE_TREE
      and payload['sourceLeaves']==23731 and payload['runtimeAcceptance']is False
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
 need(len(base)==23687,'Current full tree count differs')
 # Missing immutable donors are fetched through the original owned Git route only.
 availability=c.git('exact-two-donor-local-objects','cat-file','--batch-check',
                    data=''.join(sha+'\n'for sha in DONORS).encode()).decode().splitlines()
 need(len(availability)==2,'Exact donor object observation differs')
 missing=[]
 for commit,line in zip(DONORS,availability):
  parts=line.split()
  if parts==[commit,'missing']:missing.append(commit)
  else:need(len(parts)==3 and parts[0]==commit and parts[1]=='commit'
            and parts[2].isdigit() and int(parts[2])>0,'Unexpected donor object identity')
 if missing:
  c.git('fetch-exact-missing-two-donors','fetch','--no-tags','--refmap=','origin',*missing,publish=True,timeout=60)
 specs=[('6ade3661c261e66c987b7017a6181bdfcebc1d58','1545f6dd051caf3e4f267716c3348a10835dadc7',
         'e84da535ef04fbdde56ae200bdac78fce32e96e0',5),
        ('e6fedfdbc7390a5a4e934726806c952319ba4238','9ab4daabe6fdb75746a7862ade31e8b68e0748f7',
         'e8331a3943db99cc8c73b9c61c6120b4ecf5ee7d',40)]
 need(len(payload['donorLinks'])==2,'Exact two donor links required')
 seen=set();oids=set()
 preimages=O['batch_blobs'](c,'all-fourteen-current-preimages',
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
  c.git(tag+'-base-integrated','merge-base','--is-ancestor',parent,START)
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
 need(seen==set(donor_rows) and set(root_rows)==set(ROOT_PIN_PATHS)
      and all(q['status']=='M' and q['donorCommit']is None for q in root_rows.values()),
      'Full 45 original plus 13 reviewed source closure differs')
 donor_source=O['expected_leaves'](base,donor_rows)
 source=O['expected_leaves'](base,rows)
 before=O['validate_guards'](c,payload,base,source,prior,'before')
 O['resources']()
 c.run('create-exclusive-private-index',O['PRE']+['python3','-B','-c','import os,sys;os.mkdir(sys.argv[1],0o700)',str(PRIVATE)])
 dtree=O['private_tree'](c,'complete-two-donor-preview',base,donor_rows,donor_source)
 need(dtree==DONOR_TREE,'Complete ordinary two-donor projection differs')
 O['write_new_objects'](c,root_rows,values,oids|{v['sha']for v in base.values()if v['type']=='blob'})
 stree=O['private_tree'](c,'complete-reviewed58-preview',base,rows,source)
 need(stree==SOURCE_TREE,'Complete 58 source union differs')
 production=sorted(path for path in rows if not path.startswith('docs/'))
 c.git('production-source-whitespace','diff','--check','--no-renames',START,stree,'--',*production)
 evidence_paths={path for path in rows if path.startswith('docs/')}
 diagnostic=check_diff(c,'source-preview-whitespace',['diff','--check','--no-renames',START,stree],evidence_paths)
 after=O['validate_guards'](c,payload,base,source,prior,'after')
 need(before==payload['guardInputs']['inputPins'] and after==payload['guardInputs']['outputPins'],
      'Exact input/output pin transition differs')
 intake={'schema':'pinkha-w3-type25-sharing-sdk9af-kit414-source-intake/v1','start':START,'startTree':START_TREE,
         'normalMergeParents':[START,*DONORS],'donorTree':DONOR_TREE,'sourceTree':SOURCE_TREE,
         'sourcePaths':58,'sourceBytes':2054010,'completeSourceLeaves':23731,
         'sourceStatusCounts':{'A':44,'M':14},
         'files':{p:{k:v for k,v in row.items()if k not in('base64','beforeBase64')}for p,row in rows.items()},
         'sourceInputSHA256':INPUT_SHA,'inputPins':before,'outputPins':after,
         'protectedLeaves':83,'reviewedProtectedUpdates':13,'guardFiles':52,'reviewedGuardUpdates':3,
         'sourceMapRows':145,'sourceMapReplacementFieldsChanged':[59,102],
         'runtimeAcceptance':False,'testsExecuted':0,'compilerInvocations':0,'materializations':0,
         'Type25Scope':'Five original providers, 25 original Linux component starts/passes, 14 fixtures/38 GET/0 POST; no replay. Current Type/value and quota delivery, admitted catalog/saved plan/mapping owner, native migration and Apple/UI remain pending. Two historical compile failures remain literal.',
         'SharingScope':'Only 23 reviewed accessibility identifier lines plus four original source evidence files; original actions, labels, guards, cancellation and test membership preserved. Compiled accessibility and actual two-account sharing acceptance remain pending.',
         'SDKKitScope':'Thirteen exact source pin/map replacements: SDK c0 to published 9af and Kit 26 to 414. Main 56 pins change only the Kit revision; map 145 changes only replacementBlob at 59/102. Historical evidence and all 45 runtime tuples remain closed. No cross-repository SDK merge parent.',
         'CurrentProductPreservation':'Current Bookmark Store and ObjectCreator, all source outside 58 paths, original source-map history, four untracked files and original 22/34 then preparation then 4 UI remain unchanged.'}
 evidence={'root-source-intake.json':enc(intake),'root-integration-controller.py':read(pathlib.Path(__file__)),
           'prior-properties7-publication.original.json':prior_raw,
           'source-projection.original.json':projection_raw,'source-row-locators.original.json':locators_raw,
           'source-guard-derivation.json':enc({'originalControllerSHA256':OLD_SHA,
                'predecessorControllerSHA256':PREDECESSOR_SHA,'originalFunction':guard_old,
                'current83Function':guard_current83,'successorFunction':guard_new,
                'literalGuardOperations':GUARD_EDITS,'wholeOriginalInverse':True,
                'onlyChanges':'Exact 13 protected and 3 guard identities; SDK 9af, sole Kit 414 main pin, map 59/102 replacementBlob. All runtime fields and other source witnesses remain exact.'})}
 need(set(payload['evidence'])==set(ORIGINAL_EVIDENCE_NAMES),'Finite original evidence names differ')
 for name,item in payload['evidence'].items():
  raw=base64.b64decode(item['base64'],validate=True);O['match'](raw,item['after'])
  need(name not in evidence,'Evidence name overlaps');evidence[name]=raw
 need(len(evidence)==13,'Exact 13 intake evidence additions required')
 erows={};evals={}
 for name,raw in evidence.items():
  path=PREFIX+'/'+name;need(path not in base and path not in rows,'Evidence already exists')
  O['destination_preflight'](path,None);O['generated_evidence_is_whitespace_clean'](raw)
  erows[path]={'status':'A','before':None,'beforeBase64':None,
              'after':{'bytes':len(raw),'sha256':sha(raw),'gitBlob':O['blob'](raw),'gitMode':'100644'}}
  evals[path]=raw
 allrows={**rows,**erows};whole=O['expected_leaves'](base,allrows)
 need(len(allrows)==71 and len(whole)==23744,'Complete 71-path/23744-leaf projection differs')
 O['write_new_objects'](c,erows,evals,oids|{v['sha']for v in base.values()if v['type']=='blob'})
 finaltree=O['private_tree'](c,'complete-final-preview',base,allrows,whole)
 check_diff(c,'complete-preview-whitespace',['diff','--check','--no-renames',START,finaltree],evidence_paths,diagnostic)
 need(c.git('premerge-head-tree','rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[START,START_TREE]
      and c.git('premerge-index-tree','write-tree').decode().strip()==START_TREE,'Original HEAD or index advanced')
 need(O['original_status'](c,'premerge')==original and O['optional_file_identity'](index)==index_state,'Premerge custody changed')
 O['exact_remote'](c,'premerge-remote',START)
 r.update(phase='NORMAL_TWO_DONOR_SOURCE_MERGE',expectedDonorTree=DONOR_TREE,expectedSourceTree=SOURCE_TREE,expectedTree=finaltree)
 O['resources']()
 c.git('normal-two-donor-source-merge','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
       'merge','--no-ff','--no-commit',*DONORS,timeout=60)
 need(read(merge_head).decode().split()==DONORS,'Normal merge parents differ')
 need(c.git('actual-donor-index-tree','write-tree').decode().strip()==DONOR_TREE
      and O['tree_leaves'](c,'actual-donor-full-tree',DONOR_TREE)==donor_source,
      'Normal merge differs; preserve without reset')
 final_root_rows={**root_rows,**erows};final_root_values={**{p:values[p]for p in root_rows},**evals}
 expected_stage={p:base64.b64decode(q['beforeBase64'],validate=True)for p,q in root_rows.items()}
 expected_stage.update({p:None for p in erows})
 O['write_owned_batch'](c,'write-exact-thirteen-pins-and-intake',final_root_rows,final_root_values,expected_stage)
 c.git('stage-exact-root-pins-and-intake','add','--sparse','--',*sorted(final_root_rows))
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
 message=('Integrate Type25, sharing selectors and reviewed SDK/Kit source pins\n\n'
          'Merge exact published 6ade3661 and e6fedfdbc as ordinary parents while preserving all b852 source. '
          'Retain original Type25 Linux 25/25 evidence and 23 sharing identifier additions without inferring Apple/native/UI acceptance. '
          'Apply only 13 reviewed SDK 9af/Kit 414 pin/map replacements; preserve all 83 protected paths, 52 witnesses, 56 main pins, 145 mappings and 45 closed runtime tuples with explicit finite identity changes. '
          'No compiler or product tests rerun; historical failures stay literal.\n')
 c.git('normal-three-parent-source-commit','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
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
 input_raw=exact_file(PREP/'source-inputs.json',6975302,INPUT_SHA)
 payload=json.loads(input_raw)
 prior_raw=exact_file(pathlib.Path('/mnt/development/projects/evidence/pinkha-w3-properties7-source-integration-20261128/receipt.json'),
                      164392,'4e535e6c024232361398ad09c75ff9b726bde749594e425c49d7efef155237ee')
 prior=json.loads(prior_raw);original_closed(prior,67)
 need(all(q['exitCode']==0 for q in prior['commands'])
      and prior['head']==prior['normalPushReadback']==START and prior['tree']==START_TREE
      and prior['controllerSHA256']==PREDECESSOR_SHA and prior['normalPushCompleted']is True
      and prior['state']=='SOURCE_NORMAL_MERGE_PUBLISHED_RUNTIME_CLOSED' and prior['firstFailure']is None
      and prior['sourceRetentionPassed'] and not prior['commandCustodyBlocked'],'Actual prior publication differs')
 projection_raw=exact_file(PREP/'source-projection.json',1570,'01c98b42640bc1166ab1d987db6a8b181f9daddc5a4fa72fda6b7fa550ae849f')
 locators_raw=exact_file(PREP/'source-row-locators.json',42336,'e5bab95fdc7e98ce9da91bcc009d6801801472fac2cf1fac86f7e6f3a905e68e')
 projection=json.loads(projection_raw)
 need(projection['base']['commit']==START and projection['base']['tree']==START_TREE
      and projection['donorTree']==DONOR_TREE and projection['sourceTree']==SOURCE_TREE
      and projection['sourceRows']==58 and projection['sourceLeaves']==23731,
      'Reviewed pure-byte projection differs')
 resource=O['resources']();EVIDENCE.mkdir(mode=0o700)
 r={'schema':'pinkha-root-type25-sharing-sdk9af-kit414-source-integration/v1','state':'RUNNING','startedAt':time.time(),
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
 try:integrate(c,r,payload,prior_raw,prior,projection_raw,locators_raw)
 except BaseException as e:r.update(state='FAILED_PRESERVED_NO_AUTOMATIC_RESET',firstFailure={'type':type(e).__name__,'message':str(e)})
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  for sig,handler in handlers.items():signal.signal(sig,handler)
  r.update(finishedAt=time.time(),commandCustodyBlocked=c.blocked)
  write(EVIDENCE/'receipt.json',enc(r));write(OUT,enc(r))
  print(json.dumps({k:r.get(k)for k in ('state','head','tree','firstFailure','commandCustodyBlocked')}),flush=True)
 if r['firstFailure']:raise SystemExit(1)
if __name__=='__main__':main()
