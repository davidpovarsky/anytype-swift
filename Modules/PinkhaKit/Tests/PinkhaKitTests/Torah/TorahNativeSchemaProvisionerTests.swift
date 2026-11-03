import Foundation
import Testing
@testable import PinkhaKit

@Suite("Native Torah metadata upgrade")
struct TorahNativeSchemaProvisionerTests {
    @Test func existingSpaceUpgradePreservesIdsAndOtherPropertiesAndIsIdempotent() async throws {
        let store = NativeSchemaStore()
        let provisioner = TorahNativeSchemaProvisioner(store: store)
        let manifest = nativeSchemaManifest()
        let before = try manifest.toJSONData()
        let first = try await provisioner.provision(manifest: manifest)
        let second = try await provisioner.provision(manifest: manifest)
        #expect(first == second)
        #expect(first.propertyIdsByKey.count == 3)
        #expect(await store.installCount == 3)
        #expect(await store.addCount == 3)
        #expect(try manifest.toJSONData() == before)
        for typeId in ["chiddush-id", "article-id", "research-id"] {
            let ids = try await store.attachedPropertyIds(typeId: typeId, spaceId: "space")
            #expect(ids.contains("ordinary-tag"))
            #expect(ids.contains("concurrent-user-property"))
            #expect(Set(first.propertyIdsByKey.values).isSubset(of: Set(ids)))
        }
    }

    @Test func interruptedInstallationRetriesByStableNativeKey() async throws {
        let store = NativeSchemaStore(failAfterFirstInstall: true)
        let provisioner = TorahNativeSchemaProvisioner(store: store)
        await #expect(throws: NativeSchemaStore.Failure.self) {
            try await provisioner.provision(manifest: nativeSchemaManifest())
        }
        let registration = try await provisioner.provision(manifest: nativeSchemaManifest())
        #expect(registration.propertyIdsByKey.count == 3)
        #expect(await store.installCount == 3)
    }

    @Test func unsupportedMiddlewareDoesNotWriteOrMintOrdinaryTags() async {
        let store = NativeSchemaStore(engineVersion: 0)
        let provisioner = TorahNativeSchemaProvisioner(store: store)
        await #expect(throws: TorahNativeSchemaError.unsupportedEngine) {
            try await provisioner.provision(manifest: nativeSchemaManifest())
        }
        #expect(await store.installCount == 0)
        #expect(await store.addCount == 0)
    }

    @Test func refusesForeignSpaceDefinitionAndNeverRewritesIt() async {
        let store = NativeSchemaStore(foreignProperty: true)
        let provisioner = TorahNativeSchemaProvisioner(store: store)
        await #expect(throws: TorahNativeSchemaError.self) {
            try await provisioner.provision(manifest: nativeSchemaManifest())
        }
        #expect(await store.installCount == 0)
        #expect(await store.addCount == 0)
    }
}

private actor NativeSchemaStore: TorahNativePropertyProvisioningStore {
    enum Failure: Error { case interrupted }
    let version: Int
    var failAfterFirstInstall: Bool
    let foreignProperty: Bool
    var properties: [String: TorahNativePropertyDescriptor] = [:]
    var attached: [String: [String]] = [:]
    var installCount = 0
    var addCount = 0

    init(engineVersion: Int = 1, failAfterFirstInstall: Bool = false, foreignProperty: Bool = false) {
        version = engineVersion
        self.failAfterFirstInstall = failAfterFirstInstall
        self.foreignProperty = foreignProperty
    }

    func engineVersion(spaceId: String, manifestObjectId: String) -> Int { version }

    func property(key: String, spaceId: String) -> TorahNativePropertyDescriptor? {
        if foreignProperty {
            return TorahNativePropertyDescriptor(id: "foreign", key: key, spaceId: "other", format: 11, isReadOnlyValue: true)
        }
        return properties[key]
    }

    func installProperty(_ definition: TorahNativePropertyDefinition, spaceId: String) throws -> TorahNativePropertyDescriptor {
        installCount += 1
        let descriptor = TorahNativePropertyDescriptor(
            id: "native-\(definition.kind.rawValue)", key: definition.key,
            spaceId: spaceId, format: 11, isReadOnlyValue: true
        )
        properties[definition.key] = descriptor
        if failAfterFirstInstall { failAfterFirstInstall = false; throw Failure.interrupted }
        return descriptor
    }

    func attachedPropertyIds(typeId: String, spaceId: String) throws -> [String] {
        attached[typeId] ?? ["ordinary-tag"]
    }

    func addRecommendedProperties(_ definitions: [TorahNativePropertyDefinition], typeId: String, spaceId: String) {
        addCount += 1
        var current = attached[typeId] ?? ["ordinary-tag"]
        current.append("concurrent-user-property")
        for definition in definitions {
            if let descriptor = properties[definition.key], !current.contains(descriptor.id) { current.append(descriptor.id) }
        }
        attached[typeId] = current
    }
}

private func nativeSchemaManifest() -> PinkhaSpaceManifest {
    PinkhaSpaceManifest(
        spaceId: "space", manifestObjectId: "manifest",
        parentPropertyId: "parent", parentPropertyKey: "parent-key",
        orderPropertyId: "order", orderPropertyKey: "order-key",
        documentAssociationsPropertyId: "canonical", documentAssociationsPropertyKey: "canonical-key",
        folderTypeId: "folder", bookFolderTypeId: "book",
        registeredDocumentTypes: ["chiddush": "chiddush-id", "article": "article-id", "research": "research-id"],
        defaultTemplateIds: ["chiddush": "chiddush-template", "article": "article-template", "research": "research-template"]
    )
}
