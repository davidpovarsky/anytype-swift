import SwiftUI
import Services
import AnytypeCore
import PinkhaKit


@MainActor
@Observable
final class PropertyCreationViewModel: PropertyInfoCoordinatorViewOutput {

    var rows: [SearchDataSection<PropertySearchData>] = []
    var newPropertyData: PropertyInfoData?
    var nativeLookupFailed = false
    var existingLookupFailed = false
    var isSearching = true
    var hasLookupFailure: Bool { nativeLookupFailed || existingLookupFailed }
    private var lastSearchText = ""
    private var activeSearch: UUID?

    @ObservationIgnored
    private let searchLoader: any PinkhaPropertyPickerSearchLoading

    @ObservationIgnored
    var dismiss: DismissAction?

    @ObservationIgnored
    @Injected(\.workspaceService)
    private var workspaceService: any WorkspaceServiceProtocol
    @ObservationIgnored
    @Injected(\.dataviewService)
    private var dataviewService: any DataviewServiceProtocol
    @ObservationIgnored
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol
    @ObservationIgnored
    @Injected(\.objectActionsService)
    private var objectActionsService: any ObjectActionsServiceProtocol

    @ObservationIgnored
    private let data: PropertiesSearchData
    @ObservationIgnored
    @Injected(\.propertyDetailsStorage)
    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol
    
    init(data: PropertiesSearchData, searchLoader: (any PinkhaPropertyPickerSearchLoading)? = nil) {
        self.data = data
        self.searchLoader = searchLoader ?? PinkhaPropertyPickerSearchLoader()
    }

    func isInstalledButHidden(_ relationId: String) -> Bool {
        data.hiddenRelationsIds.contains(relationId)
    }
    
    func search(text: String) async {
        guard !Task.isCancelled else { return }
        let request = UUID()
        activeSearch = request
        lastSearchText = text
        isSearching = true
        nativeLookupFailed = false
        existingLookupFailed = false
        rows = makeRows(text: text, properties: [])
        defer {
            // A cancelled query has no authoritative empty result to display.
            if activeSearch == request && !Task.isCancelled { isSearching = false }
        }

        do {
            let result = try await searchLoader.load(text: text, data: data)
            guard activeSearch == request, !Task.isCancelled else { return }
            nativeLookupFailed = result.nativeLookupFailed
            existingLookupFailed = result.existingLookupFailed
            rows = makeRows(text: text, properties: result.properties)
        } catch is CancellationError {
            return
        } catch {
            guard activeSearch == request, !Task.isCancelled else { return }
            existingLookupFailed = true
        }
    }

    private func makeRows(text: String, properties: [PropertyDetails]) -> [SearchDataSection<PropertySearchData>] {
        let formats = SupportedPropertyFormat.allCases.filter {
            text.isEmpty || $0.title.localizedCaseInsensitiveContains(text)
        }
        return .builder {
            if formats.isNotEmpty {
                SearchDataSection(
                    searchData: formats.map { PropertySearchData.new($0) },
                    sectionName: Loc.propertiesFormats
                )
            }
            if properties.isNotEmpty {
                SearchDataSection(
                    searchData: properties.map { PropertySearchData.existing($0) },
                    sectionName: Loc.existingProperties
                )
            }
        }
    }
    
    func retryNativeLookup() async {
        searchLoader.invalidate(spaceId: data.spaceId)
        await search(text: lastSearchText)
    }

    func onRowTap(_ row: PropertySearchData) {
        Task {
            switch row {
            case .existing(let details):
                guard await PinkhaTorahPropertyPolicy.shared.canAddPropertyAsync(
                    propertyId: details.id, key: details.key, target: data.target, spaceId: data.spaceId
                ) else { return }
                try await onExistingPropertyTap(details)
                try? await objectActionsService.updateBundledDetails(contextID: details.id, details: [ .lastUsedDate(Date.now)])
                
                data.onRelationSelect(details, false) // isNew = false
                dismiss?()
            case .new(let format):
                newPropertyData = PropertyInfoData(
                    name: "",
                    objectId: data.objectId,
                    spaceId: data.spaceId,
                    target: data.target,
                    mode: .create(format: format),
                    isReadOnly: false
                )
            }
        }
    }
    
    func onNewPropertyTap(name: String) {
        newPropertyData = PropertyInfoData(
            name: name,
            objectId: data.objectId,
            spaceId: data.spaceId,
            target: data.target,
            mode: .create(format: .text),
            isReadOnly: false
        )
    }
    
    // MARK: - PropertyInfoCoordinatorViewOutput
    func didPressConfirm(_ relation: PropertyDetails) {
        data.onRelationSelect(relation, true) // isNew = true
        dismiss?()
    }
    
    // MARK: - Private
    
    private func onExistingPropertyTap(_ details: PropertyDetails) async throws {
        switch data.target {
        case let .type(typeData):
            try await addPropertyToType(relation: details, typeData: typeData)
        case let .dataview(objectId, activeViewId, typeDetails):
            try await addPropertyToDataview(objectId: objectId, relation: details, activeViewId: activeViewId, typeDetails: typeDetails)
        case .object(let objectId):
            try await addPropertyToObject(objectId: objectId, relation: details)
        case .library:
            break
        }
    }
    
    private func addPropertyToType(relation: PropertyDetails, typeData: PropertiesModuleTypeData) async throws {
        if isInstalledButHidden(relation.id) {
            switch typeData {
            case .recommendedFeaturedRelations(let type):
                try await propertiesService.revealTypeHiddenProperty(type: type, property: relation, featured: true)
            case .recommendedRelations(let type):
                try await propertiesService.revealTypeHiddenProperty(type: type, property: relation, featured: false)
            }
            return
        }
        switch typeData {
        case .recommendedFeaturedRelations(let type):
            try await propertiesService.addTypeFeaturedRecommendedProperty(type: type, property: relation)
        case .recommendedRelations(let type):
            try await propertiesService.addTypeRecommendedProperty(type: type, property: relation)
        }
    }
    
    private func addPropertyToDataview(objectId: String, relation: PropertyDetails, activeViewId: String, typeDetails: ObjectDetails?) async throws {
        let doc = Container.shared.openedDocumentProvider().document(objectId: objectId, spaceId: data.spaceId)
        let dataviewBlock: BlockDataview? = {
            guard let blockInfo = doc.infoContainer.get(id: SetConstants.dataviewBlockId),
                  case .dataView(let dv) = blockInfo.content else {
                return nil
            }
            return dv
        }()
        let alreadyInDataviewLinks = dataviewBlock?.relationLinks.contains(where: { $0.key == relation.key }) ?? false
        let activeView = dataviewBlock?.views.first(where: { $0.id == activeViewId })
        let alreadyInViewOptions = activeView?.options.contains(where: { $0.key == relation.key }) ?? false

        if !isInstalledButHidden(relation.id) && !alreadyInDataviewLinks {
            if let typeDetails {
                let type = ObjectType(details: typeDetails)
                try await addPropertyToType(relation: relation, typeData: .recommendedRelations(type))
            } else {
                try await dataviewService.addRelation(objectId: objectId, blockId: SetConstants.dataviewBlockId, relationDetails: relation)
            }
        } else if let typeDetails, isInstalledButHidden(relation.id) {
            let type = ObjectType(details: typeDetails)
            if type.recommendedHiddenRelations.contains(relation.id) {
                try await propertiesService.revealTypeHiddenProperty(type: type, property: relation, featured: false)
            }
        }
        
        let visibleOption = DataviewRelationOption(key: relation.key, isVisible: true).asMiddleware
        if alreadyInViewOptions {
            try await dataviewService.replaceViewRelation(
                objectId: objectId,
                blockId: SetConstants.dataviewBlockId,
                key: relation.key,
                with: visibleOption,
                viewId: activeViewId
            )
        } else {
            try await dataviewService.addViewRelation(
                objectId: objectId,
                blockId: SetConstants.dataviewBlockId,
                relation: visibleOption,
                viewId: activeViewId
            )
        }
    }
    
    func addPropertyToObject(objectId: String, relation: PropertyDetails) async throws {
        try await propertiesService.addProperties(objectId: objectId, propertiesDetails: [relation])
    }
}
