"""Prepare exact original-Anytype hooks for owner review; never applies them."""
from pathlib import Path
import argparse, difflib, hashlib, json, subprocess

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
changes={}
def edit(path,old,new):
    if path not in changes:
        before=(root/path).read_text(encoding='utf8')
        changes[path]=[before,before]
    assert changes[path][1].count(old)==1,(path,old)
    changes[path][1]=changes[path][1].replace(old,new)

edit('Anytype/Sources/Models/Properties/SinglePropertyBuilder.swift',
'''        switch relationDetails.format {''',
'''        if let native = TorahNativePropertyPresentation.property(
            definition: relationDetails, details: details,
            isFeatured: isFeatured, valuesLocked: propertyValuesIsLocked
        ) { return native }
        switch relationDetails.format {''')
edit('Anytype/Sources/PresentationLayer/PropertyValueFlow/PropertyValueCoordinator/PropertyValueCoordinatorViewModel.swift',
'''    func propertyModule() -> AnyView {
        switch relation {''',
'''    func propertyModule() -> AnyView {
        if TorahNativePropertyPresentation.definition(relation.key) != nil {
            mediumDetent = false
            return TorahNativePropertyEditorView(
                spaceId: objectDetails.spaceId, objectId: objectDetails.id,
                key: relation.key, canEdit: relation.isEditable
            ).eraseToAnyView()
        }
        switch relation {''')
edit('Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/Filters/List/PropertyFilterBuilder.swift',
'''        switch relationDetails.format {''',
'''        if TorahNativePropertyPresentation.definition(relationDetails.key) != nil {
            guard filter.condition.hasValues else { return nil }
            return TorahNativePropertyPresentation.value(
                definition: relationDetails,
                ids: filter.value.listValue.values.map(\\.stringValue)
            )
        }
        switch relationDetails.format {''')
edit('Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/Filters/Selection/List/SetFiltersContentViewBuilder.swift',
'''    ) -> AnyView {
        switch filter.conditionType {''',
'''    ) -> AnyView {
        if TorahNativePropertyPresentation.definition(filter.relationDetails.key) != nil {
            return TorahNativeFilterPickerView(
                spaceId: spaceId, key: filter.relationDetails.key,
                selected: selectedIds(from: filter.filter.value), onApply: onSelect
            ).eraseToAnyView()
        }
        switch filter.conditionType {''')
edit('Anytype/Sources/PresentationLayer/TextEditor/Set/Subscriptions/Set/SetSubscriptionDataBuilder.swift',
'''        return keys''',
'''        return TorahNativePropertyPresentation.subscriptionKeys(keys)''')
edit('Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/Sorts/List/SetSortsListViewModel.swift',
'''        let relationsDetails = setDocument.viewRelations(viewId: viewId, excludeRelations: excludeRelations)''',
'''        let relationsDetails = setDocument.viewRelations(viewId: viewId, excludeRelations: excludeRelations)
            .filter { TorahNativePropertyPresentation.supportsOrdering($0.key) }''')
edit('Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/RelationsSettings/GroupBy/SetViewSettingsGroupByViewModel.swift',
'''        relations.compactMap { relation in''',
'''        relations.filter { TorahNativePropertyPresentation.supportsOrdering($0.key) }.compactMap { relation in''')

args.output.mkdir(parents=True,exist_ok=True)
patch='';inventory=[]
for path,(before,after) in sorted(changes.items()):
    patch+='diff --git a/'+path+' b/'+path+'\n'
    patch+=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path))
    inventory.append(dict(path=path,before_sha256=hashlib.sha256(before.encode()).hexdigest(),after_sha256=hashlib.sha256(after.encode()).hexdigest()))
data=patch.encode('utf8')
(args.output/'native-ios-integration.patch').write_bytes(data)
head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
(args.output/'native-ios-integration.json').write_text(json.dumps(dict(app_base_sha=head,upstream_sha='e21834498cd6d8a85e91f69767caec793220a190',patch_sha256=hashlib.sha256(data).hexdigest(),status='PENDING_EXACT_OWNER_APPROVAL_NOT_APPLIED',files=inventory),indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(patch=str(args.output/'native-ios-integration.patch'),sha256=hashlib.sha256(data).hexdigest(),files=len(inventory))))
