import Foundation
import TorahInspectorCore

public protocol TorahHierarchyCache: Sendable {
    func data(now: Date) async -> Data?
    func replace(data: Data, expiresAt: Date) async
    func removeAll() async
}

public actor InMemoryTorahHierarchyCache: TorahHierarchyCache {
    private var cachedData: Data?
    private var expiresAt: Date?

    public init() {}

    public func data(now: Date) -> Data? {
        guard let expiresAt, expiresAt > now else {
            cachedData = nil
            self.expiresAt = nil
            return nil
        }
        return cachedData
    }

    public func replace(data: Data, expiresAt: Date) {
        cachedData = data
        self.expiresAt = expiresAt
    }

    public func removeAll() {
        cachedData = nil
        expiresAt = nil
    }
}

public struct SefariaHierarchyProvider: TorahHierarchyProvider {
    public let providerID = "sefaria"
    private let client: SefariaClient
    private let cache: any TorahHierarchyCache
    private let ttl: TimeInterval
    private let now: @Sendable () -> Date

    public init(
        client: SefariaClient = SefariaClient(),
        cache: any TorahHierarchyCache = InMemoryTorahHierarchyCache(),
        ttl: TimeInterval = 7 * 24 * 60 * 60,
        now: @escaping @Sendable () -> Date = Date.init
    ) {
        self.client = client
        self.cache = cache
        self.ttl = max(1, ttl)
        self.now = now
    }

    public func fetchHierarchy() async throws -> TorahSourceHierarchy {
        try Task.checkCancellation()
        let currentTime = now()
        let data: Data
        if let cached = await cache.data(now: currentTime) {
            data = cached
        } else {
            let (fetchedData, response) = try await client.get(pathSegments: ["api", "index"])
            try SefariaJSON.requireSuccess(response, operation: "table of contents request")
            data = fetchedData
            await cache.replace(
                data: fetchedData,
                expiresAt: currentTime.addingTimeInterval(ttl)
            )
        }
        try Task.checkCancellation()
        let roots = try Self.decodeTOC(data)
        return TorahSourceHierarchy(roots: roots, providerID: providerID, fetchedAt: currentTime)
    }

    static func decodeTOC(_ data: Data) throws -> [TorahSourceNode] {
        guard let entries = try SefariaJSON.object(from: data) as? [[String: Any]] else {
            throw TorahError.malformedResponse
        }
        let roots = parseTOCNodes(entries, pathPrefix: "")
        guard !roots.isEmpty else { throw TorahError.malformedResponse }
        return roots
    }

    private static func parseTOCNodes(
        _ entries: [[String: Any]],
        pathPrefix: String
    ) -> [TorahSourceNode] {
        entries.compactMap { entry in
            if let category = SefariaJSON.string(entry, keys: ["category"]) {
                let nodeID = pathPrefix.isEmpty ? category : "\(pathPrefix)/\(category)"
                let contents = entry["contents"] as? [[String: Any]] ?? []
                let children = parseTOCNodes(contents, pathPrefix: nodeID)
                guard !children.isEmpty else { return nil }
                return TorahSourceNode(
                    id: nodeID,
                    labelHe: SefariaJSON.string(entry, keys: ["heCategory"]) ?? category,
                    labelEn: category,
                    children: children
                )
            }
            if let title = SefariaJSON.string(entry, keys: ["title"]) {
                let nodeID = pathPrefix.isEmpty ? title : "\(pathPrefix)/\(title)"
                return TorahSourceNode(
                    id: nodeID,
                    labelHe: SefariaJSON.string(entry, keys: ["heTitle"]) ?? title,
                    labelEn: title,
                    canonicalKey: title
                )
            }
            return nil
        }
    }
}
