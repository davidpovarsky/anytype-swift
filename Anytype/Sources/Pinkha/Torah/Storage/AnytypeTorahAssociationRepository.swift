import Foundation
import PinkhaKit

/// Native Anytype association repository for the deliberately bounded
/// single-active-writer track. Canonical data remains one native document
/// property; full multi-client T2 remains independently blocked.
protocol AnytypeTorahAssociationSnapshotRepository: TorahAssociationRepository {
    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord]
}

final class AnytypeTorahAssociationRepository: AnytypeTorahAssociationSnapshotRepository, @unchecked Sendable {
    private struct LoadedDocument: Sendable {
        let manifest: PinkhaSpaceManifest
        let snapshot: TorahAssociationNativeDocumentSnapshot
        let payload: TorahCanonicalAssociationsPayload
    }

    private enum Mutation: Sendable {
        case add(TorahAssociationItem)
        case upsert(TorahAssociationItem)
        case update(TorahAssociationItem)
        case remove(String)

        var operationId: String {
            switch self {
            case .add(let item): "add:\(item.id)"
            case .upsert(let item): "upsert:\(item.id)"
            case .update(let item): "update:\(item.id)"
            case .remove(let id): "remove:\(id)"
            }
        }
    }

    private let nativeStore: any TorahAssociationNativeStore
    private let manifestProvider: any TorahAssociationManifestProvider
    private let coordinator: TorahAssociationMutationCoordinator
    private let statusCenter: TorahAssociationPersistenceStatusCenter
    private let codec: TorahAssociationPayloadCodec

    init(
        nativeStore: any TorahAssociationNativeStore = MiddlewareTorahAssociationNativeStore(),
        manifestProvider: any TorahAssociationManifestProvider = BootstrapTorahAssociationManifestProvider(),
        coordinator: TorahAssociationMutationCoordinator = .shared,
        statusCenter: TorahAssociationPersistenceStatusCenter = .shared,
        codec: TorahAssociationPayloadCodec = TorahAssociationPayloadCodec()
    ) {
        self.nativeStore = nativeStore
        self.manifestProvider = manifestProvider
        self.coordinator = coordinator
        self.statusCenter = statusCenter
        self.codec = codec
    }

    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        try await list(location: .init(spaceId: spaceId, target: .object(objectId: objectId)))
    }

    func listBlockAssociations(
        objectId: String,
        blockId: String,
        spaceId: String
    ) async throws -> [TorahAssociationItem] {
        try await list(
            location: .init(
                spaceId: spaceId,
                target: .block(objectId: objectId, blockId: blockId)
            )
        )
    }

    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord] {
        let location = TorahAssociationLocation(
            spaceId: spaceId,
            target: .object(objectId: objectId)
        )
        let key = documentKey(for: location)
        return try await coordinator.enqueue(key: key) { [self] in
            try await load(location: location, requiresWrite: false).payload.records
        }
    }

    func addAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws -> TorahAssociationItem {
        try await mutate(.add(item), location: .init(spaceId: spaceId, target: target)) ?? item
    }

    func upsertAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws -> TorahAssociationItem {
        try await mutate(.upsert(item), location: .init(spaceId: spaceId, target: target)) ?? item
    }

    func updateAssociation(
        _ item: TorahAssociationItem,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws -> TorahAssociationItem {
        try await mutate(.update(item), location: .init(spaceId: spaceId, target: target)) ?? item
    }

    func removeAssociation(
        associationId: String,
        target: TorahAssociationTarget,
        spaceId: String
    ) async throws {
        _ = try await mutate(
            .remove(associationId),
            location: .init(spaceId: spaceId, target: target)
        )
    }

    private func list(location: TorahAssociationLocation) async throws -> [TorahAssociationItem] {
        let key = documentKey(for: location)
        return try await coordinator.enqueue(key: key) { [self] in
            let loaded = try await load(location: location, requiresWrite: false)
            return TorahCanonicalAssociationCollectionPolicy.items(in: loaded.payload, at: location)
        }
    }

    private func mutate(
        _ mutation: Mutation,
        location: TorahAssociationLocation
    ) async throws -> TorahAssociationItem? {
        let event: @Sendable (TorahAssociationPersistenceState) -> TorahAssociationPersistenceEvent = { state in
            TorahAssociationPersistenceEvent(
                operationId: mutation.operationId,
                location: location,
                state: state
            )
        }
        await statusCenter.publish(event(.waiting))

        do {
            let result = try await coordinator.enqueue(key: documentKey(for: location)) { [self] in
                await statusCenter.publish(event(.saving))
                let loaded = try await load(location: location, requiresWrite: true)
                let change = try apply(mutation, to: loaded.payload, at: location)
                let encoded = try codec.encodeCanonicalDocument(change.payload)
                guard let encodedString = String(data: encoded, encoding: .utf8) else {
                    throw TorahAssociationRepositoryError.malformedCanonicalData
                }

                do {
                    try await nativeStore.writeDocumentProperty(
                        objectId: location.target.objectId,
                        propertyKey: loaded.manifest.documentAssociationsPropertyKey,
                        value: encodedString
                    )
                } catch {
                    return try await reconcileUncertainWrite(
                        mutation: mutation,
                        expectedValue: encodedString,
                        expectedItem: change.item,
                        location: location,
                        originalError: error
                    )
                }

                let readback = try await load(location: location, requiresWrite: false)
                guard readback.snapshot.propertyValue == encodedString else {
                    throw TorahAssociationRepositoryError.writeConflict(
                        "Native readback differs from the serialized single-writer mutation"
                    )
                }
                return change.item
            }
            await statusCenter.publish(event(.saved))
            return result
        } catch let error as TorahAssociationRepositoryError {
            switch error {
            case .writeConflict(let message):
                await statusCenter.publish(event(.conflict(message)))
            case .writeUncertain(let message):
                await statusCenter.publish(event(.uncertain(message)))
            default:
                await statusCenter.publish(event(.error(String(describing: error))))
            }
            throw error
        } catch {
            await statusCenter.publish(event(.error(error.localizedDescription)))
            throw error
        }
    }

    private func apply(
        _ mutation: Mutation,
        to payload: TorahCanonicalAssociationsPayload,
        at location: TorahAssociationLocation
    ) throws -> (payload: TorahCanonicalAssociationsPayload, item: TorahAssociationItem?) {
        switch mutation {
        case .add(let item):
            let result = TorahCanonicalAssociationCollectionPolicy.adding(item, to: payload, at: location)
            return (result.payload, result.item)
        case .upsert(let item):
            let result = TorahCanonicalAssociationCollectionPolicy.upserting(item, into: payload, at: location)
            return (result.payload, result.item)
        case .update(let item):
            let result = try TorahCanonicalAssociationCollectionPolicy.updating(item, in: payload, at: location)
            return (result.payload, result.item)
        case .remove(let id):
            return (
                TorahCanonicalAssociationCollectionPolicy.removing(id: id, from: payload, at: location),
                nil
            )
        }
    }

    private func load(
        location: TorahAssociationLocation,
        requiresWrite: Bool
    ) async throws -> LoadedDocument {
        guard !location.spaceId.isEmpty,
              !location.target.objectId.isEmpty,
              location.target.blockId?.isEmpty != true else {
            throw TorahAssociationRepositoryError.targetNotFound
        }

        let manifest = try await manifestProvider.manifest(spaceId: location.spaceId)
        let snapshot = try await nativeStore.readDocument(
            spaceId: location.spaceId,
            objectId: location.target.objectId,
            propertyKey: manifest.documentAssociationsPropertyKey
        )

        guard snapshot.objectId == location.target.objectId else {
            throw TorahAssociationRepositoryError.targetNotFound
        }
        guard snapshot.spaceId == location.spaceId else {
            throw TorahAssociationRepositoryError.targetOutsideSpace
        }
        guard !snapshot.isDeleted, !snapshot.isArchived else {
            throw TorahAssociationRepositoryError.targetNotFound
        }
        if requiresWrite, !snapshot.canWriteDetails {
            throw TorahAssociationRepositoryError.permissionDenied
        }
        if let blockId = location.target.blockId, !snapshot.blockIds.contains(blockId) {
            throw TorahAssociationRepositoryError.targetNotFound
        }

        let legacyLocation = TorahAssociationLocation(
            spaceId: location.spaceId,
            target: .object(objectId: location.target.objectId)
        )
        let payload: TorahCanonicalAssociationsPayload
        if let value = snapshot.propertyValue, !value.isEmpty {
            do {
                payload = try codec.decodeCanonicalDocument(value, legacyLocation: legacyLocation)
            } catch TorahAssociationPayloadCodecError.unsupportedVersion(let version) {
                throw TorahAssociationRepositoryError.unsupportedPayloadVersion(version)
            } catch {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
        } else {
            payload = TorahCanonicalAssociationsPayload(records: [])
        }

        try validate(payload: payload, expectedSpaceId: location.spaceId, expectedObjectId: location.target.objectId)
        return LoadedDocument(manifest: manifest, snapshot: snapshot, payload: payload)
    }

    private func validate(
        payload: TorahCanonicalAssociationsPayload,
        expectedSpaceId: String,
        expectedObjectId: String
    ) throws {
        var identities = Set<String>()
        for record in payload.records {
            guard record.spaceId == expectedSpaceId,
                  record.objectId == expectedObjectId,
                  !record.item.id.isEmpty,
                  !record.item.providerID.isEmpty,
                  (!record.item.canonicalKey.isEmpty || !record.item.externalID.isEmpty) else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            let identity = [record.spaceId, record.objectId, record.blockId ?? "", record.item.id]
                .map { "\($0.utf8.count):\($0)" }
                .joined(separator: "|")
            guard identities.insert(identity).inserted else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
        }
    }

    private func reconcileUncertainWrite(
        mutation: Mutation,
        expectedValue: String,
        expectedItem: TorahAssociationItem?,
        location: TorahAssociationLocation,
        originalError: Error
    ) async throws -> TorahAssociationItem? {
        do {
            let readback = try await load(location: location, requiresWrite: false)
            if readback.snapshot.propertyValue == expectedValue {
                return expectedItem
            }
            let items = TorahCanonicalAssociationCollectionPolicy.items(in: readback.payload, at: location)
            let effectIsPresent: Bool
            switch mutation {
            case .remove(let id):
                effectIsPresent = !items.contains(where: { $0.id == id })
            case .add, .upsert, .update:
                effectIsPresent = expectedItem.map { expected in
                    items.contains(expected)
                } ?? false
            }
            if effectIsPresent {
                throw TorahAssociationRepositoryError.writeConflict(
                    "Mutation is present but native payload contains an unexpected concurrent value"
                )
            }
        } catch let error as TorahAssociationRepositoryError {
            if case .writeConflict = error { throw error }
        } catch {
            // The original acknowledgement and reconciliation read are both uncertain.
        }
        throw TorahAssociationRepositoryError.writeUncertain(originalError.localizedDescription)
    }

    private func documentKey(for location: TorahAssociationLocation) -> TorahAssociationDocumentKey {
        TorahAssociationDocumentKey(spaceId: location.spaceId, objectId: location.target.objectId)
    }
}
