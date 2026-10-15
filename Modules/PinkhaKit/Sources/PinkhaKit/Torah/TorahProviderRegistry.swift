import Foundation
import TorahInspectorCore

public enum TorahProviderRegistryConfigurationError: Error, Equatable, Sendable {
    case emptyDefaultProviderID
    case defaultProviderNotRegistered(String)
    case duplicateProviderID(String)
}

/// Immutable provider routing. Explicit provider identifiers never fall back
/// to the default provider when they are missing.
public struct TorahProviderRegistry: Sendable {
    private let references: [String: any ReferenceProvider]
    private let topics: [String: any TopicProvider]
    private let lexicons: [String: any LexicalProvider]
    private let texts: [String: any TextProvider]
    private let relationships: [String: any RelationshipProvider]
    private let hierarchies: [String: any TorahHierarchyProvider]

    public let defaultProviderID: String

    public init(
        referenceProviders: [any ReferenceProvider],
        topicProviders: [any TopicProvider],
        lexicalProviders: [any LexicalProvider],
        textProviders: [any TextProvider] = [],
        relationshipProviders: [any RelationshipProvider] = [],
        hierarchyProviders: [any TorahHierarchyProvider] = [],
        defaultProviderID: String
    ) throws {
        let defaultID = defaultProviderID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !defaultID.isEmpty else {
            throw TorahProviderRegistryConfigurationError.emptyDefaultProviderID
        }

        self.references = try Self.index(referenceProviders) { $0.providerID }
        self.topics = try Self.index(topicProviders) { $0.providerID }
        self.lexicons = try Self.index(lexicalProviders) { $0.providerID }
        self.texts = try Self.index(textProviders) { $0.providerID }
        self.relationships = try Self.index(relationshipProviders) { $0.providerID }
        self.hierarchies = try Self.index(hierarchyProviders) { $0.providerID }

        let allIDs = Set(references.keys)
            .union(topics.keys)
            .union(lexicons.keys)
            .union(texts.keys)
            .union(relationships.keys)
            .union(hierarchies.keys)
        guard allIDs.contains(defaultID) else {
            throw TorahProviderRegistryConfigurationError.defaultProviderNotRegistered(defaultID)
        }
        self.defaultProviderID = defaultID
    }

    public func reference(_ id: String? = nil) throws -> any ReferenceProvider {
        guard let value = references[id ?? defaultProviderID] else { throw TorahError.missingProvider }
        return value
    }

    public func topic(_ id: String? = nil) throws -> any TopicProvider {
        guard let value = topics[id ?? defaultProviderID] else { throw TorahError.missingProvider }
        return value
    }

    public func lexical(_ id: String? = nil) throws -> any LexicalProvider {
        guard let value = lexicons[id ?? defaultProviderID] else { throw TorahError.missingProvider }
        return value
    }

    public func text(_ id: String? = nil) throws -> any TextProvider {
        guard let value = texts[id ?? defaultProviderID] else { throw TorahError.missingProvider }
        return value
    }

    public func relationship(_ id: String? = nil) throws -> any RelationshipProvider {
        guard let value = relationships[id ?? defaultProviderID] else { throw TorahError.missingProvider }
        return value
    }

    public func hierarchy(_ id: String? = nil) throws -> any TorahHierarchyProvider {
        guard let value = hierarchies[id ?? defaultProviderID] else { throw TorahError.missingProvider }
        return value
    }

    private static func index<Provider: Sendable>(
        _ providers: [Provider],
        providerID: (Provider) -> String
    ) throws -> [String: Provider] {
        var result: [String: Provider] = [:]
        for provider in providers {
            let id = providerID(provider)
            guard result.updateValue(provider, forKey: id) == nil else {
                throw TorahProviderRegistryConfigurationError.duplicateProviderID(id)
            }
        }
        return result
    }
}
