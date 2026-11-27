#if canImport(UIKit)
import Foundation
import UIKit
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaAnyHanlin
import PinkhaAnyEngine
import PinkhaAnyHost

extension AnyHanlinPresentation {
    /// The real editor supplies its existing native session and services. A
    /// Release or ordinary Debug call follows the original presentation path.
    @MainActor
    @discardableResult
    public static func presentFromNativeEditor(
        from presenter: UIViewController, native: AnyApplicationSession,
        documents: AnyEditorDocumentStore, client: AnyHTTPClient,
        sourceOwner: any AnyHanlinSourcePresentationOwner,
        conversationID: UUID, locale: Locale = .autoupdatingCurrent,
        creation: AnyHanlinCreationServices? = nil
    ) async throws -> PinkhaHanlinChatController {
        #if DEBUG && targetEnvironment(simulator)
        if let request = try PinkhaHanlinSaveMessageAcceptancePreparation.loadIfRequested(engine: .any) {
            let admission = try await AnyHanlinSaveMessageNativeAdmission.inspect(native: native,
                documents: documents, client: client, sourceOwner: sourceOwner,
                accountID: request.accountID, spaceID: request.spaceID, objectID: request.sourceObjectID)
            try PinkhaHanlinSaveMessageAcceptancePreparation.record(request: request,
                sourceRevision: admission.sourceRevision,
                nativeSourceReadbackSHA256: admission.sourceMarkdownSHA256,
                nativeSourceVersionSHA256: admission.sourceVersionSHA256,
                anyRuntime: .init(generation: native.generation, engineStartedAt: native.engineStartedAt))
            // Preparation performed only original reads. Its returned sheet is
            // the ordinary create-only host. Close it before supplying the fresh
            // fixture bound to the newly observed process/runtime receipt.
            return try present(from: presenter, native: native, documents: documents,
                sourceOwner: sourceOwner, conversationID: conversationID, locale: locale, creation: creation)
        }
        if let fixture = try PinkhaHanlinSaveMessageAcceptanceFixture.loadIfRequested(engine: .any) {
            guard let creation, creation.creator.workspace == native.workspace,
                  creation.authority.workspace == native.workspace else { throw HanlinHostError.invalidContext }
            let admission = try await AnyHanlinSaveMessageNativeAdmission.inspect(native: native,
                documents: documents, client: client, sourceOwner: sourceOwner,
                accountID: fixture.accountID, spaceID: fixture.spaceID, objectID: fixture.sourceObjectID,
                fixture: fixture)
            return try presentForSaveMessageAcceptance(from: presenter, native: native,
                documents: documents, client: client, sourceOwner: sourceOwner,
                conversationID: conversationID, locale: locale, creation: creation,
                hooks: .init(didMount: { presentation, controller in
                    PinkhaHanlinSaveMessageAcceptanceDriver.start(fixture: fixture,
                        presentation: presentation, controller: controller,
                        verifyStoppedRoot: { progress in
                            try await admission.verifyStoppedRoot(progress, fixture: fixture,
                                native: native, documents: documents, client: client, sourceOwner: sourceOwner)
                        }) { snapshot in
                        try await admission.verifyCreatedDocument(snapshot, fixture: fixture,
                            native: native, documents: documents, client: client, sourceOwner: sourceOwner)
                    }
                }))
        }
        #endif
        return try present(from: presenter, native: native, documents: documents,
            sourceOwner: sourceOwner, conversationID: conversationID, locale: locale, creation: creation)
    }
}

#if DEBUG && targetEnvironment(simulator)
@MainActor
private struct AnyHanlinSaveMessageNativeAdmission {
    let scope: AnyHanlinPresentationScope
    let sourceRevision: String
    let sourceMarkdownSHA256: String
    let sourceVersionSHA256: String

    static func inspect(native: AnyApplicationSession, documents: AnyEditorDocumentStore,
        client: AnyHTTPClient, sourceOwner: any AnyHanlinSourcePresentationOwner,
        accountID: String, spaceID: String, objectID: String,
        fixture: PinkhaHanlinSaveMessageAcceptanceFixture? = nil) async throws -> Self {
        let scope = try sourceOwner.currentScope()
        guard let original = scope.document, scope.selection.isEmpty,
              scope.accountID.utf8.elementsEqual(accountID.utf8), scope.spaceID.utf8.elementsEqual(spaceID.utf8),
              original.objectID.utf8.elementsEqual(objectID.utf8), original.spaceID.utf8.elementsEqual(spaceID.utf8),
              client.expectedAccountID.utf8.elementsEqual(accountID.utf8), documents.workspace == native.workspace,
              documents.dataset == "editor_blocks",
              native.workspace.accountID.utf8.elementsEqual(accountID.utf8),
              native.workspace.spaceID.utf8.elementsEqual(spaceID.utf8),
              PinkhaHanlinAccountOwner.shared.isAvailable(account: accountID, app: PinkhaHanlinEngineNamespace.any) else {
            throw HanlinHostError.staleContext
        }
        if let fixture {
            try fixture.validate()
            guard fixture.anyRuntime?.generation == native.generation,
                  fixture.anyRuntime?.engineStartedAt.utf8.elementsEqual(native.engineStartedAt.utf8) == true,
                  PinkhaHanlinCreatePagePlan.digest(Data(original.revision.utf8)) == fixture.sourceRevisionSHA256 else {
                throw HanlinHostError.staleContext
            }
        }
        let reference = try AnyNativeMarkdownReference(accountID: accountID, spaceID: spaceID, objectID: objectID)
        let body = AnyNativeMarkdownBody(client: client)
        let observed = try await native.perform { lease in
            let authorize: @Sendable () async throws -> Void = {
                try await lease.validate()
                try await MainActor.run { try validate(scope, owner: sourceOwner, native: native) }
            }
            let markdown = try await body.read(reference, authorize: authorize)
            try await authorize()
            let document = try await documents.read(objectID: objectID, lease: lease)
            try await authorize()
            guard document.generation == native.generation,
                  document.engineStartedAt.utf8.elementsEqual(native.engineStartedAt.utf8),
                  document.snapshot.objectID.utf8.elementsEqual(objectID.utf8),
                  document.snapshot.revision.utf8.elementsEqual(original.revision.utf8),
                  document.nativeVersion.utf8.elementsEqual(markdown.version.utf8),
                  document.markdown.utf8.elementsEqual(markdown.content.utf8) else { throw HanlinHostError.staleContext }
            return markdown
        }
        try Task.checkCancellation()
        try validate(scope, owner: sourceOwner, native: native)
        return .init(scope: scope, sourceRevision: original.revision,
            sourceMarkdownSHA256: observed.contentSHA256,
            sourceVersionSHA256: PinkhaHanlinCreatePagePlan.digest(Data(observed.version.utf8)))
    }

    func verifyCreatedDocument(_ snapshot: PinkhaHanlinWriteJournal.SaveMessageAcceptanceSnapshot,
        fixture: PinkhaHanlinSaveMessageAcceptanceFixture, native: AnyApplicationSession,
        documents: AnyEditorDocumentStore, client: AnyHTTPClient,
        sourceOwner: any AnyHanlinSourcePresentationOwner) async throws -> PinkhaHanlinSaveMessageBodyReadback {
        try fixture.validate(session: snapshot.entry.identity.session)
        try Self.validate(scope, owner: sourceOwner, native: native)
        guard snapshot.entry.effect == .committed, let progress = snapshot.progress,
              progress.manifest.bodyMode == .conditionalMarkdown,
              let expected = progress.bodyReadback, let ack = progress.atomicBody?.acknowledgement,
              let objectID = snapshot.entry.createdObjectReference,
              objectID.utf8.elementsEqual(expected.objectReference.utf8),
              !objectID.utf8.elementsEqual(fixture.sourceObjectID.utf8),
              fixture.anyRuntime?.generation == native.generation,
              fixture.anyRuntime?.engineStartedAt.utf8.elementsEqual(native.engineStartedAt.utf8) == true else {
            throw HanlinHostError.resultMismatch
        }
        try progress.validate()
        let reference = try AnyNativeMarkdownReference(accountID: fixture.accountID,
            spaceID: fixture.spaceID, objectID: objectID)
        let scope = scope, body = AnyNativeMarkdownBody(client: client)
        let result = try await native.perform { lease in
            let authorize: @Sendable () async throws -> Void = {
                try await lease.validate()
                try await MainActor.run { try Self.validate(scope, owner: sourceOwner, native: native) }
            }
            let first = try await body.read(reference, authorize: authorize)
            try await authorize()
            let actual = try await documents.read(objectID: objectID, lease: lease)
            try await authorize()
            let response = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", fixture.spaceID, "objects", objectID], authorize: authorize)
            guard response["objectId"]?.string?.utf8.elementsEqual(objectID.utf8) == true,
                  let record = response["record"] else { throw HanlinHostError.resultMismatch }
            let last = try await body.read(reference, authorize: authorize)
            guard actual.generation == native.generation,
                  actual.engineStartedAt.utf8.elementsEqual(native.engineStartedAt.utf8),
                  first.version.utf8.elementsEqual(last.version.utf8),
                  actual.nativeVersion.utf8.elementsEqual(last.version.utf8),
                  actual.markdown.utf8.elementsEqual(last.content.utf8),
                  PinkhaHanlinCreatePagePlan.digest(Data(last.version.utf8)) == ack.savedVersionSHA256 else {
                throw HanlinHostError.resultMismatch
            }
            let semantic = try AnyHanlinSaveMessageReadback(snapshot: actual.snapshot, rootRecord: record, workspace: lease.workspace)
            let readback = try semantic.verifiedBody(manifest: progress.manifest,
                nativeVersionSHA256: PinkhaHanlinCreatePagePlan.digest(Data(last.version.utf8)),
                nativeMarkdownSHA256: last.contentSHA256, nativeMarkdownUTF8Bytes: last.contentBytes)
            try await authorize()
            return readback
        }
        try Self.validate(scope, owner: sourceOwner, native: native)
        return result
    }

    func verifyStoppedRoot(_ progress: PinkhaHanlinSaveMessageProgress,
        fixture: PinkhaHanlinSaveMessageAcceptanceFixture, native: AnyApplicationSession,
        documents: AnyEditorDocumentStore, client: AnyHTTPClient,
        sourceOwner: any AnyHanlinSourcePresentationOwner) async throws -> PinkhaHanlinStoppedRootReadback {
        try fixture.validate(session: progress.manifest.identity.session)
        try Self.validate(scope, owner: sourceOwner, native: native)
        try progress.validate()
        guard fixture.scenario == .stopAfterDurableRoot, progress.dispatchClosed,
              progress.manifest.bodyMode == .conditionalMarkdown,
              progress.blocks.isEmpty, progress.atomicBody == nil, progress.bodyReadback == nil,
              let objectID = progress.root.reference,
              !objectID.utf8.elementsEqual(fixture.sourceObjectID.utf8),
              fixture.anyRuntime?.generation == native.generation,
              fixture.anyRuntime?.engineStartedAt.utf8.elementsEqual(native.engineStartedAt.utf8) == true else {
            throw HanlinHostError.resultMismatch
        }
        let reference = try AnyNativeMarkdownReference(accountID: fixture.accountID,
            spaceID: fixture.spaceID, objectID: objectID)
        let scope = scope, body = AnyNativeMarkdownBody(client: client)
        let result = try await native.perform { lease in
            let authorize: @Sendable () async throws -> Void = {
                try await lease.validate()
                try await MainActor.run { try Self.validate(scope, owner: sourceOwner, native: native) }
            }
            let first = try await body.read(reference, authorize: authorize)
            try await authorize()
            let actual = try await documents.read(objectID: objectID, lease: lease)
            try await authorize()
            let response = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", fixture.spaceID, "objects", objectID], authorize: authorize)
            guard response["objectId"]?.string?.utf8.elementsEqual(objectID.utf8) == true,
                  let record = response["record"] else { throw HanlinHostError.resultMismatch }
            let last = try await body.read(reference, authorize: authorize)
            guard actual.generation == native.generation,
                  actual.engineStartedAt.utf8.elementsEqual(native.engineStartedAt.utf8),
                  first.version.utf8.elementsEqual(last.version.utf8),
                  actual.nativeVersion.utf8.elementsEqual(last.version.utf8),
                  actual.markdown.utf8.elementsEqual(last.content.utf8), last.content.isEmpty else {
                throw HanlinHostError.resultMismatch
            }
            let semantic = try AnyHanlinSaveMessageReadback(snapshot: actual.snapshot, rootRecord: record, workspace: lease.workspace)
            guard semantic.blocks.isEmpty, semantic.blockReferences.isEmpty,
                  semantic.rootReadbackSHA256 == progress.manifest.expectedRootReadbackSHA256 else {
                throw HanlinHostError.resultMismatch
            }
            try await authorize()
            return PinkhaHanlinStoppedRootReadback(objectReference: actual.snapshot.objectID,
                rootReadbackSHA256: semantic.rootReadbackSHA256, bodyRowCount: actual.snapshot.blocks.count,
                nativeVersionSHA256: PinkhaHanlinCreatePagePlan.digest(Data(last.version.utf8)),
                nativeMarkdownSHA256: last.contentSHA256, nativeMarkdownUTF8Bytes: last.contentBytes,
                nativeGeneration: actual.generation,
                engineStartedAtSHA256: PinkhaHanlinCreatePagePlan.digest(Data(actual.engineStartedAt.utf8)))
        }
        try Self.validate(scope, owner: sourceOwner, native: native)
        return result
    }

    private static func validate(_ original: AnyHanlinPresentationScope,
        owner: any AnyHanlinSourcePresentationOwner, native: AnyApplicationSession) throws {
        try Task.checkCancellation()
        let current = try owner.currentScope()
        guard current.ownerID == original.ownerID, current.sceneID == original.sceneID,
              current.accountID.utf8.elementsEqual(original.accountID.utf8),
              current.spaceID.utf8.elementsEqual(original.spaceID.utf8), current.selection.isEmpty,
              current.document?.objectID.data(using: .utf8) == original.document?.objectID.data(using: .utf8),
              current.document?.spaceID.data(using: .utf8) == original.document?.spaceID.data(using: .utf8),
              current.document?.revision.data(using: .utf8) == original.document?.revision.data(using: .utf8),
              current.accountID.utf8.elementsEqual(native.workspace.accountID.utf8),
              current.spaceID.utf8.elementsEqual(native.workspace.spaceID.utf8),
              PinkhaHanlinAccountOwner.shared.isAvailable(account: current.accountID, app: PinkhaHanlinEngineNamespace.any) else {
            throw HanlinHostError.staleContext
        }
    }
}
#endif
#endif
