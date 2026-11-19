#!/usr/bin/env python3
"""Source-bound native custom document definitions, property fences and sync."""
from __future__ import annotations
import argparse, json, re, sys, tempfile, time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from run_runtime_validation import Peer, ContractFailure, require, digest, eventually
from run_native_validation import make_claim, source_manifest, refused
from run_native_object_validation import ObjectRepo, ObjectWatch

def main():
    p=argparse.ArgumentParser()
    for name in ('binary','expected-binary-sha256','runtime-source','sdk-source','result'):p.add_argument('--'+name,required=True)
    args=p.parse_args();receipt={'status':'IN_PROGRESS','scope':'Native custom document definition fences, canonical claims and properties across two fresh peers, definition-change SSE invalidation and cold restart','startedAt':datetime.now(timezone.utc).isoformat(),'checks':[]}
    peers=[];watch=None;mnemonic=None
    @contextmanager
    def step(name):
        begin=time.monotonic()
        try:yield
        except Exception as error:
            receipt['checks'].append({'name':name,'status':'FAIL','error':type(error).__name__+': '+str(error)[:260]});raise
        else:
            receipt['checks'].append({'name':name,'status':'PASS','seconds':round(time.monotonic()-begin,3)})
            print(json.dumps({'step':name,'status':'PASS'}),flush=True)
    try:
        with step('pin_clean_native_sources_binary_and_exact_harness'):
            require(digest(args.binary)==args.expected_binary_sha256.lower(),'binary pin differs')
            receipt.update(binarySHA256=digest(args.binary),anySource=source_manifest(args.runtime_source),sdkSource=source_manifest(args.sdk_source),harnessSHA256=digest(__file__))
            receipt['helperSHA256']={name:digest(Path(__file__).with_name(name)) for name in ('run_runtime_validation.py','run_native_validation.py','run_native_object_validation.py')}
        folder=Path(tempfile.mkdtemp(prefix='pinkha-definition-validation-'));a=Peer(args.binary,folder/'a');b=Peer(args.binary,folder/'b');peers=[a,b]
        with step('bootstrap_fresh_disposable_scope_and_required_capabilities'):
            a.start();auth=a.auth();account=auth['accountId'];mnemonic=auth['mnemonic'];del auth
            space=a.request('POST','/v1/spaces',{'name':'Disposable native document definition validation'})['id'];base='/v1/spaces/'+space
            caps=a.request('GET','/v1/pinkha/capabilities')
            for key in ('nativeDocumentTypePolicy','nativeDocumentMembership','conditionalMembershipSet','nativePropertyPresentation','nativeObjectClaimsSnapshot','nativeObjectClaimsWatch'):require(caps.get(key)==1,'missing '+key)
            require(caps.get('documentTypePolicy')=='canonical-editor-module-v1','document policy differs')
            require(caps.get('propertyPresentationCollection')=='pinkha_presentation_v1' and caps.get('propertyPresentationHiddenProperty')=='hiddenProperties' and caps.get('propertyPresentationMaxKeys')==512 and caps.get('propertyPresentationMaxKeyBytes')==4096,'presentation policy differs')
            root=a.request('POST',base+'/pinkha/install')['rootObjectId'];repo=ObjectRepo(a,space,account,root);receipt['capabilities']=caps
        def record(peer,oid):return peer.request('GET',base+'/properties/'+oid)['record']
        def conditional(peer,oid,owner,patch,version=None):
            version=record(peer,oid)['_ver'] if version is None else version
            return peer.request('POST',base+'/pinkha/properties/'+oid+'/set/'+owner,{'patch':patch,'ifVersion':version,'ifStartedAt':peer.request('GET','/v1/health')['startedAt']})
        def proof(peer,oid):
            value=peer.request('GET',base+'/pinkha/document-targets/'+oid)
            require(value.get('contract')=='pinkha-torah-native-v1' and value.get('version')==1 and value.get('spaceId')==space and value.get('objectId')==oid and value.get('eligible') is True and value.get('canWrite') is True and value.get('canonicalEditorDataset')=='editor_blocks','document proof mismatch')
            require(value.get('readiness',{}).get('state')=='ready-local-snapshot' and re.fullmatch('[0-9a-f]{64}',value['readiness']['generation']),'document proof readiness missing')
            return value
        with step('compiled_custom_document_creation_and_metadata_proof'):
            custom=a.request('POST',base+'/types',{'name':'Native custom note','xKey':'native_definition_note'})['typeId']
            part=a.request('POST',base+'/types/'+custom+'/parts',{'key':'body','datasets':[{'module':'editor'}]})['partId']
            doc=a.request('POST',base+'/pinkha/objects',{'type':custom,'initialProperties':{'any':{'name':'Synthetic custom note','description':'ordinary metadata survives type changes'}}})['objectId']
            block=a.request('POST',base+'/pinkha/objects/'+doc+'/editor/editor_blocks/blocks',{'type':'paragraph','text':'שדה מקור לניסוי','style':{'futureStyle':{'preserved':True}}})['recordIds'][0]
            document=proof(a,doc);require(document['typeId']==custom,'custom type was replaced')
            type_proof=a.request('GET',base+'/pinkha/document-types/'+custom);require(type_proof['eligible'] is True,'compiled custom type is not eligible')
            receipt['wireFixtures']={'documentTypeProof':type_proof,'documentTargetProof':document}
        with step('native_custom_type_claims_indexed_sources_and_related_targets'):
            doc_claim=make_claim(space,account,doc,601,item_id='custom-doc-context')
            block_claim=make_claim(space,account,doc,602,block=block,item_id='custom-block-context')
            quote_claim=make_claim(space,account,doc,603,block=block,item_id='custom-block-quote',role='sourceQuote')
            for claim in (doc_claim,block_claim,quote_claim):repo.append(claim)
            expected={claim['id'] for claim in (doc_claim,block_claim,quote_claim)}
            current=repo.object_snapshot(doc);require({r['id'] for r in current['records']}==expected and current['reachableClaimBlockIds']==[block],'custom scoped claims differ')
            source=repo.source('ref','Genesis 1:1');require(source['objectIds']==[doc] and source['coverage']=='complete','custom type missing from indexed source')
            related=repo.related('Genesis 1:1');require(related['coverage']=='complete','custom related coverage incomplete')
            receipt['wireFixtures']['source']=source;receipt['wireFixtures']['related']=related
        with step('second_peer_hydrates_custom_definition_target_and_claims'):
            b.start();require(b.auth(mnemonic)['accountId']==account,'second native identity differs');second=ObjectRepo(b,space,account,root)
            eventually(lambda:{r['id'] for r in second.object_snapshot(doc)['records']}==expected and proof(b,doc)['typeId']==custom,'custom target/definition hydration')
            require(second.source('ref','Genesis 1:1')['objectIds']==[doc],'remote source missed custom document')
        with step('fenced_type_change_preserves_native_body_claims_and_unknown_styles'):
            watch=ObjectWatch(second,doc);initial=watch.wait(lambda s:{r['id'] for r in s['records']}==expected)
            conditional(a,doc,'any',{'type':'page'})
            watch.wait(lambda s:s['readiness']['generation']!=initial['readiness']['generation']);watch.close();watch=None
            eventually(lambda:proof(b,doc)['typeId']=='page','remote type change')
            require({r['id'] for r in second.object_snapshot(doc)['records']}==expected,'type change lost immutable claims')
            rows=b.request('GET',base+'/objects/'+doc+'/editor/editor_blocks/blocks')['records']
            require(len(rows)==1 and rows[0]['id']==block and rows[0]['style']['futureStyle']=={'preserved':True},'type change recreated body or erased styles')
            require(record(b,doc)['any']['description']=='ordinary metadata survives type changes','ordinary property lost')
            conditional(a,doc,'any',{'type':custom});eventually(lambda:proof(b,doc)['typeId']==custom,'restore custom type')
        with step('fixed_presentation_schema_preserves_opaque_future_keys_and_business_values'):
            owner='pinkha_presentation_v1'
            catalog=a.request('GET',base+'/collections/'+owner);declaration=a.request('GET',base+'/collections/'+owner+'/properties')
            require(catalog.get('builtIn') is True and catalog.get('hidden') is True,'presentation collection is not compiled/hidden')
            props=declaration['properties'];require(len(props)==1 and props[0]['id']=='hiddenProperties' and props[0]['kind']=='array' and props[0]['scope']=='synced','presentation declaration differs')
            receipt['wireFixtures']['presentationCollection']=catalog;receipt['wireFixtures']['presentationProperties']=declaration
            conditional(a,doc,'any',{'collections':[owner]})
            keys=['property:v1:3:any:4:name','derived:v1:pinkha-torah-native-v1:pinkhaSources','future:v99:opaque:שלום']
            conditional(a,doc,owner,{'hiddenProperties':keys});before=record(a,doc)
            refused(lambda:conditional(a,doc,owner,{'hiddenProperties':[keys[0],keys[0]]}),400,'property.format_violation')
            require(record(a,doc)==before,'invalid visibility append changed canonical values')
            conditional(a,doc,owner,{'hiddenProperties':keys[1:]})
            eventually(lambda:record(b,doc).get(owner,{}).get('hiddenProperties')==keys[1:],'synced visibility preferences')
            require(record(b,doc)['any']['name']=='Synthetic custom note' and second.source('ref','Genesis 1:1')['objectIds']==[doc],'hiding changed business data or source index')
        with step('definition_removal_invalidates_remote_watch_and_refuses_prepared_picker'):
            spare=a.request('POST',base+'/pinkha/objects',{'type':'page'})['objectId'];prepared_version=record(a,spare)['_ver'];before=record(a,spare)
            require(a.request('GET',base+'/pinkha/document-types/'+custom)['eligible'] is True,'prepared destination was not initially eligible')
            watch=ObjectWatch(second,doc);watch.wait(lambda s:{r['id'] for r in s['records']}==expected)
            declarations=a.request('GET',base+'/types/'+custom+'/datasets')['datasets'];require(len(declarations)==1,'unexpected custom dataset count')
            a.request('DELETE',base+'/types/'+custom+'/datasets/'+declarations[0]['id'])
            refused(lambda:conditional(a,spare,'any',{'type':custom},prepared_version),409)
            require(record(a,spare)==before,'stale destination definition changed object')
            watch.refused();watch.close();watch=None
            refused(lambda:proof(a,doc),409,'pinkha.document_ineligible')
            require(repo.source('ref','Genesis 1:1')['objectIds']==[],'ineligible custom type stayed in source index')
            require(repo.ids()==expected,'definition change erased signed claim history')
        with step('restored_module_reuses_original_body_and_native_history'):
            a.request('POST',base+'/types/'+custom+'/parts/'+part+'/datasets',{'module':'editor'})
            eventually(lambda:{r['id'] for r in second.object_snapshot(doc)['records']}==expected and proof(b,doc)['typeId']==custom,'restored remote module definition')
            require(second.object_snapshot(doc)['reachableClaimBlockIds']==[block] and second.source('ref','Genesis 1:1')['objectIds']==[doc],'restoration failed to recover original body/source')
        with step('cold_restart_loads_custom_definitions_without_read_transaction_writes'):
            b.stop();b.start();b.auth(mnemonic)
            require({r['id'] for r in second.object_snapshot(doc)['records']}==expected and proof(b,doc)['typeId']==custom,'cold custom definition snapshot differs')
            require(record(b,doc)['pinkha_presentation_v1']['hiddenProperties']==keys[1:],'cold restart lost opaque presentation keys')
        with step('source_manifests_unchanged_after_native_definition_proof'):
            require(source_manifest(args.runtime_source)==receipt['anySource'] and source_manifest(args.sdk_source)==receipt['sdkSource'],'native sources changed during proof')
        receipt['final']={'accountId':account,'spaceId':space,'rootObjectId':root,'customTypeId':custom,'targetObjectId':doc,'targetBlockId':block,'immutableClaims':len(expected)}
        receipt['status']='PASS_NATIVE_DOCUMENT_DEFINITION_END_TO_END'
    except Exception as error:
        receipt['status']='FAIL';receipt['fatalFailure']=type(error).__name__+': '+str(error)[:400]
    finally:
        if watch:
            try:watch.close()
            except Exception as error:receipt.setdefault('cleanupErrors',[]).append(type(error).__name__)
        for peer in peers:
            try:peer.stop()
            except Exception as error:receipt.setdefault('cleanupErrors',[]).append(type(error).__name__)
        mnemonic=None
        if receipt.get('cleanupErrors'):receipt['status']='FAIL'
        receipt['finishedAt']=datetime.now(timezone.utc).isoformat();Path(args.result).write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
        print(json.dumps({'status':receipt['status'],'checks':len(receipt['checks']),'result':args.result,'fatalFailure':receipt.get('fatalFailure')}),flush=True)
    return 0 if receipt['status'].startswith('PASS_') else 1

if __name__=='__main__':sys.exit(main())
