import Foundation

/// One original serial native worker owns observations. The shared SDK runner
/// may close dispatch concurrently through the SAME protected store. This
/// helper retries only that one monotonic metadata race, never a native effect.
public actor PinkhaHanlinSaveMessageLedger {
    public let manifest: PinkhaHanlinSaveMessageManifest
    private let store: any PinkhaHanlinSaveMessageProgressStore

    public init(manifest: PinkhaHanlinSaveMessageManifest,
                store: any PinkhaHanlinSaveMessageProgressStore) throws {
        try manifest.validate()
        self.manifest = manifest; self.store = store
    }

    public func current() async throws -> PinkhaHanlinSaveMessageProgress {
        guard let value = try await store.saveMessageProgress(for: manifest.identity) else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        try value.validate(identity: manifest.identity)
        guard try value.manifest.canonicalSHA256() == manifest.canonicalSHA256() else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        return value
    }

    @discardableResult
    public func observe(_ event: PinkhaHanlinSaveMessageProgress.Event) async throws -> PinkhaHanlinSaveMessageProgress {
        let expected = try await current()
        let wanted = try expected.applying(event)
        if try wanted.canonicalBytes() == expected.canonicalBytes() { return expected }
        do {
            let result = try await store.advanceSaveMessage(expected, event: event)
            guard try result.canonicalBytes() == wanted.canonicalBytes() else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
            return result
        } catch PinkhaHanlinWriteError.conflict {
            // A close is the ONLY other writer permitted here. Byte equality
            // includes sequence, every native ID/digest and the original manifest.
            let closed = try expected.applying(.closeDispatch)
            let observed = try await current()
            guard !expected.dispatchClosed,
                  try observed.canonicalBytes() == closed.canonicalBytes() else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
            let wantedAfterClose = try observed.applying(event)
            if try wantedAfterClose.canonicalBytes() == observed.canonicalBytes() { return observed }
            let result = try await store.advanceSaveMessage(observed, event: event)
            guard try result.canonicalBytes() == wantedAfterClose.canonicalBytes() else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
            return result
        }
    }

    public func closeDispatch() async throws {
        try await store.closeSaveMessageDispatch(for: manifest.identity)
        let value = try await current()
        guard value.dispatchClosed || value.isReadyForCommit else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
    }
}
