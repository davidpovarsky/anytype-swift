import Foundation
import Testing
@testable import PinkhaAnyUI

@Suite("Canonical archive reads reach bounded EOF")
struct AnyCanonicalArchiveBoundedReaderTests {
    @Test func shortValidPrefixDoesNotHideUnreadTrailingBytes() throws {
        var chunks = [Data("{}".utf8), Data(" trailing".utf8)]
        let result = try AnyCanonicalArchiveBoundedReader.read(maximumBytes: 64) { _ in
            chunks.isEmpty ? nil : chunks.removeFirst()
        }
        #expect(result == Data("{} trailing".utf8))
        #expect(chunks.isEmpty)
    }
    @Test func exactBoundStillChecksEOFAndAnExtraByteFails() throws {
        var count = 0
        let result = try AnyCanonicalArchiveBoundedReader.read(maximumBytes: 2) { requested in
            count += 1
            if count == 1 { return Data("{}".utf8) }
            #expect(requested == 1)
            return nil
        }
        #expect(result.count == 2 && count == 2)
        var chunks = [Data("{}".utf8), Data("x".utf8)]
        #expect(throws: (any Error).self) {
            try AnyCanonicalArchiveBoundedReader.read(maximumBytes: 2) { _ in chunks.removeFirst() }
        }
    }
    @Test func emptyAndOversizedProviderChunksAreRejected() throws {
        #expect(throws: (any Error).self) { try AnyCanonicalArchiveBoundedReader.read(maximumBytes: 2) { _ in nil } }
        #expect(throws: (any Error).self) {
            try AnyCanonicalArchiveBoundedReader.read(maximumBytes: 2) { _ in Data(repeating: 0, count: 4) }
        }
    }
}
