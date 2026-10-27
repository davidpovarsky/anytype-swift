import Foundation

/// Process-local evidence that an object belongs to Pinkha's registered writing types.
///
/// This cache never guesses from text, locale, or a generic Anytype layout. Entries are added
/// only from a bootstrapped manifest, from the Pinkha hierarchy built from that manifest, or
/// immediately after the Pinkha creation service successfully creates a registered type.
@MainActor
final class PinkhaDocumentIdentityStorage {
    static let shared = PinkhaDocumentIdentityStorage()

    private struct Key: Hashable {
        let objectId: String
        let spaceId: String
    }

    private var confirmed = Set<Key>()
    private var createdThisSession = Set<Key>()

    private init() {}

    func registerConfirmed(objectId: String, spaceId: String) {
        confirmed.insert(Key(objectId: objectId, spaceId: spaceId))
    }

    func registerCreated(objectId: String, spaceId: String) {
        let key = Key(objectId: objectId, spaceId: spaceId)
        confirmed.insert(key)
        createdThisSession.insert(key)
    }

    func isConfirmed(objectId: String, spaceId: String) -> Bool {
        confirmed.contains(Key(objectId: objectId, spaceId: spaceId))
    }

    func wasCreatedThisSession(objectId: String, spaceId: String) -> Bool {
        createdThisSession.contains(Key(objectId: objectId, spaceId: spaceId))
    }
}
