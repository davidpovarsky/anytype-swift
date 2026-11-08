import Combine
import Services
import SwiftUI
import UIKit
import PinkhaKit

@MainActor
final class PinkhaDocumentMetadataRowModel: ObservableObject, SystemContentConfiguationProvider {
    nonisolated let blockId: String
    nonisolated var hashable: AnyHashable { blockId }
    @Published private(set) var relations: [Property]
    @Published private(set) var isEligible: Bool
    let session: TorahEditorSession
    let onRelationTap: (Property) -> Void
    private weak var document: (any BaseDocumentProtocol)?
    private var cancellables = Set<AnyCancellable>()

    init(document: some BaseDocumentProtocol, session: TorahEditorSession, onRelationTap: @escaping (Property) -> Void) {
        self.blockId = "PinkhaDocumentMetadataRow:\(document.spaceId):\(document.objectId)"
        self.document = document
        self.relations = document.featuredRelationsForEditor
        self.session = session
        self.onRelationTap = onRelationTap

        let typeId = document.details?.type ?? ""
        self.isEligible = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
            typeId: typeId, spaceId: document.spaceId
        )

        document.featuredRelationsForEditorPublisher
            .receiveOnMain()
            .removeDuplicates()
            .sink { [weak self] in self?.relations = $0 }
            .store(in: &cancellables)

        document.detailsPublisher
            .receiveOnMain()
            .sink { [weak self] details in
                guard let self else { return }
                let newEligible = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
                    typeId: details.type, spaceId: details.spaceId
                )
                if self.isEligible != newEligible {
                    self.isEligible = newEligible
                }
            }
            .store(in: &cancellables)

        NotificationCenter.default.publisher(for: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification)
            .receiveOnMain()
            .sink { [weak self] _ in
                guard let self, let doc = self.document else { return }
                let typeId = doc.details?.type ?? ""
                let newEligible = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
                    typeId: typeId, spaceId: doc.spaceId
                )
                if self.isEligible != newEligible {
                    self.isEligible = newEligible
                }
            }
            .store(in: &cancellables)
    }

    func makeContentConfiguration(maxWidth: CGFloat) -> any UIContentConfiguration {
        UIHostingConfiguration {
            PinkhaDocumentMetadataRowContent(model: self)
        }
        .minSize(height: 0)
        .margins(.vertical, 0)
        .margins(.horizontal, 20)
    }

    func didSelectRowInTableView(editorEditingState: EditorEditingState) { }

    static func insertionIndex(in items: [EditorItem]) -> Int? {
        guard !items.contains(where: { item in
            if case let .block(model) = item { return model.content == .featuredRelations }
            return item.blockId.hasPrefix("PinkhaDocumentMetadataRow:")
        }) else { return nil }
        let headerEnd = items.lastIndex { item in
            guard case let .block(model) = item, case let .text(text) = model.content else { return false }
            return text.contentType == .title || text.contentType == .description
        }
        return headerEnd.map { $0 + 1 } ?? 0
    }
}

private struct PinkhaDocumentMetadataRowContent: View {
    @ObservedObject var model: PinkhaDocumentMetadataRowModel

    var body: some View {
        EditorFeaturedPropertiesView(
            relations: model.relations,
            torahSession: model.session,
            isEligible: model.isEligible,
            onRelationTap: model.onRelationTap
        )
    }
}
