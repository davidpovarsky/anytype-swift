#!/usr/bin/env python3
"""Real native Pinkha API, signed history, indexed projection and partition proof.

All accounts, spaces and data are synthetic. Secrets stay in memory/private
temporary runtime directories. The receipt contains only synthetic fixture IDs,
source/binary digests, assertions and verified firewall cleanup.
"""
from __future__ import annotations
import argparse, base64, copy, hashlib, json, queue, re, socket, struct
import subprocess, sys, tempfile, threading, time, urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from run_runtime_validation import Peer, OutboundBlock, HTTP, ContractFailure, require, digest, eventually

CONTRACT='pinkha-torah-native-v1'
DATASET='pinkha_torah_claims_v1'
FIELDS=('spaceId','operationId','authorId','kind','targetObjectId','targetBlockId','providerId','canonicalRef')
MAX_BYTES=16*1024*1024

def frame(value):
    raw=value if isinstance(value,bytes) else value.encode('utf-8')
    return struct.pack('>I',len(raw))+raw

def make_claim(space,account,target,n,*,block='',kind='add',observed=(),ref='Genesis 1:1',item_id='context',item_kind='ref',role='context',label='מקור',raw=None):
    opid=f'{n:032x}';observed=sorted(set(observed));provider='sefaria'
    if kind=='remove':raw=b'';provider='';ref=''
    elif raw is None:
        record={'spaceId':space,'objectId':target,'futureRecordField':17,'item':{'id':item_id,'kind':item_kind,'role':role,'providerID':provider,'canonicalKey':ref,'externalID':ref,'labelHe':label,'futureItemField':{'kept':True}}}
        if block:record['blockId']=block
        raw=json.dumps({'version':2,'records':[record],'futureEnvelopeField':'preserved'},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')
    values=[space,opid,account,kind,target,block,provider,ref]
    canonical=b'pinkha-t2-operation\0'+struct.pack('>I',1)+b''.join(map(frame,values))+frame(raw)+struct.pack('>I',len(observed))+b''.join(map(frame,observed))
    key=hashlib.sha256(b'pinkha-t2-operation-key-v1\0'+frame(space)+frame(opid)).hexdigest()
    content=hashlib.sha256(canonical).hexdigest()
    fields=dict(zip(FIELDS,values),version=1,payload=base64.b64encode(raw).decode(),observed=observed,logicalKey=key,contentHash=content)
    return {'id':key+content,'claimId':key+'/'+content,'fields':fields}

def identity(kind,ref):
    parts=[kind,'sefaria',ref]
    return 'torah1|'+'|'.join(f'{len(p.encode("utf8"))}:{p}' for p in parts)

def source_manifest(repo):
    # Frozen v9 deliberately has an existing parent commit plus a tested
    # effective tree. Enforce all exact sealed build input bytes, including
    # new Go files; never mislabel the parent as a clean v9 source commit.
    pins_file=Path(__file__).with_name('source-pins.json')
    require(digest(pins_file)=='3e7212537a718e298703a0654abcd07cb7eb68e2dcdec1b09da960468062ffad','frozen source pin file changed')
    pins=json.loads(pins_file.read_text(encoding='utf8'))
    repo=Path(repo).resolve();entry=pins['roots'].get(str(repo))
    require(entry is not None,'unrecognized frozen native source root')
    def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(repo),*args],encoding='utf8',timeout=30).strip()
    head=git('rev-parse','HEAD')
    paths=sorted({p for p in git('ls-files','--cached','--others','--exclude-standard').splitlines() if p.endswith('.go') or p in ('go.mod','go.sum')})
    files={p:digest(repo/p) for p in paths}
    require(head==entry['expected']['gitHEAD'] and files==entry['expected']['files'],'frozen effective native source differs from exact tested build')
    return {'commit':head,'testedEffectiveTree':entry['testedEffectiveTree'],'workingTreeIncludesUncommittedChanges':True,'workingTreeRevision':'v9','nativeManifestSHA256':pins['nativeManifestSHA256'],'files':files,'manifestSHA256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()}

class NativeRepo:
    def __init__(self,peer,space,account,root):self.peer,self.space,self.account,self.root=peer,space,account,root;self.base='/v1/spaces/'+space
    def append(self,claim):
        body={'objectId':self.root,'dataset':DATASET,'records':[{'id':claim['id'],'upsert':True,'ops':[{'type':'$set','value':claim['fields']}]}]}
        result=self.peer.request('POST',self.base+'/modify',body)
        require(result.get('recordIds')==[claim['id']],'native write receipt record identity mismatch')
        return result
    def snapshot(self,limit=10000):
        value=self.peer.request('GET',self.base+'/pinkha/claims?limit='+str(limit))
        self.validate_snapshot(value);return value
    def validate_snapshot(self,value):
        require(value.get('contract')==CONTRACT and value.get('spaceId')==self.space and value.get('rootObjectId')==self.root and value.get('dataset')==DATASET and value.get('complete') is True,'native snapshot scope/completeness mismatch')
        require(value.get('readiness',{}).get('state')=='ready-local-snapshot' and re.fullmatch('[0-9a-f]{64}',value['readiness']['generation']),'native snapshot readiness unavailable')
        require(len(value['records'])<=value['limit']<=10000 and len(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode())<=MAX_BYTES,'native snapshot exceeds promised bounds')
        ids=set()
        for row in value['records']:
            require(row['id'] not in ids,'duplicate native record');ids.add(row['id'])
            require(row['spaceId']==self.space and row['creator']==row['authorId']==self.account and row.get('nativeChangeId') and row.get('nativeACLHeadId'),'native signed provenance mismatch')
            reconstructed=make_claim(row['spaceId'],row['authorId'],row['targetObjectId'],int(row['operationId'],16),block=row['targetBlockId'],kind=row['kind'],observed=row['observed'],ref=row['canonicalRef'],raw=base64.b64decode(row['payload']))
            require(reconstructed['id']==row['id'] and all(reconstructed['fields'][k]==row[k] for k in reconstructed['fields']),'native canonical content/hash mismatch')
        return value
    def ids(self):return {r['id'] for r in self.snapshot()['records']}
    def target(self,target,block=''):
        return self.peer.request('GET',self.base+'/pinkha/targets/'+target+'?'+urlencode({'blockId':block}))
    def source(self,kind,ref):
        field={'ref':'pinkhaSources','topic':'pinkhaTopics','word':'pinkhaWords'}[kind]
        return self.peer.request('GET',self.base+'/pinkha/sources?'+urlencode({'field':field,'identity':identity(kind,ref)}))
    def related(self,ref):return self.peer.request('GET',self.base+'/pinkha/related?'+urlencode({'identity':identity('ref',ref)}))

class NativeWatch:
    def __init__(self,repo):
        self.repo=repo;self.events=queue.Queue();self.closed=threading.Event();self.response=None;self.error=None
        self.thread=threading.Thread(target=self.read,daemon=True);self.thread.start()
    def read(self):
        try:
            request=urllib.request.Request(self.repo.peer.endpoint+self.repo.base+'/pinkha/claims/subscribe',method='GET')
            with HTTP.open(request,timeout=10) as response:
                self.response=response
                require(response.headers.get_content_type()=='text/event-stream','native watch content type mismatch')
                event='';data=[]
                for raw in response:
                    if self.closed.is_set():return
                    line=raw.decode('utf8').rstrip('\r\n')
                    if not line:
                        if data:self.events.put((event,json.loads('\n'.join(data))))
                        event='';data=[]
                    elif line.startswith('event:'):event=line[6:].strip()
                    elif line.startswith('data:'):data.append(line[5:].lstrip())
        except Exception as error:
            if not self.closed.is_set():self.error=type(error).__name__+': '+str(error)[:200];self.events.put(('failure',{}))
    def wait(self,predicate,timeout=45):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:event,value=self.events.get(timeout=min(1,end-time.monotonic()))
            except queue.Empty:continue
            require(event=='snapshot','native stream failed or sent an unexpected event')
            self.repo.validate_snapshot(value)
            if predicate(value):return value
        raise ContractFailure('native watch did not produce expected complete state')
    def close(self):
        self.closed.set()
        if self.response:
            try:self.response.fp.raw._sock.shutdown(socket.SHUT_RDWR)
            except (AttributeError,OSError):pass
            self.response.close()
        self.thread.join(timeout=5)
        require(not self.thread.is_alive(),'native watch thread did not close')

def refused(action,status=400,code=None):
    try:action()
    except ContractFailure as error:
        require(str(error).startswith('HTTP '+str(status)+':'),'unexpected refusal class: '+str(error))
        if code:require(str(error)=='HTTP '+str(status)+': '+code,'unexpected refusal code')
        return
    raise ContractFailure('invalid native operation unexpectedly succeeded')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binary',required=True);parser.add_argument('--expected-binary-sha256',required=True);parser.add_argument('--runtime-source',required=True);parser.add_argument('--sdk-source',required=True);parser.add_argument('--result',required=True)
    args=parser.parse_args();receipt={'status':'IN_PROGRESS','scope':'Real native Any HTTP, immutable signed claims, indexed projections, two-peer firewall partitions and native complete-state SSE','startedAt':datetime.now(timezone.utc).isoformat(),'checks':[]}
    peers=[];rules=[];watch=None;mnemonic=None
    @contextmanager
    def step(name):
        start=time.monotonic()
        try:yield
        except Exception as error:
            receipt['checks'].append({'name':name,'status':'FAIL','error':type(error).__name__+': '+str(error)[:300]});raise
        else:receipt['checks'].append({'name':name,'status':'PASS','seconds':round(time.monotonic()-start,3)});print(json.dumps({'step':name,'status':'PASS'}),flush=True)
    try:
        with step('pin_binary_and_clean_source'):
            require(digest(args.binary)==args.expected_binary_sha256.lower(),'native binary digest mismatch')
            receipt['binarySHA256']=digest(args.binary);receipt['anySource']=source_manifest(args.runtime_source);receipt['sdkSource']=source_manifest(args.sdk_source);receipt['harnessSHA256']=digest(__file__);receipt['sharedRuntimeHelperSHA256']=digest(Path(__file__).with_name('run_runtime_validation.py'))
        with step('independent_old_go_swift_golden_vector'):
            golden=make_claim('disposable-space','disposable-account','disposable-document',1,block='stable-block',ref='Genesis.1.1',raw='א<>&\n'.encode())
            require(golden['claimId']=='89344c7ac74f7d5df8ef2a94f9592a7ed86a9dccc47084f8ce27d98080c29263/3652b732b88752a35184fcf1af80f8d3e499fb5e5e4132a8064e6236a54cd589','independent canonical codec drift')
        folder=Path(tempfile.mkdtemp(prefix='pinkha-native-validation-'));a=Peer(args.binary,folder/'a');b=Peer(args.binary,folder/'b');peers=[a,b]
        with step('fresh_native_process_account_and_space'):
            a.start();auth=a.auth();account=auth['accountId'];mnemonic=auth['mnemonic'];del auth
            space=a.request('POST','/v1/spaces',{'name':'Disposable native Pinkha end-to-end proof'})['id'];base='/v1/spaces/'+space
        with step('native_contract_capabilities_and_install'):
            caps=a.request('GET','/v1/pinkha/capabilities');require(caps['contract']==CONTRACT,'native capability pin mismatch')
            for key in ('nativeSignedClaims','currentACLCommitFence','targetTreeCommitFence','nativeClaimsSnapshot','nativeClaimsWatch','nativeIndexedSourceQuery','nativeRelatedVersion','conditionalBlockPatch','conditionalPropertiesSet'):require(caps.get(key)==1,'missing native capability '+key)
            installed=a.request('POST',base+'/pinkha/install');root=installed['rootObjectId'];repo=NativeRepo(a,space,account,root);require(not repo.ids(),'fresh native root is not empty');receipt['capabilities']=caps
        def page(name):return a.request('POST',base+'/objects',{'type':'page','initialProperties':{'any':{'name':name}}})['objectId']
        with step('native_document_and_editor_graph_fixtures'):
            doc=page('Native source בראשית');safe=page('Safe unlink context');matrix=page('Native conflict target');other=page('Cross-target collision')
            blocks=base+'/objects/'+doc+'/editor/editor_blocks/blocks'
            parent=a.request('POST',blocks,{'type':'paragraph','text':'אב מקור'})['recordIds'][0]
            child=a.request('POST',blocks,{'type':'paragraph','text':'ילד מקושר','nav':{'parentId':parent}})['recordIds'][0]
        expected=set()
        def append(c,where=repo):
            result=where.append(c);expected.add(c['id']);return result
        fixtures=[make_claim(space,account,doc,1,item_id='main-context'),make_claim(space,account,doc,2,item_kind='topic',ref='faith',item_id='topic'),make_claim(space,account,doc,3,item_kind='word',ref='בראשית',item_id='word'),make_claim(space,account,doc,4,role='sourceQuote',item_id='quote-a'),make_claim(space,account,doc,5,role='sourceQuote',item_id='quote-b'),make_claim(space,account,doc,6,block=child,item_id='block-context'),make_claim(space,account,safe,7,item_id='safe-context')]
        with step('native_claims_hash_creator_provenance_and_unknown_bytes'):
            for claim in fixtures:append(claim)
            snapshot=repo.snapshot();require(repo.ids()==expected,'native immutable claims missing')
            stored={row['id']:row for row in snapshot['records']}
            for claim in fixtures:require(stored[claim['id']]['payload']==claim['fields']['payload'],'native engine rewrote canonical opaque bytes')
            receipt['sanitizedNativeRecordSample']=stored[fixtures[0]['id']]
        with step('native_complete_snapshot_overflow_is_explicit'):
            refused(lambda:repo.snapshot(1),409,'pinkha.read_limit');refused(lambda:repo.snapshot(0),400,'pinkha.invalid_request')
        with step('generic_native_query_and_subscription_refused'):
            query={'objectId':root,'dataset':DATASET}
            refused(lambda:a.request('POST',base+'/query',query),400,'pinkha.native_read_required')
            refused(lambda:a.request('POST',base+'/query/subscribe',query),400,'pinkha.native_read_required')
        with step('native_source_topic_word_indexes'):
            require(set(repo.source('ref','Genesis 1:1')['objectIds'])=={doc,safe},'native Source candidates differ')
            for kind,ref in [('topic','faith'),('word','בראשית')]:require(repo.source(kind,ref)['objectIds']==[doc],'native '+kind+' index differs')
            require(repo.target(doc)['semantic']['coverage']=='complete','native semantics unexpectedly incomplete')
        with step('internal_note_external_reference_excluded_from_native_source'):
            note='anytype-note:synthetic'
            payload=json.dumps({'version':2,'records':[{'spaceId':space,'objectId':doc,'item':{'id':'internal-note','kind':'ref','role':'context','providerID':'sefaria','canonicalKey':'','externalID':note,'labelHe':'קישור פנימי'}}]},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')
            append(make_claim(space,account,doc,50,ref=note,item_id='internal-note',raw=payload))
            require(repo.source('ref',note)['objectIds']==[] and repo.related(note)['targets']==[],'internal note leaked into native source indexes')
        with step('expanded_related_preserves_distinct_quotes_and_block_scope'):
            related=repo.related('Genesis 1:1');require(related['coverage']=='complete' and related['version']==1,'expanded semantic capability incomplete')
            targets={(t['objectId'],t.get('blockId','')):t for t in related['targets']}
            require(set(targets)=={(doc,''),(doc,child),(safe,'')},'expanded native targets differ')
            require(targets[(doc,'')]['sourceQuoteItemIds']==['quote-a','quote-b'] and targets[(doc,'')]['contextItemIds']==['main-context'] and not targets[(doc,'')]['canSafelyUnlink'],'quote identity/safe unlink contract violated')
            require(targets[(safe,'')]['canSafelyUnlink'] and not targets[(doc,child)]['canSafelyUnlink'],'document-only unlink authority violated')
        with step('native_exact_retry_has_no_new_history'):
            before=repo.snapshot();retry=repo.append(fixtures[0]);after=repo.snapshot()
            require(not retry.get('changeId') and not retry.get('versionId'),'exact retry appended native history')
            require(before==after,'exact retry changed native snapshot or generation')
        with step('native_forgery_and_predecessor_guards_refuse_before_append'):
            bad=make_claim(space,'forged-author',doc,20);refused(lambda:repo.append(bad))
            bad=copy.deepcopy(fixtures[0]);bad['fields']['payload']=base64.b64encode(b'forged').decode();refused(lambda:repo.append(bad))
            unknown=make_claim(space,account,doc,21,kind='remove',observed=['0'*64+'/'+'0'*64]);refused(lambda:repo.append(unknown))
            foreign=make_claim(space,account,doc,22,kind='remove',observed=[fixtures[-1]['claimId']]);refused(lambda:repo.append(foreign))
            null=copy.deepcopy(fixtures[0]);null['fields']['observed']=None;refused(lambda:repo.append(null))
            require(repo.ids()==expected,'rejected operation changed canonical history')
        with step('observed_remove_excludes_quotes_and_blocks_from_document_source'):
            append(make_claim(space,account,doc,10,kind='remove',observed=[fixtures[0]['claimId']]))
            require(repo.source('ref','Genesis 1:1')['objectIds']==[safe],'quotes or block context leaked into document Source')
            targets={(t['objectId'],t.get('blockId','')):t for t in repo.related('Genesis 1:1')['targets']}
            require(targets[(doc,'')]['contextItemIds']==[] and targets[(doc,'')]['sourceQuoteItemIds']==['quote-a','quote-b'],'native fold lost quote instances')
            append(make_claim(space,account,doc,11,item_id='main-context'))
            require(set(repo.source('ref','Genesis 1:1')['objectIds'])=={doc,safe},'new native context did not restore Source')
        with step('native_bin_membership_invalidates_reads_and_writes'):
            membership=base+'/properties/'+safe+'/collections/bin';a.request('POST',membership)
            require(repo.source('ref','Genesis 1:1')['objectIds']==[doc],'binned target remained in Source')
            refused(lambda:repo.append(make_claim(space,account,safe,23,ref='new after bin',item_id='refused')))
            a.request('DELETE',membership);require(set(repo.source('ref','Genesis 1:1')['objectIds'])=={doc,safe},'restored eligible target not re-derived')
        with step('native_orphan_block_excluded_and_reachable_identity_restored'):
            a.request('DELETE',blocks+'/'+parent)
            require(all(not t.get('blockId') for t in repo.related('Genesis 1:1')['targets']),'orphan block remained in expanded related')
            refused(lambda:repo.append(make_claim(space,account,doc,24,block=child,item_id='orphan-refused')))
            a.request('PATCH',blocks+'/'+child,{'set':{'nav.parentId':''}})
            require(any(t.get('blockId')==child for t in repo.related('Genesis 1:1')['targets']),'reattached same block identity was lost')
        with step('native_deleted_target_excluded_without_erasing_claim_history'):
            a.request('DELETE',base+'/objects/'+safe)
            require(repo.source('ref','Genesis 1:1')['objectIds']==[doc],'deleted target remained indexed')
            require(all(t['objectId']!=safe for t in repo.related('Genesis 1:1')['targets']),'deleted target remained related')
            require(fixtures[-1]['id'] in repo.ids(),'canonical claim history was destructively removed')
        anchors=[make_claim(space,account,matrix,100,ref='Exodus 1:1',item_id='remove-anchor'),make_claim(space,account,matrix,101,ref='Exodus 1:2',item_id='replace-anchor'),make_claim(space,account,matrix,102,ref='Exodus 1:3',item_id='collision-anchor')]
        with step('native_partition_anchor_history'):
            for claim in anchors:append(claim)
        with step('second_real_peer_restores_only_disposable_account'):
            b.start();require(b.auth(mnemonic)['accountId']==account,'second account differs')
            second=NativeRepo(b,space,account,root)
            eventually(lambda:second.ids()==expected,'native initial peer convergence')
        with step('both_native_peers_restarted_under_verified_program_firewalls'):
            a.stop();b.stop();rules=[OutboundBlock(a),OutboundBlock(b)]
            for rule in rules:rule.enable()
            a.start();b.start();require(a.auth(mnemonic)['accountId']==b.auth(mnemonic)['accountId']==account,'offline auth differs')
            require(repo.ids()==second.ids()==expected,'offline native baseline differs')
        colliding_a=make_claim(space,account,matrix,200,kind='remove',observed=[anchors[2]['claimId']])
        colliding_b=make_claim(space,account,other,200,ref='collision-other',item_id='other-target')
        observed_remove=make_claim(space,account,matrix,201,kind='remove',observed=[anchors[0]['claimId']])
        unseen_add=make_claim(space,account,matrix,202,ref='Exodus 1:1',item_id='unseen-add')
        replace_a=make_claim(space,account,matrix,203,kind='replace',observed=[anchors[1]['claimId']],ref='replacement A',item_id='replace-A')
        replace_b=make_claim(space,account,matrix,204,kind='replace',observed=[anchors[1]['claimId']],ref='replacement B',item_id='replace-B')
        before_partition=set(expected)
        with step('real_offline_conflict_remove_unseen_add_and_concurrent_replace'):
            for claim in (colliding_a,observed_remove,replace_a):append(claim)
            for claim in (colliding_b,unseen_add,replace_b):append(claim,second)
            require(repo.ids()==before_partition|{c['id'] for c in (colliding_a,observed_remove,replace_a)},'peer A saw disconnected peer state')
            require(second.ids()==before_partition|{c['id'] for c in (colliding_b,unseen_add,replace_b)},'peer B saw disconnected peer state')
        with step('native_offline_retry_and_ordered_collision_refusal'):
            prior=repo.snapshot();require(not repo.append(replace_a).get('changeId'),'offline retry created history');require(repo.snapshot()==prior,'offline retry changed state')
            collision=make_claim(space,account,matrix,204,ref='ordered conflicting bytes',item_id='ordered-conflict')
            refused(lambda:second.append(collision));require(collision['id'] not in second.ids(),'ordered collision persisted')
        with step('native_cold_restart_while_still_physically_partitioned'):
            prior=repo.ids();a.stop();a.start();require(a.auth(mnemonic)['accountId']==account,'offline restart account differs');require(repo.ids()==prior,'native claims lost across offline restart')
        with step('remove_only_test_firewalls_and_reconnect'):
            a.stop();b.stop()
            for rule in rules:rule.disable()
            a.start();b.start();a.auth(mnemonic);b.auth(mnemonic)
        live={anchors[2]['claimId'],unseen_add['claimId'],replace_a['claimId'],replace_b['claimId']}
        def correct_projection(where):
            snapshot=where.target(matrix)['operations']
            return {c['id'] for c in snapshot['live']}==live and len(snapshot['conflicts'])==1 and snapshot['conflicts'][0]['logicalKey']==colliding_a['fields']['logicalKey'] and snapshot['pendingObserved']==[]
        with step('native_two_peer_exact_history_and_operation_projection_convergence'):
            eventually(lambda:repo.ids()==second.ids()==expected and correct_projection(repo) and correct_projection(second),'native full conflict convergence')
            require(second.target(other)['operations']['live']==[] and len(second.target(other)['operations']['conflicts'])==1,'cross-target logical conflict escaped quarantine')
        with step('native_conflict_quarantined_before_predecessor_suppression'):
            value=repo.source('ref','Exodus 1:3');require(value['objectIds']==[] and value['conflictedObjectIds']==[matrix],'native indexed query hid unresolved collision')
            require(anchors[2]['claimId'] in {c['id'] for c in repo.target(matrix)['operations']['live']},'colliding remove suppressed its predecessor')
        with step('native_atomic_initial_complete_watch_snapshot'):
            watch=NativeWatch(repo);watch.wait(lambda s:{r['id'] for r in s['records']}==expected)
        marker=make_claim(space,account,doc,300,ref='SSE marker',item_id='watch-marker')
        with step('native_watch_observes_other_peer_signed_apply'):
            append(marker,second);watch.wait(lambda s:{r['id'] for r in s['records']}==expected)
            eventually(lambda:repo.ids()==second.ids()==expected,'native watch final convergence')
            watch.close();watch=None
        with step('native_source_manifests_unchanged_after_end_to_end'):
            require(source_manifest(args.runtime_source)==receipt['anySource'] and source_manifest(args.sdk_source)==receipt['sdkSource'],'native source changed during validation')
        receipt['final']={'allClaims':len(expected),'matrixLiveClaims':sorted(live),'matrixConflictKeys':[colliding_a['fields']['logicalKey']],'spaceId':space,'rootObjectId':root,'accountId':account}
        receipt['status']='PASS_NATIVE_END_TO_END'
    except Exception as error:
        receipt['status']='FAIL';receipt['fatalFailure']=type(error).__name__+': '+str(error)[:500]
    finally:
        if watch:
            try:watch.close()
            except Exception as error:receipt.setdefault('cleanupErrors',[]).append(type(error).__name__)
        for peer in peers:
            try:peer.stop()
            except Exception as error:receipt.setdefault('cleanupErrors',[]).append(type(error).__name__)
        for rule in rules:
            try:rule.disable()
            except Exception as error:receipt.setdefault('cleanupErrors',[]).append(type(error).__name__)
        receipt['firewallRules']=[rule.evidence for rule in rules]
        mnemonic=None
        if receipt.get('cleanupErrors'):receipt['status']='FAIL'
        receipt['finishedAt']=datetime.now(timezone.utc).isoformat();path=Path(args.result);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(json.dumps({'status':receipt['status'],'checks':len(receipt['checks']),'fatalFailure':receipt.get('fatalFailure'),'receipt':str(path)},ensure_ascii=True),flush=True)
    return 0 if receipt['status']=='PASS_NATIVE_END_TO_END' else 1

if __name__=='__main__':sys.exit(main())
