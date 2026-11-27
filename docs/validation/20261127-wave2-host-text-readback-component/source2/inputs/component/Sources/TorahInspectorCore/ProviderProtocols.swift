import Foundation

public protocol TextProvider: Sendable {
    var providerID: String { get }
    func fetchText(reference: String, request: TorahTextRequest) async throws -> TorahTextDocument
}

public protocol RelationshipProvider: Sendable {
    var providerID: String { get }
    func links(for reference: String) async throws -> [TorahLinkedSource]
    func topics(for reference: String) async throws -> [TorahLinkedTopic]
}

public protocol TorahInspectorProvider: TextProvider, RelationshipProvider {}
