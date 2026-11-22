import Foundation
import SwiftUI
import Services

@MainActor
protocol PropertyInfoCoordinatorViewOutput: AnyObject {
    func didPressConfirm(_ relation: PropertyDetails)
}

@MainActor
@Observable
final class PropertyInfoCoordinatorViewModel: PropertyInfoModuleOutput {

    var propertyFormatsData: PropertyFormatsData?
    var searchData: ObjectTypesLimitedSearchData?
    
    let data: PropertyInfoData
    
    private weak var output: (any PropertyInfoCoordinatorViewOutput)?
    
    init(data: PropertyInfoData, output: (any PropertyInfoCoordinatorViewOutput)?) {
        self.data = data
        self.output = output
    }
    
    // MARK: - PropertyInfoModuleOutput
    
    func didAskToShowPropertyFormats(selectedFormat: SupportedPropertyFormat, onSelect: @escaping (SupportedPropertyFormat) -> Void) {
        if let scope = data.originalEditorScope {
            try? scope.withCurrent {
                propertyFormatsData = PropertyFormatsData(format: selectedFormat, onSelect: { format in
                    try? scope.withCurrent { onSelect(format) }
                })
            }
            return
        }
        propertyFormatsData = PropertyFormatsData(
            format: selectedFormat,
            onSelect: onSelect
        )
    }
    
    func didAskToShowObjectTypesSearch(selectedObjectTypesIds: [String], onSelect: @escaping ([String]) -> Void) {
        // This legacy search has its own unqualified subscription/tasks. The
        // prepared object-property increment does not activate that subroute.
        guard data.originalEditorScope == nil else { return }
        searchData = ObjectTypesLimitedSearchData(
            title: Loc.limitObjectTypes,
            spaceId: data.spaceId,
            selectedObjectTypesIds: selectedObjectTypesIds,
            onSelect: { ids in
                onSelect(ids)
            }
        )
    }
    
    func didPressConfirm(_ relation: PropertyDetails) {
        if let scope = data.originalEditorScope {
            try? scope.withActionCallback(requiredPermissions: OriginalEditorPropertyScope.listPermissions) {
                output?.didPressConfirm(relation)
            }
            return
        }
        output?.didPressConfirm(relation)
    }
    
}
