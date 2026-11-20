import Foundation

public enum AnyLiveQueryError: Error, Equatable, Sendable {
    case invalidUTF8
    case frameTooLarge
    case windowTooLarge
    case invalidEvent(String)
    case invalidSequence(String)
    case incompleteWindow
    case staleGeneration
    case closed(String)
    case disconnected
    case bufferOverflow
    case http(Int)
}

public struct AnySSEFrame: Equatable, Sendable {
    public let event: String
    public let data: Data
    public let id: String?
    public init(event: String, data: Data, id: String? = nil) {
        self.event = event; self.data = data; self.id = id
    }
}

/// Incremental strict UTF-8 SSE parser. UTF-8 and CRLF may split at any byte.
/// No Last-Event-ID/replay cursor is invented; reconnect requires a new snapshot.
public struct AnySSEParser: Sendable {
    private var line = Data()
    private var event = ""
    private var eventID: String?
    private var dataLines: [String] = []
    private var frameBytes = 0
    private var previousCR = false
    private var firstLine = true
    private let maximumFrameBytes: Int

    public init(maximumFrameBytes: Int = 8 * 1024 * 1024) {
        self.maximumFrameBytes = max(1, maximumFrameBytes)
    }

    public mutating func feed(_ chunk: Data) throws -> [AnySSEFrame] {
        var frames: [AnySSEFrame] = []
        for byte in chunk {
            if previousCR {
                previousCR = false
                if byte == 10 { continue }
            }
            if byte == 10 || byte == 13 {
                if let frame = try consumeLine() { frames.append(frame) }
                previousCR = byte == 13
            } else {
                frameBytes += 1
                guard frameBytes <= maximumFrameBytes else { throw AnyLiveQueryError.frameTooLarge }
                line.append(byte)
            }
        }
        return frames
    }

    public mutating func finish() throws {
        guard line.isEmpty, dataLines.isEmpty, event.isEmpty, eventID == nil else {
            throw AnyLiveQueryError.invalidSequence("truncated frame")
        }
    }

    private mutating func consumeLine() throws -> AnySSEFrame? {
        guard var text = String(data: line, encoding: .utf8) else { throw AnyLiveQueryError.invalidUTF8 }
        line.removeAll(keepingCapacity: true)
        if firstLine {
            firstLine = false
            if text.hasPrefix("\u{feff}") { text.removeFirst() }
        }
        if text.isEmpty {
            defer { event = ""; eventID = nil; dataLines.removeAll(keepingCapacity: true); frameBytes = 0 }
            guard !dataLines.isEmpty else { return nil }
            return AnySSEFrame(event: event.isEmpty ? "message" : event,
                               data: Data(dataLines.joined(separator: "\n").utf8), id: eventID)
        }
        if text.hasPrefix(":") { return nil }
        let split = text.firstIndex(of: ":")
        let field = split.map { String(text[..<$0]) } ?? text
        var value = split.map { String(text[text.index(after: $0)...]) } ?? ""
        if value.hasPrefix(" ") { value.removeFirst() }
        switch field {
        case "event": event = value
        case "data": dataLines.append(value)
        case "id":
            guard !value.utf8.contains(0), value.utf8.count <= 1024 else {
                throw AnyLiveQueryError.invalidEvent("event ID")
            }
            eventID = value
        default: break
        }
        return nil
    }
}

public struct AnyQueryRemoval: Equatable, Sendable {
    public let id: String
    public let reason: String
}
public struct AnyQueryUpdate: Equatable, Sendable {
    public let generation: UUID
    /// Stable ID order; presentation-specific ordering belongs to the consumer.
    public let records: [AnyJSON]
    public let initial: Bool
    public let removed: [AnyQueryRemoval]
}

/// Applies each complete SSE frame atomically. The full post-apply doc is
/// authoritative; no local version-ID comparison discards legitimate rereads.
public struct AnyQueryWindow: Sendable {
    public let generation: UUID
    private let limit: Int
    private let requireComplete: Bool
    private let maximumWindowBytes: Int
    private var recordBytes: [String: Int] = [:]
    private var retainedBytes = 0
    private var ready = false
    private var receivedSnapshot = false
    private var records: [String: AnyJSON] = [:]

    public init(generation: UUID, limit: Int, requireComplete: Bool = false,
                maximumWindowBytes: Int = 8 * 1024 * 1024) {
        self.generation = generation
        self.limit = limit
        self.requireComplete = requireComplete
        self.maximumWindowBytes = maximumWindowBytes
    }

    public mutating func apply(_ frame: AnySSEFrame, generation: UUID) throws -> AnyQueryUpdate? {
        guard generation == self.generation else { throw AnyLiveQueryError.staleGeneration }
        guard (1...10001).contains(limit), maximumWindowBytes > 0 else { throw AnyLiveQueryError.incompleteWindow }
        let payload = try JSONDecoder().decode(AnyJSON.self, from: frame.data)
        switch frame.event {
        case "ready":
            guard !ready, !receivedSnapshot, payload.object != nil else {
                throw AnyLiveQueryError.invalidSequence("ready")
            }
            ready = true
            return nil
        case "snapshot":
            guard ready, !receivedSnapshot, let values = payload["records"]?.array else {
                throw AnyLiveQueryError.invalidSequence("snapshot")
            }
            guard values.count <= limit else { throw AnyLiveQueryError.incompleteWindow }
            if requireComplete {
                guard payload["hasNext"]?.bool == false,
                      payload["total"]?.integer == Int64(values.count) else {
                    throw AnyLiveQueryError.incompleteWindow
                }
            }
            var next: [String: AnyJSON] = [:]
            var sizes: [String: Int] = [:]
            var size = 0
            for value in values {
                let id = try value.requireString("id")
                guard !id.isEmpty, next[id] == nil else { throw AnyLiveQueryError.invalidEvent("duplicate snapshot id") }
                let count = try JSONEncoder().encode(value).count
                size += count
                guard size <= maximumWindowBytes else { throw AnyLiveQueryError.windowTooLarge }
                sizes[id] = count
                next[id] = value
            }
            records = next
            recordBytes = sizes
            retainedBytes = size
            receivedSnapshot = true
            return update(initial: true, removed: [])
        case "changes":
            guard receivedSnapshot, let batches = payload.array else {
                throw AnyLiveQueryError.invalidSequence("changes before snapshot")
            }
            var next = records
            var sizes = recordBytes
            var size = retainedBytes
            var removals: [AnyQueryRemoval] = []
            for batch in batches {
                guard batch["versionId"]?.string != nil else { throw AnyLiveQueryError.invalidEvent("versionId") }
                for field in ["added", "updated"] {
                    if let raw = batch[field] {
                        guard let entries = raw.array else { throw AnyLiveQueryError.invalidEvent(field) }
                        for entry in entries {
                            let id = try entry.requireString("id")
                            guard let doc = entry["doc"], doc["id"]?.string == id, !id.isEmpty else {
                                throw AnyLiveQueryError.invalidEvent("record identity")
                            }
                            if field == "added" && next[id] != nil { throw AnyLiveQueryError.invalidEvent("duplicate added") }
                            if field == "updated" && next[id] == nil { throw AnyLiveQueryError.invalidEvent("unknown updated") }
                            let count = try JSONEncoder().encode(doc).count
                            size += count - (sizes[id] ?? 0)
                            sizes[id] = count
                            next[id] = doc
                        }
                    }
                }
                if let raw = batch["removed"] {
                    guard let entries = raw.array else { throw AnyLiveQueryError.invalidEvent("removed") }
                    for entry in entries {
                        let id = try entry.requireString("id"), reason = try entry.requireString("reason")
                        guard ["deleted", "filtered-out", "displaced"].contains(reason),
                              next[id] != nil else { throw AnyLiveQueryError.invalidEvent("removed record") }
                        if requireComplete && reason != "deleted" { throw AnyLiveQueryError.incompleteWindow }
                        next.removeValue(forKey: id)
                        size -= sizes.removeValue(forKey: id) ?? 0
                        removals.append(.init(id: id, reason: reason))
                    }
                }
            }
            guard next.count <= limit else { throw AnyLiveQueryError.incompleteWindow }
            guard size <= maximumWindowBytes else { throw AnyLiveQueryError.windowTooLarge }
            records = next
            recordBytes = sizes
            retainedBytes = size
            return update(initial: false, removed: removals)
        case "closed":
            let reason = try payload.requireString("reason")
            guard ["server_shutdown", "deauthorized", "sdk_closed", "overflow", "drifted",
                   "object_deleted", "open_failed"].contains(reason) else {
                throw AnyLiveQueryError.invalidEvent("unknown closed reason")
            }
            throw AnyLiveQueryError.closed(reason)
        default:
            throw AnyLiveQueryError.invalidEvent("unknown event")
        }
    }

    private func update(initial: Bool, removed: [AnyQueryRemoval]) -> AnyQueryUpdate {
        .init(generation: generation, records: records.keys.sorted().compactMap { records[$0] },
              initial: initial, removed: removed)
    }
}
