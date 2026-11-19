#!/usr/bin/env python3
"""Source-bound real HTTP proof for independent native document metadata."""
from __future__ import annotations
import argparse,json,re,sys,tempfile,time
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from run_runtime_validation import Peer,require,digest
from run_native_validation import NativeRepo,make_claim,source_manifest,refused

class DirectPeer(Peer):
    """No executable copy or firewall rules: this proof tests local metadata."""
    def __init__(self,binary,folder):
        self.folder=Path(folder);self.folder.mkdir()
        self.binary=str(Path(binary).resolve());self.network=None
        self.process=None;self.endpoint=None;self.token=None;self.boot=0;self.streams=[]

def main():
    p=argparse.ArgumentParser()
    for name in ('binary','expected-binary-sha256','runtime-source','sdk-source','result'):p.add_argument('--'+name,required=True)
    args=p.parse_args();receipt={'status':'IN_PROGRESS','scope':'Real native metadata before claims installation, cold reopen and exact target/type/current-ACL generation dependencies. No network partition claim.','startedAt':datetime.now(timezone.utc).isoformat(),'checks':[]}
    peer=None;mnemonic=None
    @contextmanager
    def step(name):
        started=time.monotonic()
        try:yield
        except Exception as error:
            receipt['checks'].append({'name':name,'status':'FAIL','error':type(error).__name__+': '+str(error)[:240]});raise
        else:
            receipt['checks'].append({'name':name,'status':'PASS','seconds':round(time.monotonic()-started,3)})
            print(json.dumps({'step':name,'status':'PASS'}),flush=True)
    try:
        with step('pin_clean_native_sources_binary_and_exact_harness'):
            require(digest(args.binary)==args.expected_binary_sha256.lower(),'native binary pin differs')
            receipt.update(binarySHA256=digest(args.binary),anySource=source_manifest(args.runtime_source),sdkSource=source_manifest(args.sdk_source),harnessSHA256=digest(__file__))
            receipt['helperSHA256']={name:digest(Path(__file__).with_name(name)) for name in ('run_runtime_validation.py','run_native_validation.py')}
        folder=Path(tempfile.mkdtemp(prefix='pinkha-metadata-validation-'));peer=DirectPeer(args.binary,folder/'peer')
        with step('fresh_disposable_account_space_without_claims_installation'):
            peer.start();auth=peer.auth();account=auth['accountId'];mnemonic=auth['mnemonic'];del auth
            space=peer.request('POST','/v1/spaces',{'name':'Disposable metadata-only native document proof'})['id'];base='/v1/spaces/'+space
            caps=peer.request('GET','/v1/pinkha/capabilities')
            require(caps.get('nativeDocumentTypePolicy')==1 and caps.get('documentTypePolicy')=='canonical-editor-module-v1','native document policy mismatch')
            refused(lambda:peer.request('GET',base+'/pinkha/claims'),404)
        def type_proof(type_id):
            value=peer.request('GET',base+'/pinkha/document-types/'+type_id)
            require(value.get('contract')=='pinkha-torah-native-v1' and value.get('version')==1 and value.get('policy')=='canonical-editor-module-v1' and value.get('spaceId')==space and value.get('typeId')==type_id,'Type policy scope differs')
            require(value.get('canonicalEditorDataset')=='editor_blocks' and value.get('readiness',{}).get('state')=='ready-local-snapshot' and re.fullmatch('[0-9a-f]{64}',value['readiness']['generation']),'Type policy readiness differs')
            return value
        def target_proof(object_id):
            value=peer.request('GET',base+'/pinkha/document-targets/'+object_id)
            require(value.get('contract')=='pinkha-torah-native-v1' and value.get('version')==1 and value.get('spaceId')==space and value.get('objectId')==object_id and value.get('eligible') is True and value.get('canWrite') is True,'target policy scope/authority differs')
            require(value.get('readiness',{}).get('state')=='ready-local-snapshot' and re.fullmatch('[0-9a-f]{64}',value['readiness']['generation']),'target policy readiness differs')
            return value
        with step('page_and_compiled_custom_type_editor_work_without_implicit_install'):
            require(type_proof('page')['eligible'] is True,'compiled Page was refused')
            custom=peer.request('POST',base+'/types',{'name':'Metadata custom document','xKey':'metadata_custom_v7'})['typeId']
            part=peer.request('POST',base+'/types/'+custom+'/parts',{'key':'body','datasets':[{'module':'editor'}]})['partId']
            require(type_proof(custom)['eligible'] is True,'custom canonical editor was refused')
            targets=[]
            for type_id in ('page',custom):
                oid=peer.request('POST',base+'/pinkha/objects',{'type':type_id,'initialProperties':{'any':{'name':'Metadata-only editor'}}})['objectId']
                before=target_proof(oid)
                block=peer.request('POST',base+'/pinkha/objects/'+oid+'/editor/editor_blocks/blocks',{'type':'paragraph','text':'גוף מקומי לפני התקנת הרחבות','style':{'unknownField':'retained'}})['recordIds'][0]
                after=target_proof(oid)
                require(after['typeId']==type_id and before['readiness']!=after['readiness'],'native body edit did not update the target generation')
                targets.append((oid,block,type_id))
            refused(lambda:peer.request('GET',base+'/pinkha/claims'),404)
            receipt['wireFixtures']={'pageType':type_proof('page'),'customType':type_proof(custom),'customTarget':target_proof(targets[1][0])}
        with step('cold_reopen_retains_uninstalled_editor_and_current_native_proofs'):
            peer.stop();peer.start();require(peer.auth(mnemonic)['accountId']==account,'cold account differs')
            refused(lambda:peer.request('GET',base+'/pinkha/claims'),404)
            for oid,block,type_id in targets:
                require(target_proof(oid)['typeId']==type_id,'cold target Type differs')
                rows=peer.request('POST',base+'/query',{'objectId':oid,'dataset':'editor_blocks','sort':['nav.pos'],'limit':100})['records']
                require(len(rows)==1 and rows[0]['id']==block and rows[0]['style']['unknownField']=='retained','cold editor body/unknown style differs')
            require(type_proof(custom)['eligible'] is True,'cold custom Type proof failed')
        with step('unrelated_native_install_and_signed_claim_do_not_invalidate_policy'):
            doc=targets[1][0];before_target=target_proof(doc);before_type=type_proof(custom);before_page=type_proof('page')
            root=peer.request('POST',base+'/pinkha/install')['rootObjectId']
            require(target_proof(doc)['readiness']==before_target['readiness'],'carrier installation invalidated unrelated document')
            repo=NativeRepo(peer,space,account,root);claim=make_claim(space,account,targets[0][0],701,item_id='unrelated-native-context')
            result=repo.append(claim);require(result.get('changeId') and repo.ids()=={claim['id']},'actual signed claim was not durably read back')
            require(target_proof(doc)['readiness']==before_target['readiness'],'unrelated signed claim invalidated target policy')
            require(type_proof(custom)['readiness']==before_type['readiness'] and type_proof('page')['readiness']==before_page['readiness'],'unrelated signed claim invalidated Type policy')
        with step('actual_target_and_dynamic_type_changes_still_invalidate_or_refuse'):
            peer.request('POST',base+'/pinkha/objects/'+doc+'/editor/editor_blocks/blocks',{'type':'paragraph','text':'actual target revision'})
            require(target_proof(doc)['readiness']!=before_target['readiness'],'actual target change did not invalidate generation')
            require(type_proof(custom)['readiness']==before_type['readiness'],'target body changed an unrelated Type definition generation')
            declarations=peer.request('GET',base+'/types/'+custom+'/datasets')['datasets'];require(len(declarations)==1,'custom dataset count differs')
            peer.request('DELETE',base+'/types/'+custom+'/datasets/'+declarations[0]['id'])
            changed=type_proof(custom);require(changed['eligible'] is False and changed['readiness']!=before_type['readiness'],'removed native module stayed eligible')
            refused(lambda:target_proof(doc),409,'pinkha.document_ineligible')
            peer.request('POST',base+'/types/'+custom+'/parts/'+part+'/datasets',{'module':'editor'})
            require(type_proof(custom)['eligible'] is True and target_proof(doc)['typeId']==custom,'restored canonical module failed native revalidation')
        with step('source_manifests_and_binary_unchanged_after_proof'):
            require(source_manifest(args.runtime_source)==receipt['anySource'] and source_manifest(args.sdk_source)==receipt['sdkSource'],'native source changed during proof')
            require(digest(args.binary)==receipt['binarySHA256'],'native executable changed during proof')
        receipt['final']={'accountId':account,'spaceId':space,'rootObjectId':root,'customTypeId':custom,'targetObjectId':doc,'signedClaims':1,'coldReopens':1}
        receipt['status']='PASS_NATIVE_DOCUMENT_METADATA_END_TO_END'
    except Exception as error:
        receipt['status']='FAIL';receipt['fatalFailure']=type(error).__name__+': '+str(error)[:400]
    finally:
        if peer:
            try:peer.stop()
            except Exception as error:receipt.setdefault('cleanupErrors',[]).append(type(error).__name__)
        mnemonic=None
        if receipt.get('cleanupErrors'):receipt['status']='FAIL'
        receipt['finishedAt']=datetime.now(timezone.utc).isoformat();Path(args.result).write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
        print(json.dumps({'status':receipt['status'],'checks':len(receipt['checks']),'result':args.result,'fatalFailure':receipt.get('fatalFailure')}),flush=True)
    return 0 if receipt['status'].startswith('PASS_') else 1

if __name__=='__main__':sys.exit(main())
