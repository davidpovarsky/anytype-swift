import TorahInspectorCore

@MainActor
public enum TorahInspectorRepositoryFactory {
    public static func make(
        workspace: AnytypeTorahWorkspace,
        documentCapacity: Int = 30,
        relationshipCapacity: Int = 50
    ) -> TorahInspectorRepository {
        TorahInspectorRepository(
            documentCapacity: documentCapacity,
            relationshipCapacity: relationshipCapacity,
            textFetcher: { reference, providerID in
                try await workspace.fetchSectionText(
                    reference: reference,
                    providerID: providerID
                )
            },
            linksFetcher: { reference, providerID in
                try await workspace.links(for: reference, providerID: providerID)
            },
            topicsFetcher: { reference, providerID in
                try await workspace.topics(for: reference, providerID: providerID)
            },
            notesFetcher: { _ in [] }
        )
    }
}
