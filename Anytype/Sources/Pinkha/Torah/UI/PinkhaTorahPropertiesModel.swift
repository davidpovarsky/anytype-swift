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
    private var manifest: PinkhaSpaceManifest?
    private let document: any BaseDocumentProtocol
    private let bootstrap: any PinkhaSpaceBootstrapServiceProtocol

    var isResolvingManifest: Bool { PinkhaRuntime.enabled && session != nil && manifest == nil }

    init(
        document: some BaseDocumentProtocol,
        session: TorahEditorSession?,
        bootstrap: any PinkhaSpaceBootstrapServiceProtocol = Container.shared.pinkhaBootstrapService()
    ) {
        self.document = document
        self.session = session.flatMap {
            $0.spaceId == document.spaceId && $0.objectId == document.objectId ? $0 : nil
        }
        self.bootstrap = bootstrap
        update()
    }

    func observeDocument() async {
        update()
        if let session { await session.refreshAssociationSnapshot() }
        update()
        for await _ in document.syncPublisher.values {
            guard !Task.isCancelled else { return }
            update()
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
        return TorahDocumentPropertyEligibility.isCanonicalProperty(
            id: property.id, key: property.key, spaceId: document.spaceId, manifest: manifest
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
        await session?.refreshAssociationSnapshot()
        update()
    }

    private func update() {
        session?.installAssociationEditingPolicy { [weak document] in
            guard let document else { return false }
            return document.permissions.canEditRelationValues && document.details?.isReadonly == false
        }
        manifest = bootstrap.manifest(forSpaceId: document.spaceId)
        isEligible = PinkhaRuntime.enabled && session != nil && TorahDocumentPropertyEligibility.includes(
            typeId: document.details?.type ?? "", spaceId: document.spaceId, manifest: manifest
        )
        canEdit = document.permissions.canEditRelationValues && document.details?.isReadonly == false
    }
}
