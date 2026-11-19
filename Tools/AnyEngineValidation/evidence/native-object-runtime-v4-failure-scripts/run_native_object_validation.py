#!/usr/bin/env python3
"""Native per-object history/eligibility/watch and unrelated-Space-size proof."""
from __future__ import annotations
import argparse,hashlib,json,queue,re,socket,sys,tempfile,threading,time,urllib.request
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from run_runtime_validation import Peer,OutboundBlock,HTTP,ContractFailure,require,digest,eventually
from run_native_validation import NativeRepo,make_claim,source_manifest,refused

class ObjectRepo(NativeRepo):
    def object_snapshot(self,object_id,limit=10000):
        value=self.peer.request('GET',self.base+'/pinkha/objects/'+object_id+'/claims?limit='+str(limit))
        return self.validate_object(value,object_id)
    def validate_object(self,value,object_id):
        self.validate_snapshot(value)
        require(value.get('scope')=='object-logical-closure' and value.get('version')==1 and value.get('targetObjectId')==object_id,'object snapshot scope mismatch')
        seeds=[r for r in value['records'] if r['targetObjectId']==object_id]
        keys={r['logicalKey'] for r in seeds}
        require(all(r['logicalKey'] in keys for r in value['records']),'unrelated record escaped logical closure')
        known={r['targetBlockId'] for r in seeds if r['targetBlockId']}
        reachable=value.get('reachableClaimBlockIds')
        require(isinstance(reachable,list) and reachable==sorted(set(reachable)) and set(reachable)<=known,'invalid native reachable claim blocks')
        return value
    def append_batch(self,claims):
        result=self.peer.request('POST',self.base+'/modify',{'objectId':self.root,'dataset':'pinkha_torah_claims_v1','records':[{'id':c['id'],'upsert':True,'ops':[{'type':'$set','value':c['fields']}]} for c in claims]},timeout=90)
        require(result.get('recordIds')==[c['id'] for c in claims] and not result.get('rejections'),'batch receipt mismatch')

class ObjectWatch:
    def __init__(self,repo,object_id,limit=10000):
        self.repo,self.object_id,self.limit=repo,object_id,limit;self.events=queue.Queue();self.closed=threading.Event();self.response=None
        self.thread=threading.Thread(target=self.read,daemon=True);self.thread.start()
    def read(self):
        try:
            url=self.repo.peer.endpoint+self.repo.base+'/pinkha/objects/'+self.object_id+'/claims/subscribe?limit='+str(self.limit)
            with HTTP.open(urllib.request.Request(url),timeout=10) as response:
                self.response=response;require(response.headers.get_content_type()=='text/event-stream','object watch content type')
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
            if not self.closed.is_set():self.events.put(('failure',{'type':type(error).__name__}))
    def wait(self,predicate,timeout=40):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:event,value=self.events.get(timeout=min(1,end-time.monotonic()))
            except queue.Empty:continue
            require(event=='snapshot','object watch emitted failure before expected state')
            self.repo.validate_object(value,self.object_id)
            if predicate(value):return value
        raise ContractFailure('object watch expected state timeout')
    def refused(self,timeout=15):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:event,value=self.events.get(timeout=min(1,end-time.monotonic()))
            except queue.Empty:continue
            if event=='snapshot':continue
            require(event=='error' and value.get('complete') is False and value.get('scope')=='object-logical-closure' and value.get('targetObjectId')==self.object_id and value.get('code')=='pinkha.snapshot_unavailable' and 'records' not in value,'invalid scoped watch refusal')
            return
        raise ContractFailure('scoped watch did not invalidate unavailable state')
    def close(self):
        self.closed.set()
        if self.response:
            try:self.response.fp.raw._sock.shutdown(socket.SHUT_RDWR)
            except (AttributeError,OSError):pass
            self.response.close()
        self.thread.join(timeout=5);require(not self.thread.is_alive(),'scoped watch did not close')

def main():
    p=argparse.ArgumentParser();p.add_argument('--binary',required=True);p.add_argument('--expected-binary-sha256',required=True);p.add_argument('--runtime-source',required=True);p.add_argument('--sdk-source',required=True);p.add_argument('--result',required=True);p.add_argument('--large-space-proof',action='store_true');args=p.parse_args()
    receipt={'status':'IN_PROGRESS','scope':'Native indexed object logical closure, native reachable block eligibility, two-peer cross-object collision witness, scoped SSE invalidation, and optional >10000 unrelated signed claims','startedAt':datetime.now(timezone.utc).isoformat(),'checks':[]}
    peers=[];rules=[];watch=None;mnemonic=None
    @contextmanager
    def step(name):
        start=time.monotonic()
        try:yield
        except Exception as error:receipt['checks'].append({'name':name,'status':'FAIL','error':type(error).__name__+': '+str(error)[:240]});raise
        else:receipt['checks'].append({'name':name,'status':'PASS','seconds':round(time.monotonic()-start,3)});print(json.dumps({'step':name,'status':'PASS'}),flush=True)
    try:
        with step('source_bound_binary_and_exact_harness'):
            require(digest(args.binary)==args.expected_binary_sha256.lower(),'binary pin mismatch')
            receipt.update(binarySHA256=digest(args.binary),anySource=source_manifest(args.runtime_source),sdkSource=source_manifest(args.sdk_source),harnessSHA256=digest(__file__),nativeHelperSHA256=digest(Path(__file__).with_name('run_native_validation.py')),runtimeHelperSHA256=digest(Path(__file__).with_name('run_runtime_validation.py')))
        folder=Path(tempfile.mkdtemp(prefix='pinkha-object-validation-'));a=Peer(args.binary,folder/'a');b=Peer(args.binary,folder/'b');peers=[a,b]
        with step('fresh_native_account_space_and_scoped_capabilities'):
            a.start();auth=a.auth();account=auth['accountId'];mnemonic=auth['mnemonic'];del auth
            space=a.request('POST','/v1/spaces',{'name':'Disposable scoped native claim validation'})['id'];base='/v1/spaces/'+space
            caps=a.request('GET','/v1/pinkha/capabilities')
            for key in ('nativeObjectClaimsSnapshot','nativeObjectClaimsWatch','conditionalBlockCurrentWriterFence'):require(caps.get(key)==1,'missing '+key)
            root=a.request('POST',base+'/pinkha/install')['rootObjectId'];repo=ObjectRepo(a,space,account,root);receipt['capabilities']=caps
        def page(name):return a.request('POST',base+'/objects',{'type':'page','initialProperties':{'any':{'name':name}}})['objectId']
        with step('scoped_document_block_and_foreign_predecessor_history'):
            doc=page('Object-scoped native document');foreign=page('Unrelated native document');blocks=base+'/objects/'+doc+'/editor/editor_blocks/blocks'
            parent=a.request('POST',blocks,{'type':'paragraph','text':'parent'})['recordIds'][0]
            child=a.request('POST',blocks,{'type':'paragraph','text':'child','nav':{'parentId':parent}})['recordIds'][0]
            old=make_claim(space,account,doc,1,item_id='doc-context');block=make_claim(space,account,doc,2,block=child,item_id='block-context');foreign_old=make_claim(space,account,foreign,3,item_id='foreign-context')
            for claim in (old,block,foreign_old):repo.append(claim)
            expected={c['id'] for c in (old,block,foreign_old)}
            scoped=repo.object_snapshot(doc);require({r['id'] for r in scoped['records']}=={old['id'],block['id']} and scoped['reachableClaimBlockIds']==[child],'initial scoped history mismatch')
        with step('second_peer_native_initial_convergence'):
            b.start();require(b.auth(mnemonic)['accountId']==account,'second account mismatch');second=ObjectRepo(b,space,account,root)
            eventually(lambda:second.ids()==expected,'scoped fixture convergence')
            # Carrier convergence does not imply hydration of target trees.
            # Verify both native target snapshots while the network is live,
            # then cold-restart under the per-program partition.
            eventually(lambda:{r['id'] for r in second.object_snapshot(doc)['records']}=={old['id'],block['id']} and {r['id'] for r in second.object_snapshot(foreign)['records']}=={foreign_old['id']},'target tree hydration before offline writes')
        with step('verified_native_program_partitions'):
            a.stop();b.stop();rules=[OutboundBlock(a),OutboundBlock(b)]
            for rule in rules:rule.enable()
            a.start();b.start();a.auth(mnemonic);b.auth(mnemonic)
        removal=make_claim(space,account,doc,100,kind='remove',observed=[old['claimId']])
        witness=make_claim(space,account,foreign,100,kind='replace',observed=[foreign_old['claimId']],ref='foreign replacement',item_id='foreign-replacement')
        with step('offline_collision_witness_observes_foreign_predecessor'):
            repo.append(removal);second.append(witness);expected|={removal['id'],witness['id']}
            require(witness['id'] not in repo.ids() and removal['id'] not in second.ids(),'partition leaked peer changes')
        with step('restore_network_and_merge_native_collision'):
            a.stop();b.stop()
            for rule in rules:rule.disable()
            a.start();b.start();a.auth(mnemonic);b.auth(mnemonic)
            eventually(lambda:repo.ids()==second.ids()==expected,'cross-object native collision convergence')
        closure={old['id'],block['id'],removal['id'],witness['id']}
        with step('object_closure_includes_witness_but_omits_its_quarantined_predecessor'):
            scoped=repo.object_snapshot(doc);require({r['id'] for r in scoped['records']}==closure,'logical witness closure differs')
            require(foreign_old['id'] not in {r['id'] for r in scoped['records']} and witness['id'] in {r['id'] for r in scoped['records']},'foreign predecessor was incorrectly required')
            projection=repo.target(doc)['operations'];require([c['id'] for c in projection['live']]==[old['claimId']] and len(projection['conflicts'])==1 and projection['pendingObserved']==[],'collision processed witness predecessors before quarantine')
            require(repo.target(doc,child)['operations']['live'][0]['id']==block['claimId'],'block association lost in object closure')
            refused(lambda:repo.object_snapshot(doc,3),409,'pinkha.read_limit')
        with step('scoped_atomic_watch_initial_state'):
            watch=ObjectWatch(repo,doc);watch.wait(lambda s:{r['id'] for r in s['records']}==closure and s['reachableClaimBlockIds']==[child])
        with step('scoped_watch_invalidates_orphan_reachability_without_erasing_history'):
            a.request('DELETE',blocks+'/'+parent)
            changed=watch.wait(lambda s:s['reachableClaimBlockIds']==[]);require({r['id'] for r in changed['records']}==closure,'orphan filtering erased immutable claims')
        with step('fenced_block_patch_restores_same_identity_and_watch_eligibility'):
            markdown=a.request('GET',base+'/objects/'+doc+'/editor/editor_blocks/markdown');started=a.request('GET','/v1/health')['startedAt']
            result=a.request('PATCH',blocks+'/'+child,{'set':{'nav.parentId':''},'ifVersion':markdown['version'],'ifStartedAt':started})
            require(result['recordIds']==[child] and result.get('editorVersion'),'conditional writer-fenced block receipt absent')
            watch.wait(lambda s:s['reachableClaimBlockIds']==[child])
        with step('scoped_watch_refuses_binned_target_without_canonical_payload'):
            a.request('POST',base+'/properties/'+doc+'/collections/bin');watch.refused();watch.close();watch=None
            refused(lambda:repo.object_snapshot(doc))
            a.request('DELETE',base+'/properties/'+doc+'/collections/bin');require(repo.object_snapshot(doc)['reachableClaimBlockIds']==[child],'eligible target did not return')
        with step('scoped_watch_reports_cross_peer_native_append'):
            watch=ObjectWatch(repo,doc);watch.wait(lambda s:{r['id'] for r in s['records']}==closure)
            marker=make_claim(space,account,doc,200,ref='cross-peer scoped marker',item_id='scoped-marker');second.append(marker);closure.add(marker['id']);expected.add(marker['id'])
            watch.wait(lambda s:{r['id'] for r in s['records']}==closure);watch.close();watch=None
            b.stop()
        if args.large_space_proof:
            with step('append_10001_unrelated_signed_native_claims'):
                for offset in range(0,10001,50):
                    batch=[make_claim(space,account,foreign,100000+n,ref='unrelated-source-'+str(n),item_id='unrelated-'+str(n)) for n in range(offset,min(offset+50,10001))]
                    repo.append_batch(batch)
                receipt['unrelatedSignedClaims']=10001
            with step('object_read_remains_complete_above_workspace_claim_cap'):
                refused(lambda:repo.snapshot(),409,'pinkha.read_limit')
                current=repo.object_snapshot(doc,len(closure));require({r['id'] for r in current['records']}==closure,'unrelated Space size changed target result')
                source=repo.source('ref','cross-peer scoped marker');require(source['objectIds']==[] and source['conflictedObjectIds']==[doc] and source['coverage']=='incomplete-conflict-or-pending','indexed source did not truthfully report existing object collision')
            # The queried marker shares a conflicted object. Completeness must
            # honestly report that conflict, while lookup itself remains bounded.
        with step('native_object_watch_overflow_invalidates_previous_state'):
            watch=ObjectWatch(repo,doc,limit=len(closure));watch.wait(lambda s:{r['id'] for r in s['records']}==closure)
            overflow=make_claim(space,account,doc,201,ref='overflow marker',item_id='overflow-marker');repo.append(overflow);watch.refused();watch.close();watch=None
        with step('source_manifests_unchanged_after_scoped_runtime_proof'):
            require(source_manifest(args.runtime_source)==receipt['anySource'] and source_manifest(args.sdk_source)==receipt['sdkSource'],'native sources changed during proof')
        receipt['final']={'accountId':account,'spaceId':space,'rootObjectId':root,'targetObjectId':doc,'targetBlockId':child,'objectClosureCountBeforeOverflow':len(closure),'crossObjectWitnessHasOmittedForeignPredecessor':True}
        receipt['status']='PASS_NATIVE_OBJECT_SCOPE_END_TO_END'
    except Exception as error:receipt['status']='FAIL';receipt['fatalFailure']=type(error).__name__+': '+str(error)[:450]
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
        receipt['firewallRules']=[r.evidence for r in rules]
        if receipt.get('cleanupErrors'):receipt['status']='FAIL'
        receipt['finishedAt']=datetime.now(timezone.utc).isoformat();path=Path(args.result);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8');mnemonic=None
        print(json.dumps({'status':receipt['status'],'checks':len(receipt['checks']),'fatalFailure':receipt.get('fatalFailure'),'receipt':str(path)},ensure_ascii=True),flush=True)
    return 0 if receipt['status']=='PASS_NATIVE_OBJECT_SCOPE_END_TO_END' else 1
if __name__=='__main__':sys.exit(main())
