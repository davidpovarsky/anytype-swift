import Foundation
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration

/// One original application lease owns root creation, conditional body write,
/// ACK retention and whole-document readback. It is not registered as a tool.
struct AnyHanlinAtomicSaveMessageOperation: Sendable {
    typealias Authorization = @Sendable () async throws -> Void
    typealias Receive = @Sendable (String) async throws -> Void
    let session: HanlinHostSession
    let native: AnyApplicationSession
    let client: AnyHTTPClient
    let creator: AnyNativeObjectCreator
    let authority: AnyHanlinCreationAuthority
    let documents: AnyEditorDocumentStore
    let markdown: AnyNativeMarkdownBody

    init(session: HanlinHostSession, native: AnyApplicationSession, client: AnyHTTPClient,
         creator: AnyNativeObjectCreator, authority: AnyHanlinCreationAuthority,
         documents: AnyEditorDocumentStore, markdown: AnyNativeMarkdownBody) throws {
        let scope = session.context.namespace, original = native.workspace
        guard scope.app.utf8.elementsEqual(PinkhaHanlinEngineNamespace.any.utf8),
              scope.account.utf8.elementsEqual(original.accountID.utf8),
              scope.space.utf8.elementsEqual(original.spaceID.utf8),
              scope.workspace.utf8.elementsEqual(original.spaceID.utf8),
              client.expectedAccountID.utf8.elementsEqual(original.accountID.utf8),
              Self.same(creator.workspace, original), Self.same(authority.workspace, original),
              Self.same(documents.workspace, original), documents.dataset == "editor_blocks" else {
            throw HanlinHostError.invalidContext
        }
        self.session = session; self.native = native; self.client = client
        self.creator = creator; self.authority = authority; self.documents = documents; self.markdown = markdown
    }

    func execute(plan: PinkhaHanlinSaveMessagePlan, body: AnyHanlinAtomicSaveBody,
                 eligibility: AnyHanlinPageEligibility, journal: PinkhaHanlinWriteJournal,
                 authorizeNextEffect: @escaping Authorization, authorizeOriginalRead: @escaping Authorization,
                 receiveFinalRoot: @escaping Receive) async throws {
        guard plan.identity.session == session, eligibility.typeID.utf8.elementsEqual("page".utf8) else {
            throw HanlinHostError.staleContext
        }
        try body.manifest.validate(plan: plan)
        guard body.manifest.bodyMode == .conditionalMarkdown else { throw HanlinHostError.invalidContext }
        let ledger = try PinkhaHanlinSaveMessageLedger(manifest: body.manifest, store: journal)
        let initial = try await ledger.current()
        guard try initial.canonicalBytes() == PinkhaHanlinSaveMessageProgress(manifest: body.manifest).canonicalBytes() else {
            // A repeated or uncertain invocation cannot create a replacement,
            // replay a PUT, or infer an original ACK from current equal text.
            throw HanlinHostError.unresolvedWrite
        }
        let rootIntent = try AnyNativeObjectCreationIntent(workspace: native.workspace,
            mutationID: body.manifest.rootMutationID, typeID: eligibility.typeID, collections: [],
            initialProperties: .object(["any": .object(["name": .string(plan.title)])]))
        try await native.perform { lease in
            let readAuthorization: Authorization = {
                try await self.validateRead(lease: lease, eligibility: eligibility, authorize: authorizeOriginalRead)
            }
            let writeAuthorization: Authorization = {
                do {
                    try await readAuthorization()
                    try await authorizeNextEffect()
                    let current = try await ledger.current()
                    guard !current.dispatchClosed else { throw HanlinHostError.cancelled }
                    try await authorizeNextEffect()
                    try Task.checkCancellation()
                } catch {
                    try await ledger.closeDispatch()
                    throw error
                }
            }
            do {
                try await writeAuthorization()
                try await ledger.observe(.rootDispatched)
                let objectID: String
                do {
                    objectID = try await self.creator.ensureObject(rootIntent, authorize: writeAuthorization,
                        onNativeConfirmed: { id in
                            // Original native creation journal is already durable.
                            // Retain the real root before any new read or body effect.
                            try await ledger.observe(.rootKnown(reference: id))
                            try await journal.recordKnownIncompleteObject(id, identity: plan.identity)
                        })
                } catch {
                    let known: String?
                    if let failure = error as? AnyNativeCreationError,
                       case .createdObjectIncomplete(let id) = failure { known = id }
                    else { known = try await self.creator.recordedObjectID(for: rootIntent) }
                    if let known {
                        try await ledger.observe(.rootKnown(reference: known))
                        try await journal.recordKnownIncompleteObject(known, identity: plan.identity)
                    }
                    throw error
                }
                let reference = try AnyNativeMarkdownReference(accountID: self.native.workspace.accountID,
                    spaceID: self.native.workspace.spaceID, objectID: objectID)
                let fresh = try await self.read(reference, lease: lease, authorize: readAuthorization)
                guard fresh.read.snapshot.blocks.isEmpty, fresh.read.snapshot.depthFirstIDs.isEmpty,
                      fresh.read.snapshot.unreachableIDs.isEmpty, fresh.read.markdown.isEmpty,
                      fresh.semantic.rootReadbackSHA256 == body.manifest.expectedRootReadbackSHA256 else {
                    throw PinkhaHanlinSaveMessageError.conflictingReceipt
                }
                try await ledger.observe(.rootVerified(reference: objectID,
                    readbackSHA256: fresh.semantic.rootReadbackSHA256))
                let empty = try await self.markdown.read(reference, authorize: readAuthorization)
                guard empty.reference == reference, empty.content.isEmpty, empty.contentBytes == 0,
                      empty.version.utf8.elementsEqual(fresh.read.nativeVersion.utf8) else {
                    throw PinkhaHanlinSaveMessageError.conflictingReceipt
                }
                let intent = try body.intent(reference: reference, expectedVersion: empty.version)
                let requestSHA256 = try body.requestSHA256(intent, generation: lease.generation,
                                                          engineStartedAt: lease.engineStartedAt)
                try await writeAuthorization()
                try await ledger.observe(.atomicBodyDispatched(requestSHA256: requestSHA256,
                    expectedVersionSHA256: AnyHanlinAtomicSaveBody.digest(intent.expectedVersion)))
                let receipt: AnyNativeMarkdownWriteReceipt
                do {
                    receipt = try await self.markdown.replace(intent, authorizeRead: readAuthorization,
                                                             authorizeWrite: writeAuthorization)
                } catch let failure as AnyNativeMarkdownWriteFailure {
                    switch failure {
                    case .uncertain(let context):
                        guard context.reference == reference,
                              context.requestID.utf8.elementsEqual(intent.context.requestID.utf8),
                              context.requestedContentSHA256 == intent.context.requestedContentSHA256,
                              context.requestedContentBytes == intent.context.requestedContentBytes else {
                            throw PinkhaHanlinSaveMessageError.conflictingReceipt
                        }
                    case .acknowledgedReadbackUnavailable(let acknowledgement),
                         .acknowledgedReadbackChanged(let acknowledgement):
                        try await self.retain(acknowledgement, intent: intent,
                                              requestSHA256: requestSHA256, ledger: ledger)
                    }
                    throw failure
                }
                try await self.retain(receipt.acknowledgement, intent: intent,
                                      requestSHA256: requestSHA256, ledger: ledger)
                guard receipt.saved.reference == reference,
                      receipt.saved.version.utf8.elementsEqual(receipt.acknowledgement.nativeVersion.utf8),
                      receipt.saved.contentSHA256 == AnyHanlinAtomicSaveBody.digest(receipt.saved.content),
                      receipt.saved.contentBytes == receipt.saved.content.utf8.count else {
                    throw PinkhaHanlinSaveMessageError.conflictingReceipt
                }
                let actual = try await self.read(reference, lease: lease, authorize: readAuthorization)
                guard actual.read.nativeVersion.utf8.elementsEqual(receipt.saved.version.utf8),
                      actual.read.markdown.utf8.elementsEqual(receipt.saved.content.utf8) else {
                    throw AnyHostError.changedDocument
                }
                let boundary = try await self.markdown.read(reference, authorize: readAuthorization)
                guard boundary.version.utf8.elementsEqual(receipt.saved.version.utf8),
                      boundary.contentSHA256 == receipt.saved.contentSHA256,
                      boundary.contentBytes == receipt.saved.contentBytes else {
                    throw AnyHostError.changedDocument
                }
                let witness = try actual.semantic.verifiedBody(manifest: body.manifest,
                    nativeVersionSHA256: AnyHanlinAtomicSaveBody.digest(receipt.saved.version),
                    nativeMarkdownSHA256: receipt.saved.contentSHA256,
                    nativeMarkdownUTF8Bytes: receipt.saved.contentBytes)
                let complete = try await ledger.observe(.bodyVerified(witness))
                guard complete.isReadyForCommit else { throw HanlinHostError.unresolvedWrite }
                // This is metadata in the original namespace. The shared runner
                // alone commits/delivers, and suppresses stale foreground output.
                try await receiveFinalRoot(objectID)
            } catch {
                try await ledger.closeDispatch()
                let current = try await ledger.current()
                if current.root == .dispatched { try await ledger.observe(.rootUncertain) }
                if current.atomicBody?.outcome == .dispatched { try await ledger.observe(.atomicBodyUncertain) }
                throw error
            }
        }
    }

    private func retain(_ acknowledgement: AnyNativeMarkdownAcknowledgement,
                        intent: AnyNativeMarkdownWriteIntent, requestSHA256: String,
                        ledger: PinkhaHanlinSaveMessageLedger) async throws {
        try AnyHanlinAtomicSaveBody.validate(acknowledgement, intent: intent)
        let admitted: PinkhaHanlinSaveMessageAtomicAcknowledgement
        do {
            admitted = try AnyHanlinAtomicSaveBody.admittedAcknowledgement(acknowledgement,
                intent: intent, requestSHA256: requestSHA256)
        } catch {
            // A real ACK outside this strict consumer bound remains unresolved.
            // Retain its full, untruncated fingerprint; never substitute fewer IDs.
            let digest = try AnyHanlinAtomicSaveBody.unadmittedAcknowledgementDigest(acknowledgement,
                intent: intent, requestSHA256: requestSHA256)
            try await ledger.observe(.atomicBodyAcknowledged(requestSHA256: requestSHA256,
                savedVersionSHA256: AnyHanlinAtomicSaveBody.digest(acknowledgement.nativeVersion),
                nativeReceiptSHA256: digest))
            throw error
        }
        // Persistence failures do not retry through a weaker digest-only path.
        try await ledger.observe(.atomicBodyReceipt(admitted))
    }

    private func read(_ reference: AnyNativeMarkdownReference, lease: AnyHostLease,
                      authorize: @escaping Authorization) async throws -> (read: AnyEditorRead, semantic: AnyHanlinSaveMessageReadback) {
        try await authorize()
        let value = try await documents.read(objectID: reference.objectID, lease: lease)
        guard value.generation == lease.generation,
              value.engineStartedAt.utf8.elementsEqual(lease.engineStartedAt.utf8),
              value.snapshot.objectID.utf8.elementsEqual(reference.objectID.utf8) else {
            throw HanlinHostError.staleContext
        }
        let response = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", reference.spaceID, "objects", reference.objectID], authorize: authorize)
        guard response["objectId"]?.string?.utf8.elementsEqual(reference.objectID.utf8) == true,
              let record = response["record"] else { throw PinkhaHanlinSaveMessageError.conflictingReceipt }
        let semantic = try AnyHanlinSaveMessageReadback(snapshot: value.snapshot, rootRecord: record, workspace: lease.workspace)
        try await authorize()
        return (value, semantic)
    }

    private func validateRead(lease: AnyHostLease, eligibility: AnyHanlinPageEligibility,
                              authorize: @escaping Authorization) async throws {
        try await authorize(); try await lease.validate()
        guard Self.same(lease.workspace, native.workspace), lease.generation == native.generation,
              lease.engineStartedAt.utf8.elementsEqual(native.engineStartedAt.utf8),
              try await authority.inspect(lease: lease) == eligibility else {
            throw HanlinHostError.staleContext
        }
        try await authorize(); try await lease.validate()
    }

    private static func same(_ lhs: AnyTorahWorkspace, _ rhs: AnyTorahWorkspace) -> Bool {
        lhs.accountID.utf8.elementsEqual(rhs.accountID.utf8) && lhs.spaceID.utf8.elementsEqual(rhs.spaceID.utf8)
    }
}
