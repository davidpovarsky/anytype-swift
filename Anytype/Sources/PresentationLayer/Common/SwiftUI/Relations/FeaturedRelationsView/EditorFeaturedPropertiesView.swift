import SwiftUI

struct EditorFeaturedPropertiesView: View {
    let relations: [Property]
    let torahSession: TorahEditorSession?
    let onRelationTap: ((Property) -> Void)

    init(
        relations: [Property],
        torahSession: TorahEditorSession? = nil,
        onRelationTap: @escaping (Property) -> Void
    ) {
        self.relations = relations
        self.torahSession = torahSession
        self.onRelationTap = onRelationTap
    }

    var body: some View {
        if relations.isNotEmpty || torahSession != nil {
            content
        }
    }

    @ViewBuilder
    private var content: some View {
        if let torahSession {
            FeaturedPropertiesView(relations: relations, view: relationContent) {
                PinkhaDocumentSourcesFeaturedContent(session: torahSession)
            }
            .padding(.top, 8)
        } else {
            FeaturedPropertiesView(relations: relations, view: relationContent)
                .padding(.top, 8)
        }
    }

    private func relationContent(for relation: Property) -> some View {
        PropertyValueView(
            model: PropertyValueViewModel(
                property:  PropertyItemModel(property: relation),
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
