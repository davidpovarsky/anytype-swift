import Foundation
import CryptoKit
import AnytypeCore
import PinkhaKit
import ProtobufMessages
import Services
import Testing
import TorahInspectorCore
@testable import Anytype

/// Creates only real native data in a fresh job-owned simulator. A paired
/// compatibility account, when that route is selected, is never opened here.
@Suite("T5 real Inspector UI fixture", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_T5_UI_PREPARATION"] == "1"))
struct TorahT5UIAcceptancePreparationTests {
    private struct Target: Codable {
        let role: String
        let objectID: String
        let typeKey: String
        let title: String
        let blockID: String?
        let blockText: String?
        let firstBlockID: String?
        let firstBlockText: String?
        let associationID: String
        let canonicalSHA256: String
        var resultID: String?
    }

    private struct Excluded: Codable {
        let objectID: String
        let spaceID: String
        let reason: String
    }

    private struct PresentationProbe: Codable {
        let objectID: String
        let blockID: String
        let text: String
    }

    private struct Fixture: Codable {
        let protocolVersion: Int
        let token: String
        let appSourceSHA: String
        let runID: String
        let runtimeVersion: String
        let preparationProcessID: Int32
        let accountID: String
        let spaceID: String
        let foreignSpaceID: String
        let accountRootPathSHA256: String
        let providerID: String
        let canonicalReference: String
        let coverage: String
        let limitations: [String]
        let targets: [Target]
        let excluded: [Excluded]
        let presentationProbe: PresentationProbe
        let productLookupFlag: String
    }

    private struct Secrets: Codable {
        let token: String
        let mnemonic: String
        let accountKey: String
    }

    private struct MutationRow: Codable, Equatable {
        let resultID: String
        let objectID: String
        let spaceID: String
        let blockID: String?
        let title: String
        let typeID: String
        let kind: String
        let canUnlink: Bool
    }

    private struct MutationObservation: Codable {
        let stage: String
        let nativeReadStatus: String
        let nativeTypeID: String?
        let nativeTypeKey: String?
        let nativeLayout: Int?
        let nativeTitle: String?
        let associationID: String?
        let canonicalSHA256: String?
        let bodySHA256: String?
        let blockReachable: Bool?
        let relatedRows: [MutationRow]
        let coverage: String
        let limitations: [String]
    }

    private struct MutationReceipt: Codable {
        let protocolVersion: Int
        let status: String
        let scope: String
        let token: String
        let appSourceSHA: String
        let runID: String
        let runtimeVersion: String
        let preparationProcessID: Int32
        let accountID: String
        let spaceID: String
        let accountRootPathSHA256: String
        let providerID: String
        let canonicalReference: String
        let transientObjectID: String
        let transientAssociationID: String
        let transientBlockID: String
        let canonicalPropertyKey: String
        let observations: [MutationObservation]
        let productLookupFlag: String
        let fullT5Accepted: Bool
    }

    private enum Failure: Error { case invariant(String) }
    private let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 1:1")

    @MainActor
    @Test("Prepare exact current-Space rows, offscreen block targets and a persisted native login")
    func prepareFreshNativeUIFixture() async throws {
        let environment = ProcessInfo.processInfo.environment
        try require(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1", "disposable-confirmation-required")
        let token = try #require(environment["PINKHA_T5_UI_TOKEN"])
        let sourceSHA = try #require(environment["PINKHA_T5_UI_APP_SHA"])
        let runID = try #require(environment["PINKHA_T5_UI_RUN_ID"])
        try require(token.count == 32 && token.allSatisfy(\.isHexDigit), "invalid-run-token")
        try require(sourceSHA.count == 40 && sourceSHA.allSatisfy(\.isHexDigit), "invalid-app-source")
        try require(!runID.isEmpty && runID.allSatisfy(\.isNumber), "invalid-run-id")
        let support = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true)
        let fixtureURL = support.appendingPathComponent("pinkha-t5-native-ui-fixture.json")
        let privateDirectory = support.appendingPathComponent("pinkha-t5-native-ui-private", isDirectory: true)
        try require(!FileManager.default.fileExists(atPath: fixtureURL.path)
            && !FileManager.default.fileExists(atPath: privateDirectory.path)
            && !FileManager.default.fileExists(atPath: support.appendingPathComponent("pinkha-t5-runtime-pair").path),
            "fixture-or-pair-account-already-present")
        let expectedVersion: String
        switch environment["PINKHA_T5_UI_RUNTIME_PROFILE"] ?? "r15" {
        case "r15":
            expectedVersion = T5NativeRelatedLookupCapability.runtimeVersion
        case "r15-attachment-v1":
            expectedVersion = T5NativeRelatedLookupCapability.correctedRuntimeVersion
        default:
            throw Failure.invariant("unknown-explicit-ui-runtime-profile")
        }
        // Capability recognition remains exact and cannot turn on an unapproved host.
        guard case .unavailable = T5NativeRelatedLookupCapability.resolve(
            enabledByBuild: false, runtimeVersion: expectedVersion
        ) else { throw Failure.invariant("runtime-enabled-disabled-host") }
        for foreign in [expectedVersion + "-unreviewed", expectedVersion + "\n",
                        expectedVersion.replacingOccurrences(of: "595f8142", with: "00000000")] {
            if foreign == expectedVersion { continue }
            guard case .unavailable = T5NativeRelatedLookupCapability.resolve(
                enabledByBuild: true, runtimeVersion: foreign
            ) else { throw Failure.invariant("foreign-runtime-granted-capability") }
        }
        let actualVersion = try await ClientCommands.appGetVersion().invoke().version
        try require(actualVersion == expectedVersion, "actual-r15-runtime-required")
        guard case .verified = try await AnytypeT5NativeRelatedLookup.current() else {
            throw Failure.invariant("actual-production-runtime-capability-required")
        }

        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
        let root = Container.shared.localRepoService().middlewareRepoURL.resolvingSymlinksInPath().path
        // Capture both credentials privately and mask both in the command log.
        // The real seed is persisted so ordinary App launches perform login.
        let wallet = try await ClientCommands.walletCreate(.with { $0.rootPath = root }).invoke(responseMask: {
            $0.mnemonic = "***"
            $0.accountKey = "***"
        })
        try require(!wallet.mnemonic.isEmpty && !wallet.accountKey.isEmpty, "empty-native-wallet")
        try FileManager.default.createDirectory(at: privateDirectory, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700])
        let secretsURL = privateDirectory.appendingPathComponent("secrets.json")
        try JSONEncoder().encode(Secrets(token: token, mnemonic: wallet.mnemonic, accountKey: wallet.accountKey))
            .write(to: secretsURL, options: .withoutOverwriting)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: secretsURL.path)
        let seed = Container.shared.seedService()
        try seed.saveSeed(wallet.mnemonic)
        let recovered = try seed.obtainSeed()
        try require(recovered == wallet.mnemonic.trimmingCharacters(in: .whitespacesAndNewlines), "keychain-readback-differs")
        let account = try await Container.shared.authService().createAccount(name: "T5 UI disposable", iconOption: 1, imagePath: "")
        try require(!account.id.isEmpty, "native-account-missing")
        let spaceID = try await createSpace(name: "T5 UI current Space")
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceID)
        let manifest = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceID)
        let writingID = try #require(manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey])
        let writingType = ObjectType(details: try await details(writingID, spaceID: spaceID)).uniqueKey
        _ = try await ClientCommands.workspaceObjectListAdd(.with {
            $0.spaceID = spaceID
            $0.objectIds = ["_otnote"]
        }).invoke()
        try await waitForType(.note, spaceID: spaceID)
        let associations = AnytypeTorahAssociationRepository()
        var targets: [Target] = []
        var presentationProbe: PresentationProbe?
        for (role, type) in [("page", ObjectTypeUniqueKey.page), ("note", .note), ("writing", writingType),
                             ("block", .page), ("quote", .page)] {
            let title = presentationTitle(role: role, token: token)
            let object = try await create(type: type, name: title, spaceID: spaceID)
            var blockID: String?
            var blockText: String?
            var firstID: String?
            var firstText: String?
            if role == "block" || role == "quote" {
                // The control route opens the document without a block target.
                // Real UI must observe this first block and an offscreen target,
                // then show the exact distant target after the Inspector tap.
                for index in 0..<24 {
                    let text = "T5 " + role + " leading paragraph \(index). "
                        + String(repeating: "Existing native content remains unchanged. ", count: 12)
                    let id = try await append(text, objectID: object.id, spaceID: spaceID)
                    if index == 0 { firstID = id; firstText = text }
                }
                let text = "T5 native " + role + " target " + token
                blockID = try await append(text, objectID: object.id, spaceID: spaceID)
                blockText = text
            } else if role == "note" {
                _ = try await append("T5 existing Note " + token, objectID: object.id, spaceID: spaceID)
            } else if role == "page" {
                let text = "פסקה עברית לקריאה בלבד עם טקסט מעורב T5 — " + token
                let id = try await append(text, objectID: object.id, spaceID: spaceID)
                presentationProbe = .init(objectID: object.id, blockID: id, text: text)
            }
            var item = source.item
            if role == "quote" {
                item.role = .sourceQuote
                // Synthetic document content is an explicit native fixture.
                // This is discovery/navigation acceptance, not provider insertion.
                item.providerPayload = String(decoding: try TorahAssociationPayloadCodec().encodeSourceQuote(.init(
                    providerID: source.providerID, externalID: source.canonicalReference,
                    canonicalKey: source.canonicalReference, labelHe: source.canonicalReference,
                    snapshotText: blockText
                )), as: UTF8.self)
            }
            let target: TorahAssociationTarget = blockID.map { .block(objectId: object.id, blockId: $0) }
                ?? .object(objectId: object.id)
            let saved = try await associations.addAssociation(item, target: target, spaceId: spaceID)
            let readback: [TorahAssociationItem]
            if let blockID {
                readback = try await associations.listBlockAssociations(objectId: object.id, blockId: blockID, spaceId: spaceID)
                let documentLinks = try await associations.listDocumentAssociations(objectId: object.id, spaceId: spaceID)
                try require(!documentLinks.contains(where: source.matches), "block-only-target-has-document-link")
            } else {
                readback = try await associations.listDocumentAssociations(objectId: object.id, spaceId: spaceID)
            }
            try require(readback.filter { $0.id == saved.id && $0.role == item.role
                && $0.providerID == source.providerID && $0.canonicalKey == source.canonicalReference }.count == 1,
                "canonical-role-readback-differs")
            let response = try await show(object.id, spaceID: spaceID)
            let value = try rootDetails(response, objectID: object.id, spaceID: spaceID)
            try require(value.name == title, "native-title-readback-differs")
            let canonical = try #require(value.values[manifest.documentAssociationsPropertyKey]?.stringValue)
            if let blockID, let blockText {
                let graph = try await T5BlockReachability.evaluate(spaceID: spaceID, rootID: object.id,
                    nodes: response.objectView.blocks.map { .init(id: $0.id, childIDs: $0.childrenIds) })
                try require(graph.isVerified && graph.reachableBlockIDs.contains(blockID), "native-target-unreachable")
                let nativeBlock = try #require(response.objectView.blocks.first { $0.id == blockID })
                guard case .text(let content) = nativeBlock.content else { throw Failure.invariant("native-target-not-text") }
                try require(content.text == blockText, "native-target-text-differs")
            }
            if role == "page" {
                let probe = try #require(presentationProbe)
                let graph = try await T5BlockReachability.evaluate(spaceID: spaceID, rootID: object.id,
                    nodes: response.objectView.blocks.map { .init(id: $0.id, childIDs: $0.childrenIds) })
                try require(graph.isVerified && graph.reachableBlockIDs.contains(probe.blockID), "presentation-probe-unreachable")
                let nativeBlock = try #require(response.objectView.blocks.first { $0.id == probe.blockID })
                guard case .text(let content) = nativeBlock.content else { throw Failure.invariant("presentation-probe-not-text") }
                try require(content.text == probe.text, "presentation-probe-readback-differs")
            }
            targets.append(.init(role: role, objectID: object.id, typeKey: type.value, title: value.name, blockID: blockID,
                blockText: blockText, firstBlockID: firstID, firstBlockText: firstText, associationID: saved.id,
                canonicalSHA256: hash(Data(canonical.utf8)), resultID: nil))
        }
        try require(Set(targets.map(\.objectID)).count == 5, "native-positive-objects-not-distinct")
        var excluded: [Excluded] = []
        for (reason, identity) in [
            ("differentVerse", T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 1:2")),
            ("differentProvider", T5SourceIdentity(providerID: "fixture-other-provider", canonicalReference: source.canonicalReference))
        ] {
            let object = try await create(type: .page, name: "T5 excluded " + reason, spaceID: spaceID)
            _ = try await associations.addAssociation(identity.item, target: .object(objectId: object.id), spaceId: spaceID)
            excluded.append(.init(objectID: object.id, spaceID: spaceID, reason: reason))
        }
        let foreignSpace = try await createSpace(name: "T5 UI other Space")
        try require(foreignSpace != spaceID, "native-spaces-not-distinct")
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: foreignSpace)
        _ = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: foreignSpace)
        let foreign = try await create(type: .page, name: "T5 excluded other Space", spaceID: foreignSpace)
        _ = try await associations.addAssociation(source.item, target: .object(objectId: foreign.id), spaceId: foreignSpace)
        excluded.append(.init(objectID: foreign.id, spaceID: foreignSpace, reason: "differentSpace"))
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceID)
        let service = AnytypeTorahSpaceRelatedDocumentsService(associations: associations)
        let selection = TorahInspectorSelection(providerID: source.providerID, canonicalRef: source.canonicalReference)
        var snapshot = try await waitForSnapshot(service, selection: selection, targets: targets, spaceID: spaceID)
        // Only the new corrected-runtime route adds the two missing mutations.
        // The historical pair route and its existing five-target fixture are unchanged.
        var mutationReceipt: MutationReceipt?
        if environment["PINKHA_T5_UI_RUNTIME_PROFILE"] == "r15-attachment-v1" {
            let result = try await verifyTypeChangeAndWholeObjectDelete(
                service: service, associations: associations, selection: selection, baseline: snapshot,
                spaceID: spaceID, canonicalPropertyKey: manifest.documentAssociationsPropertyKey,
                token: token, sourceSHA: sourceSHA, runID: runID, runtimeVersion: actualVersion,
                accountID: account.id, root: root
            )
            mutationReceipt = result.receipt
            snapshot = result.finalSnapshot
        }
        try require(snapshot.coverage == .indexedTargetsOnly && snapshot.limitations == [.indexFreshnessUnverified],
            "coverage-must-remain-explicitly-incomplete")
        try require(Set(snapshot.documents.map(\.id)).count == 5, "native-result-ids-not-distinct")
        for index in targets.indices {
            let row = try #require(snapshot.documents.first {
                $0.objectID == targets[index].objectID && $0.blockID == targets[index].blockID
            })
            try require(row.spaceID == spaceID && row.canUnlink == (targets[index].blockID == nil), "native-row-authority-differs")
            try require((row.kind == .note) == (targets[index].role == "note"), "native-row-type-differs")
            try require(row.title == targets[index].title, "native-row-title-differs")
            targets[index].resultID = row.id
        }
        let fixture = Fixture(protocolVersion: 1, token: token, appSourceSHA: sourceSHA, runID: runID,
            runtimeVersion: actualVersion, preparationProcessID: ProcessInfo.processInfo.processIdentifier,
            accountID: account.id, spaceID: spaceID, foreignSpaceID: foreignSpace,
            accountRootPathSHA256: hash(Data(root.utf8)), providerID: source.providerID,
            canonicalReference: source.canonicalReference, coverage: "indexedTargetsOnly",
            limitations: ["indexFreshnessUnverified"], targets: targets, excluded: excluded,
            presentationProbe: try #require(presentationProbe), productLookupFlag: "OFF")
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        try encoder.encode(fixture).write(to: fixtureURL, options: .withoutOverwriting)
        if let mutationReceipt {
            try encoder.encode(mutationReceipt).write(
                to: support.appendingPathComponent("pinkha-t5-native-ui-mutations.json"), options: .withoutOverwriting)
            print("T5_UI_NATIVE_MUTATIONS real_type_change=1 real_whole_object_delete=1 observations=3 final_targets=5")
        }
        print("T5_UI_PREPARED real_native_targets=5 excluded=3 keychain_readback=matched coverage=indexedTargetsOnly")
    }

    @MainActor
    private func verifyTypeChangeAndWholeObjectDelete(
        service: AnytypeTorahSpaceRelatedDocumentsService, associations: AnytypeTorahAssociationRepository,
        selection: TorahInspectorSelection, baseline: TorahRelatedDocumentsSnapshot,
        spaceID: String, canonicalPropertyKey: String, token: String, sourceSHA: String,
        runID: String, runtimeVersion: String, accountID: String, root: String
    ) async throws -> (receipt: MutationReceipt, finalSnapshot: TorahRelatedDocumentsSnapshot) {
        let originalRows = mutationRows(baseline)
        try require(originalRows.count == 5 && Set(originalRows.map(\.objectID)).count == 5,
            "mutation-baseline-must-be-the-original-five")
        let object = try await create(type: .page, name: "T5 transient type/delete " + String(token.prefix(8)), spaceID: spaceID)
        try require(!originalRows.contains { $0.objectID == object.id }, "mutation-object-reuses-ui-target")
        let body = "T5 native type/delete preserved body " + token
        let blockID = try await append(body, objectID: object.id, spaceID: spaceID)
        let saved = try await associations.addAssociation(source.item, target: .object(objectId: object.id), spaceId: spaceID)
        let before = try await mutationReadback(objectID: object.id, blockID: blockID, body: body,
            spaceID: spaceID, canonicalPropertyKey: canonicalPropertyKey, expectedType: .page)
        let originalLinks = try await associations.listDocumentAssociations(objectId: object.id, spaceId: spaceID)
        try require(originalLinks.count == 1 && originalLinks[0].id == saved.id && source.matches(originalLinks[0]),
            "mutation-original-canonical-link-differs")
        let first = try await waitForMutationSnapshot(service, selection: selection, originalRows: originalRows,
            spaceID: spaceID, objectID: object.id, typeID: before.details.type, isNote: false)
        var observations = [mutationObservation(stage: "page-before-type-change", readback: before,
            typeKey: ObjectTypeUniqueKey.page.value, associationID: originalLinks[0].id, snapshot: first)]

        // This is the normal native command, with no fake search response or rewritten receipt.
        try await Container.shared.objectActionsService().setObjectType(objectId: object.id, typeUniqueKey: .note)
        let changed = try await mutationReadback(objectID: object.id, blockID: blockID, body: body,
            spaceID: spaceID, canonicalPropertyKey: canonicalPropertyKey, expectedType: .note)
        try require(changed.details.type != before.details.type && Data(changed.canonical.utf8) == Data(before.canonical.utf8),
            "type-change-did-not-preserve-exact-canonical-bytes")
        let changedLinks = try await associations.listDocumentAssociations(objectId: object.id, spaceId: spaceID)
        try require(changedLinks.count == 1 && changedLinks[0].id == saved.id && source.matches(changedLinks[0]),
            "type-change-altered-canonical-link-identity")
        let second = try await waitForMutationSnapshot(service, selection: selection, originalRows: originalRows,
            spaceID: spaceID, objectID: object.id, typeID: changed.details.type, isNote: true)
        observations.append(mutationObservation(stage: "note-after-type-change", readback: changed,
            typeKey: ObjectTypeUniqueKey.note.value, associationID: changedLinks[0].id, snapshot: second))

        // Delete this whole disposable document; none of the five UI targets is mutated.
        try await Container.shared.objectActionsService().delete(objectIds: [object.id])
        let deletedStatus = try await waitForNativeDeletion(objectID: object.id, spaceID: spaceID)
        let final = try await waitForMutationSnapshot(service, selection: selection, originalRows: originalRows,
            spaceID: spaceID, objectID: object.id, typeID: nil, isNote: nil)
        try require(mutationRows(final) == originalRows, "whole-object-delete-altered-original-five-rows")
        observations.append(.init(stage: "whole-object-deleted", nativeReadStatus: deletedStatus,
            nativeTypeID: nil, nativeTypeKey: nil, nativeLayout: nil, nativeTitle: nil, associationID: nil, canonicalSHA256: nil, bodySHA256: nil,
            blockReachable: nil, relatedRows: mutationRows(final), coverage: "indexedTargetsOnly",
            limitations: ["indexFreshnessUnverified"]))
        return (.init(protocolVersion: 1, status: "PASS", scope: "type-change-and-whole-object-delete",
            token: token, appSourceSHA: sourceSHA, runID: runID, runtimeVersion: runtimeVersion,
            preparationProcessID: ProcessInfo.processInfo.processIdentifier, accountID: accountID, spaceID: spaceID,
            accountRootPathSHA256: hash(Data(root.utf8)), providerID: source.providerID,
            canonicalReference: source.canonicalReference, transientObjectID: object.id,
            transientAssociationID: saved.id, transientBlockID: blockID, canonicalPropertyKey: canonicalPropertyKey,
            observations: observations, productLookupFlag: "OFF", fullT5Accepted: false), final)
    }

    @MainActor
    private func mutationReadback(objectID: String, blockID: String, body: String, spaceID: String,
                                  canonicalPropertyKey: String, expectedType: ObjectTypeUniqueKey)
        async throws -> (details: ObjectDetails, canonical: String, bodySHA256: String) {
        let response = try await show(objectID, spaceID: spaceID)
        let value = try rootDetails(response, objectID: objectID, spaceID: spaceID)
        try require(!value.type.isEmpty, "mutation-native-type-missing")
        let actualType = ObjectType(details: try await details(value.type, spaceID: spaceID)).uniqueKey
        try require(actualType == expectedType,
            "mutation-native-type-readback-differs")
        let canonical = try #require(value.values[canonicalPropertyKey]?.stringValue)
        try require(!canonical.isEmpty, "mutation-native-canonical-missing")
        let graph = try await T5BlockReachability.evaluate(spaceID: spaceID, rootID: objectID,
            nodes: response.objectView.blocks.map { .init(id: $0.id, childIDs: $0.childrenIds) })
        try require(graph.isVerified && graph.reachableBlockIDs.contains(blockID), "mutation-native-body-unreachable")
        let block = try #require(response.objectView.blocks.first { $0.id == blockID })
        guard case .text(let text) = block.content else { throw Failure.invariant("mutation-native-body-not-text") }
        try require(Data(text.text.utf8) == Data(body.utf8), "mutation-native-body-bytes-changed")
        return (value, canonical, hash(Data(text.text.utf8)))
    }

    private func mutationRows(_ snapshot: TorahRelatedDocumentsSnapshot) -> [MutationRow] {
        snapshot.documents.map {
            MutationRow(resultID: $0.id, objectID: $0.objectID, spaceID: $0.spaceID, blockID: $0.blockID,
                title: $0.title, typeID: $0.typeID ?? "", kind: $0.kind == .note ? "note" : "document", canUnlink: $0.canUnlink)
        }.sorted { $0.resultID < $1.resultID }
    }

    private func mutationObservation(stage: String,
        readback: (details: ObjectDetails, canonical: String, bodySHA256: String), typeKey: String, associationID: String,
        snapshot: TorahRelatedDocumentsSnapshot) -> MutationObservation {
        .init(stage: stage, nativeReadStatus: "present", nativeTypeID: readback.details.type,
            nativeTypeKey: typeKey, nativeLayout: readback.details.resolvedLayout ?? readback.details.layout,
            nativeTitle: readback.details.name,
            associationID: associationID,
            canonicalSHA256: hash(Data(readback.canonical.utf8)), bodySHA256: readback.bodySHA256,
            blockReachable: true, relatedRows: mutationRows(snapshot), coverage: "indexedTargetsOnly",
            limitations: ["indexFreshnessUnverified"])
    }

    @MainActor
    private func waitForMutationSnapshot(_ service: AnytypeTorahSpaceRelatedDocumentsService,
        selection: TorahInspectorSelection, originalRows: [MutationRow], spaceID: String,
        objectID: String, typeID: String?, isNote: Bool?) async throws -> TorahRelatedDocumentsSnapshot {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            do {
                let snapshot = try await service.relatedDocuments(spaceID: spaceID, selection: selection)
                let rows = mutationRows(snapshot)
                let preserved = rows.filter { $0.objectID != objectID }
                let changed = rows.filter { $0.objectID == objectID }
                let expectedCount = typeID == nil ? 0 : 1
                let expectedKind = isNote == true ? "note" : "document"
                if snapshot.coverage == .indexedTargetsOnly && snapshot.limitations == [.indexFreshnessUnverified]
                    && preserved == originalRows && changed.count == expectedCount
                    && changed.allSatisfy({ $0.spaceID == spaceID && $0.blockID == nil
                        && $0.typeID == typeID && $0.kind == expectedKind && $0.canUnlink }) {
                    return snapshot
                }
            } catch T5SpaceRelatedDocumentsError.indexUnavailable { }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw Failure.invariant("native-type-or-delete-query-did-not-converge")
    }

    private func waitForNativeDeletion(objectID: String, spaceID: String) async throws -> String {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            do {
                let response = try await show(objectID, spaceID: spaceID)
                try require(response.objectView.rootID == objectID, "deleted-readback-root-differs")
                let value = try ObjectDetails(protobufStruct: try #require(response.objectView.details.first { $0.id == objectID }?.details))
                try require(value.id == objectID && value.spaceId == spaceID, "deleted-readback-identity-differs")
                if value.isDeleted { return "isDeleted" }
            } catch let error as Anytype_Rpc.Object.Show.Response.Error where error.code == .notFound || error.code == .objectDeleted {
                return error.code == .objectDeleted ? "objectDeleted" : "notFound"
            }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw Failure.invariant("whole-object-delete-native-state-did-not-converge")
    }

    private func presentationTitle(role: String, token: String) -> String {
        guard role == "page" || role == "writing" else { return "T5 UI " + role }
        return "כותרת עברית ארוכה למסמך " + role + " — "
            + String(repeating: "מקור קנוני והערות עם טקסט מעורב T5. ", count: 5) + String(token.prefix(8))
    }

    @MainActor
    private func createSpace(name: String) async throws -> String {
        let value = try await Container.shared.workspaceService().createSpace(name: name, iconOption: 1,
            accessType: .private, useCase: .none, withChat: false, spaceType: .regular)
        try require(!value.spaceID.isEmpty, "native-space-missing")
        return value.spaceID
    }

    @MainActor
    private func create(type: ObjectTypeUniqueKey, name: String, spaceID: String) async throws -> ObjectDetails {
        try await Container.shared.objectActionsService().createObject(name: name, typeUniqueKey: type,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceID, origin: .none, templateId: nil)
    }

    @MainActor
    private func append(_ text: String, objectID: String, spaceID: String) async throws -> String {
        let service = Container.shared.blockService()
        let last = try await service.lastBlockId(from: objectID, spaceId: spaceID)
        return try await service.add(contextId: objectID, targetId: last,
            info: .empty(id: "", content: .text(.plain(text, contentType: .text))), position: .bottom)
    }

    @MainActor
    private func waitForType(_ type: ObjectTypeUniqueKey, spaceID: String) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            let values = try await Container.shared.searchMiddleService().search(spaceId: spaceID, filters: [.with {
                $0.relationKey = BundledPropertyKey.uniqueKey.rawValue
                $0.condition = .equal
                $0.value = type.value.protobufValue
            }], keys: [BundledPropertyKey.id, .spaceId, .uniqueKey].map(\.rawValue), limit: 2)
            if values.count == 1, let value = values.first, value.spaceId == spaceID,
               ObjectType(details: try await details(value.id, spaceID: spaceID)).uniqueKey == type { return }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw Failure.invariant("native-note-type-not-ready")
    }

    @MainActor
    private func waitForSnapshot(_ service: AnytypeTorahSpaceRelatedDocumentsService,
                                selection: TorahInspectorSelection, targets: [Target], spaceID: String) async throws -> TorahRelatedDocumentsSnapshot {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            do {
                let snapshot = try await service.relatedDocuments(spaceID: spaceID, selection: selection)
                if snapshot.documents.count == targets.count && targets.allSatisfy({ target in
                    snapshot.documents.filter { $0.spaceID == spaceID && $0.objectID == target.objectID && $0.blockID == target.blockID }.count == 1
                }) { return snapshot }
            } catch T5SpaceRelatedDocumentsError.indexUnavailable { }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw Failure.invariant("native-current-space-membership-did-not-converge")
    }

    private func show(_ objectID: String, spaceID: String) async throws -> Anytype_Rpc.Object.Show.Response {
        try await ClientCommands.objectShow(.with {
            $0.contextID = objectID; $0.objectID = objectID; $0.spaceID = spaceID
        }).invoke()
    }

    private func details(_ objectID: String, spaceID: String) async throws -> ObjectDetails {
        try rootDetails(try await show(objectID, spaceID: spaceID), objectID: objectID, spaceID: spaceID)
    }

    private func rootDetails(_ response: Anytype_Rpc.Object.Show.Response, objectID: String, spaceID: String) throws -> ObjectDetails {
        try require(response.objectView.rootID == objectID, "native-root-differs")
        let value = try ObjectDetails(protobufStruct: try #require(response.objectView.details.first { $0.id == objectID }?.details))
        try require(value.id == objectID && value.spaceId == spaceID && !value.isDeleted && !value.isArchived, "native-object-identity-differs")
        return value
    }

    private func hash(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    private func require(_ condition: Bool, _ label: String) throws {
        guard condition else { throw Failure.invariant(label) }
    }
}
