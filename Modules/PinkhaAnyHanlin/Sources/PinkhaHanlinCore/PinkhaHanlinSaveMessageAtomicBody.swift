import Foundation

/// Absence of this optional manifest field retains the original ordered-block
/// contract and its exact canonical bytes. One conditional native body write is
/// a different effect; it must never synthesize per-block dispatch receipts.
public enum PinkhaHanlinSaveMessageBodyMode: String, Codable, Equatable, Sendable {
    case conditionalMarkdown
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

    public init(requestSHA256: String, expectedVersionSHA256: String) throws {
        self.requestSHA256 = requestSHA256
        self.expectedVersionSHA256 = expectedVersionSHA256
        outcome = .dispatched
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
    }

    func markedUncertain() throws -> Self {
        try validate()
        var next = self
        if case .dispatched = outcome { next.outcome = .uncertain }
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
        case .acknowledged: 2...3
        }
    }
}
