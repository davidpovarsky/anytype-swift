import Foundation
import PinkhaKit
import Services
import AnytypeCore
import Factory
import SwiftProtobuf
import ProtobufMessages

/// Installs real native relation objects and uses Heart's atomic Type property
/// API. Neither canonical association data nor replacement Type lists are written.
public final class AnytypeTorahNativePropertyProvisioningStore: TorahNativePropertyProvisioningStore, Sendable {
    @Injected(\.searchMiddleService)
    private var search: any SearchMiddleServiceProtocol

    public init() {}

    public func engineVersion(spaceId: String, manifestObjectId: String) async throws -> Int {
        // The custom iOS route sets this compilation flag only after verifying
        // the embedded custom Heart. Original middleware retains a cheap probe.
        #if PINKHA_NATIVE_DERIVED
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(30))
        repeat {
            let details = try await objectDetails(id: manifestObjectId, spaceId: spaceId)
            if let version = details.intValue(for: TorahNativePropertyDefinition.engineVersionKey), version > 0 { return version }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw TorahNativeSchemaError.invalidManifest
        #else
        let details = try await objectDetails(id: manifestObjectId, spaceId: spaceId)
        return details.intValue(for: TorahNativePropertyDefinition.engineVersionKey) ?? 0
        #endif
    }

    public func property(key: String, spaceId: String) async throws -> TorahNativePropertyDescriptor? {
        let results = try await search.search(
            spaceId: spaceId,
            filters: [.with {
                $0.relationKey = BundledPropertyKey.relationKey.rawValue
                $0.condition = .equal
                $0.value = key.protobufValue
            }],
            keys: PropertyDetails.subscriptionKeys.map(\.rawValue),
            limit: 0
        )
        let matching = results
            .map { PropertyDetails(details: $0) }
            .filter { property in
                property.key == key &&
                property.spaceId == spaceId &&
                !property.isDeleted &&
                property.sourceObject == "_br" + key
            }
        guard matching.count <= 1 else { throw TorahNativeSchemaError.invalidProperty(key) }
        guard let property = matching.first else { return nil }
        return TorahNativePropertyDescriptor(
            id: property.id, key: property.key, spaceId: property.spaceId,
            format: property.format.asMiddleware.rawValue, isReadOnlyValue: property.isReadOnlyValue
        )
    }

    public func installProperty(
        _ definition: TorahNativePropertyDefinition, spaceId: String
    ) async throws -> TorahNativePropertyDescriptor {
        if let existing = try await property(key: definition.key, spaceId: spaceId) { return existing }
        do {
            _ = try await ClientCommands.objectCreateRelation(.with {
                $0.spaceID = spaceId
                $0.details = Google_Protobuf_Struct(fields: [
                    BundledPropertyKey.relationKey.rawValue: definition.key.protobufValue,
                    BundledPropertyKey.relationFormat.rawValue: TorahNativePropertyDefinition.wireFormat.protobufValue,
                    BundledPropertyKey.name.rawValue: definition.name.protobufValue,
                    BundledPropertyKey.relationReadonlyValue.rawValue: true.protobufValue,
                    BundledPropertyKey.relationMaxCount.rawValue: 0.protobufValue
                ])
            }).invoke(qos: .userInitiated)
        } catch {
            // A retry may race a completed installation. Read the actual fixed
            // key; do not mint a replacement key or silently accept other errors.
            if let existing = try await property(key: definition.key, spaceId: spaceId) { return existing }
            throw error
        }
        // Native creation and background indexing have separate completion
        // boundaries. Wait for verified indexed readback before another caller
        // may retry the stable key or attach it to existing Types.
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(30))
        repeat {
            if let created = try? await property(key: definition.key, spaceId: spaceId), created != nil {
                return created!
            }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        if let created = try await property(key: definition.key, spaceId: spaceId) { return created }
        throw TorahNativeSchemaError.invalidProperty(definition.key)
    }

    public func attachedPropertyIds(typeId: String, spaceId: String) async throws -> [String] {
        let details = try await objectDetails(id: typeId, spaceId: spaceId)
        let keys: [BundledPropertyKey] = [
            .recommendedRelations, .recommendedFeaturedRelations, .recommendedHiddenRelations
        ]
        return keys.flatMap { details.stringArrayValue(for: $0.rawValue) }
    }

    public func addRecommendedProperties(
        _ definitions: [TorahNativePropertyDefinition], typeId: String, spaceId: String
    ) async throws {
        _ = try await objectDetails(id: typeId, spaceId: spaceId)
        for definition in definitions {
            _ = try await ClientCommands.objectTypePropertyAdd(.with {
                $0.objectTypeID = typeId
                $0.key = definition.key
                $0.section = .recommended
                $0.enableInViews = false
            }).invoke(qos: .userInitiated)
        }
    }

    private func objectDetails(id: String, spaceId: String) async throws -> ObjectDetails {
        let response = try await ClientCommands.objectShow(.with {
            $0.contextID = id
            $0.objectID = id
            $0.spaceID = spaceId
        }).invoke(qos: .userInitiated)
        guard let value = response.objectView.details.first(where: { $0.id == id })?.details else {
            throw TorahNativeSchemaError.invalidManifest
        }
        let details = try ObjectDetails(protobufStruct: value)
        guard details.id == id, details.spaceId == spaceId else { throw TorahNativeSchemaError.invalidManifest }
        return details
    }
}
