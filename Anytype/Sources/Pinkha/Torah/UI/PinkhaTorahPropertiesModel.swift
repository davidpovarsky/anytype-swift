import AnytypeCore
import Combine
import Foundation
import Factory
import Observation
import PinkhaKit
import Services

@MainActor
@Observable
final class PinkhaTorahPropertiesModel {
    let session: TorahEditorSession?
    private(set) var isEligible = false
    private(set) var canEdit = false
    private(set) var manifestResolutionError: String?
    private var identityStatus: InternalIdentityStatus = .loading
    private var manifest: PinkhaSpaceManifest?
    private let document: any BaseDocumentProtocol
    private let bootstrap: any PinkhaSpaceBootstrapServiceProtocol
    private let policy: PinkhaTorahPropertyPolicy

    var isResolvingManifest: Bool {
        guard PinkhaRuntime.enabled, !document.spaceId.isEmpty else { return false }
        if manifest != nil { return false }
        if case .loading = identityStatus { return true }
        return false
    }
    var usesNativeProperties: Bool {
        document.details?.intValue(for: TorahNativePropertyDefinition.engineVersionKey) == TorahNativePropertyDefinition.engineVersion
    }
    var showsLegacyProjectionRows: Bool {
        #if PINKHA_NATIVE_DERIVED
        false
        #else
        !usesNativeProperties
        #endif
    }

    init(
        document: some BaseDocumentProtocol,
        session: TorahEditorSession?,
        bootstrap: any PinkhaSpaceBootstrapServiceProtocol = Container.shared.pinkhaBootstrapService(),
        policy: PinkhaTorahPropertyPolicy = .shared
    ) {
        self.document = document
        self.session = session.flatMap {
            $0.spaceId == document.spaceId && $0.objectId == document.objectId ? $0 : nil
        }
        self.bootstrap = bootstrap
        self.policy = policy
        update()
    }

    func observeDocument() async {
        update()
        if let session { await session.refreshAssociationSnapshot() }
        if manifest == nil {
            _ = await policy.awaitInternalIdentity(spaceId: document.spaceId)
        }
        update()
        let identityNotifications = NotificationCenter.default.notifications(
            named: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification
        )
        await withTaskGroup(of: Void.self) { group in
            group.addTask { @MainActor [weak self] in
                guard let self else { return }
                for await _ in self.document.syncPublisher.values {
                    guard !Task.isCancelled else { return }
                    self.update()
                }
            }
            group.addTask { @MainActor [weak self] in
                guard let self else { return }
                for await notification in identityNotifications {
                    guard !Task.isCancelled else { return }
                    if let notifiedSpace = notification.userInfo?["spaceId"] as? String,
                       notifiedSpace != self.document.spaceId {
                        continue
                    }
                    self.update()
                }
            }
        }
    }

    func visibleSections(_ sections: [PropertiesSection]) -> [PropertiesSection] {
        guard !isResolvingManifest else { return [] }
        return sections.compactMap { section in
            let relations = section.relations.filter { !isInternalProperty($0) }
            guard !relations.isEmpty else { return nil }
            return PropertiesSection(
                id: section.id, title: section.title, relations: relations,
                isMissingFields: section.isMissingFields, isExpandable: section.isExpandable
            )
        }
    }

    func isInternalProperty(_ property: Property) -> Bool {
        guard PinkhaRuntime.enabled else { return false }
        if TorahDocumentPropertyEligibility.isInternalProperty(
            id: property.id, key: property.key, spaceId: document.spaceId, manifest: manifest
        ) { return true }
        return policy.isInternalProperty(
            propertyId: property.id, key: property.key, spaceId: document.spaceId
        )
    }

    func edit(_ kind: TorahAssociationKind) {
        update()
        guard isEligible, canEdit, let session else { return }
        let category: TorahEditorSession.SearchScope = switch kind {
        case .ref: .references
        case .topic: .topics
        case .word: .words
        }
        session.presentSearch(scope: .document, initialCategory: category, host: .properties)
    }

    func reloadManifest() async {
        policy.retryIdentityResolution(spaceId: document.spaceId)
        _ = await policy.awaitInternalIdentity(spaceId: document.spaceId)
        await session?.refreshAssociationSnapshot()
        update()
    }

    private func update() {
        session?.installAssociationEditingPolicy { [weak document] in
            guard let document else { return false }
            return document.permissions.canEditRelationValues && document.details?.isReadonly == false
        }
        manifest = bootstrap.manifest(forSpaceId: document.spaceId)
        identityStatus = policy.internalIdentityStatus(spaceId: document.spaceId)
        if case .unavailable(let reason) = identityStatus {
            manifestResolutionError = reason
        } else {
            manifestResolutionError = nil
        }
        isEligible = PinkhaRuntime.enabled && session != nil && TorahDocumentPropertyEligibility.includes(
            typeId: document.details?.type ?? "", spaceId: document.spaceId, manifest: manifest
        )
        canEdit = document.permissions.canEditRelationValues && document.details?.isReadonly == false
    }
}
