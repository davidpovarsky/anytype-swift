import SwiftUI
import PinkhaKit

struct EditorFeaturedPropertiesView: View {
    let relations: [Property]
    let torahSession: TorahEditorSession?
    let isEligible: Bool
    let onRelationTap: ((Property) -> Void)

    init(
        relations: [Property],
        torahSession: TorahEditorSession? = nil,
        isEligible: Bool = false,
        onRelationTap: @escaping (Property) -> Void
    ) {
        self.relations = relations
        self.torahSession = torahSession
        self.isEligible = isEligible
        self.onRelationTap = onRelationTap
    }

    private var isSourcesHeaderActive: Bool {
        guard let torahSession, isEligible else { return false }
        return torahSession.documentPropertyProjection.sources.isNotEmpty
            || torahSession.canEditAssociations
    }

    private var filteredRelations: [Property] {
        relations.filter { relation in
            // Canonical storage must never appear in featured header
            if let torahSession, PinkhaTorahPropertyPolicy.shared.isCanonicalStorage(
                propertyId: relation.id, key: relation.key, spaceId: torahSession.spaceId
            ) {
                return false
            }
            // When custom source header is actively presenting sources, avoid duplicate presentation of native sources
            if isSourcesHeaderActive && relation.key == TorahNativePropertyDefinition.all[0].key {
                return false
            }
            return true
        }
    }

    private var hasSourcesContent: Bool {
        isSourcesHeaderActive
    }

    var body: some View {
        if filteredRelations.isNotEmpty || hasSourcesContent {
            content
        }
    }

    @ViewBuilder
    private var content: some View {
        if let torahSession, hasSourcesContent {
            FeaturedPropertiesView(
                relations: filteredRelations,
                view: relationContent,
                hasTrailingContent: filteredRelations.isNotEmpty
            ) {
                PinkhaDocumentSourcesFeaturedContent(session: torahSession)
            }
            .padding(.top, 8)
        } else if filteredRelations.isNotEmpty {
            FeaturedPropertiesView(
                relations: filteredRelations,
                view: relationContent,
                hasTrailingContent: false
            ) {
                EmptyView()
            }
            .padding(.top, 8)
        }
    }

    private func relationContent(for relation: Property) -> some View {
        PropertyValueView(
            model: PropertyValueViewModel(
                property: PropertyItemModel(property: relation),
                style: .featuredBlock(
                    FeaturedPropertySettings(
                        allowMultiLine: false,
                        error: PropertyItemModel(property: relation).isErrorState,
                        links: relation.links
                    )
                ),
                mode: .button(action: { onRelationTap(relation) })
            )
        )
    }
}
