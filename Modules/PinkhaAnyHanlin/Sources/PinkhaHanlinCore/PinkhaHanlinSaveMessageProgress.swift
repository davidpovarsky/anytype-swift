import Foundation

/// Metadata only. A native converter supplies a complete, preflighted semantic
/// block plan; its bytes stay in memory. Hashes are bindings, not native proof.
public struct PinkhaHanlinSaveMessageManifest: Codable, Equatable, Sendable {
    public static let conversionContract = "pinkha-hanlin-markdown-native-blocks-v1"
    public let version: Int
    public let identity: PinkhaHanlinWriteIdentity
    public let identitySHA256: String
    public let titleSHA256: String
    public let titleUTF8Bytes: Int
    public let markdownSHA256: String
    public let markdownUTF8Bytes: Int
    public let conversion: String
    public let bodyPlanSHA256: String
    public let expectedRootReadbackSHA256: String
    public let expectedBodyReadbackSHA256: String
    /// Expected canonical semantic block readbacks in document order. Native
    /// auto-IDs are bound separately; title/content/style/hierarchy are not omitted.
    public let blockSHA256: [String]

    public init(plan: PinkhaHanlinSaveMessagePlan, bodyPlanSHA256: String,
                expectedRootReadbackSHA256: String, expectedBodyReadbackSHA256: String,
                blockSHA256: [String]) throws {
        version = 1
        identity = plan.identity
        identitySHA256 = try Self.digest(plan.identity)
        titleSHA256 = plan.titleSHA256
        titleUTF8Bytes = plan.title.utf8.count
        markdownSHA256 = plan.markdownSHA256
        markdownUTF8Bytes = plan.markdown.utf8.count
        conversion = Self.conversionContract
        self.bodyPlanSHA256 = bodyPlanSHA256
        self.expectedRootReadbackSHA256 = expectedRootReadbackSHA256
        self.expectedBodyReadbackSHA256 = expectedBodyReadbackSHA256
        self.blockSHA256 = blockSHA256
        try validate()
    }

    /// Stable native mutation IDs derive from the ORIGINAL session/invocation,
    /// plus the complete converted plan. Restart/reconciliation cannot mint IDs.
    public var rootMutationID: String {
        String(PinkhaHanlinSaveMessagePlan.materialDigest(
            ["pinkha-hanlin-save-root/v1", identitySHA256, bodyPlanSHA256]).prefix(32))
    }

    public func blockMutationID(at index: Int) throws -> String {
        guard blockSHA256.indices.contains(index) else { throw PinkhaHanlinSaveMessageError.invalidProgress }
        return String(PinkhaHanlinSaveMessagePlan.materialDigest(
            ["pinkha-hanlin-save-block/v1", identitySHA256, bodyPlanSHA256,
             String(index), blockSHA256[index]]).prefix(32))
    }

    public func validate(plan: PinkhaHanlinSaveMessagePlan) throws {
        try validate()
        guard try Self.digest(plan.identity) == identitySHA256,
              plan.titleSHA256 == titleSHA256, plan.title.utf8.count == titleUTF8Bytes,
              plan.markdownSHA256 == markdownSHA256,
              plan.markdown.utf8.count == markdownUTF8Bytes else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
    }

    public func validate() throws {
        try identity.validate()
        guard version == 1, conversion == Self.conversionContract,
              identitySHA256 == (try Self.digest(identity)),
              PinkhaHanlinWriteIdentity.isDigest(titleSHA256),
              PinkhaHanlinWriteIdentity.isDigest(markdownSHA256),
              PinkhaHanlinWriteIdentity.isDigest(bodyPlanSHA256),
              PinkhaHanlinWriteIdentity.isDigest(expectedRootReadbackSHA256),
              PinkhaHanlinWriteIdentity.isDigest(expectedBodyReadbackSHA256),
              (1...PinkhaHanlinSaveMessagePlan.maximumTitleUTF8Bytes).contains(titleUTF8Bytes),
              (1...PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes).contains(markdownUTF8Bytes),
              (1...PinkhaHanlinSaveMessagePlan.maximumBlocks).contains(blockSHA256.count),
              blockSHA256.allSatisfy(PinkhaHanlinWriteIdentity.isDigest) else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        let ids = try blockSHA256.indices.map { try blockMutationID(at: $0) }
        guard Set(ids).count == ids.count, !ids.contains(rootMutationID) else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
    }

    public func canonicalSHA256() throws -> String { try Self.digest(self) }

    static func digest<T: Encodable>(_ value: T) throws -> String {
        PinkhaHanlinSaveMessagePlan.digest(try PinkhaHanlinSaveMessagePlan.canonicalBytes(value))
    }
}

/// The original native owner constructs this only after reading the entire new
/// document: title, ordered block identities, content, style and hierarchy. This
/// metadata value alone is not authority and must never be decoded from tool args.
public struct PinkhaHanlinSaveMessageBodyReadback: Codable, Equatable, Sendable {
    public let manifestSHA256: String
    public let objectReference: String
    public let blockReferences: [String]
    public let nativeReadbackSHA256: String

    public init(manifestSHA256: String, objectReference: String, blockReferences: [String],
                nativeReadbackSHA256: String) {
        self.manifestSHA256 = manifestSHA256
        self.objectReference = objectReference
        self.blockReferences = blockReferences
        self.nativeReadbackSHA256 = nativeReadbackSHA256
    }
}

public struct PinkhaHanlinSaveMessageProgress: Codable, Equatable, Sendable {
    public enum NativeEffect: Codable, Equatable, Sendable {
        case pending
        case dispatched
        case uncertain(knownReference: String?)
        case verified(reference: String, readbackSHA256: String)

        public var reference: String? {
            switch self {
            case .pending, .dispatched: nil
            case .uncertain(let reference): reference
            case .verified(let reference, _): reference
            }
        }

        public var isVerified: Bool {
            if case .verified = self { return true }
            return false
        }
    }

    public enum Event: Codable, Equatable, Sendable {
        case rootDispatched
        case rootKnown(reference: String)
        case rootVerified(reference: String, readbackSHA256: String)
        case rootUncertain
        case blockDispatched(index: Int)
        case blockKnown(index: Int, reference: String)
        case blockVerified(index: Int, reference: String, readbackSHA256: String)
        case blockUncertain(index: Int)
        case closeDispatch
        case bodyVerified(PinkhaHanlinSaveMessageBodyReadback)
    }

    public let version: Int
    public let manifest: PinkhaHanlinSaveMessageManifest
    public private(set) var sequence: Int
    public private(set) var root: NativeEffect
    public private(set) var blocks: [NativeEffect]
    public private(set) var dispatchClosed: Bool
    public private(set) var bodyReadback: PinkhaHanlinSaveMessageBodyReadback?

    public init(manifest: PinkhaHanlinSaveMessageManifest) throws {
        version = 1
        self.manifest = manifest
        sequence = 0
        root = .pending
        blocks = Array(repeating: .pending, count: manifest.blockSHA256.count)
        dispatchClosed = false
        bodyReadback = nil
        try validate()
    }

    /// The maximum follows from four monotonic transitions per native effect,
    /// plus closing dispatch and recording one complete document readback.
    public static let maximumEvents = 4 * (PinkhaHanlinSaveMessagePlan.maximumBlocks + 1) + 2
    public static let maximumEncodedBytes = 131_072

    public var isNotDispatched: Bool { dispatchClosed && root == .pending }
    public var isReadyForCommit: Bool { bodyReadback != nil }

    /// This is a pure transition, not a disk write. Its returned value must be
    /// durably appended by the original journal BEFORE the corresponding native
    /// dispatch or final Hanlin receipt. A replay of identical metadata is a no-op.
    public func applying(_ event: Event) throws -> Self {
        try validate()
        var next = self
        switch event {
        case .rootDispatched:
            guard !dispatchClosed, root == .pending else { throw PinkhaHanlinSaveMessageError.invalidTransition }
            next.root = .dispatched
        case .rootKnown(let reference):
            next.root = try Self.observe(root, reference: reference, readbackSHA256: nil)
        case .rootVerified(let reference, let digest):
            guard digest == manifest.expectedRootReadbackSHA256 else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
            next.root = try Self.observe(root, reference: reference, readbackSHA256: digest)
        case .rootUncertain:
            next.root = try Self.markUncertain(root)
        case .blockDispatched(let index):
            try requireBlock(index)
            guard !dispatchClosed, root.isVerified, blocks[index] == .pending,
                  blocks.prefix(index).allSatisfy(\.isVerified) else {
                throw PinkhaHanlinSaveMessageError.invalidTransition
            }
            next.blocks[index] = .dispatched
        case .blockKnown(let index, let reference):
            try requireBlock(index)
            next.blocks[index] = try Self.observe(blocks[index], reference: reference, readbackSHA256: nil)
        case .blockVerified(let index, let reference, let digest):
            try requireBlock(index)
            guard digest == manifest.blockSHA256[index] else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
            next.blocks[index] = try Self.observe(blocks[index], reference: reference, readbackSHA256: digest)
        case .blockUncertain(let index):
            try requireBlock(index)
            next.blocks[index] = try Self.markUncertain(blocks[index])
        case .closeDispatch:
            next.dispatchClosed = true
        case .bodyVerified(let readback):
            try validateReadback(readback)
            if let original = bodyReadback, original != readback {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
            next.bodyReadback = readback
        }
        if next == self { return self }
        guard sequence < Self.maximumEvents else { throw PinkhaHanlinSaveMessageError.invalidProgress }
        next.sequence += 1
        try next.validate()
        return next
    }

    public func validate() throws {
        try manifest.validate()
        guard version == 1, (0...Self.maximumEvents).contains(sequence),
              blocks.count == manifest.blockSHA256.count else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        try Self.validateEffect(root)
        if case .verified(_, let digest) = root, digest != manifest.expectedRootReadbackSHA256 {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        for (index, block) in blocks.enumerated() {
            try Self.validateEffect(block)
            if case .verified(_, let digest) = block, digest != manifest.blockSHA256[index] {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
        }
        if !root.isVerified, blocks.contains(where: { $0 != .pending }) {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        var foundUnfinished = false
        for block in blocks {
            if foundUnfinished, block != .pending { throw PinkhaHanlinSaveMessageError.invalidProgress }
            if !block.isVerified { foundUnfinished = true }
        }
        let references = blocks.compactMap(\.reference)
        guard Set(references.map { Data($0.utf8) }).count == references.count else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        if let rootReference = root.reference,
           references.contains(where: { $0.utf8.elementsEqual(rootReference.utf8) }) {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        if let bodyReadback { try validateReadback(bodyReadback) }
        let ranges = ([root] + blocks).map(Self.transitionRange)
        let extra = (dispatchClosed ? 1 : 0) + (bodyReadback == nil ? 0 : 1)
        let minimum = ranges.reduce(extra) { $0 + $1.lowerBound }
        let maximum = ranges.reduce(extra) { $0 + $1.upperBound }
        guard (minimum...maximum).contains(sequence) else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
    }

    public func validate(identity: PinkhaHanlinWriteIdentity) throws {
        try validate()
        guard try PinkhaHanlinSaveMessageManifest.digest(identity) == manifest.identitySHA256 else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
    }

    public func canonicalBytes() throws -> Data {
        try validate()
        let bytes = try PinkhaHanlinSaveMessagePlan.canonicalBytes(self)
        guard bytes.count <= Self.maximumEncodedBytes else { throw PinkhaHanlinSaveMessageError.invalidProgress }
        return bytes
    }

    public func canonicalSHA256() throws -> String { PinkhaHanlinSaveMessagePlan.digest(try canonicalBytes()) }

    public static func decodeCanonical(_ bytes: Data, identity: PinkhaHanlinWriteIdentity) throws -> Self {
        guard bytes.count <= maximumEncodedBytes else { throw PinkhaHanlinSaveMessageError.invalidProgress }
        let result = try JSONDecoder().decode(Self.self, from: bytes)
        try result.validate(identity: identity)
        guard try result.canonicalBytes() == bytes else { throw PinkhaHanlinSaveMessageError.invalidProgress }
        return result
    }

    private func requireBlock(_ index: Int) throws {
        guard blocks.indices.contains(index) else { throw PinkhaHanlinSaveMessageError.invalidProgress }
    }

    private func validateReadback(_ value: PinkhaHanlinSaveMessageBodyReadback) throws {
        guard root.isVerified, let rootReference = root.reference, blocks.allSatisfy(\.isVerified),
              value.manifestSHA256 == (try manifest.canonicalSHA256()),
              value.objectReference.utf8.elementsEqual(rootReference.utf8),
              value.blockReferences.map({ Data($0.utf8) }) == blocks.compactMap(\.reference).map({ Data($0.utf8) }),
              value.nativeReadbackSHA256 == manifest.expectedBodyReadbackSHA256 else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
    }

    private static func validateEffect(_ effect: NativeEffect) throws {
        if let reference = effect.reference, !PinkhaHanlinSaveMessagePlan.validReference(reference) {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        if case .verified(_, let digest) = effect, !PinkhaHanlinWriteIdentity.isDigest(digest) {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
    }

    private static func transitionRange(_ effect: NativeEffect) -> ClosedRange<Int> {
        switch effect {
        case .pending: 0...0
        case .dispatched: 1...1
        case .uncertain(let reference): reference == nil ? 2...2 : 2...3
        case .verified: 2...4
        }
    }

    private static func observe(_ old: NativeEffect, reference: String, readbackSHA256: String?) throws -> NativeEffect {
        guard old != .pending, PinkhaHanlinSaveMessagePlan.validReference(reference),
              readbackSHA256.map(PinkhaHanlinWriteIdentity.isDigest) ?? true else {
            throw PinkhaHanlinSaveMessageError.invalidTransition
        }
        if let known = old.reference, !known.utf8.elementsEqual(reference.utf8) {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        if case .verified(_, let digest) = old {
            guard readbackSHA256 == nil || readbackSHA256 == digest else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
            return old
        }
        if let readbackSHA256 { return .verified(reference: reference, readbackSHA256: readbackSHA256) }
        return .uncertain(knownReference: reference)
    }

    private static func markUncertain(_ old: NativeEffect) throws -> NativeEffect {
        switch old {
        case .pending: throw PinkhaHanlinSaveMessageError.invalidTransition
        case .dispatched: .uncertain(knownReference: nil)
        case .uncertain, .verified: old
        }
    }
}
