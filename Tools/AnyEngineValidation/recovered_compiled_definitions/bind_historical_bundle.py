"""Bind qualified recovered descriptors to the unchanged historical156 bundle."""
from pathlib import Path
import hashlib, importlib.util, json

ROOT = Path('/mnt/development/projects/worktrees/anytype-migration-final-20261125')
RECEIPTS = ROOT/'docs/validation/20261126-original-source-compiled-definitions/actual-original-go-export'
CAPTURE = Path('/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156')
def sha(data): return hashlib.sha256(data).hexdigest()
def main():
    verifier = ROOT/'Tools/AnyEngineValidation/native_captured_content/run_native_captured_content_roundtrip.py'
    assert sha(verifier.read_bytes()) == 'da4311e3cf0af4d0d14d42fa39a799348bea29122e7fb0d313b111e47fddf299'
    spec=importlib.util.spec_from_file_location('original_member_verifier',verifier)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    before=module.verify_original()
    manifest_bytes=(CAPTURE/'bundle/manifest.json').read_bytes()
    assert sha(manifest_bytes)=='cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4'
    capture=json.loads(manifest_bytes)
    original_path=ROOT/'Tools/AnyEngineValidation/native_file_peer/retained-scheduling-45492064232/producer-result.json'
    producer_bytes=original_path.read_bytes();producer=json.loads(producer_bytes)
    receipt_bytes=(RECEIPTS/'receipt.json').read_bytes();receipt=json.loads(receipt_bytes)
    export_bytes=(RECEIPTS/'descriptors/export.json').read_bytes();export=json.loads(export_bytes)
    assert sha(producer_bytes)=='10dcb731241232985f626fcb8d084ec8a138c9e0aeffa46190f417d2da05c157'
    assert sha(receipt_bytes)=='b4561fa708141c463fce941ba4e266e42d12760d81cc63524d1cb96766ad7eb6'
    assert sha(export_bytes)=='50458de19c0c9c8ae0bfc1b9cca1b6c5e29fbcf53d63bf32c5caabd0a3358ebb'
    ids=[v['Kind']+':'+v['Key'] for v in export['Descriptors']]
    assert len(ids)==len(set(ids))==7 and set(ids)==set(capture['BundledDefinitionsUsed'])
    assert not capture.get('BundledDefinitions')
    assert producer['compiled_source_unchanged'] is True
    assert producer['source']['manifest_sha256']==receipt['originalSourceManifestSHA256']
    assert producer['input_sha256']['source']==receipt['originalSourceArchiveSHA256']
    assert producer['binary']['sha256']==receipt['originalNativeBinarySHA256']
    assert producer['heart_sha']==receipt['heartCommit']
    value={
        'Contract':'pinkha-recovered-compiled-definition-sidecar-v1',
        'OriginalCapture':{
            'ManifestSHA256':sha(manifest_bytes),
            'SourceWitnessSHA256':capture['Receipt']['Inventory']['SourceWitnessSHA256'],
            'AccountSHA256':capture['Receipt']['Source']['accountSHA256'],
            'SpaceSHA256':capture['Receipt']['Inventory']['SpaceSHA256'],
        },
        'OriginalProducer':{
            'ReceiptSHA256':sha(producer_bytes),
            'SourceArchiveSHA256':receipt['originalSourceArchiveSHA256'],
            'SourceManifestSHA256':receipt['originalSourceManifestSHA256'],
            'NativeBinarySHA256':receipt['originalNativeBinarySHA256'],
            'HeartCommit':receipt['heartCommit'],
        },
        'RecoveryReceiptSHA256':sha(receipt_bytes),
        'RegistryExportSHA256':sha(export_bytes),
        'DefinitionIDs':ids,
        'OriginalCapturedMembersReplaced':False,
    }
    raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    after=module.verify_original();assert before==after
    output=RECEIPTS/'historical156-binding.json'
    with output.open('xb') as stream:stream.write(raw)
    proof={'protocol':'pinkha-historical156-recovered-registry-binding-v1',
           'status':'PASS_SOURCE_BINDING_ONLY_NOT_SWIFT_OR_DESTINATION_ACCEPTANCE',
           'bindingSHA256':sha(raw),'originalBefore':before,'originalAfter':after,
           'originalMembersUnchanged':True,'recoveredDefinitionCount':7,
           'originalCapturedMembersReplaced':False,'destinationWrites':False,
           'engineCalls':0,'controllerSHA256':sha(Path(__file__).read_bytes())}
    with (RECEIPTS/'historical156-binding-proof.json').open('x') as stream:
        json.dump(proof,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps({'bindingSHA256':sha(raw),'path':str(output),'status':proof['status']}))
if __name__=='__main__':main()
