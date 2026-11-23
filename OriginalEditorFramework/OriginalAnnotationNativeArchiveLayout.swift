import Foundation

/// Fixed byte budgets for the annotation's untouched native archive and frame.
/// This is data admission only; no account, Space or write authority is granted.
internal enum OriginalAnnotationPayloadBudget {
    static let maximumArchiveBytes = 1_048_576
    static let maximumHeaderBytes = 16_384
    static let framePrefixBytes = 16
    static let maximumBodyBytes = framePrefixBytes + maximumHeaderBytes + maximumArchiveBytes

    static func acceptsBodyLimit(_ maximum: Int) -> Bool {
        maximum > framePrefixBytes && maximum <= maximumBodyBytes
    }

    static func acceptsArchiveBytes(_ count: Int, maximumBodyBytes: Int) -> Bool {
        acceptsBodyLimit(maximumBodyBytes) && count >= 0
            && count <= maximumArchiveBytes && count <= maximumBodyBytes
    }

    static func acceptsFrame(headerBytes: Int, archiveBytes: Int, maximumBodyBytes: Int) -> Bool {
        guard acceptsArchiveBytes(archiveBytes, maximumBodyBytes: maximumBodyBytes),
              headerBytes > 0, headerBytes <= maximumHeaderBytes else { return false }
        // Both operands are independently bounded before addition.
        return framePrefixBytes + headerBytes + archiveBytes <= maximumBodyBytes
    }
}

/// A bounded inventory of the original exporter's ordinary ZIP framing. This
/// does not decompress, extract paths, decode native objects or establish owner
/// authority. ZIP64, encryption and alternate path encodings are unsupported.
internal struct OriginalAnnotationNativeArchiveLayout: Sendable {
    internal struct Entry: Sendable {
        let path: String
        let pathBytes: Data
        let checksum: UInt32
        let compressedBytes: Int
        let uncompressedBytes: Int
        let localOffset: Int
        let endOffset: Int
    }

    internal enum Failure: Error, Sendable, Equatable {
        case unsupportedZIP
        case malformedZIP
        case unsafePath
        case duplicatePath
        case invalidCount
        case sizeLimit
        case unindexedData
    }

    static let maximumArchiveBytes = OriginalAnnotationPayloadBudget.maximumArchiveBytes
    static let maximumEntries = 512
    static let maximumExpandedBytes = 8 * 1_024 * 1_024
    let entries: [Entry]

    init(_ data: Data) throws {
        guard data.count >= 22, data.count <= Self.maximumArchiveBytes else {
            throw Failure.sizeLimit
        }
        let bytes = Array(data)
        func u16(_ at: Int) -> Int {
            Int(bytes[at]) | Int(bytes[at + 1]) << 8
        }
        func u32(_ at: Int) -> UInt32 {
            UInt32(bytes[at]) | UInt32(bytes[at + 1]) << 8
                | UInt32(bytes[at + 2]) << 16 | UInt32(bytes[at + 3]) << 24
        }
        // Match the actual EOCD including its comment length. More than one
        // possible record is ambiguous; no scan-back fallback may hide entries.
        let ends = (0...(bytes.count - 22)).filter {
            u32($0) == 0x0605_4b50 && $0 + 22 + u16($0 + 20) == bytes.count
        }
        guard ends.count == 1, let end = ends.first else { throw Failure.malformedZIP }
        let count = u16(end + 10)
        guard u16(end + 4) == 0, u16(end + 6) == 0,
              u16(end + 8) == count,
              count != 0xffff, u32(end + 12) != UInt32.max,
              u32(end + 16) != UInt32.max else { throw Failure.unsupportedZIP }
        guard count > 0, count <= Self.maximumEntries else { throw Failure.invalidCount }
        let centralSize = Int(u32(end + 12)), centralOffset = Int(u32(end + 16))
        guard centralOffset <= end, centralSize == end - centralOffset else {
            throw Failure.malformedZIP
        }

        var cursor = centralOffset
        var inventory: [Entry] = []
        var paths = Set<Data>()
        var expanded = 0
        for _ in 0..<count {
            guard cursor <= end - 46, u32(cursor) == 0x0201_4b50 else {
                throw Failure.malformedZIP
            }
            let needed = u16(cursor + 6), flags = u16(cursor + 8)
            let method = u16(cursor + 10), checksum = u32(cursor + 16)
            let compressed = Int(u32(cursor + 20)), uncompressed = Int(u32(cursor + 24))
            let nameCount = u16(cursor + 28), extraCount = u16(cursor + 30)
            let commentCount = u16(cursor + 32), local = Int(u32(cursor + 42))
            guard (needed == 10 || needed == 20), flags & ~0x0808 == 0,
                  (method == 0 || method == 8), u16(cursor + 34) == 0,
                  compressed != Int(UInt32.max), uncompressed != Int(UInt32.max),
                  local != Int(UInt32.max) else { throw Failure.unsupportedZIP }
            let nameStart = cursor + 46
            let centralEnd = nameStart + nameCount + extraCount + commentCount
            guard centralEnd <= end, nameCount > 0, nameCount <= 1_024 else {
                throw Failure.malformedZIP
            }
            let name = Data(bytes[nameStart..<(nameStart + nameCount)])
            guard let path = String(data: name, encoding: .utf8),
                  Data(path.utf8) == name else { throw Failure.unsafePath }
            guard flags & 0x0800 != 0 || name.allSatisfy({ $0 < 128 }) else {
                throw Failure.unsupportedZIP
            }
            try Self.validatePath(path)
            guard paths.insert(name).inserted else { throw Failure.duplicatePath }
            guard uncompressed <= Self.maximumExpandedBytes - expanded else {
                throw Failure.sizeLimit
            }
            expanded += uncompressed
            try Self.validateExtra(bytes, start: nameStart + nameCount, count: extraCount)
            // A local record must identify exactly the same member. Reconcile
            // its descriptor as well, rather than trusting one header only.
            guard local <= centralOffset - 30, u32(local) == 0x0403_4b50,
                  u16(local + 4) == needed, u16(local + 6) == flags,
                  u16(local + 8) == method, u16(local + 26) == nameCount else {
                throw Failure.malformedZIP
            }
            let localExtra = u16(local + 28), localNameStart = local + 30
            let dataStart = localNameStart + nameCount + localExtra
            guard dataStart <= centralOffset,
                  Data(bytes[localNameStart..<(localNameStart + nameCount)]) == name,
                  compressed <= centralOffset - dataStart else { throw Failure.malformedZIP }
            try Self.validateExtra(bytes, start: localNameStart + nameCount, count: localExtra)
            var localEnd = dataStart + compressed
            if flags & 0x0008 != 0 {
                guard localEnd <= centralOffset - 16, u32(localEnd) == 0x0807_4b50,
                      u32(localEnd + 4) == checksum,
                      Int(u32(localEnd + 8)) == compressed,
                      Int(u32(localEnd + 12)) == uncompressed else { throw Failure.malformedZIP }
                localEnd += 16
            } else {
                guard u32(local + 14) == checksum,
                      Int(u32(local + 18)) == compressed,
                      Int(u32(local + 22)) == uncompressed else { throw Failure.malformedZIP }
            }
            inventory.append(Entry(path: path, pathBytes: name, checksum: checksum,
                                   compressedBytes: compressed, uncompressedBytes: uncompressed,
                                   localOffset: local, endOffset: localEnd))
            cursor = centralEnd
        }
        guard cursor == end else { throw Failure.invalidCount }
        // The original exporter emits contiguous local records followed by one
        // central directory. Reject hidden members, overlaps and SFX prefixes.
        var nextOffset = 0
        for item in inventory.sorted(by: { $0.localOffset < $1.localOffset }) {
            guard item.localOffset == nextOffset else { throw Failure.unindexedData }
            nextOffset = item.endOffset
        }
        guard nextOffset == centralOffset else { throw Failure.unindexedData }
        entries = inventory
    }

    static func validatePath(_ path: String) throws {
        let bytes = path.utf8
        guard !bytes.isEmpty, bytes.count <= 1_024,
              !bytes.contains(0), !bytes.contains(92), !bytes.contains(58),
              bytes.first != 47, bytes.last != 47,
              !bytes.contains(where: { $0 < 32 || $0 == 127 }) else { throw Failure.unsafePath }
        let parts = path.split(separator: "/", omittingEmptySubsequences: false)
        guard parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
            throw Failure.unsafePath
        }
    }

    private static func validateExtra(_ bytes: [UInt8], start: Int, count: Int) throws {
        guard start >= 0, count <= bytes.count - start else { throw Failure.malformedZIP }
        var cursor = start
        let end = start + count
        while cursor < end {
            guard cursor <= end - 4 else { throw Failure.malformedZIP }
            let tag = Int(bytes[cursor]) | Int(bytes[cursor + 1]) << 8
            let length = Int(bytes[cursor + 2]) | Int(bytes[cursor + 3]) << 8
            // The pinned Go ZIP writer emits the extended timestamp. Other
            // layouts require a reviewed codec version instead of silent loss.
            guard tag == 0x5455 else { throw Failure.unsupportedZIP }
            cursor += 4
            guard length <= end - cursor else { throw Failure.malformedZIP }
            cursor += length
        }
    }
}
