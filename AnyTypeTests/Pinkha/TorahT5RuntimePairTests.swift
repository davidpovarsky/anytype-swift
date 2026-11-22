import Foundation
import CryptoKit
import AnytypeCore
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
import TorahInspectorCore
@testable import Anytype

private enum T5ApplePairFailure: Error {
    case invariant(String)
}

private enum T5ApplePairPhase: String, CaseIterable {
    case oldCreate = "old-create"
    case newUpgrade = "new-upgrade"
    case oldEdit = "old-edit"
    case newRecover = "new-recover"
    case newFreshness = "new-freshness"

    var expanded: Bool { self == .newUpgrade || self == .newRecover || self == .newFreshness }

    var expectedVersion: String {
        if expanded { return T5NativeRelatedLookupCapability.runtimeVersion }
        return "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-"
            + "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077"
    }

    var predecessors: [String] {
        Self.allCases.prefix { $0 != self }.map(\.rawValue)
    }
}

private struct T5ApplePairSecrets: Codable {
    let token: String
    let mnemonic: String
    let accountKey: String
}

private struct T5ApplePairDocument: Codable {
    let objectID: String
    let typeKey: String
    let initialName: String
    let blockID: String?
    let blockText: String?
    let canonicalSHA256: String
    let publicSHA256: String
}

private struct T5ApplePairLedger: Codable {
    let token: String
    let appSourceSHA: String
    let rootPathSHA256: String
    let rootRelativePath: String
    let accountID: String
    let spaceID: String
    let manifestID: String
    let manifestSHA256: String
    let canonicalKey: String
    let documents: [T5ApplePairDocument]
    var completedPhases: [String]
}

private struct T5ApplePairTarget: Codable, Equatable {
    let objectID: String
    let blockID: String?
    let canUnlink: Bool
}

private struct T5ApplePairReadback: Codable {
    let objectID: String
    let canonicalSHA256: String
    let publicSHA256: String
    let blockID: String?
    let blockTextSHA256: String?
    let nativeRelatedVersion: Int?
    let title: String
}


private struct T5AppleFreshnessGraphNode: Codable {
    let id: String
    let childIDs: [String]
}

private struct T5AppleFreshnessGraph: Codable {
    let spaceID: String
    let rootID: String
    let targetID: String
    let targetReachable: Bool
    let nodes: [T5AppleFreshnessGraphNode]
}

private struct T5AppleFreshnessObservation: Codable {
    let name: String
    let sourceReference: String
    let spaceID: String
    let nativeCandidatesBefore: [String]
    let nativeCandidatesAfter: [String]
    let targets: [T5ApplePairTarget]
    let coverage: String
    let limitations: [String]
    let objectID: String?
    let canonicalRaw: String?
    let canonicalSHA256: String?
    let objectRetained: Bool?
    let isArchived: Bool?
    let graph: T5AppleFreshnessGraph?
    let objectShowError: Int?
}

private struct T5AppleFreshnessReceipt: Codable {
    let status: String
    let writeOrigin: String
    let serviceScope: String
    let coverage: String
    let spaceWideFreshness: String
    let navigationStatus: String
    let originalCanonical: [String: String]
    let nativeMutationCounts: [String: Int]
    let observations: [T5AppleFreshnessObservation]
}

private struct T5ApplePairReceipt: Codable {
    let protocolVersion: String
    let status: String
    let phase: String
    let token: String
    let nonce: String
    let processID: Int32
    let appSourceSHA: String
    let runtimeVersion: String
    let actualCapability: String
    let coverage: String
    let limitations: [String]
    let rootPathSHA256: String
    let rootRelativePath: String
    let currentRootPathSHA256: String
    let accountID: String
    let spaceID: String
    let manifestID: String
    let manifestSHA256: String
    let canonicalKey: String
    let previousLedgerSHA256: String?
    let nextLedgerSHA256: String
    let migrationPerformed: Bool
    let walletCreated: Bool
    let walletRecovered: Bool
    let accountCreated: Bool
    let accountSelected: Bool
    let accountStopCompleted: Bool
    let accountNotRunningConfirmed: Bool
    let appShutdownCompleted: Bool
    let documents: [T5ApplePairReadback]
    let targets: [T5ApplePairTarget]
    let readbackBoundary: String
    let freshness: T5AppleFreshnessReceipt?
}

@Suite("T5 real same-account Apple runtime pair", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_T5_APPLE_PAIR"] == "1"))
struct TorahT5RuntimePairTests {
    @MainActor
    @Test("Same source, runtime-derived capability, account continuity and optional host freshness")
    func realSameAccountRuntimePairPhase() async throws {
        #if PINKHA_NATIVE_T5_LOOKUP_V1
        let environment = ProcessInfo.processInfo.environment
        let phase = try #require(T5ApplePairPhase(rawValue: environment["PINKHA_T5_PAIR_PHASE"] ?? ""))
        let token = try requiredEnvironment("PINKHA_T5_PAIR_TOKEN", environment)
        let nonce = try requiredEnvironment("PINKHA_T5_PAIR_NONCE", environment)
        let sourceSHA = try requiredEnvironment("PINKHA_T5_PAIR_APP_SHA", environment)
        try require(sourceSHA.count == 40 && sourceSHA.allSatisfy(\.isHexDigit), "invalid-source-identity")
        try require(token.count == 32 && nonce.count == 32, "invalid-attempt-identity")
        let support = try #require(FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first)
        let directory = support.appendingPathComponent("pinkha-t5-runtime-pair", isDirectory: true)
        let ledgerURL = directory.appendingPathComponent("ledger.json")
        let secretsURL = directory.appendingPathComponent("secrets.json")
        let resultURL = directory.appendingPathComponent("result-" + phase.rawValue + ".json")
        try require(!FileManager.default.fileExists(atPath: resultURL.path), "phase-result-already-exists")
        let root = Container.shared.localRepoService().middlewareRepoURL.resolvingSymlinksInPath().path
        let rootRelativePath = "Library/Application Support/Anytype/middleware-go"
        let currentHome = URL(fileURLWithPath: NSHomeDirectory(), isDirectory: true).resolvingSymlinksInPath()
        try require(root == currentHome.appendingPathComponent(rootRelativePath).resolvingSymlinksInPath().path,
                    "native-root-is-not-original-relative-location")
        let rootSHA = hash(Data(root.utf8))
        let version = try await ClientCommands.appGetVersion().invoke().version
        try require(version == phase.expectedVersion, "actual-runtime-version-differs")
        let capability = try await AnytypeT5NativeRelatedLookup.current()
        let expanded: Bool
        switch capability {
        case .verified: expanded = true
        case .unavailable: expanded = false
        }
        try require(expanded == phase.expanded, "production-runtime-capability-differs")
        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
        let auth = Container.shared.authService()
        var ledger: T5ApplePairLedger
        var migration = false
        var previousLedgerSHA: String?

        do {
            if phase == .oldCreate {
                try require(!FileManager.default.fileExists(atPath: directory.path), "existing-pair-directory")
                try FileManager.default.createDirectory(
                    at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700]
                )
                let wallet = try await ClientCommands.walletCreate(.with {
                    $0.rootPath = root
                }).invoke(responseMask: {
                    $0.mnemonic = "***"
                    $0.accountKey = "***"
                })
                try require(!wallet.mnemonic.isEmpty && !wallet.accountKey.isEmpty, "empty-disposable-wallet")
                try writePrivate(T5ApplePairSecrets(
                    token: token, mnemonic: wallet.mnemonic, accountKey: wallet.accountKey
                ), to: secretsURL)
                let account = try await auth.createAccount(name: "T5 runtime pair", iconOption: 1, imagePath: "")
                let space = try await Container.shared.workspaceService().createSpace(
                    name: "T5 runtime pair", iconOption: 1, accessType: .private,
                    useCase: .none, withChat: false, spaceType: .regular
                )
                _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: space.spaceID)
                ledger = try await prepareFixture(
                    token: token, sourceSHA: sourceSHA, rootSHA: rootSHA,
                    accountID: account.id, spaceID: space.spaceID
                )
                try writePrivate(ledger, to: ledgerURL)
            } else {
                let previous = try Data(contentsOf: ledgerURL)
                previousLedgerSHA = hash(previous)
                ledger = try JSONDecoder().decode(T5ApplePairLedger.self, from: previous)
                try require(
                    ledger.token == token && ledger.appSourceSHA == sourceSHA
                        && ledger.rootRelativePath == rootRelativePath,
                    "existing-ledger-identity-differs"
                )
                try require(ledger.completedPhases == phase.predecessors, "invalid-native-process-sequence")
                let secrets = try JSONDecoder().decode(T5ApplePairSecrets.self, from: Data(contentsOf: secretsURL))
                try require(
                    secrets.token == token && !secrets.mnemonic.isEmpty && !secrets.accountKey.isEmpty,
                    "invalid-private-credential-record"
                )
                _ = try await ClientCommands.walletRecover(.with {
                    $0.rootPath = root
                    $0.accountKey = secrets.accountKey
                }).invoke(requestMask: {
                    $0.mnemonic = "***"
                    $0.accountKey = "***"
                })
                let account: AccountData
                do {
                    account = try await auth.selectAccount(id: ledger.accountID, preferredSpaceId: ledger.spaceID)
                } catch SelectAccountError.accountStoreNotMigrated {
                    migration = true
                    _ = try await ClientCommands.accountMigrate(.with {
                        $0.id = ledger.accountID
                        $0.rootPath = root
                    }).invoke()
                    account = try await auth.selectAccount(id: ledger.accountID, preferredSpaceId: ledger.spaceID)
                }
                try require(account.id == ledger.accountID, "reopened-account-identity-differs")
                _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: ledger.spaceID)
            }

            let manifest = try await details(ledger.manifestID, spaceID: ledger.spaceID)
            let manifestRaw = try #require(manifest.values[BundledPropertyKey.description.rawValue]?.stringValue)
            try require(hash(Data(manifestRaw.utf8)) == ledger.manifestSHA256, "manifest-changed")
            let decodedManifest = try PinkhaSpaceManifest.fromJSONString(manifestRaw)
            try require(
                decodedManifest.spaceId == ledger.spaceID
                    && decodedManifest.documentAssociationsPropertyKey == ledger.canonicalKey,
                "canonical-manifest-contract-changed"
            )
            if phase == .oldEdit {
                let document = try #require(ledger.documents.first)
                _ = try await ClientCommands.objectSetDetails(.with {
                    $0.contextID = document.objectID
                    $0.details = [.with {
                        $0.key = BundledPropertyKey.name.rawValue
                        $0.value = "T5 ordinary edit by r14".protobufValue
                    }]
                }).invoke()
            }
            let service = AnytypeTorahSpaceRelatedDocumentsService(associations: AnytypeTorahAssociationRepository())
            let selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: "Genesis 3:3")
            let expected = ledger.documents.prefix(expanded ? 3 : 1).map {
                T5ApplePairTarget(objectID: $0.objectID, blockID: expanded ? $0.blockID : nil, canUnlink: $0.blockID == nil)
            }
            let snapshot = try await waitForSnapshot(
                service: service, spaceID: ledger.spaceID, selection: selection, expected: expected
            )
            try require(
                snapshot.coverage == (expanded ? .indexedTargetsOnly : .indexedDocumentsOnly),
                "actual-host-coverage-differs"
            )
            try require(snapshot.limitations.contains(.indexFreshnessUnverified), "unproven-freshness-was-hidden")
            if expanded {
                try require(
                    !snapshot.limitations.contains(.blockAssociationsNotIndexed)
                        && !snapshot.limitations.contains(.sourceQuotesNotIndexed),
                    "expanded-lookup-retained-legacy-limitations"
                )
            } else {
                try require(
                    snapshot.limitations.contains(.blockAssociationsNotIndexed)
                        && snapshot.limitations.contains(.sourceQuotesNotIndexed),
                    "old-runtime-lost-fallback-disclosure"
                )
            }
            try require(
                !snapshot.limitations.contains(.staleCandidates) && !snapshot.limitations.contains(.resultLimitReached),
                "fixture-results-incomplete"
            )
            var readbacks: [T5ApplePairReadback] = []
            var canonicalByID: [String: String] = [:]
            for (index, document) in ledger.documents.enumerated() {
                let response = try await show(document.objectID, spaceID: ledger.spaceID)
                let value = try rootDetails(response, objectID: document.objectID, spaceID: ledger.spaceID)
                let canonical = try #require(value.values[ledger.canonicalKey]?.stringValue)
                canonicalByID[document.objectID] = canonical
                let canonicalSHA = hash(Data(canonical.utf8))
                let publicSHA = try publicHash(value)
                try require(canonicalSHA == document.canonicalSHA256, "canonical-or-unknown-fields-changed")
                try require(publicSHA == document.publicSHA256, "public-derived-projection-changed")
                let privateVersion = value.values["_pinkhaTorahRelatedVersion"]?.numberValue
                if expanded { try require(privateVersion == 1, "new-runtime-private-projection-missing") }
                if let blockID = document.blockID, let text = document.blockText {
                    let graph = try await T5BlockReachability.evaluate(
                        spaceID: ledger.spaceID, rootID: document.objectID,
                        nodes: response.objectView.blocks.map { .init(id: $0.id, childIDs: $0.childrenIds) }
                    )
                    try require(graph.isVerified && graph.reachableBlockIDs.contains(blockID), "block-no-longer-reachable")
                    let block = try #require(response.objectView.blocks.first { $0.id == blockID })
                    guard case .text(let content) = block.content else {
                        throw T5ApplePairFailure.invariant("quoted-block-content-type-changed")
                    }
                    try require(content.text == text, "quoted-block-text-changed")
                }
                let expectedName = index == 0 && (phase == .oldEdit || phase == .newRecover || phase == .newFreshness)
                    ? "T5 ordinary edit by r14" : document.initialName
                try require(value.name == expectedName, "ordinary-title-or-old-client-edit-not-preserved")
                readbacks.append(.init(
                    objectID: document.objectID, canonicalSHA256: canonicalSHA, publicSHA256: publicSHA,
                    blockID: document.blockID, blockTextSHA256: document.blockText.map { hash(Data($0.utf8)) },
                    nativeRelatedVersion: privateVersion.map(Int.init), title: value.name
                ))
            }
            let freshness: T5AppleFreshnessReceipt?
            if phase == .newFreshness {
                freshness = try await verifyHostFreshness(ledger: ledger, originalCanonical: canonicalByID, service: service)
            } else {
                freshness = nil
            }
            _ = try await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            do {
                _ = try await ClientCommands.accountPreloadRemainingSpaces().invoke(ignoreLogErrors: .accountIsNotRunning)
                throw T5ApplePairFailure.invariant("native-account-remains-running-after-stop")
            } catch let error as Anytype_Rpc.Account.PreloadRemainingSpaces.Response.Error
                where error.code == .accountIsNotRunning { }
            _ = try await ClientCommands.appShutdown().invoke()
            ledger.completedPhases.append(phase.rawValue)
            try writePrivate(ledger, to: ledgerURL)
            let receipt = T5ApplePairReceipt(
                protocolVersion: "pinkha-t5-apple-runtime-pair-v2", status: "PASS", phase: phase.rawValue,
                token: token, nonce: nonce, processID: ProcessInfo.processInfo.processIdentifier,
                appSourceSHA: sourceSHA, runtimeVersion: version, actualCapability: expanded ? "verified" : "unavailable",
                coverage: snapshot.coverage.rawValue, limitations: snapshot.limitations.map { String(describing: $0) }.sorted(),
                rootPathSHA256: ledger.rootPathSHA256, rootRelativePath: rootRelativePath,
                currentRootPathSHA256: rootSHA, accountID: ledger.accountID, spaceID: ledger.spaceID,
                manifestID: ledger.manifestID, manifestSHA256: ledger.manifestSHA256, canonicalKey: ledger.canonicalKey,
                previousLedgerSHA256: previousLedgerSHA, nextLedgerSHA256: hash(try Data(contentsOf: ledgerURL)),
                migrationPerformed: migration, walletCreated: phase == .oldCreate, walletRecovered: phase != .oldCreate,
                accountCreated: phase == .oldCreate, accountSelected: phase != .oldCreate,
                accountStopCompleted: true, accountNotRunningConfirmed: true, appShutdownCompleted: true,
                documents: readbacks, targets: snapshot.documents.map {
                    .init(objectID: $0.objectID, blockID: $0.blockID, canUnlink: $0.canUnlink)
                }.sorted { $0.objectID < $1.objectID },
                readbackBoundary: phase == .newFreshness ? "BEFORE_FRESHNESS_MUTATIONS" : "BEFORE_ACCOUNT_STOP",
                freshness: freshness
            )
            try writePrivate(receipt, to: resultURL)
            print("T5_APPLE_PAIR_PHASE_PASS phase=\(phase.rawValue) pid=\(receipt.processID) capability=\(receipt.actualCapability)")
        } catch {
            _ = try? await ClientCommands.appShutdown().invoke()
            throw error
        }
        #else
        throw T5ApplePairFailure.invariant("test-only-lookup-build-flag-missing")
        #endif
    }


    @MainActor
    private func verifyHostFreshness(
        ledger: T5ApplePairLedger, originalCanonical: [String: String],
        service: AnytypeTorahSpaceRelatedDocumentsService
    ) async throws -> T5AppleFreshnessReceipt {
        try require(ledger.documents.count == 3, "freshness-original-targets-missing")
        let documents = ledger.documents
        let allIDs = documents.map(\.objectID)
        let original = try documents.map { document in
            let raw = try #require(originalCanonical[document.objectID])
            try require(hash(Data(raw.utf8)) == document.canonicalSHA256, "freshness-original-payload-differs")
            return raw
        }
        var mutations: [String: Int] = [:]
        var observations: [T5AppleFreshnessObservation] = []
        func targets(_ indices: [Int]) -> [T5ApplePairTarget] {
            indices.map { index in
                let document = documents[index]
                return .init(objectID: document.objectID, blockID: document.blockID, canUnlink: document.blockID == nil)
            }
        }
        @MainActor
        func writeCanonical(_ index: Int, raw: String) async throws {
            _ = try await ClientCommands.objectSetDetails(.with {
                $0.contextID = documents[index].objectID
                $0.details = [.with {
                    $0.key = ledger.canonicalKey
                    $0.value = raw.protobufValue
                }]
            }).invoke()
            mutations["ObjectSetDetails", default: 0] += 1
        }
        @MainActor
        func observe(
            _ name: String, reference: String = "Genesis 3:3", candidates: [String], host: [Int],
            stale: Bool = false, inspect: Int? = nil, expectedRaw: String? = nil,
            reachable: Bool? = nil, archived: Bool = false, deleted: Bool = false
        ) async throws {
            let before = try await waitForNativeCandidates(
                spaceID: ledger.spaceID, reference: reference, expected: candidates
            )
            let selection = TorahInspectorSelection(providerID: "sefaria", canonicalRef: reference)
            // The same retained production service performs every lookup. There
            // is no direct repository/cache invalidation after the native writes.
            let snapshot = try await waitForSnapshot(
                service: service, spaceID: ledger.spaceID, selection: selection, expected: targets(host)
            )
            let after = try await waitForNativeCandidates(
                spaceID: ledger.spaceID, reference: reference, expected: candidates
            )
            let limitations = snapshot.limitations.map { String(describing: $0) }.sorted()
            let expectedLimits = stale ? ["indexFreshnessUnverified", "staleCandidates"] : ["indexFreshnessUnverified"]
            try require(snapshot.coverage == .indexedTargetsOnly && limitations == expectedLimits,
                        "freshness-host-coverage-or-stale-disclosure-differs")
            var objectID: String?
            var canonicalRaw: String?
            var retained: Bool?
            var observedArchive: Bool?
            var graph: T5AppleFreshnessGraph?
            var deletedError: Int?
            if let index = inspect {
                let document = documents[index]
                objectID = document.objectID
                if deleted {
                    do {
                        _ = try await show(document.objectID, spaceID: ledger.spaceID)
                        throw T5ApplePairFailure.invariant("deleted-page-still-opens")
                    } catch let error as Anytype_Rpc.Object.Show.Response.Error
                        where error.code == .notFound || error.code == .objectDeleted {
                        deletedError = error.code.rawValue
                    }
                } else {
                    let response = try await show(document.objectID, spaceID: ledger.spaceID)
                    let value = try rootDetails(response, objectID: document.objectID, spaceID: ledger.spaceID)
                    let raw = try #require(value.values[ledger.canonicalKey]?.stringValue)
                    try require(raw == expectedRaw, "freshness-live-canonical-bytes-differ")
                    try require(value.isArchived == archived, "freshness-live-archive-state-differs")
                    canonicalRaw = raw
                    retained = true
                    observedArchive = value.isArchived
                    if let blockID = document.blockID, let shouldReach = reachable {
                        let nodes = response.objectView.blocks.map {
                            T5AppleFreshnessGraphNode(id: $0.id, childIDs: $0.childrenIds)
                        }
                        let actual = try await T5BlockReachability.evaluate(
                            spaceID: ledger.spaceID, rootID: document.objectID,
                            nodes: nodes.map { .init(id: $0.id, childIDs: $0.childIDs) }
                        )
                        try require(actual.isVerified && actual.reachableBlockIDs.contains(blockID) == shouldReach,
                                    "freshness-live-block-reachability-differs")
                        if shouldReach {
                            let block = try #require(response.objectView.blocks.first { $0.id == blockID })
                            guard case .text(let text) = block.content, text.text == document.blockText else {
                                throw T5ApplePairFailure.invariant("freshness-retained-block-text-changed")
                            }
                        }
                        graph = .init(spaceID: ledger.spaceID, rootID: response.objectView.rootID,
                                      targetID: blockID, targetReachable: shouldReach, nodes: nodes)
                    }
                }
            }
            observations.append(.init(
                name: name, sourceReference: reference, spaceID: ledger.spaceID,
                nativeCandidatesBefore: before, nativeCandidatesAfter: after,
                targets: snapshot.documents.map {
                    .init(objectID: $0.objectID, blockID: $0.blockID, canUnlink: $0.canUnlink)
                }.sorted { $0.objectID < $1.objectID }, coverage: snapshot.coverage.rawValue,
                limitations: limitations, objectID: objectID, canonicalRaw: canonicalRaw,
                canonicalSHA256: canonicalRaw.map { hash(Data($0.utf8)) }, objectRetained: retained,
                isArchived: observedArchive, graph: graph, objectShowError: deletedError
            ))
        }
        try await observe("baseline", candidates: allIDs, host: [0, 1, 2])
        let unlink = try changedCanonical(original[1], unlink: true)
        try await writeCanonical(1, raw: unlink)
        try await observe("note_unlink", candidates: [allIDs[0], allIDs[2]], host: [0, 2],
                          inspect: 1, expectedRaw: unlink, reachable: true)
        try await writeCanonical(1, raw: original[1])
        try await observe("note_restore", candidates: allIDs, host: [0, 1, 2],
                          inspect: 1, expectedRaw: original[1], reachable: true)
        let quoteUpdate = try changedCanonical(original[2], unlink: false)
        try await writeCanonical(2, raw: quoteUpdate)
        try await observe("quote_update_original", candidates: [allIDs[0], allIDs[1]], host: [0, 1],
                          inspect: 2, expectedRaw: quoteUpdate, reachable: true)
        try await observe("quote_update_other", reference: "Genesis 3:4", candidates: [allIDs[2]], host: [2],
                          inspect: 2, expectedRaw: quoteUpdate, reachable: true)
        try await writeCanonical(2, raw: original[2])
        try await observe("quote_restore", candidates: allIDs, host: [0, 1, 2],
                          inspect: 2, expectedRaw: original[2], reachable: true)
        for archived in [true, false] {
            _ = try await ClientCommands.objectListSetIsArchived(.with {
                $0.objectIds = [allIDs[1]]
                $0.isArchived = archived
            }).invoke()
            mutations["ObjectListSetIsArchived", default: 0] += 1
            try await observe(archived ? "note_archive" : "note_unarchive",
                              candidates: archived ? [allIDs[0], allIDs[2]] : allIDs,
                              host: archived ? [0, 2] : [0, 1, 2],
                              inspect: 1, expectedRaw: original[1], reachable: true, archived: archived)
        }
        for index in [1, 2] {
            let blockID = try #require(documents[index].blockID)
            _ = try await ClientCommands.blockListDelete(.with {
                $0.contextID = allIDs[index]
                $0.blockIds = [blockID]
            }).invoke()
            mutations["BlockListDelete", default: 0] += 1
            // The index still contains the canonical reference. Only the live
            // graph in the production service can exclude this exact target.
            try await observe(index == 1 ? "note_block_removed" : "quote_block_removed",
                              candidates: allIDs, host: index == 1 ? [0, 2] : [0], stale: true,
                              inspect: index, expectedRaw: original[index], reachable: false)
        }
        _ = try await ClientCommands.objectListDelete(.with { $0.objectIds = [allIDs[0]] }).invoke()
        mutations["ObjectListDelete", default: 0] += 1
        try await observe("page_deleted", candidates: [allIDs[1], allIDs[2]], host: [], stale: true,
                          inspect: 0, deleted: true)
        try require(observations.count == 11 && mutations == [
            "ObjectSetDetails": 4, "ObjectListSetIsArchived": 2, "BlockListDelete": 2, "ObjectListDelete": 1
        ], "freshness-native-mutation-sequence-differs")
        return .init(
            status: "PASS_ACTUAL_SWIFT_NATIVE_LOOKUP",
            writeOrigin: "DIRECT_NATIVE_RPC_WITHOUT_EXPLICIT_HOST_INVALIDATION",
            serviceScope: "ONE_REUSED_PRODUCTION_SERVICE", coverage: "indexedTargetsOnly",
            spaceWideFreshness: "NOT_PROVEN", navigationStatus: "NOT_RUN",
            originalCanonical: originalCanonical, nativeMutationCounts: mutations, observations: observations
        )
    }

    private func changedCanonical(_ original: String, unlink: Bool) throws -> String {
        var root = try #require(JSONSerialization.jsonObject(with: Data(original.utf8)) as? [String: Any])
        var records = try #require(root["records"] as? [[String: Any]])
        try require(records.count == 1, "freshness-single-original-canonical-record-required")
        if unlink {
            records = []
        } else {
            var item = try #require(records[0]["item"] as? [String: Any])
            item["canonicalKey"] = "Genesis 3:4"
            item["externalID"] = "Genesis 3:4"
            records[0]["item"] = item
        }
        root["records"] = records
        let data = try JSONSerialization.data(withJSONObject: root, options: [.sortedKeys, .withoutEscapingSlashes])
        return try #require(String(data: data, encoding: .utf8))
    }

    @MainActor
    private func waitForNativeCandidates(spaceID: String, reference: String, expected: [String]) async throws -> [String] {
        let identity = T5SourceIdentity(providerID: "sefaria", canonicalReference: reference).indexValue
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            let records = try await Container.shared.searchMiddleService().search(
                spaceId: spaceID, filters: [.with {
                    $0.relationKey = "_pinkhaTorahRelatedSources"
                    $0.condition = .in
                    $0.value = [identity].protobufValue
                }], keys: [BundledPropertyKey.id.rawValue, BundledPropertyKey.spaceId.rawValue,
                           "_pinkhaTorahRelatedVersion"], limit: 20
            )
            try require(records.allSatisfy {
                !$0.id.isEmpty && $0.spaceId == spaceID && $0.values["_pinkhaTorahRelatedVersion"]?.numberValue == 1
            }, "freshness-native-candidate-identity-or-version-differs")
            let identifiers = records.map(\.id).sorted()
            if identifiers == expected.sorted() { return identifiers }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw T5ApplePairFailure.invariant("freshness-native-index-did-not-converge")
    }

    @MainActor
    private func prepareFixture(
        token: String, sourceSHA: String, rootSHA: String, accountID: String, spaceID: String
    ) async throws -> T5ApplePairLedger {
        let manifest = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceID)
        let manifestID = try #require(manifest.manifestObjectId)
        _ = try await ClientCommands.workspaceObjectListAdd(.with {
            $0.spaceID = spaceID
            $0.objectIds = ["_otnote"]
        }).invoke()
        let customID = try #require(manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey])
        let custom = ObjectType(details: try await details(customID, spaceID: spaceID)).uniqueKey
        let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 3:3")
        let repository = AnytypeTorahAssociationRepository()
        var documents: [T5ApplePairDocument] = []
        for (index, type) in [ObjectTypeUniqueKey.page, .note, custom].enumerated() {
            try await waitForType(type, spaceID: spaceID)
            let document = try await Container.shared.objectActionsService().createObject(
                name: "T5 runtime fixture \(index)", typeUniqueKey: type,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: spaceID, origin: .none, templateId: nil
            )
            var blockID: String?
            var blockText: String?
            var item = source.item
            item.unknownFields["futurePairField"] = .object(["token": .string(token), "preserve": .bool(true)])
            if index > 0 {
                let text = index == 1 ? "Block context survives both runtimes" : "Source quote survives both runtimes"
                blockID = try await Container.shared.blockService().addFirstBlock(
                    contextId: document.id, info: .empty(id: "", content: .text(.plain(text, contentType: .text)))
                )
                blockText = text
            }
            if index == 2 {
                item.role = .sourceQuote
                item.providerPayload = String(decoding: try TorahAssociationPayloadCodec().encodeSourceQuote(.init(
                    providerID: source.providerID, externalID: source.canonicalReference,
                    canonicalKey: source.canonicalReference, labelHe: source.canonicalReference,
                    snapshotText: blockText, unknownFields: ["futureQuoteField": .string(token)]
                )), as: UTF8.self)
            }
            let target: TorahAssociationTarget
            if let blockID { target = .block(objectId: document.id, blockId: blockID) }
            else { target = .object(objectId: document.id) }
            _ = try await repository.addAssociation(item, target: target, spaceId: spaceID)
            let ready = try await waitForReady(document.id, spaceID: spaceID)
            let canonical = try #require(ready.values[manifest.documentAssociationsPropertyKey]?.stringValue)
            documents.append(.init(
                objectID: document.id, typeKey: type.value, initialName: ready.name, blockID: blockID, blockText: blockText,
                canonicalSHA256: hash(Data(canonical.utf8)), publicSHA256: try publicHash(ready)
            ))
        }
        try require(Set(documents.map(\.objectID)).count == 3, "native-created-document-ids-not-distinct")
        let manifestDetails = try await details(manifestID, spaceID: spaceID)
        let raw = try #require(manifestDetails.values[BundledPropertyKey.description.rawValue]?.stringValue)
        return .init(
            token: token, appSourceSHA: sourceSHA, rootPathSHA256: rootSHA,
            rootRelativePath: "Library/Application Support/Anytype/middleware-go",
            accountID: accountID, spaceID: spaceID,
            manifestID: manifestID, manifestSHA256: hash(Data(raw.utf8)),
            canonicalKey: manifest.documentAssociationsPropertyKey, documents: documents, completedPhases: []
        )
    }

    @MainActor
    private func waitForType(_ type: ObjectTypeUniqueKey, spaceID: String) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            let results = try await Container.shared.searchMiddleService().search(
                spaceId: spaceID, filters: [.with {
                    $0.relationKey = BundledPropertyKey.uniqueKey.rawValue
                    $0.condition = .equal
                    $0.value = type.value.protobufValue
                }], keys: [BundledPropertyKey.id, .spaceId, .uniqueKey].map(\.rawValue), limit: 2
            )
            if results.count == 1, let indexed = results.first, indexed.spaceId == spaceID,
               ObjectType(details: try await details(indexed.id, spaceID: spaceID)).uniqueKey == type {
                return
            }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw T5ApplePairFailure.invariant("native-type-index-did-not-become-ready-\(type.value)")
    }

    @MainActor
    private func waitForReady(_ objectID: String, spaceID: String) async throws -> ObjectDetails {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            let value = try await details(objectID, spaceID: spaceID)
            if value.values[TorahNativePropertyDefinition.readinessKey]?.boolValue == true,
               value.values[TorahNativePropertyDefinition.statusKey]?.stringValue == "READY" {
                return value
            }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw T5ApplePairFailure.invariant("native-public-projection-did-not-become-ready")
    }

    @MainActor
    private func waitForSnapshot(
        service: AnytypeTorahSpaceRelatedDocumentsService, spaceID: String,
        selection: TorahInspectorSelection, expected: [T5ApplePairTarget]
    ) async throws -> TorahRelatedDocumentsSnapshot {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            do {
                let result = try await service.relatedDocuments(spaceID: spaceID, selection: selection)
                let targets = result.documents.map {
                    T5ApplePairTarget(objectID: $0.objectID, blockID: $0.blockID, canUnlink: $0.canUnlink)
                }.sorted { $0.objectID < $1.objectID }
                if targets == expected.sorted(by: { $0.objectID < $1.objectID }),
                   result.documents.allSatisfy({ $0.spaceID == spaceID && $0.typeID?.isEmpty == false }) {
                    return result
                }
            } catch T5SpaceRelatedDocumentsError.indexUnavailable { }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw T5ApplePairFailure.invariant("actual-app-related-lookup-did-not-converge")
    }

    private func show(_ objectID: String, spaceID: String) async throws -> Anytype_Rpc.Object.Show.Response {
        try await ClientCommands.objectShow(.with {
            $0.contextID = objectID
            $0.objectID = objectID
            $0.spaceID = spaceID
        }).invoke()
    }

    private func details(_ objectID: String, spaceID: String) async throws -> ObjectDetails {
        try rootDetails(try await show(objectID, spaceID: spaceID), objectID: objectID, spaceID: spaceID)
    }

    private func rootDetails(
        _ response: Anytype_Rpc.Object.Show.Response, objectID: String, spaceID: String
    ) throws -> ObjectDetails {
        try require(response.objectView.rootID == objectID, "native-root-identity-differs")
        let raw = try #require(response.objectView.details.first { $0.id == objectID }?.details)
        let value = try ObjectDetails(protobufStruct: raw)
        try require(value.id == objectID && value.spaceId == spaceID && !value.isDeleted, "native-space-identity-differs")
        return value
    }

    private func publicHash(_ details: ObjectDetails) throws -> String {
        let keys = TorahNativePropertyDefinition.all.map(\.key) + [
            TorahNativePropertyDefinition.engineVersionKey, TorahNativePropertyDefinition.readinessKey,
            TorahNativePropertyDefinition.labelsKey, TorahNativePropertyDefinition.statusKey,
            TorahNativePropertyDefinition.attachedPropertiesKey
        ]
        var object: [String: Any] = [:]
        for key in keys {
            if let value = details.values[key] {
                object[key] = try JSONSerialization.jsonObject(with: value.jsonUTF8Data(), options: [.fragmentsAllowed])
            }
        }
        return hash(try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes]))
    }

    private func writePrivate<T: Encodable>(_ value: T, to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        try encoder.encode(value).write(to: url, options: [.atomic, .completeFileProtectionUnlessOpen])
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
    }

    private func requiredEnvironment(_ key: String, _ environment: [String: String]) throws -> String {
        let value = try #require(environment[key])
        try require(!value.isEmpty, "empty-required-environment")
        return value
    }

    private func require(_ predicate: Bool, _ label: String) throws {
        guard predicate else { throw T5ApplePairFailure.invariant(label) }
    }

    private func hash(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
}

// The original runtime-pair suite above remains independently selectable.
// This separate suite covers only the quote freshness stages missing from the
// retained pagination proof; it never executes the original pair or pagination.
private struct T5RemainingFreshnessReadback: Codable {
    let objectID: String
    let spaceID: String
    let title: String
    let typeKey: String
    let canonicalRaw: String
    let canonicalSHA256: String
}

private struct T5RemainingFreshnessObservation: Codable {
    let name: String
    let sourceReference: String
    let spaceID: String
    let serviceID: String
    let serviceQueryOrdinal: Int
    let nativeCandidatesBefore: [String]
    let nativeCandidatesAfter: [String]
    let targets: [T5ApplePairTarget]
    let coverage: String
    let limitations: [String]
    let readbacks: [T5RemainingFreshnessReadback]
    let quoteGraph: T5AppleFreshnessGraph
    let quoteBlockTextSHA256: String?
}

private struct T5RemainingFreshnessReceipt: Codable {
    let protocolVersion: String
    let status: String
    let token: String
    let appSourceSHA: String
    let runID: String
    let runAttempt: String
    let processID: Int32
    let runtimeProfile: String
    let runtimeVersion: String
    let actualCapability: String
    let accountID: String
    let spaceID: String
    let rootPathSHA256: String
    let serverConfiguration: String
    let ledger: T5ApplePairLedger
    let originalCanonical: [String: String]
    let serviceID: String
    let serviceQueryCount: Int
    let nativeMutationCounts: [String: Int]
    let observations: [T5RemainingFreshnessObservation]
    let accountStopCompleted: Bool
    let accountNotRunningConfirmed: Bool
    let appShutdownCompleted: Bool
    let historicalPaginationInvocations: Int
    let runtimePairPhasesExecuted: [String]
    let mixedVersionAccepted: Bool
    let wholeIndexCompleteness: String
    let forcedNetworkOutage: String
    let productLookupFlag: String
}

@Suite("T5 remaining native quote freshness", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_T5_REMAINING_FRESHNESS"] == "1"))
struct TorahT5RemainingFreshnessTests {
    @Test("Same-service canonical quote move and live quote-block deletion")
    @MainActor
    func nativeQuoteMoveAndBlockDeletion() async throws {
        try await TorahT5RuntimePairTests().runRemainingQuoteFreshness()
    }
}

extension TorahT5RuntimePairTests {
    @MainActor
    fileprivate func runRemainingQuoteFreshness() async throws {
        #if PINKHA_NATIVE_T5_LOOKUP_V1
        let environment = ProcessInfo.processInfo.environment
        try require(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1"
                    && environment["PINKHA_T5_REMAINING_FRESHNESS"] == "1", "fresh-disposable-scope-required")
        let token = try requiredEnvironment("PINKHA_T5_FRESHNESS_TOKEN", environment)
        let sourceSHA = try requiredEnvironment("PINKHA_T5_FRESHNESS_APP_SHA", environment)
        let runID = try requiredEnvironment("PINKHA_T5_FRESHNESS_RUN_ID", environment)
        let runAttempt = try requiredEnvironment("PINKHA_T5_FRESHNESS_RUN_ATTEMPT", environment)
        let runtimeProfile = try requiredEnvironment("PINKHA_T5_FRESHNESS_RUNTIME_PROFILE", environment)
        try require(token.count == 32 && token.allSatisfy(\.isHexDigit)
                    && sourceSHA.count == 40 && sourceSHA.allSatisfy(\.isHexDigit)
                    && runID.allSatisfy(\.isNumber) && Int(runAttempt).map({ $0 > 0 }) == true,
                    "invalid-current-run-identity")
        try require(runtimeProfile == "r15-attachment-authorized-current-read-v1", "explicit-coherent-runtime-required")
        let version = try await ClientCommands.appGetVersion().invoke().version
        try require(version == T5NativeRelatedLookupCapability.coherentRuntimeVersion, "actual-coherent-runtime-differs")
        guard case .verified = try await AnytypeT5NativeRelatedLookup.current() else {
            throw T5ApplePairFailure.invariant("actual-production-lookup-capability-unavailable")
        }
        let support = try #require(FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first)
        let directory = support.appendingPathComponent("pinkha-t5-remaining-freshness", isDirectory: true)
        try require(!FileManager.default.fileExists(atPath: directory.path), "existing-freshness-account-work")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true,
                                                attributes: [.posixPermissions: 0o700])
        let root = Container.shared.localRepoService().middlewareRepoURL.resolvingSymlinksInPath().path
        let expectedRoot = URL(fileURLWithPath: NSHomeDirectory(), isDirectory: true)
            .appendingPathComponent("Library/Application Support/Anytype/middleware-go").resolvingSymlinksInPath().path
        try require(root == expectedRoot, "freshness-native-root-outside-owned-container")
        let rootSHA = hash(Data(root.utf8))
        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
        do {
            let wallet = try await ClientCommands.walletCreate(.with { $0.rootPath = root }).invoke(responseMask: {
                $0.mnemonic = "***"; $0.accountKey = "***"
            })
            try require(!wallet.mnemonic.isEmpty && !wallet.accountKey.isEmpty, "empty-freshness-private-credentials")
            try writePrivate(T5ApplePairSecrets(token: token, mnemonic: wallet.mnemonic, accountKey: wallet.accountKey),
                             to: directory.appendingPathComponent("secrets.json"))
            let account = try await Container.shared.authService().createAccount(name: "T5 quote freshness", iconOption: 1, imagePath: "")
            let space = try await Container.shared.workspaceService().createSpace(name: "T5 quote freshness",
                iconOption: 1, accessType: .private, useCase: .none, withChat: false, spaceType: .regular)
            _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: space.spaceID)
            let ledger = try await prepareFixture(token: token, sourceSHA: sourceSHA, rootSHA: rootSHA,
                                                 accountID: account.id, spaceID: space.spaceID)
            try require(ledger.completedPhases.isEmpty && ledger.documents.count == 3, "historical-pair-must-not-execute")
            var originals: [String: String] = [:]
            for document in ledger.documents {
                let value = try await details(document.objectID, spaceID: ledger.spaceID)
                let raw = try #require(value.values[ledger.canonicalKey]?.stringValue)
                try require(hash(Data(raw.utf8)) == document.canonicalSHA256, "prepared-original-canonical-differs")
                originals[document.objectID] = raw
            }
            let quote = ledger.documents[2]
            let quoteBlock = try #require(quote.blockID)
            let originalQuote = try #require(originals[quote.objectID])
            let movedQuote = try changedCanonical(originalQuote, unlink: false)
            let ids = ledger.documents.map(\.objectID)
            let service = AnytypeTorahSpaceRelatedDocumentsService(associations: AnytypeTorahAssociationRepository())
            let serviceID = String(describing: ObjectIdentifier(service))
            var observations: [T5RemainingFreshnessObservation] = []
            var mutations: [String: Int] = [:]
            var queryCount = 0

            @MainActor
            func observe(_ name: String, reference: String, candidates: [String], host: [Int],
                         quoteRaw: String, reachable: Bool) async throws {
                let before = try await waitForNativeCandidates(spaceID: ledger.spaceID, reference: reference, expected: candidates)
                // One immediate call through the same production service after
                // native membership converges. No host cache invalidation or
                // service recreation can hide a stale quote result.
                queryCount += 1
                let snapshot = try await service.relatedDocuments(spaceID: ledger.spaceID,
                    selection: TorahInspectorSelection(providerID: "sefaria", canonicalRef: reference))
                let actual = snapshot.documents.map { T5ApplePairTarget(objectID: $0.objectID, blockID: $0.blockID, canUnlink: $0.canUnlink) }
                    .sorted { $0.objectID < $1.objectID }
                let wanted = host.map { index in
                    let document = ledger.documents[index]
                    return T5ApplePairTarget(objectID: document.objectID, blockID: document.blockID, canUnlink: document.blockID == nil)
                }.sorted { $0.objectID < $1.objectID }
                try require(actual == wanted, "immediate-same-service-quote-membership-differs")
                let limits = snapshot.limitations.map { String(describing: $0) }.sorted()
                try require(snapshot.coverage == .indexedTargetsOnly
                    && limits == (reachable ? ["indexFreshnessUnverified"] : ["indexFreshnessUnverified", "staleCandidates"]),
                    "quote-freshness-coverage-or-stale-disclosure-differs")
                let after = try await waitForNativeCandidates(spaceID: ledger.spaceID, reference: reference, expected: candidates)
                var readbacks: [T5RemainingFreshnessReadback] = []
                var observedGraph: T5AppleFreshnessGraph?
                var textSHA: String?
                for document in ledger.documents {
                    let response = try await show(document.objectID, spaceID: ledger.spaceID)
                    let value = try rootDetails(response, objectID: document.objectID, spaceID: ledger.spaceID)
                    let raw = try #require(value.values[ledger.canonicalKey]?.stringValue)
                    let expected: String
                    if document.objectID == quote.objectID { expected = quoteRaw }
                    else { expected = try #require(originals[document.objectID]) }
                    try require(raw == expected && !value.isArchived && !value.isDeleted
                        && value.name == document.initialName, "quote-mutation-changed-unrelated-native-content")
                    let typeKey = ObjectType(details: try await details(value.type, spaceID: ledger.spaceID)).uniqueKey.value
                    try require(typeKey == document.typeKey, "quote-mutation-changed-native-type")
                    readbacks.append(.init(objectID: document.objectID, spaceID: value.spaceId, title: value.name,
                        typeKey: typeKey, canonicalRaw: raw, canonicalSHA256: hash(Data(raw.utf8))))
                    if document.objectID == quote.objectID {
                        let nodes = response.objectView.blocks.map { T5AppleFreshnessGraphNode(id: $0.id, childIDs: $0.childrenIds) }
                        let graph = try await T5BlockReachability.evaluate(spaceID: ledger.spaceID, rootID: quote.objectID,
                            nodes: nodes.map { .init(id: $0.id, childIDs: $0.childIDs) })
                        try require(graph.isVerified && graph.reachableBlockIDs.contains(quoteBlock) == reachable,
                                    "actual-quote-block-reachability-differs")
                        if reachable {
                            let block = try #require(response.objectView.blocks.first { $0.id == quoteBlock })
                            guard case .text(let text) = block.content, text.text == quote.blockText else {
                                throw T5ApplePairFailure.invariant("quote-body-text-changed")
                            }
                            textSHA = hash(Data(text.text.utf8))
                        }
                        observedGraph = .init(spaceID: ledger.spaceID, rootID: response.objectView.rootID,
                            targetID: quoteBlock, targetReachable: reachable, nodes: nodes)
                    }
                }
                observations.append(.init(name: name, sourceReference: reference, spaceID: ledger.spaceID,
                    serviceID: serviceID, serviceQueryOrdinal: queryCount, nativeCandidatesBefore: before,
                    nativeCandidatesAfter: after, targets: actual, coverage: snapshot.coverage.rawValue,
                    limitations: limits, readbacks: readbacks, quoteGraph: try #require(observedGraph),
                    quoteBlockTextSHA256: textSHA))
            }

            try await observe("baseline", reference: "Genesis 3:3", candidates: ids, host: [0, 1, 2], quoteRaw: originalQuote, reachable: true)
            _ = try await ClientCommands.objectSetDetails(.with {
                $0.contextID = quote.objectID; $0.details = [.with { $0.key = ledger.canonicalKey; $0.value = movedQuote.protobufValue }]
            }).invoke()
            mutations["ObjectSetDetails", default: 0] += 1
            try await observe("moved_original", reference: "Genesis 3:3", candidates: Array(ids.prefix(2)), host: [0, 1], quoteRaw: movedQuote, reachable: true)
            try await observe("moved_other", reference: "Genesis 3:4", candidates: [quote.objectID], host: [2], quoteRaw: movedQuote, reachable: true)
            _ = try await ClientCommands.objectSetDetails(.with {
                $0.contextID = quote.objectID; $0.details = [.with { $0.key = ledger.canonicalKey; $0.value = originalQuote.protobufValue }]
            }).invoke()
            mutations["ObjectSetDetails", default: 0] += 1
            try await observe("restored_original", reference: "Genesis 3:3", candidates: ids, host: [0, 1, 2], quoteRaw: originalQuote, reachable: true)
            try await observe("restored_other_empty", reference: "Genesis 3:4", candidates: [], host: [], quoteRaw: originalQuote, reachable: true)
            _ = try await ClientCommands.blockListDelete(.with { $0.contextID = quote.objectID; $0.blockIds = [quoteBlock] }).invoke()
            mutations["BlockListDelete", default: 0] += 1
            try await observe("quote_block_removed", reference: "Genesis 3:3", candidates: ids, host: [0, 1], quoteRaw: originalQuote, reachable: false)
            try require(observations.count == 6 && queryCount == 6
                && mutations == ["ObjectSetDetails": 2, "BlockListDelete": 1], "remaining-freshness-scope-differs")
            _ = try await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            do {
                _ = try await ClientCommands.accountPreloadRemainingSpaces().invoke(ignoreLogErrors: .accountIsNotRunning)
                throw T5ApplePairFailure.invariant("freshness-account-remains-running")
            } catch let error as Anytype_Rpc.Account.PreloadRemainingSpaces.Response.Error where error.code == .accountIsNotRunning { }
            _ = try await ClientCommands.appShutdown().invoke()
            try writePrivate(T5RemainingFreshnessReceipt(protocolVersion: "pinkha-t5-remaining-quote-freshness-v1",
                status: "PASS_ACTUAL_NATIVE_QUOTE_FRESHNESS", token: token, appSourceSHA: sourceSHA,
                runID: runID, runAttempt: runAttempt, processID: ProcessInfo.processInfo.processIdentifier,
                runtimeProfile: runtimeProfile, runtimeVersion: version, actualCapability: "verified",
                accountID: account.id, spaceID: ledger.spaceID, rootPathSHA256: rootSHA, serverConfiguration: "localOnly",
                ledger: ledger, originalCanonical: originals, serviceID: serviceID, serviceQueryCount: queryCount,
                nativeMutationCounts: mutations, observations: observations, accountStopCompleted: true,
                accountNotRunningConfirmed: true, appShutdownCompleted: true, historicalPaginationInvocations: 0,
                runtimePairPhasesExecuted: [], mixedVersionAccepted: false, wholeIndexCompleteness: "NOT_PROVEN",
                forcedNetworkOutage: "NOT_RUN", productLookupFlag: "OFF"), to: directory.appendingPathComponent("receipt.json"))
            print("T5_REMAINING_QUOTE_FRESHNESS observations=6 host_queries=6 native_mutations=3")
        } catch {
            _ = try? await ClientCommands.appShutdown().invoke()
            throw error
        }
        #else
        throw T5ApplePairFailure.invariant("test-only-native-lookup-flag-required")
        #endif
    }
}
