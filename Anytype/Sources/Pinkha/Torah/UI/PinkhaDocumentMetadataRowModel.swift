import Combine
import Services
import SwiftUI
import UIKit

@MainActor
final class PinkhaDocumentMetadataRowModel: ObservableObject, SystemContentConfiguationProvider {
    nonisolated let blockId: String
    nonisolated var hashable: AnyHashable { blockId }
    @Published private(set) var relations: [Property]
    let session: TorahEditorSession
    let onRelationTap: (Property) -> Void
    private var subscription: AnyCancellable?

    init(document: some BaseDocumentProtocol, session: TorahEditorSession, onRelationTap: @escaping (Property) -> Void) {
        blockId = "PinkhaDocumentMetadataRow:\(document.spaceId):\(document.objectId)"
        relations = document.featuredRelationsForEditor
        self.session = session
        self.onRelationTap = onRelationTap
        subscription = document.featuredRelationsForEditorPublisher
            .receiveOnMain()
            .removeDuplicates()
            .sink { [weak self] in self?.relations = $0 }
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
            onRelationTap: model.onRelationTap
        )
    }
}
