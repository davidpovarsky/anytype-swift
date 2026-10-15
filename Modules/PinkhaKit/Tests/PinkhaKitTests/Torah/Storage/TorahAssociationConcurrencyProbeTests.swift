import Testing
@testable import PinkhaKit

@Suite("Torah association adversarial storage probe")
struct TorahAssociationConcurrencyProbeTests {
    @Test("Two stale JSON read-modify-write additions lose one association")
    func staleScalarReplacementLosesConcurrentAdd() {
        let location = TorahAssociationLocation(spaceId: "space", target: .object(objectId: "document"))
        let old: [TorahAssociationItem] = []
        let clientA = TorahAssociationCollectionPolicy.adding(item("A"), to: old, location: location)
        let clientB = TorahAssociationCollectionPolicy.adding(item("B"), to: old, location: location)

        // Heart's ObjectSetDetails and BlockSetFields ultimately replace one scalar value.
        // If B is the later scalar winner, A cannot be reconstructed from either payload.
        let persistedLastWriter = clientB
        #expect(clientA.map(\.id) == ["A"])
        #expect(clientB.map(\.id) == ["B"])
        #expect(persistedLastWriter.map(\.id) == ["B"])
        #expect(!persistedLastWriter.contains(where: { $0.id == "A" }))
    }

    @Test("Deprecated snapshot entry points fail visibly")
    func staleSnapshotAPIsThrow() async {
        let repository = ProbeRepository()
        do {
            try await repository.setDocumentAssociations(objectId: "document", items: [], spaceId: "space")
            Issue.record("Document snapshot replacement unexpectedly succeeded")
        } catch let error as TorahAssociationRepositoryError {
            #expect(error == .unsafeSnapshotReplacement)
        } catch {
            Issue.record("Unexpected error: \(error)")
        }

        do {
            try await repository.setBlockAssociations(
                objectId: "document",
                blockId: "block",
                items: [],
                spaceId: "space"
            )
            Issue.record("Block snapshot replacement unexpectedly succeeded")
        } catch let error as TorahAssociationRepositoryError {
            #expect(error == .unsafeSnapshotReplacement)
        } catch {
            Issue.record("Unexpected error: \(error)")
        }
    }

    private func item(_ id: String) -> TorahAssociationItem {
        TorahAssociationItem(
            id: id,
            kind: .ref,
            role: .context,
            providerID: "sefaria",
            externalID: id,
            canonicalKey: id,
            labelHe: id,
            labelEn: id
        )
    }
}

private actor ProbeRepository: TorahAssociationRepository {
    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] { [] }
    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] { [] }
    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem { item }
    func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem { item }
    func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem { item }
    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws {}
}
