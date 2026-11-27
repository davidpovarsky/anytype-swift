import Foundation
import Factory
import Services
import ProtobufMessages
import HanlinHostContracts
import PinkhaHanlinCore

/// Original Heart object-create + native Block.Create composition. These are
/// separate effects, not a transaction. Every effect is durably dispatched once;
/// the original shared runner owns Stop, timeout and draining. The tool is not
/// registered by this type and no title-only callback is a successful save.
@MainActor
enum PinkhaHanlinHeartSaveMessageOperation {
    typealias Authorization = @MainActor @Sendable () throws -> Void
    typealias Receive = @MainActor @Sendable (String) async throws -> Void

    static func execute(plan: PinkhaHanlinSaveMessagePlan, type: ObjectType,
                        body: PinkhaHanlinHeartSaveBody, journal: PinkhaHanlinWriteJournal,
                        authorizeNextEffect: @escaping Authorization,
                        authorizeOriginalRead: @escaping Authorization,
                        receive: @escaping Receive) async throws {
        try body.manifest.validate(plan: plan)
        guard body.manifest.bodyMode == nil,
              plan.identity.session.context.namespace.app.utf8.elementsEqual(PinkhaHanlinEngineNamespace.heart.utf8),
              type.spaceId.utf8.elementsEqual(plan.identity.session.context.namespace.space.utf8),
              type.uniqueKey.value.utf8.elementsEqual(ObjectTypeUniqueKey.page.value.utf8) else {
            throw HanlinHostError.staleContext
        }
        let ledger = try PinkhaHanlinSaveMessageLedger(manifest: body.manifest, store: journal)
        let starting = try await ledger.current()
        guard starting == (try PinkhaHanlinSaveMessageProgress(manifest: body.manifest)) else {
            // Cold/repeated invocation cannot mint a new root or replay a block.
            throw HanlinHostError.unresolvedWrite
        }
        let originalSpace = plan.identity.session.context.namespace.space
        let actions = Container.shared.objectActionsService()
        let blocks = Container.shared.blockService()
        let lifecycle = Container.shared.objectLifecycleService()
        func read(_ objectID: String) async throws -> PinkhaHanlinHeartSaveReadback {
            // Object.Show is a NEW native call. Cancellation/scene/account loss
            // never lets it run through another current global Heart account.
            try authorizeOriginalRead()
            let view = try await lifecycle.openForPreview(contextId: objectID, spaceId: originalSpace)
            try authorizeOriginalRead()
            return try .init(view: view, objectID: objectID, spaceID: originalSpace, typeID: type.id)
        }
        do {
            try authorizeNextEffect()
            try await ledger.observe(.rootDispatched)
            try authorizeNextEffect() // The durable metadata await may race Stop.
            let details = try await actions.createObject(name: plan.title, typeUniqueKey: type.uniqueKey,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: originalSpace, origin: .none, templateId: nil,
                createdInContext: "", createdInContextRef: "", additionalDetails: [])
            guard validReference(details.id), details.spaceId.utf8.elementsEqual(originalSpace.utf8) else {
                throw HanlinHostError.resultMismatch
            }
            // The actual original returned ID is preserved even if authority or
            // title/body validation was lost during the native call. No title
            // lookup, regenerated create request or guessed reference is allowed.
            try await ledger.observe(.rootKnown(reference: details.id))
            try await journal.recordKnownIncompleteObject(details.id, identity: plan.identity)
            let created = try await read(details.id)
            _ = try created.verifyPrefix(body, count: 0)
            try await ledger.observe(.rootVerified(reference: details.id,
                                                  readbackSHA256: created.rootReadbackSHA256()))

            for index in body.blocks.indices {
                try authorizeNextEffect()
                let before = try await read(details.id)
                let previousIDs = try before.verifyPrefix(body, count: index)
                let progress = try await ledger.current()
                guard progress.blocks.prefix(index).allSatisfy(\.isVerified),
                      previousIDs.map({ Data($0.utf8) }) == progress.blocks.prefix(index)
                        .compactMap(\.reference).map({ Data($0.utf8) }) else {
                    throw PinkhaHanlinSaveMessageError.conflictingReceipt
                }
                try authorizeNextEffect()
                try await ledger.observe(.blockDispatched(index: index))
                try authorizeNextEffect()
                let actualID: String
                if let anchor = previousIDs.last {
                    actualID = try await blocks.add(contextId: details.id, targetId: anchor,
                        info: body.blocks[index], position: .bottom)
                } else {
                    actualID = try await blocks.addFirstBlock(contextId: details.id, info: body.blocks[index])
                }
                guard validReference(actualID) else { throw HanlinHostError.resultMismatch }
                try await ledger.observe(.blockKnown(index: index, reference: actualID))
                let after = try await read(details.id)
                let persistedIDs = try after.verifyPrefix(body, count: index + 1)
                guard persistedIDs.last?.utf8.elementsEqual(actualID.utf8) == true,
                      persistedIDs.dropLast().map({ Data($0.utf8) }) == previousIDs.map({ Data($0.utf8) }) else {
                    throw PinkhaHanlinSaveMessageError.conflictingReceipt
                }
                // verifyPrefix rebuilt the canonical semantic block from actual
                // original native bytes and compared its COMPLETE expected hash.
                try await ledger.observe(.blockVerified(index: index, reference: actualID,
                    readbackSHA256: after.blockReadbackSHA256(at: index, plan: body)))
            }
            let current = try await read(details.id)
            let actualBody = try current.verifiedBody(body)
            try await ledger.observe(.bodyVerified(actualBody))
            let complete = try await ledger.current()
            guard complete.isReadyForCommit,
                  complete.bodyReadback == actualBody else { throw HanlinHostError.unresolvedWrite }
            // Metadata can settle after cancellation in the ORIGINAL namespace.
            // The shared worker suppresses stale UI delivery; no new native call
            // is made here and it refuses committed unless this body is durable.
            try await receive(details.id)
        } catch {
            // Closure is durable before any later observation. There is no next
            // native effect on this path and no cleanup/deletion of partial work.
            try await ledger.closeDispatch()
            let progress = try await ledger.current()
            if progress.root == .dispatched { try await ledger.observe(.rootUncertain) }
            if let index = progress.blocks.firstIndex(of: .dispatched) {
                try await ledger.observe(.blockUncertain(index: index))
            }
            throw error
        }
    }

    private static func validReference(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 256 &&
            value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }
}
