import Foundation
import Services
import SwiftProtobuf
import UIKit
import AnytypeCore
import SwiftUI
import PinkhaKit

@MainActor
@Observable
final class ObjectPropertiesViewModel {
    var sections = [PropertiesSection]()
    var showConflictingInfo = false
    var expandedSections = Set<String>()

    var typeId: String? { document.details?.objectType.id }

    var shouldShowEmptyState: Bool {
        guard let firstSection = sections.first else { return true }
        return firstSection.id != PropertiesSection.Constants.featuredPropertiesSectionId
    }

    // MARK: - Private variables

    @ObservationIgnored
    private let document: any BaseDocumentProtocol
    @ObservationIgnored
    private let sectionsBuilder = PropertiesSectionBuilder()

    @ObservationIgnored
    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol
    @ObservationIgnored
    @Injected(\.propertyDetailsStorage)
    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol
    @ObservationIgnored
    @Injected(\.documentsProvider)
    private var documentsProvider: any DocumentsProviderProtocol

    @ObservationIgnored
    private weak var output: (any PropertiesListModuleOutput)?
    
    // MARK: - Initializers
    
    init(
        document: some BaseDocumentProtocol,
        output: (any PropertiesListModuleOutput)?
    ) {
        self.document = document
        self.output = output
    }
    
    func setupSubscriptions() async {
        for await properties in document.parsedPropertiesPublisher.values {
            sections = sectionsBuilder.buildObjectSections(parsedProperties: properties)
        }
    }
    
    func handleTapOnRelation(_ relation: Property) {
        guard !PinkhaTorahPropertyPolicy.shared.isCanonicalStorage(
            propertyId: relation.id, key: relation.key, spaceId: document.spaceId
        ) else { return }
        output?.editRelationValueAction(document: document, relationKey: relation.key)
    }
    
    func removeRelation(_ relation: Property) {
        guard !PinkhaTorahPropertyPolicy.shared.isCanonicalStorage(
            propertyId: relation.id, key: relation.key, spaceId: document.spaceId
        ) else { return }
        let isNative = TorahNativePropertyDefinition.definition(for: relation.key) != nil
        if isNative, let typeId = typeId, PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(typeId: typeId, spaceId: document.spaceId) {
            return
        }

        Task {
            try await propertiesService.removeProperty(objectId: document.objectId, propertyKey: relation.key)
            let relationDetails = try propertyDetailsStorage.relationsDetails(key: relation.key, spaceId: document.spaceId)
            AnytypeAnalytics.instance().logDeleteRelation(format: relationDetails.format, key: relationDetails.analyticsKey, route: .object)
        }
    }
    
    func onEditTap() {
        guard let typeId else { return }
        output?.showTypeRelationsView(typeId: typeId)
    }
    
    func addRelationToType(_ relation: Property) {
        guard let details = document.details else { return }
        guard !PinkhaTorahPropertyPolicy.shared.isCanonicalStorage(
            propertyId: relation.id, key: relation.key, spaceId: details.spaceId
        ) else { return }
        if TorahNativePropertyDefinition.definition(for: relation.key) != nil {
            guard PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(typeId: details.objectType.id, spaceId: details.spaceId) else { return }
        }

        AnytypeAnalytics.instance().logAddConflictRelation()
        
        Task {
            let relationsDetail = try propertyDetailsStorage.relationsDetails(key: relation.key, spaceId: details.spaceId)
            try await propertiesService.addTypeRecommendedProperty(type: details.objectType, property: relationsDetail)
        }
    }
    
    func onConflictingInfoTap() {
        AnytypeAnalytics.instance().logConflictFieldHelp()
        showConflictingInfo.toggle()
    }
    
    func toggleSectionExpansion(_ sectionId: String) {
        withAnimation(.fastSpring) {
            if expandedSections.contains(sectionId) {
                expandedSections.remove(sectionId)
            } else {
                expandedSections.insert(sectionId)
            }
        }
    }
    
    func isSectionExpanded(_ sectionId: String) -> Bool {
        expandedSections.contains(sectionId)
    }
}
