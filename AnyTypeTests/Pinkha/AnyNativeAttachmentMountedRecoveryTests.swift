#if DEBUG && canImport(UIKit) && canImport(Network) && canImport(HanlinMiniAppsBridge)
import Foundation
import UIKit
import SwiftUI
import Network
import XCTest
import Darwin
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost
@testable import PinkhaAnyNative
@testable import PinkhaAnyUI

/// Hosted UIKit + controlled loopback HTTP. This does not use a Native account,
/// prove the production account-connect route, exercise the system file picker,
/// or qualify physical-device data protection. No opaque token is constructed.
@MainActor
final class AnyNativeAttachmentMountedRecoveryTests: XCTestCase {
    func testMountedCheckRecoversOriginalACKAfterProtectedJournalFailureAndOwnerDrain() async throws {
        executionTimeAllowance = 120
        let fixture = try MountedAttachmentHTTPFixture()
        let workspace = try AnyTorahWorkspace(accountID: fixture.accountID, spaceID: fixture.spaceID)
        let recovery = AnyNativeLibraryRecovery(workspace: workspace)
        var activeOwner: AnyNativeWorkspaceOwner?
        var activeLifetime: AnyUIPresentationLifetime?
        var activeJournal: AnyProtectedCreationJournal?
        var window: UIWindow?
        var previousKey: UIWindow?
        var firstFailure: (any Error)?
        do {
            let baseURL = try await fixture.start()
            let client = try AnyHTTPClient(baseURL: baseURL, expectedAccountID: workspace.accountID)
            let journal = try AnyProtectedCreationJournal.openForTesting(workspace: workspace, parent: fixture.journalParent)
            activeJournal = journal
            let scene = try XCTUnwrap(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
                .first { $0.activationState == .foregroundActive })
            previousKey = scene.windows.first(where: \.isKeyWindow)
            let visible = UIWindow(windowScene: scene)
            visible.frame = scene.coordinateSpace.bounds
            window = visible
            let first = try await mountOwner(client: client, workspace: workspace, journal: journal,
                recovery: recovery, fixture: fixture, window: visible)
            activeOwner = first.owner; activeLifetime = first.lifetime
            let originalGeneration = first.owner.session.generation
            let originalRead = try XCTUnwrap(first.document.read)
            let originalStore = try first.document.attachmentIntentStore(for: first.document.mountedOwnerID)
            let original = try AnyNativeAttachmentsPresentation(document: first.document)
            first.pane.show(original)
            try await wait(fixture) { original.canAddAttachment && !original.busy }

            // The real model handles the picker callback for this owned small
            // file. The system document-provider UI itself is not under test.
            original.chooseAttachment()
            let selection = try XCTUnwrap(original.filePicker)
            original.selectedAttachment(.success(fixture.selectedFile), pickerID: selection.id)
            try await wait(fixture) { fixture.heldExportCheck }
            let intent = try fixture.recordedOriginalIntent()
            let originalCallerJSON = try fixture.callerIntentBytes()
            XCTAssertEqual(intent.contentSHA256, AnyContentDigest.sha256(MountedAttachmentHTTPFixture.payload))
            XCTAssertEqual(intent.byteCount, Int64(MountedAttachmentHTTPFixture.payload.count))
            do {
                _ = try await journal.lookup(intent.identity)
                throw MountedAttachmentFixtureFailure.invalid("actual journal did not become poisoned")
            } catch AnyNativeCreationError.journalUnavailable { }
            // The live catch is suspended in its real current-lease HTTP read.
            // No second caller claim may pass while that original task is live.
            do {
                let unexpected = try await originalStore.claim(objectID: fixture.objectID)
                await originalStore.release(unexpected)
                throw MountedAttachmentFixtureFailure.invalid("caller claim released before operation drain")
            } catch AnyNativeAttachmentRecoveryError.operationInProgress { }
            try capture(first.document, model: original, window: visible, phase: "ack-with-poisoned-journal")

            // Repair only the deliberate test-owned mode change. The original
            // poisoned journal stays poisoned and still owns its lock.
            try fixture.restoreJournalMode()
            do {
                let unexpected = try AnyProtectedCreationJournal.openForTesting(workspace: workspace, parent: fixture.journalParent)
                await unexpected.close()
                throw MountedAttachmentFixtureFailure.invalid("protected journal reopened before original owner closed")
            } catch AnyNativeCreationError.journalUnavailable { }
            fixture.beginDrain()
            first.lifetime.revoke()
            fixture.releaseHeldExportCheck()
            await first.lifetime.drain()
            await first.owner.close() // Actual production session-drain → journal-close method.
            activeOwner = nil; activeLifetime = nil; activeJournal = nil
            try await wait(fixture) { fixture.remainingConnections == 0 }

            let released = try await originalStore.claim(objectID: fixture.objectID)
            do {
                let cached = try await originalStore.recoveryReceipt(for: intent, claim: released)
                let pending = try await originalStore.pending(released)
                XCTAssertNil(cached, "Cancellation must prevent the live-only token handoff")
                XCTAssertEqual(pending, intent)
                XCTAssertEqual(try fixture.callerIntentBytes(), originalCallerJSON)
                await originalStore.release(released)
            } catch { await originalStore.release(released); throw error }

            // Existing DEBUG path uses the unchanged protected-journal loader
            // and physical namespace, not an in-memory journal replacement.
            let reopened = try AnyProtectedCreationJournal.openForTesting(workspace: workspace, parent: fixture.journalParent)
            activeJournal = reopened
            let reservation = try await reopened.lookup(intent.identity)
            XCTAssertEqual(reservation, .reserved)
            try fixture.advanceToReplacementOwner()
            let second = try await mountOwner(client: client, workspace: workspace, journal: reopened,
                recovery: recovery, fixture: fixture, window: visible)
            activeOwner = second.owner; activeLifetime = second.lifetime
            XCTAssertNotEqual(second.owner.session.generation, originalGeneration)
            let oldActive = await first.owner.session.isActive
            XCTAssertFalse(oldActive)
            let currentStore = try second.document.attachmentIntentStore(for: second.document.mountedOwnerID)
            XCTAssertTrue(currentStore === originalStore)
            let current = try AnyNativeAttachmentsPresentation(document: second.document)
            second.pane.show(current)
            try await wait(fixture) {
                !current.busy && current.pendingAttachment != nil && current.showsAttachmentCheck && current.error == nil
            }
            XCTAssertEqual(current.pendingAttachment, intent)
            XCTAssertFalse(current.canAddAttachment)
            try capture(second.document, model: current, window: visible, phase: "reopened-original-request")
            current.checkPendingAttachment() // Same action as the actual rendered Check button.
            try await wait(fixture) {
                !current.busy && current.pendingAttachment == nil && !current.showsAttachmentCheck &&
                    current.error == nil && current.files.count == 1 && current.uploadNotice != nil
            }
            let file = try XCTUnwrap(current.files.first)
            XCTAssertEqual(file.id, fixture.fileID)
            XCTAssertEqual(file.objectID, fixture.objectID)
            XCTAssertEqual(file.name, fixture.selectedFile.lastPathComponent)
            XCTAssertEqual(file.mime, "text/plain")
            XCTAssertEqual(file.size, Int64(MountedAttachmentHTTPFixture.payload.count))
            XCTAssertTrue(file.inline && file.cached && file.durable)
            let finalState = try await reopened.lookup(intent.identity)
            XCTAssertEqual(finalState, .verified(fixture.fileID))
            let finalClaim = try await currentStore.claim(objectID: fixture.objectID)
            do {
                let removed = try await currentStore.pending(finalClaim)
                XCTAssertNil(removed)
                await currentStore.release(finalClaim)
            } catch { await currentStore.release(finalClaim); throw error }
            XCTAssertFalse(FileManager.default.fileExists(atPath: fixture.callerIntentURL.path))
            let currentRead = try XCTUnwrap(second.document.read)
            XCTAssertEqual(currentRead.snapshot.objectID, originalRead.snapshot.objectID)
            XCTAssertEqual(currentRead.snapshot.spaceID, originalRead.snapshot.spaceID)
            XCTAssertEqual(currentRead.snapshot.depthFirstIDs, originalRead.snapshot.depthFirstIDs)
            XCTAssertEqual(Array(try XCTUnwrap(currentRead.snapshot.blocks.first).text.utf8),
                           Array(try XCTUnwrap(originalRead.snapshot.blocks.first).text.utf8))
            XCTAssertTrue(second.editor.isForegroundMounted)
            XCTAssertTrue(second.pane.attachmentsAreVisible(in: visible))
            try capture(second.document, model: current, window: visible, phase: "verified-current-caller")
            try fixture.requireVerifiedSingleUpload()
        } catch { firstFailure = error }

        // Restore only the owned fault before cleanup; do not replace the first
        // test failure with a later cleanup/attachment error.
        do { try fixture.restoreJournalMode() }
        catch { retain(error, first: &firstFailure, stage: "restore journal mode") }
        fixture.beginDrain()
        activeLifetime?.revoke()
        fixture.releaseHeldExportCheck()
        await activeLifetime?.drain()
        await activeOwner?.close()
        if activeOwner == nil { await activeJournal?.close() }
        do { try await fixture.stop() }
        catch { retain(error, first: &firstFailure, stage: "owned listener drainage") }
        do {
            let evidence = XCTAttachment(data: try fixture.retainedTrace(), uniformTypeIdentifier: "public.json")
            evidence.name = "mounted-attachment-recovery-controlled-http"
            evidence.lifetime = .keepAlways; add(evidence)
        } catch { retain(error, first: &firstFailure, stage: "raw fixture trace retention") }
        window?.isHidden = true; window?.rootViewController = nil
        previousKey?.makeKeyAndVisible()
        // XCTAssert failures are recorded without throwing. Keep the owned
        // fixture unless both thrown and actual XCTest issue counts are clear;
        // a missing run also retains it. The caller namespace is never removed.
        if firstFailure == nil, testRun?.totalFailureCount == 0 {
            do { try fixture.removeOwnedFilesAfterDrain() }
            catch { retain(error, first: &firstFailure, stage: "owned temporary files") }
        }
        if let firstFailure { throw firstFailure }
    }

    private func mountOwner(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                            journal: AnyProtectedCreationJournal, recovery: AnyNativeLibraryRecovery,
                            fixture: MountedAttachmentHTTPFixture, window: UIWindow) async throws
    -> (owner: AnyNativeWorkspaceOwner, lifetime: AnyUIPresentationLifetime,
        document: AnyDocumentPresentation, editor: AnyNativeEditorController, pane: MountedAttachmentPane) {
        let session = try await AnyApplicationSession.connect(client: client, workspace: workspace)
        let lifetime = AnyUIPresentationLifetime()
        do {
            let capabilities = try await AnyUIFoundationCapabilities.verify(client: client, session: session)
            let marker = try await AnyNativeNoteMarker.verify(client: client, workspace: workspace,
                collectionID: fixture.notesID)
            let objects = try AnyNativeObjectCreator(client: client, workspace: workspace, journal: journal)
            let blocks = try AnyNativeBlockCreator(client: client, workspace: workspace,
                journal: journal, allowedTypeIDs: ["page"])
            let owner = AnyNativeWorkspaceOwner(client: client, session: session, journal: journal,
                objects: objects, blocks: blocks, capabilities: capabilities)
            let document = try AnyDocumentPresentation(client: client, session: session,
                objects: objects, blocks: blocks, capabilities: capabilities,
                operations: AnyGuardedTorahOperationStore(client: client, workspace: workspace),
                noteMarker: marker, objectID: fixture.objectID, lifetime: lifetime, recovery: recovery)
            let editor = AnyNativeEditorController(presentation: document)
            let pane = MountedAttachmentPane(editor: editor)
            window.rootViewController = pane; window.makeKeyAndVisible()
            try await wait(fixture) {
                document.read != nil && !document.isLoading && document.canMutate &&
                    editor.isForegroundMounted && fixture.heldObservationKinds == ["editor", "claims"]
            }
            return (owner, lifetime, document, editor, pane)
        } catch {
            fixture.beginDrain(); lifetime.revoke(); fixture.releaseHeldExportCheck()
            await lifetime.drain(); await session.revokeAndDrain(); await journal.close()
            throw error
        }
    }

    private func wait(_ fixture: MountedAttachmentHTTPFixture,
                      _ predicate: @MainActor () -> Bool) async throws {
        let deadline = ContinuousClock.now.advanced(by: .seconds(10))
        while !predicate() {
            try Task.checkCancellation(); try fixture.requireHealthy()
            guard ContinuousClock.now < deadline else {
                throw MountedAttachmentFixtureFailure.invalid("mounted caller readiness deadline")
            }
            try await Task.sleep(for: .milliseconds(10))
        }
        try fixture.requireHealthy()
    }

    private func retain(_ error: any Error, first: inout (any Error)?, stage: String) {
        if first == nil { first = error } else { XCTFail("Additional \(stage) failure: \(error)") }
    }

    private func capture(_ document: AnyDocumentPresentation, model: AnyNativeAttachmentsPresentation,
                         window: UIWindow, phase: String) throws {
        window.layoutIfNeeded()
        var didRender = false
        let rendered = UIGraphicsImageRenderer(bounds: window.bounds).image { _ in
            didRender = window.drawHierarchy(in: window.bounds, afterScreenUpdates: true)
        }
        let value: [String: Any] = [
            "schema": "mounted-attachment-caller-recovery/v1", "phase": phase,
            "scope": "controlled-HTTP-hosted-UIKit-not-real-Native-engine",
            "account": document.workspace.accountID, "space": document.workspace.spaceID,
            "object": document.objectID, "owner": document.mountedOwnerID.uuidString,
            "sessionGeneration": document.nativeSession.generation.uuidString,
            "mounted": document.isMounted, "busy": model.busy,
            "pendingIntent": model.pendingAttachment != nil, "showsCheck": model.showsAttachmentCheck,
            "fileIDs": model.files.map(\.id), "notice": model.uploadNotice ?? "",
            "error": model.error ?? "", "actualNativeEngineAcceptance": false,
            "systemPickerAcceptance": false, "drawHierarchySucceeded": didRender,
            "windowVisible": !window.isHidden, "visualReview": "PENDING"]
        let json = XCTAttachment(data: try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]),
                                 uniformTypeIdentifier: "public.json")
        json.name = "mounted-attachment-" + phase; json.lifetime = .keepAlways; add(json)
        let screenshot = XCTAttachment(image: rendered)
        screenshot.name = "mounted-attachment-" + phase + "-visual"
        screenshot.lifetime = .keepAlways; add(screenshot)
        guard didRender, !window.isHidden, window.windowScene?.activationState == .foregroundActive else {
            throw MountedAttachmentFixtureFailure.invalid("actual mounted-window screenshot failed")
        }
    }
}

@MainActor
private final class MountedAttachmentPane: UIViewController {
    let editor: AnyNativeEditorController
    private var attachments: UIHostingController<AnyNativeAttachmentsView>?
    init(editor: AnyNativeEditorController) { self.editor = editor; super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { fatalError("test fixture has no coder") }
    override func viewDidLoad() {
        super.viewDidLoad(); view.backgroundColor = .systemBackground
        addChild(editor); view.addSubview(editor.view); editor.didMove(toParent: self)
    }
    func show(_ model: AnyNativeAttachmentsPresentation) {
        precondition(attachments == nil)
        let host = UIHostingController(rootView: AnyNativeAttachmentsView(model: model))
        attachments = host; addChild(host); view.addSubview(host.view); host.didMove(toParent: self)
        view.setNeedsLayout(); view.layoutIfNeeded()
    }
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        let width = view.bounds.width / 2
        editor.view.frame = CGRect(x: 0, y: 0, width: width, height: view.bounds.height)
        attachments?.view.frame = CGRect(x: width, y: 0, width: width, height: view.bounds.height)
    }
    func attachmentsAreVisible(in window: UIWindow) -> Bool {
        guard let view = attachments?.view else { return false }
        return view.window === window && !view.isHidden && view.alpha == 1 &&
            view.bounds.width > 0 && view.bounds.height > 0 && window.windowScene?.activationState == .foregroundActive
    }
}

private enum MountedAttachmentFixtureFailure: Error, Sendable {
    case invalid(String)
}

private final class MountedAttachmentHTTPFixture: @unchecked Sendable {
    static let payload = Data("example".utf8)
    let accountID: String
    let spaceID: String
    let fileID = "mounted-attachment-original-file"
    let ownedRoot: URL
    let journalParent: URL
    let selectedFile: URL
    let callerIntentURL: URL
    private let journalDirectory: URL
    private let rootIdentity: (dev_t, ino_t)
    private var journalIdentity: (dev_t, ino_t)?
    private var faultArmed = false
    private var faultRestored = false
    private var heldExport: NWConnection?
    private var heldExportOnce = false
    private var uploads = 0
    private var acknowledgedResponses = 0
    private var infoReads = 0
    private var contentReads = 0
    private var listsByPhase = [0, 0]
    private var originalIntent: AnyNativeFileAttachmentIntent?
    private var originalCallerSHA256 = ""
    private var originalReservationSHA256 = ""
    private var uploadedSHA256 = ""
    private var returnedSHA256 = ""
    let objectID = "render-object"
    let blockID = "render-block"
    let notesID = "render-notes"
    private let rootID = "render-claims-root"
    private let run = "controlled-render-run"
    private let queue = DispatchQueue(label: "pinkha.tests.mounted-refresh." + UUID().uuidString)
    private let listener: NWListener
    private var listenerClosed = false
    private var started = false
    private var draining = false
    private var stopping = false
    private var phase = 0
    private var failures: [String] = []
    private var requests = 0
    private var requestTrace: [[String: String]] = []
    private var readsByPhase = [0, 0]
    private var completedPropertiesByPhase = [0, 0]
    private var heldKinds: Set<String> = []
    private var connections: [UUID: NWConnection] = [:]
    private var startWaiter: CheckedContinuation<URL, any Error>?
    private var stopWaiter: CheckedContinuation<Void, any Error>?

    init() throws {
        let tag = UUID().uuidString.lowercased()
        accountID = "attachment-account-" + tag
        spaceID = "attachment-space-" + tag
        let workspace = try AnyTorahWorkspace(accountID: accountID, spaceID: spaceID)
        let root = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("mounted-attachment-" + tag, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false,
                                               attributes: [.posixPermissions: 0o700])
        guard chmod(root.path, mode_t(0o700)) == 0 else {
            throw MountedAttachmentFixtureFailure.invalid("fresh fixture root mode")
        }
        var rootStat = stat()
        guard lstat(root.path, &rootStat) == 0, rootStat.st_uid == geteuid(),
              rootStat.st_mode & S_IFMT == S_IFDIR, rootStat.st_mode & 0o7777 == 0o700 else {
            throw MountedAttachmentFixtureFailure.invalid("fresh fixture root identity")
        }
        ownedRoot = root; rootIdentity = (rootStat.st_dev, rootStat.st_ino)
        var initializationFinished = false
        defer {
            if !initializationFinished {
                var current = stat()
                if lstat(root.path, &current) == 0, current.st_uid == geteuid(),
                   current.st_mode & S_IFMT == S_IFDIR,
                   current.st_dev == rootStat.st_dev, current.st_ino == rootStat.st_ino {
                    try? FileManager.default.removeItem(at: root)
                }
            }
        }
        journalParent = root.appendingPathComponent("journal", isDirectory: true)
        try FileManager.default.createDirectory(at: journalParent, withIntermediateDirectories: false,
                                               attributes: [.posixPermissions: 0o700])
        guard chmod(journalParent.path, mode_t(0o700)) == 0 else {
            throw MountedAttachmentFixtureFailure.invalid("fresh journal parent mode")
        }
        selectedFile = root.appendingPathComponent("attachment.txt")
        let fd = Darwin.open(selectedFile.path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode_t(0o600))
        guard fd >= 0 else { throw MountedAttachmentFixtureFailure.invalid("fresh selected file") }
        let file = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        do { try file.write(contentsOf: Self.payload); try file.synchronize(); try file.close() }
        catch { try? file.close(); throw error }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let journalScope = AnyContentDigest.sha256(try encoder.encode(workspace))
        journalDirectory = journalParent.appendingPathComponent("AnyNativeCreationMetadataV1", isDirectory: true)
            .appendingPathComponent(journalScope, isDirectory: true)
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let callerScope = AnyContentDigest.sha256(try encoder.encode(["any", accountID, spaceID]))
        let support = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true).resolvingSymlinksInPath()
        callerIntentURL = support.appendingPathComponent("PinkhaAttachmentIntents/any/" + callerScope, isDirectory: true)
            .appendingPathComponent(AnyContentDigest.sha256(Data(objectID.utf8)) + ".json")
        guard !FileManager.default.fileExists(atPath: callerIntentURL.path) else {
            throw MountedAttachmentFixtureFailure.invalid("fixture caller scope already exists")
        }
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        listener = try NWListener(using: parameters, on: .any)
        // Network decrements this cumulative acceptance allowance for every
        // connection. The independent tracked simultaneous-connection cap is16.
        listener.newConnectionLimit = 512
        initializationFinished = true
    }

    func start() async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                guard !self.started else {
                    continuation.resume(throwing: MountedAttachmentFixtureFailure.invalid("duplicate start")); return
                }
                self.started = true; self.startWaiter = continuation
                self.listener.stateUpdateHandler = { [weak self] state in self?.listenerState(state) }
                self.listener.newConnectionHandler = { [weak self] connection in
                    guard let self else { connection.cancel(); return }
                    self.accept(connection)
                }
                self.listener.start(queue: self.queue)
                self.queue.asyncAfter(deadline: .now() + 5) { [weak self] in
                    guard let self, self.startWaiter != nil else { return }
                    self.fail("listener readiness deadline"); self.cancelOwnedConnections()
                    self.finishStart(.failure(MountedAttachmentFixtureFailure.invalid("listener readiness deadline")))
                }
                self.queue.asyncAfter(deadline: .now() + 90) { [weak self] in
                    guard let self, !self.stopping else { return }
                    self.fail("fixture lifetime deadline"); self.cancelOwnedConnections()
                }
            }
        }
    }

    var heldObservationKinds: Set<String> { queue.sync { heldKinds } }

    func requireHealthy() throws {
        try queue.sync {
            guard failures.isEmpty else { throw MountedAttachmentFixtureFailure.invalid(failures.joined(separator: "; ")) }
        }
    }

    var heldExportCheck: Bool { queue.sync { heldExport != nil } }
    var remainingConnections: Int { queue.sync { connections.count } }

    func recordedOriginalIntent() throws -> AnyNativeFileAttachmentIntent {
        try queue.sync {
            guard let originalIntent else { throw MountedAttachmentFixtureFailure.invalid("no actual caller intent observed") }
            return originalIntent
        }
    }

    func callerIntentBytes() throws -> Data {
        let attributes = try FileManager.default.attributesOfItem(atPath: callerIntentURL.path)
        guard let size = attributes[.size] as? NSNumber, size.intValue > 0, size.intValue <= 32_768 else {
            throw MountedAttachmentFixtureFailure.invalid("owned caller record bounds")
        }
        return try Data(contentsOf: callerIntentURL)
    }

    private func armCreatedAppendFailure() throws {
        guard !faultArmed, !faultRestored, phase == 0, uploads == 0, geteuid() != 0 else {
            throw MountedAttachmentFixtureFailure.invalid("journal fault is single-use and requires unprivileged test process")
        }
        let raw = try callerIntentBytes()
        let object = try JSONDecoder().decode(AnyJSON.self, from: raw)
        guard object["format"]?.integer == 1, let encoded = object["intent"] else {
            throw MountedAttachmentFixtureFailure.invalid("original caller record shape")
        }
        let intent = try JSONDecoder().decode(AnyNativeFileAttachmentIntent.self, from: JSONEncoder().encode(encoded))
        guard intent.workspace.accountID.utf8.elementsEqual(accountID.utf8),
              intent.workspace.spaceID.utf8.elementsEqual(spaceID.utf8), intent.objectID == objectID,
              intent.name == selectedFile.lastPathComponent, intent.mime == "text/plain",
              intent.byteCount == Int64(Self.payload.count), intent.contentSHA256 == AnyContentDigest.sha256(Self.payload) else {
            throw MountedAttachmentFixtureFailure.invalid("actual caller intent differs from controlled upload")
        }
        let reservation = journalDirectory.appendingPathComponent(intent.identity.key + ".reserved.json")
        let entryBytes = try Data(contentsOf: reservation)
        guard !entryBytes.isEmpty, entryBytes.count <= 16_384 else {
            throw MountedAttachmentFixtureFailure.invalid("original journal reservation bounds")
        }
        let entry = try JSONDecoder().decode(AnyJSON.self, from: entryBytes)
        guard entry["version"]?.integer == 1, let identity = entry["identity"], let state = entry["state"],
              try JSONDecoder().decode(AnyNativeCreationIdentity.self, from: JSONEncoder().encode(identity)) == intent.identity,
              try JSONDecoder().decode(AnyNativeCreationState.self, from: JSONEncoder().encode(state)) == .reserved,
              !FileManager.default.fileExists(atPath: journalDirectory.appendingPathComponent(intent.identity.key + ".created.json").path),
              !FileManager.default.fileExists(atPath: journalDirectory.appendingPathComponent(intent.identity.key + ".verified.json").path) else {
            throw MountedAttachmentFixtureFailure.invalid("original protected reservation is not the one dispatch")
        }
        var before = stat()
        guard lstat(journalDirectory.path, &before) == 0, before.st_uid == geteuid(),
              before.st_mode & S_IFMT == S_IFDIR, before.st_mode & 0o7777 == 0o700,
              chmod(journalDirectory.path, mode_t(0o500)) == 0 else {
            throw MountedAttachmentFixtureFailure.invalid("cannot arm owned created-entry permission failure")
        }
        // Keep restoration identity before any subsequent validation can throw.
        journalIdentity = (before.st_dev, before.st_ino)
        faultArmed = true
        var after = stat()
        guard lstat(journalDirectory.path, &after) == 0, after.st_uid == before.st_uid,
              after.st_dev == before.st_dev, after.st_ino == before.st_ino,
              after.st_mode & S_IFMT == S_IFDIR, after.st_mode & 0o7777 == 0o500 else {
            throw MountedAttachmentFixtureFailure.invalid("owned journal mode barrier identity")
        }
        originalIntent = intent
        originalCallerSHA256 = AnyContentDigest.sha256(raw)
        originalReservationSHA256 = AnyContentDigest.sha256(entryBytes)
    }

    func restoreJournalMode() throws {
        try queue.sync {
            guard faultArmed else { return }
            guard let identity = journalIdentity else { throw MountedAttachmentFixtureFailure.invalid("missing owned journal identity") }
            var before = stat()
            guard lstat(journalDirectory.path, &before) == 0, before.st_uid == geteuid(),
                  before.st_dev == identity.0, before.st_ino == identity.1,
                  before.st_mode & S_IFMT == S_IFDIR, before.st_mode & 0o7777 == 0o500,
                  chmod(journalDirectory.path, mode_t(0o700)) == 0 else {
                throw MountedAttachmentFixtureFailure.invalid("owned journal restoration identity or mode")
            }
            var after = stat()
            guard lstat(journalDirectory.path, &after) == 0, after.st_dev == identity.0,
                  after.st_ino == identity.1, after.st_uid == geteuid(),
                  after.st_mode & S_IFMT == S_IFDIR, after.st_mode & 0o7777 == 0o700 else {
                throw MountedAttachmentFixtureFailure.invalid("owned journal restored mode readback")
            }
            faultArmed = false; faultRestored = true
        }
    }

    func releaseHeldExportCheck() {
        queue.sync {
            guard let connection = heldExport else { return }
            heldExport = nil
            do { try respondJSON(connection, value: health) }
            catch { fail("held current-lease response: \(error)"); connection.cancel() }
        }
    }

    func advanceToReplacementOwner() throws {
        try queue.sync {
            guard draining, !stopping, failures.isEmpty, phase == 0, connections.isEmpty,
                  heldExport == nil, heldExportOnce, faultRestored, !faultArmed,
                  uploads == 1, acknowledgedResponses == 1 else {
                throw MountedAttachmentFixtureFailure.invalid("replacement phase before completed original transport drain")
            }
            phase = 1; heldKinds = []; draining = false
        }
    }

    func requireVerifiedSingleUpload() throws {
        try queue.sync {
            guard failures.isEmpty, phase == 1, uploads == 1, acknowledgedResponses == 1,
                  infoReads == 2, contentReads == 1, heldExportOnce, faultRestored, !faultArmed,
                  readsByPhase.allSatisfy({ $0 > 0 }), completedPropertiesByPhase.allSatisfy({ $0 > 0 }),
                  listsByPhase.allSatisfy({ $0 > 0 }), heldKinds == ["editor", "claims"],
                  uploadedSHA256 == AnyContentDigest.sha256(Self.payload),
                  returnedSHA256 == uploadedSHA256 else {
                throw MountedAttachmentFixtureFailure.invalid("controlled recovery did not verify original one-upload/digest flow")
            }
        }
    }

    func removeOwnedFilesAfterDrain() throws {
        try queue.sync {
            guard stopping, listenerClosed, connections.isEmpty, !faultArmed else {
                throw MountedAttachmentFixtureFailure.invalid("owned files cannot be removed before transport and permission cleanup")
            }
            var current = stat()
            guard lstat(ownedRoot.path, &current) == 0, current.st_uid == geteuid(),
                  current.st_mode & S_IFMT == S_IFDIR, current.st_mode & 0o7777 == 0o700,
                  current.st_dev == rootIdentity.0, current.st_ino == rootIdentity.1 else {
                throw MountedAttachmentFixtureFailure.invalid("owned fixture root changed before cleanup")
            }
            try FileManager.default.removeItem(at: ownedRoot)
        }
    }

    private var health: AnyJSON {
        .object(["status": .string("ok"), "account": .string(accountID), "startedAt": .string(run)])
    }

    private var fileMetadata: AnyJSON {
        .object(["fileId": .string(fileID), "objectId": .string(objectID),
                 "name": .string(selectedFile.lastPathComponent), "mime": .string("text/plain"),
                 "size": .integer(Int64(Self.payload.count)), "inline": .bool(true),
                 "cached": .bool(true), "durable": .bool(true)])
    }

    private func respondJSON(_ connection: NWConnection, value: AnyJSON, status: Int = 200) throws {
        let bytes = try JSONEncoder().encode(value)
        guard bytes.count <= 16_384 else { throw MountedAttachmentFixtureFailure.invalid("response byte budget") }
        send(connection, bytes: bytes, status: status, contentType: "application/json")
    }

    private func send(_ connection: NWConnection, bytes: Data, status: Int, contentType: String,
                      contentRange: String? = nil) {
        let reason = status == 201 ? "Created" : (status == 206 ? "Partial Content" : "OK")
        var header = "HTTP/1.1 \(status) \(reason)\r\nContent-Type: \(contentType)\r\nContent-Length: \(bytes.count)\r\nConnection: close\r\n"
        if let contentRange { header += "Content-Range: \(contentRange)\r\n" }
        header += "\r\n"
        var response = Data(header.utf8); response.append(bytes)
        connection.send(content: response, contentContext: .finalMessage, isComplete: true,
                        completion: .contentProcessed { [weak self] error in
            if let self {
                if let error, !self.draining { self.fail("response send failed: \(error)") }
                if error == nil, status == 201 { self.acknowledgedResponses += 1 }
            }
            connection.cancel()
        })
    }


    func beginDrain() { queue.sync { draining = true } }

    func retainedTrace() throws -> Data {
        try queue.sync {
            let value: [String: Any] = [
                "scope": "controlled-loopback-hosted-UIKit-not-Native-acceptance",
                "requests": requestTrace, "failures": failures,
                "queriesBySourcePhase": readsByPhase, "propertiesBySourcePhase": completedPropertiesByPhase,
                "heldObservationKinds": heldKinds.sorted(), "listenerCancelled": listenerClosed,
                "remainingOwnedConnections": connections.count,
                "uploads": uploads, "actual201Responses": acknowledgedResponses,
                "metadataReads": infoReads, "contentReads": contentReads, "listsByOwner": listsByPhase,
                "heldPostACKLeaseRead": heldExportOnce, "ownedModeRestored": faultRestored,
                "ownedModeStillArmed": faultArmed, "callerIntentSHA256": originalCallerSHA256,
                "originalReservationSHA256": originalReservationSHA256,
                "uploadedSHA256": uploadedSHA256, "returnedSHA256": returnedSHA256,
                "realNativeEngineAcceptance": false, "systemPickerAcceptance": false,
                "visualReview": "PENDING"]
            return try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        }
    }

    func stop() async throws {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                guard self.stopWaiter == nil, !self.stopping else {
                    continuation.resume(throwing: MountedAttachmentFixtureFailure.invalid("duplicate stop")); return
                }
                self.draining = true; self.stopping = true; self.stopWaiter = continuation
                self.cancelOwnedConnections()
                self.finishStopIfClosed()
                self.queue.asyncAfter(deadline: .now() + 5) { [weak self] in
                    guard let self, let waiter = self.stopWaiter else { return }
                    self.stopWaiter = nil
                    self.fail("owned listener/connection drain deadline")
                    waiter.resume(throwing: MountedAttachmentFixtureFailure.invalid("owned listener/connection drain deadline"))
                }
            }
        }
    }

    private func listenerState(_ state: NWListener.State) {
        switch state {
        case .ready:
            guard let port = listener.port,
                  let url = URL(string: "http://127.0.0.1:\(port.rawValue)") else {
                fail("missing owned listener port"); cancelOwnedConnections(); return
            }
            finishStart(.success(url))
        case .failed(let error):
            fail("listener failed: \(error)")
            finishStart(.failure(error)); cancelOwnedConnections()
        case .cancelled:
            listenerClosed = true
            finishStart(.failure(MountedAttachmentFixtureFailure.invalid("listener cancelled before readiness")))
            finishStopIfClosed()
        default: break
        }
    }

    private func finishStart(_ result: Result<URL, any Error>) {
        let waiter = startWaiter; startWaiter = nil; waiter?.resume(with: result)
    }

    private func finishStopIfClosed() {
        guard stopping, listenerClosed, connections.isEmpty, let waiter = stopWaiter else { return }
        stopWaiter = nil
        if failures.isEmpty { waiter.resume() }
        else { waiter.resume(throwing: MountedAttachmentFixtureFailure.invalid(failures.joined(separator: "; "))) }
    }

    private func cancelOwnedConnections() {
        listener.cancel()
        for connection in connections.values { connection.cancel() }
    }

    private func fail(_ message: String) {
        if failures.count < 16 { failures.append(message) }
    }

    private func accept(_ connection: NWConnection) {
        let reject = stopping || connections.count >= 16
        if !stopping, connections.count >= 16 { fail("connection budget exceeded") }
        let id = UUID()
        connections[id] = connection
        connection.stateUpdateHandler = { [weak self] state in
            guard let self else { return }
            switch state {
            case .failed(let error):
                if !self.draining { self.fail("connection failed: \(error)") }
                self.connections[id]?.cancel()
            case .cancelled:
                self.connections.removeValue(forKey: id)
                self.finishStopIfClosed()
            default: break
            }
        }
        connection.start(queue: queue)
        // Even a late or over-budget accepted connection is tracked until its
        // actual cancellation callback; cleanup never drops an owned socket.
        if reject { connection.cancel(); return }
        receiveRequest(connection, accumulated: Data())
    }

    private func receiveRequest(_ connection: NWConnection, accumulated: Data) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16_384) { [weak self] bytes, _, complete, error in
            guard let self else { connection.cancel(); return }
            if let error {
                if !self.draining { self.fail("request receive failed: \(error)") }
                connection.cancel(); return
            }
            var data = accumulated
            if let bytes { data.append(bytes) }
            do {
                guard data.count <= 32_768 else { throw MountedAttachmentFixtureFailure.invalid("request byte budget") }
                guard let split = data.range(of: Data([13, 10, 13, 10])) else {
                    guard !complete, data.count <= 16_384 else { throw MountedAttachmentFixtureFailure.invalid("incomplete header") }
                    self.receiveRequest(connection, accumulated: data); return
                }
                guard split.lowerBound <= 16_384,
                      let header = String(data: data[..<split.lowerBound], encoding: .utf8) else {
                    throw MountedAttachmentFixtureFailure.invalid("invalid header")
                }
                let lines = header.components(separatedBy: "\r\n")
                let request = lines[0].split(separator: " ", omittingEmptySubsequences: false)
                guard request.count == 3, request[2] == "HTTP/1.1" else {
                    throw MountedAttachmentFixtureFailure.invalid("unexpected request line")
                }
                var headers: [String: String] = [:]
                for line in lines.dropFirst() {
                    guard let colon = line.firstIndex(of: ":") else { throw MountedAttachmentFixtureFailure.invalid("header separator") }
                    let key = line[..<colon].lowercased()
                    guard headers[key] == nil else { throw MountedAttachmentFixtureFailure.invalid("duplicate header") }
                    headers[key] = line[line.index(after: colon)...].trimmingCharacters(in: .whitespaces)
                }
                guard headers["transfer-encoding"] == nil,
                      let length = Int(headers["content-length"] ?? "0"), (0...16_384).contains(length),
                      let port = self.listener.port,
                      headers["host"] == "127.0.0.1:\(port.rawValue)" else {
                    throw MountedAttachmentFixtureFailure.invalid("request framing or host")
                }
                let body = data[split.upperBound...]
                if body.count < length {
                    guard !complete else { throw MountedAttachmentFixtureFailure.invalid("incomplete body") }
                    self.receiveRequest(connection, accumulated: data); return
                }
                guard body.count == length else { throw MountedAttachmentFixtureFailure.invalid("pipelined or excess body") }
                try self.route(connection, method: String(request[0]), target: String(request[1]), headers: headers, body: Data(body))
            } catch {
                self.fail("request rejected: \(error)"); connection.cancel()
            }
        }
    }

    private func route(_ connection: NWConnection, method: String, target: String, headers: [String: String], body: Data) throws {
        requests += 1
        guard !stopping, requests <= 512, target.hasPrefix("/"),
              let url = URLComponents(string: "http://127.0.0.1" + target), url.fragment == nil else {
            throw MountedAttachmentFixtureFailure.invalid("request scope or count")
        }
        let parts = url.percentEncodedPath.split(separator: "/").map { String($0).removingPercentEncoding ?? "" }
        requestTrace.append(["method": method, "target": target, "sourcePhase": String(phase)])
        let queryItems = url.queryItems ?? []
        guard queryItems.count <= 2, Set(queryItems.map(\.name)).count == queryItems.count,
              queryItems.allSatisfy({ $0.value != nil }) else {
            throw MountedAttachmentFixtureFailure.invalid("unexpected query")
        }
        let query = Dictionary(uniqueKeysWithValues: queryItems.map { ($0.name, $0.value!) })
        let limited = query == ["limit": "10000"]
        let unqueried = query.isEmpty
        let space = ["v1", "spaces", spaceID]
        let text = "Mounted attachment document stays unchanged."
        let version = "mounted-attachment-document-v1"
        if method == "POST", parts == space + ["objects", objectID, "files"] {
            guard phase == 0, uploads == 0, query == ["name": selectedFile.lastPathComponent],
                  headers["content-type"] == "text/plain", headers["accept-encoding"] == "identity",
                  body == Self.payload else {
                throw MountedAttachmentFixtureFailure.invalid("duplicate, wrong-scope or changed upload")
            }
            try armCreatedAppendFailure()
            uploads += 1; uploadedSHA256 = AnyContentDigest.sha256(body)
            try respondJSON(connection, value: fileMetadata, status: 201)
            return
        }
        let value: AnyJSON
        if method == "GET" {
            guard body.isEmpty else { throw MountedAttachmentFixtureFailure.invalid("GET body") }
            switch parts {
            case ["v1", "auth"] where unqueried:
                value = .object(["authorized": .bool(true), "accountId": .string(accountID)])
            case ["v1", "health"] where unqueried:
                if phase == 0, uploads == 1, !heldExportOnce {
                    heldExportOnce = true; heldExport = connection
                    return // The test revokes the real owner before this read resumes.
                }
                value = health
            case space + ["files"] where query == ["objectId": objectID, "limit": "10001"]:
                listsByPhase[phase] += 1
                value = .object(["files": .array(uploads == 1 ? [fileMetadata] : [])])
            case space + ["files", fileID] where unqueried:
                guard phase == 1, uploads == 1, infoReads < 2 else {
                    throw MountedAttachmentFixtureFailure.invalid("unexpected original-file metadata read")
                }
                infoReads += 1; value = fileMetadata
            case space + ["files", fileID, "content"] where unqueried:
                guard phase == 1, uploads == 1, contentReads == 0,
                      headers["range"] == "bytes=0-6", headers["accept"] == "text/plain",
                      headers["accept-encoding"] == "identity" else {
                    throw MountedAttachmentFixtureFailure.invalid("unexpected original-file content read")
                }
                contentReads += 1; returnedSHA256 = AnyContentDigest.sha256(Self.payload)
                send(connection, bytes: Self.payload, status: 206, contentType: "text/plain", contentRange: "bytes 0-6/7")
                return
            case ["v1", "pinkha", "capabilities"] where unqueried:
                value = capabilities
            case space + ["members", "me"] where unqueried:
                value = .object(["identity": .string(accountID), "status": .string("active"), "permission": .string("owner")])
            case space + ["collections", notesID] where unqueried:
                value = .object(["id": .string(notesID), "xKey": .string("pinkha-note-v1")])
            case space + ["pinkha", "document-targets", objectID] where unqueried:
                value = targetProof
            case space + ["objects", objectID] where unqueried:
                value = .object(["objectId": .string(objectID), "record": .object([
                    "id": .string(objectID), "spaceId": .string(spaceID),
                    "any": .object(["name": .string("Mounted refresh fixture"), "type": .string("page"), "collections": .array([])])])])
            case space + ["objects", objectID, "editor", "editor_blocks", "markdown"] where unqueried:
                value = .object(["content": .string(text), "version": .string(version)])
            case space + ["bundles", "pinkha/torah-native/v1"] where unqueried:
                value = .object(["bundle": .object(["derived": .bool(true), "losers": .array([]), "rootId": .string(rootID)])])
            case space + ["pinkha", "objects", objectID, "claims"] where limited:
                value = claimsSnapshot
            case space + ["pinkha", "targets", objectID] where limited:
                completedPropertiesByPhase[phase] += 1
                value = derivedProperties
            case space + ["pinkha", "objects", objectID, "claims", "subscribe"] where limited:
                holdObservation(connection, kind: "claims"); return
            default:
                throw MountedAttachmentFixtureFailure.invalid("unexpected GET route")
            }
        } else if method == "POST", unqueried {
            let query = try JSONDecoder().decode(AnyJSON.self, from: body)
            let expected: AnyJSON = .object(["objectId": .string(objectID), "dataset": .string("editor_blocks"),
                "limit": .integer(10_001), "includeTotal": .bool(true),
                "sort": .array(parts == space + ["query"] ? [.string("nav.pos"), .string("id")] : [.string("id")])])
            guard query == expected else { throw MountedAttachmentFixtureFailure.invalid("unexpected read query body") }
            if parts == space + ["query", "subscribe"] {
                holdObservation(connection, kind: "editor"); return
            }
            guard parts == space + ["query"] else { throw MountedAttachmentFixtureFailure.invalid("unexpected POST route") }
            readsByPhase[phase] += 1
            value = .object(["records": .array([.object([
                "id": .string(blockID), "type": .string("paragraph"), "text": .string(text), "style": .object([:]),
                "nav": .object(["parentId": .string(""), "pos": .string("A")]),
                "_ver": .object(["id": .string("render-block-create"), "text": .string(version)])])]),
                "total": .integer(1), "hasNext": .bool(false)])
        } else { throw MountedAttachmentFixtureFailure.invalid("unexpected mutation method") }
        try respondJSON(connection, value: value)
    }

    private func holdObservation(_ connection: NWConnection, kind: String) {
        guard heldKinds.insert(kind).inserted else {
            fail("duplicate observation subscription"); connection.cancel(); return
        }
        let response = "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: keep-alive\r\n\r\n: controlled fixture held\n\n"
        connection.send(content: Data(response.utf8), completion: .contentProcessed { [weak self] error in
            guard let self else { connection.cancel(); return }
            if let error {
                if !self.draining { self.fail("observation send failed: \(error)") }
                connection.cancel(); return
            }
            connection.receive(minimumIncompleteLength: 1, maximumLength: 1) { [weak self] data, _, _, error in
                if let self, !self.draining {
                    self.fail("held observation ended before owner drainage: bytes=\(data?.count ?? 0), error=\(String(describing: error))")
                }
                connection.cancel()
            }
        })
    }

    private var readiness: AnyJSON {
        .object(["version": .integer(1), "state": .string("ready-local-snapshot"),
                 "generation": .string(String(repeating: "a", count: 64))])
    }

    private var targetProof: AnyJSON {
        .object(["contract": .string("pinkha-torah-native-v1"), "version": .integer(1),
            "policy": .string("canonical-editor-module-v1"), "spaceId": .string(spaceID),
            "typeId": .string("page"), "objectId": .string(objectID), "eligible": .bool(true),
            "canWrite": .bool(true), "collections": .array([]),
            "canonicalEditorDataset": .string("editor_blocks"), "readiness": readiness])
    }

    private var claimsSnapshot: AnyJSON {
        .object(["contract": .string("pinkha-torah-native-v1"), "version": .integer(1),
            "scope": .string("object-logical-closure"), "targetObjectId": .string(objectID),
            "reachableClaimBlockIds": .array([]), "spaceId": .string(spaceID), "rootObjectId": .string(rootID),
            "dataset": .string("pinkha_torah_claims_v1"), "complete": .bool(true), "limit": .integer(10_000),
            "records": .array([]), "readiness": readiness])
    }

    private var derivedProperties: AnyJSON {
        .object(["contract": .string("pinkha-torah-native-v1"), "target": .object(["objectId": .string(objectID)]),
            "semantic": .object(["version": .integer(1), "coverage": .string("complete"),
                "inputSHA256": .string(String(repeating: "b", count: 64)), "labels": .object([:]),
                "records": .array([]), "sources": .array([]), "topics": .array([]), "words": .array([])]),
            "readiness": readiness])
    }

    private var capabilities: AnyJSON {
        var value: [String: AnyJSON] = [
            "contract": .string("pinkha-torah-native-v1"), "bundleId": .string("pinkha/torah-native/v1"),
            "module": .string("pinkha_torah_native"), "dataset": .string("pinkha_torah_claims_v1"),
            "dataVersion": .string("pinkha-torah-native-claims-v1"),
            "nativeSemanticPayload": .string("canonical-associations-v2-single-record"),
            "associationBlockDataset": .string("editor_blocks"), "documentTypePolicy": .string("canonical-editor-module-v1"),
            "propertyPresentationCollection": .string("pinkha_presentation_v1"),
            "propertyPresentationHiddenProperty": .string("hiddenProperties"), "allowedTargetTypes": .array([.string("page")]),
            "nativeClaimsMaxRecords": .integer(10_000), "nativeClaimsMaxBytes": .integer(16_777_216),
            "mobileManagedTokenGateway": .integer(0)]
        for key in ["nativeSignedClaims", "spaceWideOperationConflictDomain", "currentACLCommitFence", "targetTreeCommitFence",
                    "nativeDocumentProperties", "nativeIndexedSourceQuery", "nativeRelatedVersion", "conditionalBlockPatch",
                    "conditionalPropertiesSet", "conditionalPropertiesApplySeq", "conditionalPropertiesNoop",
                    "conditionalBlockCurrentWriterFence", "currentWriterObjectCreate", "currentWriterBlockCreate",
                    "nativeClaimsSnapshot", "nativeClaimsWatch", "nativeObjectClaimsSnapshot", "nativeObjectClaimsWatch",
                    "nativeDocumentTypePolicy", "nativeDocumentMembership", "conditionalMembershipSet", "nativePropertyPresentation"] {
            value[key] = .integer(1)
        }
        return .object(value)
    }
}
#endif
