import SwiftUI
import Services

struct PropertiesSearchData: Identifiable {
    let id = UUID()
    let objectId: String
    let spaceId: String
    let excludedRelationsIds: [String]
    let hiddenRelationsIds: Set<String>
    let target: PropertiesModuleTarget
    let originalEditorScope: OriginalEditorPropertyScope?
    @EquatableNoop
    var onRelationSelect: (_ relationDetails: PropertyDetails, _ isNew: Bool) -> Void

    init(
        objectId: String,
        spaceId: String,
        excludedRelationsIds: [String],
        hiddenRelationsIds: Set<String> = [],
        target: PropertiesModuleTarget,
        originalEditorScope: OriginalEditorPropertyScope? = nil,
        onRelationSelect: @escaping (_ relationDetails: PropertyDetails, _ isNew: Bool) -> Void
    ) {
        self.objectId = objectId
        self.spaceId = spaceId
        self.excludedRelationsIds = excludedRelationsIds
        self.hiddenRelationsIds = hiddenRelationsIds
        self.target = target
        self.originalEditorScope = originalEditorScope
        self.onRelationSelect = onRelationSelect
    }
}
