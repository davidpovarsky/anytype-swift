from pathlib import Path
import json, hashlib, importlib.util
r=Path('/Users/m1/builds/any-semantic-20261125/source-links-unlink3');e=r/'evidence';private=r/'private-ui-attachments'
def require(value,name):
    if not value: raise RuntimeError(name)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())
def textsha(value):return hashlib.sha256(value.encode()).hexdigest()
execution=load(e/'execution.json');summary=load(e/'ui/summary.json');cleanup=load(e/'cleanup.json')
require(execution['status']=='PASS' and execution['sourceCommit']=='4b9b381d3f9b8d5a9a358d626a69333c145e3282','original_controller_not_passed')
require(summary['result']=='Passed' and summary['totalTestCount']==summary['passedTests']==1 and summary['failedTests']==summary['skippedTests']==summary['expectedFailures']==0,'original_method_count_or_status')
require(cleanup['status']=='PASS' and cleanup['remainingOwnedGroups']==[],'owned_cleanup')
require(execution['acceptedNewNativeTestsRerun']==execution['acceptedOldTestsRerun']==execution['nativeLibraryBuilds']==0,'unnecessary_rerun')
require(sha(e/'original-native-pass-ui-lookup-fail.json')=='a1558d0b732f905f6ad3d21723c84deebfca62fb5d7993c9133a2bf215188bbf','native_accepted_proof')
require(sha(e/'original-unlink-reachability-failure.json')=='01d8f5a1c7100da5fe231bbe85b58da04adec7415cf701e6a85fd895d02531e0','original_failure_proof')
require(load(e/'source-before.json')==load(e/'source-after.json'),'source_changed')
require(load(e/'dependencies-before.json')==load(e/'dependencies-after.json'),'dependencies_changed')
controller=Path('/Users/m1/builds/any-semantic-20261125/inputs/controller-ad9db960f9db5440be19774c95e89cbbc3deac67.py')
require(sha(controller)=='341f28c617c1ada9d30b77cc682f652fe2207fff630e6f0ad1ec95685594e59d','qualified_base_changed')
spec=importlib.util.spec_from_file_location('e_original_driver',controller);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
products=load(e/'ui/original-products.json')
require(base.inventory(e/'ui/retained-original/Build/Products')==products,'retained_products_changed')
require(base.source_state(Path('/Users/m1/builds/any-semantic-20261125/source-fbb7b19'),execution['sourceCommit'])==load(e/'source-after.json'),'current_source_changed')
phases=['source-target-native-anchor-created','source-link-canonical-native-readback','source-link-follows-real-text-edit','source-link-fresh-process-native-reopen','source-unlink-keeps-native-text-and-marker','source-unlink-fresh-process-readback'];observations=[];by_phase={}
for attachment in load(private/'manifest.json')[0]['attachments']:
    name=attachment['suggestedHumanReadableName'];path=private/attachment['exportedFileName']
    if path.suffix!='.json' or not name.startswith('native-semantic-anchor-'):continue
    value=load(path)
    require(value['schema']=='any-semantic-anchor-native-rendered/v1' and value['state']=='MATCHED' and value['mode']=='read-only','observation_shape')
    require(value['engineCalls']==value['mutations']==value['selectionChanges']==0,'observer_performed_actions')
    require(value['nativeMarkCount']==value['renderedMarkCount'] and all(b['nativeMarks']==b['renderedMarks'] for b in value['blocks']),'native_rendered_differ')
    observations.append({'attachment':path.name,'name':name,'bytes':path.stat().st_size,'sha256':sha(path),'observation':value})
    for phase in phases:
        if name.startswith('native-semantic-anchor-'+phase+'_'):
            require(phase not in by_phase,'duplicate_phase');by_phase[phase]=value
require(set(by_phase)==set(phases) and len(observations)==15,'missing_original_observations')
created,linked,edited,cold,unlinked,removed=[by_phase[phase] for phase in phases]
for value in by_phase.values():
    require(len(value['blocks'])==1 and (value['spaceSHA256'],value['objectSHA256'],value['blocks'][0]['blockSHA256'])==(created['spaceSHA256'],created['objectSHA256'],created['blocks'][0]['blockSHA256']),'document_or_block_identity_changed')
# AnyEditorRead.nativeVersion comes from the native markdown read's version.
# It is a document revision, not an engine/framework version: editing must change
# it; the same saved text on cold reopen must retain that revision.
require(created['nativeVersionSHA256']==linked['nativeVersionSHA256'],'unrequested_text_revision_before_edit')
require(edited['nativeVersionSHA256']!=linked['nativeVersionSHA256'],'text_edit_did_not_change_native_document_revision')
require(edited['nativeVersionSHA256']==cold['nativeVersionSHA256']==unlinked['nativeVersionSHA256']==removed['nativeVersionSHA256'],'saved_native_text_revision_changed_after_reopen_or_unlink')
mark=created['blocks'][0]['nativeMarks'][0]
require(mark['location']==0 and mark['length']==6 and mark['textSHA256']==textsha('Anchor'),'original_selected_marker')
require(created['semanticSources']==[] and len(linked['semanticSources'])==1,'canonical_link_count')
association=linked['semanticSources'][0]
require(association['identitySHA256']==mark['identitySHA256'] and association['canonicalSHA256']==textsha('Genesis 1:1') and association['resolution']=='resolved','canonical_source_identity')
require(linked['sourceReadOrigin']=='TorahEditorSession.associationRecords','canonical_read_origin')
require(edited['semanticSources']==cold['semanticSources']==[association],'canonical_source_changed_after_edit_or_reopen')
for value in [edited,cold,unlinked,removed]:
    block=value['blocks'][0]
    require(block['textSHA256']==textsha('Changed') and len(block['nativeMarks'])==1,'edited_native_text_or_mark_count')
    current=block['nativeMarks'][0]
    require(current['identitySHA256']==mark['identitySHA256'] and current['location']==0 and current['length']==7,'edited_native_marker_identity_or_extent')
require(edited['blocks'][0]['sourceSHA256']==cold['blocks'][0]['sourceSHA256']==unlinked['blocks'][0]['sourceSHA256']==removed['blocks'][0]['sourceSHA256'],'unlink_changed_native_source_bytes')
require(unlinked['semanticSources']==removed['semanticSources']==[],'unlink_not_persisted')
require(len({edited['pid'],cold['pid'],removed['pid']})==3 and len({edited['generation'],cold['generation'],removed['generation']})==3,'cold_process_not_distinct')
files=['execution.json','cleanup.json','source-before.json','source-after.json','dependencies-before.json','dependencies-after.json','native-binding.json','ui/summary.json','ui/tests.json','ui/original.xctestrun','ui/original-products.json','ui/product-retention.json','commands/007-ui-test.stdout','initial-readonly-qualification-failure.json']
record={'protocol':'any-semantic-source-link-and-unlink-actual-ui-pass-v1','status':'PASS_ACTUAL_NATIVE_UI_SOURCE_LINK_EDIT_COLD_UNLINK_COLD','sourceCommit':execution['sourceCommit'],'controllerCommit':execution['controllerCommit'],'scope':execution['scope'],'physicalDevice':'NOT_RUN','method':'NativeLaunchTests/testSemanticSourceLinkSurvivesEditAndColdReopen','passed':1,'failed':0,'skipped':0,'durationSeconds':393.402,'device':summary['devicesAndConfigurations'][0]['device'],'observations':observations,'nativeRenderedComparisons':len(observations),'verifiedBoundaries':phases,'canonicalSourceRecordUnchangedAfterEditAndColdReopen':True,'unlinkSourceAbsentAfterSecondColdProcess':True,'textAndMarkerUnchangedByUnlink':True,'nativeDocumentRevisionChangesWithTextEditAndPersistsAfterward':True,'processSequence':[edited['pid'],cold['pid'],removed['pid']],'unlinkMinimum44By44AndHittableAssertionsPassed':True,'sourceUnchanged':True,'dependenciesUnchanged':True,'originalProductsEntries':len(products),'originalProductsHashVerification':'PASS','acceptedOldControlsRerun':0,'acceptedNewNativeMethodsRerun':0,'acceptedNewNativeEvidenceSHA256':execution['acceptedNewNativeEvidenceSHA256'],'originalFiles':{name:{'bytes':(e/name).stat().st_size,'sha256':sha(e/name)} for name in files},'qualifierSHA256':sha(Path(__file__)),'privateAttachmentManifest':{'bytes':(private/'manifest.json').stat().st_size,'sha256':sha(private/'manifest.json')},'cleanup':cleanup,'limitations':['not combined-runtime or SDK97 acceptance','Heart source-link continuation pending','not physical-device acceptance']}
output=e/'actual-source-ui-pass.json';require(not output.exists(),'receipt_exists');output.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({'receipt':str(output),'sha256':sha(output),'bytes':output.stat().st_size,'products':len(products),'observations':len(observations),'pids':record['processSequence']}))
