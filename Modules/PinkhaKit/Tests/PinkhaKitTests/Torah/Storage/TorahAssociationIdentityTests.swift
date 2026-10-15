import Foundation
import Testing
@testable import PinkhaKit

@Suite("Torah association identity and collection policy")
struct TorahAssociationIdentityTests {
    @Test("Identity is isolated by Space, document, and block")
    func targetIsolation() {
        let item = association(id: "same", role: .context)
        let documentA = TorahAssociationIdentity(
            item: item,
            location: .init(spaceId: "space-a", target: .object(objectId: "document"))
        )
        let documentB = TorahAssociationIdentity(
            item: item,
            location: .init(spaceId: "space-a", target: .object(objectId: "other"))
        )
        let otherSpace = TorahAssociationIdentity(
            item: item,
            location: .init(spaceId: "space-b", target: .object(objectId: "document"))
        )
        let blockA = TorahAssociationIdentity(
            item: item,
            location: .init(spaceId: "space-a", target: .block(objectId: "document", blockId: "block-a"))
        )
        let blockB = TorahAssociationIdentity(
            item: item,
            location: .init(spaceId: "space-a", target: .block(objectId: "document", blockId: "block-b"))
        )

        #expect(documentA != documentB)
        #expect(documentA != otherSpace)
        #expect(documentA != blockA)
        #expect(blockA != blockB)
        #expect(documentA.storageKey == TorahAssociationIdentity(
            item: item,
            location: .init(spaceId: "space-a", target: .object(objectId: "document"))
        ).storageKey)
    }

    @Test("Context duplicate preserves stable ID and original creation time")
    func contextDeduplication() {
        let location = TorahAssociationLocation(spaceId: "space", target: .object(objectId: "document"))
        let created = Date(timeIntervalSince1970: 100)
        let existing = association(id: "stable", role: .context, label: "Old", createdAt: created)
        let retryWithNewClientID = association(id: "different", role: .context, label: "New", createdAt: nil)

        let result = TorahAssociationCollectionPolicy.upserting(
            retryWithNewClientID,
            into: [existing],
            location: location
        )

        #expect(result.count == 1)
        #expect(result[0].id == "stable")
        #expect(result[0].labelEn == "New")
        #expect(result[0].createdAt == created)
    }

    @Test("Same quote operation is idempotent while distinct excerpts remain distinct")
    func quoteInstances() {
        let location = TorahAssociationLocation(
            spaceId: "space",
            target: .block(objectId: "document", blockId: "block")
        )
        let quoteA = association(id: "quote-a", role: .sourceQuote, label: "A")
        let quoteB = association(id: "quote-b", role: .sourceQuote, label: "B")

        let once = TorahAssociationCollectionPolicy.adding(quoteA, to: [], location: location)
        let retried = TorahAssociationCollectionPolicy.adding(quoteA, to: once, location: location)
        let distinct = TorahAssociationCollectionPolicy.adding(quoteB, to: retried, location: location)

        #expect(once.count == 1)
        #expect(retried.count == 1)
        #expect(distinct.map(\.id) == ["quote-a", "quote-b"])
    }

    @Test("Update requires an existing stable ID and remove touches only that ID")
    func updateAndRemove() throws {
        let first = association(id: "a", role: .context, label: "A")
        let second = association(id: "b", role: .context, label: "B", canonical: "Exodus 1:1")
        let changed = association(id: "a", role: .context, label: "Changed")
        let updated = try TorahAssociationCollectionPolicy.updating(changed, in: [first, second])
        let removed = TorahAssociationCollectionPolicy.removing(id: "a", from: updated)

        #expect(updated.first(where: { $0.id == "a" })?.labelEn == "Changed")
        #expect(removed == [second])

        do {
            _ = try TorahAssociationCollectionPolicy.updating(
                association(id: "missing", role: .context),
                in: updated
            )
            Issue.record("Missing association unexpectedly updated")
        } catch let error as TorahAssociationRepositoryError {
            #expect(error == .associationNotFound("missing"))
        }
    }

    private func association(
        id: String,
        role: TorahAssociationRole,
        label: String = "Genesis 1:1",
        createdAt: Date? = nil,
        canonical: String = "Genesis 1:1"
    ) -> TorahAssociationItem {
        TorahAssociationItem(
            id: id,
            kind: .ref,
            role: role,
            providerID: "sefaria",
            externalID: canonical.replacingOccurrences(of: " ", with: "."),
            canonicalKey: canonical,
            labelHe: "בראשית א:א",
            labelEn: label,
            createdAt: createdAt
        )
    }
}
