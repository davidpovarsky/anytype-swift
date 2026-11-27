import Foundation

/// Absence of this optional manifest field retains the original ordered-block
/// contract and its exact canonical bytes. One conditional native body write is
/// a different effect; it must never synthesize per-block dispatch receipts.
public enum PinkhaHanlinSaveMessageBodyMode: String, Codable, Equatable, Sendable {
    case conditionalMarkdown
}

/// Exact metadata from one actual native ACK. These IDs are retained even when
/// its authorized body readback is no longer available. They confer no authority
/// and are never fabricated from a later body snapshot or model arguments.
public struct PinkhaHanlinSaveMessageAtomicAcknowledgement: Codable, Equatable, Sendable {
    public let version: Int
    public let requestSHA256: String
    public let savedVersionSHA256: String
    public let nativeReceiptSHA256: String
    public let insertedReferences: [String]
    public let updatedReferences: [String]
    public let deletedReferences: [String]
    public let unchangedBlocks: Int64

    public init(requestSHA256: String, savedVersionSHA256: String,
                insertedReferences: [String], updatedReferences: [String],
                deletedReferences: [String], unchangedBlocks: Int64) throws {
        version = 1; self.requestSHA256 = requestSHA256
        self.savedVersionSHA256 = savedVersionSHA256
        self.insertedReferences = insertedReferences; self.updatedReferences = updatedReferences
        self.deletedReferences = deletedReferences; self.unchangedBlocks = unchangedBlocks
        nativeReceiptSHA256 = try Self.digestUnadmittedNativeReceipt(requestSHA256: requestSHA256,
            savedVersionSHA256: savedVersionSHA256, insertedReferences: insertedReferences,
            updatedReferences: updatedReferences, deletedReferences: deletedReferences,
            unchangedBlocks: unchangedBlocks)
        try validate()
    }

    public func validate() throws {
        let all = insertedReferences + updatedReferences + deletedReferences
        guard version == 1, all.count <= PinkhaHanlinSaveMessagePlan.maximumBlocks,
              all.allSatisfy(PinkhaHanlinSaveMessagePlan.validReference),
              Set(all.map { Data($0.utf8) }).count == all.count,
              (0...Int64(PinkhaHanlinSaveMessagePlan.maximumBlocks)).contains(unchangedBlocks),
              nativeReceiptSHA256 == (try Self.digestUnadmittedNativeReceipt(requestSHA256: requestSHA256,
                savedVersionSHA256: savedVersionSHA256, insertedReferences: insertedReferences,
                updatedReferences: updatedReferences, deletedReferences: deletedReferences,
                unchangedBlocks: unchangedBlocks)) else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
    }

    public func canonicalBytes() throws -> Data {
        try validate()
        let bytes = try PinkhaHanlinSaveMessagePlan.canonicalBytes(self)
        guard bytes.count <= PinkhaHanlinSaveMessageProgressRecord.maximumEncodedBytes else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        return bytes
    }

    /// Hashes an actual native ACK that exceeds this consumer's admission bound
    /// without truncating its IDs. Only the digest may then be retained as an
    /// unresolved outcome; this helper cannot construct a verified body receipt.
    public static func digestUnadmittedNativeReceipt(requestSHA256: String, savedVersionSHA256: String,
        insertedReferences: [String], updatedReferences: [String], deletedReferences: [String],
        unchangedBlocks: Int64) throws -> String {
        let all = insertedReferences + updatedReferences + deletedReferences
        guard PinkhaHanlinWriteIdentity.isDigest(requestSHA256),
              PinkhaHanlinWriteIdentity.isDigest(savedVersionSHA256),
              all.count <= 10_000, all.allSatisfy({ $0.utf8.count <= 4_096 }),
              all.reduce(0, { $0 + $1.utf8.count }) <= 4_194_304,
              (0...10_000).contains(unchangedBlocks) else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        struct Material: Encodable {
            let contract: String; let requestSHA256: String; let savedVersionSHA256: String
            let insertedReferences: [String]; let updatedReferences: [String]; let deletedReferences: [String]
            let unchangedBlocks: Int64
        }
        let bytes = try PinkhaHanlinSaveMessagePlan.canonicalBytes(Material(
            contract: "pinkha-hanlin-native-markdown-ack/v1", requestSHA256: requestSHA256,
            savedVersionSHA256: savedVersionSHA256, insertedReferences: insertedReferences,
            updatedReferences: updatedReferences, deletedReferences: deletedReferences,
            unchangedBlocks: unchangedBlocks))
        guard bytes.count <= 8_388_608 else { throw PinkhaHanlinSaveMessageError.conflictingReceipt }
        return PinkhaHanlinSaveMessagePlan.digest(bytes)
    }
}

/// Metadata for ONE original native conditional body operation. The request ID
/// is host correlation, never a claim that native supports mutation-ID dedup.
/// An uncertain operation cannot dispatch again, even when current text matches.
public struct PinkhaHanlinSaveMessageAtomicBody: Codable, Equatable, Sendable {
    public enum Outcome: Codable, Equatable, Sendable {
        case dispatched
        case uncertain
        case acknowledged(savedVersionSHA256: String, nativeReceiptSHA256: String)
    }

    public let requestSHA256: String
    public let expectedVersionSHA256: String
    public private(set) var outcome: Outcome
    /// Nil is a digest-only unresolved ACK. It can never certify a full body.
    public private(set) var acknowledgement: PinkhaHanlinSaveMessageAtomicAcknowledgement?

    public init(requestSHA256: String, expectedVersionSHA256: String) throws {
        self.requestSHA256 = requestSHA256
        self.expectedVersionSHA256 = expectedVersionSHA256
        outcome = .dispatched
        acknowledgement = nil
        try validate()
    }

    public func validate() throws {
        guard PinkhaHanlinWriteIdentity.isDigest(requestSHA256),
              PinkhaHanlinWriteIdentity.isDigest(expectedVersionSHA256) else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        if case .acknowledged(let version, let receipt) = outcome {
            guard PinkhaHanlinWriteIdentity.isDigest(version),
                  PinkhaHanlinWriteIdentity.isDigest(receipt) else {
                throw PinkhaHanlinSaveMessageError.invalidProgress
            }
        }
        if let acknowledgement {
            try acknowledgement.validate()
            guard acknowledgement.requestSHA256 == requestSHA256,
                  outcome == .acknowledged(savedVersionSHA256: acknowledgement.savedVersionSHA256,
                    nativeReceiptSHA256: acknowledgement.nativeReceiptSHA256) else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
        }
    }

    func markedUncertain() throws -> Self {
        try validate()
        var next = self
        if case .dispatched = outcome { next.outcome = .uncertain }
        return next
    }

    func retaining(_ receipt: PinkhaHanlinSaveMessageAtomicAcknowledgement) throws -> Self {
        try receipt.validate()
        var next = try acknowledged(requestSHA256: receipt.requestSHA256,
            savedVersionSHA256: receipt.savedVersionSHA256, nativeReceiptSHA256: receipt.nativeReceiptSHA256)
        if let original = acknowledgement,
           try original.canonicalBytes() != receipt.canonicalBytes() {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        next.acknowledgement = receipt
        try next.validate()
        return next
    }

    func acknowledged(requestSHA256: String, savedVersionSHA256: String,
                      nativeReceiptSHA256: String) throws -> Self {
        try validate()
        guard requestSHA256 == self.requestSHA256 else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        let observation = Outcome.acknowledged(savedVersionSHA256: savedVersionSHA256,
                                              nativeReceiptSHA256: nativeReceiptSHA256)
        if case .acknowledged = outcome, outcome != observation {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        var next = self
        next.outcome = observation
        try next.validate()
        return next
    }

    var transitionRange: ClosedRange<Int> {
        switch outcome {
        case .dispatched: 1...1
        case .uncertain: 2...2
        case .acknowledged: acknowledgement == nil ? 2...3 : 2...4
        }
    }
}
