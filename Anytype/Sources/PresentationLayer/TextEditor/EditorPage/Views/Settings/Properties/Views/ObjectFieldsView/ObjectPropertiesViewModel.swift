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
    private var latestParsedProperties = ParsedProperties.empty

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
        NotificationCenter.default.addObserver(
            forName: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let self else { return }
            let notifiedSpace = notification.userInfo?["spaceId"] as? String
            if notifiedSpace == nil || notifiedSpace == self.document.spaceId {
                self.rebuildSections(from: self.latestParsedProperties)
            }
        }

        for await properties in document.parsedPropertiesPublisher.values {
            latestParsedProperties = properties
            rebuildSections(from: properties)
        }
    }

    private func rebuildSections(from properties: ParsedProperties) {
        let isEligible = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
            typeId: document.details?.type ?? "", spaceId: document.spaceId
        )
        let rawSections = sectionsBuilder.buildObjectSections(parsedProperties: properties)
        sections = rawSections.compactMap { section in
            let filtered = section.relations.filter { relation in
                if PinkhaTorahPropertyPolicy.shared.isInternalProperty(
                    propertyId: relation.id, key: relation.key, spaceId: document.spaceId
                ) {
                    return false
                }
                if TorahNativePropertyDefinition.definition(for: relation.key) != nil && !isEligible {
                    return false
                }
                return true
            }
            guard !filtered.isEmpty else { return nil }
            return PropertiesSection(
                id: section.id,
                title: section.title,
                relations: filtered,
                isMissingFields: section.isMissingFields,
                isExpandable: section.isExpandable
            )
        }
    }
    
    func handleTapOnRelation(_ relation: Property) {
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: relation.id, key: relation.key, spaceId: document.spaceId
        ) else { return }
        output?.editRelationValueAction(document: document, relationKey: relation.key)
    }
    
    func removeRelation(_ relation: Property) {
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
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
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
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

    func revealHiddenRelation(_ relation: Property) {
        guard let details = document.details else { return }
        guard !PinkhaTorahPropertyPolicy.shared.isInternalProperty(
            propertyId: relation.id, key: relation.key, spaceId: details.spaceId
        ) else { return }
        if TorahNativePropertyDefinition.definition(for: relation.key) != nil {
            guard PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(typeId: details.objectType.id, spaceId: details.spaceId) else { return }
        }

        Task {
            let relationsDetail = try propertyDetailsStorage.relationsDetails(key: relation.key, spaceId: details.spaceId)
            try await propertiesService.revealTypeHiddenProperty(type: details.objectType, property: relationsDetail)
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
