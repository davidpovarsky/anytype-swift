import Foundation
import CryptoKit
import Factory
import AnytypeCore
import PinkhaKit
import ProtobufMessages
import Services
import SwiftProtobuf
import Testing
import TorahInspectorCore
@testable import Anytype

private struct T5PaginationFilter: Codable {
    let key: String
    let condition: String
    let valueJSON: String
}

private struct T5PaginationSort: Codable {
    let key: String
    let direction: String
    let noCollate: Bool
}

private struct T5PaginationSearchCall: Codable {
    let spaceID: String
    let limit: Int
    let offset: Int
    let fullText: String
    let keys: [String]
    let filters: [T5PaginationFilter]
    let sorts: [T5PaginationSort]
    let objectIDs: [String]
    let resultSpaceIDs: [String]
}

@MainActor private final class T5PaginationSearchRecorder: SearchMiddleServiceProtocol {
    private let upstream: any SearchMiddleServiceProtocol
    private(set) var calls: [T5PaginationSearchCall] = []

    init(upstream: any SearchMiddleServiceProtocol) { self.upstream = upstream }

    func search(data: SearchRequest) async throws -> [ObjectDetails] {
        let result = try await upstream.search(data: data)
        calls.append(.init(
            spaceID: data.spaceId, limit: data.limit, offset: data.offset, fullText: data.fullText,
            keys: data.keys,
            filters: try data.filters.map {
                .init(key: $0.relationKey, condition: String(describing: $0.condition), valueJSON: try $0.value.jsonString())
            },
            sorts: data.sorts.map { .init(key: $0.relationKey, direction: String(describing: $0.type), noCollate: $0.noCollate) },
            objectIDs: result.map(\.id), resultSpaceIDs: result.map(\.spaceId)
        ))
        return result
    }

    func reset() { calls.removeAll() }
}

private struct T5PaginationNode: Codable {
    let id: String
    let childIDs: [String]
}

private struct T5PaginationTarget: Codable, Equatable {
    let objectID: String
    let blockID: String?
    let associationID: String
    let role: String
}

private struct T5PaginationReadback: Codable {
    let objectID: String
    let spaceID: String
    let rootID: String
    let title: String
    let typeID: String
    let isArchived: Bool
    let isDeleted: Bool
    let isReadonly: Bool
    let detailsRestricted: Bool
    let projectionReady: Bool
    let projectionState: String
    let projectionVersion: Int
    let relatedVersion: Int
    let canonicalRaw: String
    let canonicalSHA256: String
    let updatedAt: Double?
    let nodes: [T5PaginationNode]
}

private struct T5PaginationObject: Codable {
    let role: String
    let spaceID: String
    let objectID: String
    let canonicalKey: String
    let targets: [T5PaginationTarget]
    let original: T5PaginationReadback
}

private struct T5PaginationRow: Codable {
    let id: String
    let spaceID: String
    let objectID: String
    let blockID: String?
    let title: String
    let typeID: String?
    let sourceReference: String
    let canUnlink: Bool
    let kind: String
    let updatedAt: Double?
}

private struct T5PaginationObservation: Codable {
    let name: String
    let serviceID: String
    let activeSpaceID: String
    let requestedSpaceID: String
    let pageSize: Int
    let candidateLimit: Int
    let targetLimit: Int
    let nativeCandidatesBefore: [String]
    let nativeCandidatesAfter: [String]
    let calls: [T5PaginationSearchCall]
    let rows: [T5PaginationRow]
    let coverage: String
    let limitations: [String]
    let readbacks: [T5PaginationReadback]
}

private struct T5PaginationReceipt: Codable {
    let protocolVersion: String
    let status: String
    let token: String
    let appSourceSHA: String
    let runID: String
    let processID: Int32
    let runtimeVersion: String
    let accountID: String
    let spaceID: String
    let foreignSpaceID: String
    let rootPathSHA256: String
    let providerID: String
    let canonicalReference: String
    let indexValue: String
    let objects: [T5PaginationObject]
    let observations: [T5PaginationObservation]
    let nativeMutationCounts: [String: Int]
    let accountStopCompleted: Bool
    let accountNotRunningConfirmed: Bool
    let appShutdownCompleted: Bool
    let productLookupFlag: String
    let wholeIndexCompleteness: String
    let aclRevocation: String
}

private struct T5PaginationSecrets: Codable {
    let token: String
    let mnemonic: String
    let accountKey: String
}

private enum T5PaginationFailure: Error { case invariant(String) }

@Suite("T5 production native pagination", .serialized,
       .enabled(if: ProcessInfo.processInfo.environment["PINKHA_T5_NATIVE_PAGINATION"] == "1"))
@MainActor
struct TorahT5NativePaginationTests {
    private let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 5:5")

    @Test("Real multi-page queries, independent caps, current Space and native mutations")
    func nativePaginationCurrentSpaceAndMutationAcceptance() async throws {
        #if PINKHA_NATIVE_DERIVED && PINKHA_NATIVE_T5_LOOKUP_V1
        let environment = ProcessInfo.processInfo.environment
        try require(environment["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1", "disposable-confirmation-required")
        let token = try #require(environment["PINKHA_T5_PAGINATION_TOKEN"])
        let sourceSHA = try #require(environment["PINKHA_T5_PAGINATION_APP_SHA"])
        let runID = try #require(environment["PINKHA_T5_PAGINATION_RUN_ID"])
        try require(token.count == 32 && token.allSatisfy(\.isHexDigit), "invalid-token")
        try require(sourceSHA.count == 40 && sourceSHA.allSatisfy(\.isHexDigit), "invalid-source")
        try require(!runID.isEmpty && runID.allSatisfy(\.isNumber), "invalid-run")
        let support = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true)
        let privateDirectory = support.appendingPathComponent("pinkha-t5-native-pagination", isDirectory: true)
        try require(!FileManager.default.fileExists(atPath: privateDirectory.path)
            && !FileManager.default.fileExists(atPath: support.appendingPathComponent("pinkha-t5-runtime-pair").path)
            && !FileManager.default.fileExists(atPath: support.appendingPathComponent("pinkha-t5-native-ui-fixture.json").path),
            "fresh-private-account-required")
        let patch = "5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2"
        let version = try await ClientCommands.appGetVersion().invoke().version
        try require(version == "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + patch
            + "-pinkha-native-t5-lookup-v1-" + patch, "exact-r15-runtime-required")
        guard case .verified = try await AnytypeT5NativeRelatedLookup.current() else {
            throw T5PaginationFailure.invariant("production-capability-not-verified")
        }
        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)
        let root = Container.shared.localRepoService().middlewareRepoURL.resolvingSymlinksInPath().path
        let wallet = try await ClientCommands.walletCreate(.with { $0.rootPath = root }).invoke(responseMask: {
            $0.mnemonic = "***"; $0.accountKey = "***"
        })
        try require(!wallet.mnemonic.isEmpty && !wallet.accountKey.isEmpty, "native-credentials-missing")
        try FileManager.default.createDirectory(at: privateDirectory, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700])
        try write(T5PaginationSecrets(token: token, mnemonic: wallet.mnemonic, accountKey: wallet.accountKey),
                  to: privateDirectory.appendingPathComponent("secrets.json"))
        do {
            try Container.shared.seedService().saveSeed(wallet.mnemonic)
            let account = try await Container.shared.authService().createAccount(name: "T5 pagination disposable", iconOption: 1, imagePath: "")
            try require(!account.id.isEmpty, "native-account-missing")
            let spaceID = try await createSpace("T5 pagination current Space")
            try await activate(spaceID)
            let manifest = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: spaceID)
            let writingID = try #require(manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey])
            let writing = ObjectType(details: try await details(writingID, spaceID: spaceID)).uniqueKey
            _ = try await ClientCommands.workspaceObjectListAdd(.with { $0.spaceID = spaceID; $0.objectIds = ["_otnote"] }).invoke()
            try await waitForNoteType(spaceID)
            let associations = AnytypeTorahAssociationRepository()
            var objects: [T5PaginationObject] = []
            for (role, type) in [("page_a", ObjectTypeUniqueKey.page), ("page_b", .page), ("note", .note),
                                 ("writing", writing), ("block", .page), ("quote", .page), ("multi", .page)] {
                objects.append(try await createFixture(role: role, type: type, spaceID: spaceID,
                    canonicalKey: manifest.documentAssociationsPropertyKey, token: token, identity: source, associations: associations))
            }
            for (role, identity) in [
                ("different_verse", T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 5:6")),
                ("different_provider", T5SourceIdentity(providerID: "fixture-other-provider", canonicalReference: source.canonicalReference))
            ] {
                objects.append(try await createFixture(role: role, type: .page, spaceID: spaceID,
                    canonicalKey: manifest.documentAssociationsPropertyKey, token: token, identity: identity, associations: associations))
            }
            let foreignSpaceID = try await createSpace("T5 pagination other Space")
            try require(foreignSpaceID != spaceID, "distinct-native-spaces-required")
            try await activate(foreignSpaceID)
            let foreignManifest = try await Container.shared.pinkhaBootstrapService().bootstrapSpace(spaceId: foreignSpaceID)
            objects.append(try await createFixture(role: "foreign", type: .page, spaceID: foreignSpaceID,
                canonicalKey: foreignManifest.documentAssociationsPropertyKey, token: token, identity: source, associations: associations))
            try await activate(spaceID)
            let originals = objects.filter { !["different_verse", "different_provider", "foreign"].contains($0.role) }
            let foreign = try #require(objects.first { $0.role == "foreign" })
            try require(originals.count == 7 && originals.flatMap(\.targets).count == 9, "fixture-target-count-differs")
            try require(Set(objects.map(\.objectID)).count == 10, "fixture-object-identities-overlap")
            let originalSearch = Container.shared.searchMiddleService()
            let recorder = T5PaginationSearchRecorder(upstream: originalSearch)
            Container.shared.searchMiddleService.register { recorder }
            defer { Container.shared.searchMiddleService.register { originalSearch } }
            let baseQuery = T5ExpandedRelatedDocumentsQuery(pageSize: 2, candidateLimit: 50, targetLimit: 50)
            let candidateQuery = T5ExpandedRelatedDocumentsQuery(pageSize: 2, candidateLimit: 5, targetLimit: 50)
            let targetQuery = T5ExpandedRelatedDocumentsQuery(pageSize: 2, candidateLimit: 50, targetLimit: 3)
            let service = AnytypeTorahSpaceRelatedDocumentsService(associations: associations, expandedQuery: baseQuery)
            let candidateService = AnytypeTorahSpaceRelatedDocumentsService(associations: associations, expandedQuery: candidateQuery)
            let targetService = AnytypeTorahSpaceRelatedDocumentsService(associations: associations, expandedQuery: targetQuery)
            var observations: [T5PaginationObservation] = []
            var mutations: [String: Int] = [:]
            let ids = originals.map(\.objectID)
            let selection = TorahInspectorSelection(providerID: source.providerID, canonicalRef: source.canonicalReference)
            @MainActor
            func observe(_ name: String, service selectedService: AnytypeTorahSpaceRelatedDocumentsService,
                         query: T5ExpandedRelatedDocumentsQuery, space: String, candidates: [String],
                         inspected: [T5PaginationObject]) async throws {
                let before = try await waitForCandidates(space, expected: candidates, search: originalSearch)
                try require(Container.shared.activeSpaceManager().workspaceInfo?.accountSpaceId == space, "active-space-differs")
                recorder.reset()
                let snapshot = try await selectedService.relatedDocuments(spaceID: space, selection: selection)
                let calls = recorder.calls
                let after = try await waitForCandidates(space, expected: candidates, search: originalSearch)
                var readbacks: [T5PaginationReadback] = []
                for object in inspected { readbacks.append(try await readback(object.objectID, spaceID: object.spaceID, canonicalKey: object.canonicalKey)) }
                try require(!calls.isEmpty && calls.allSatisfy { $0.spaceID == space && $0.limit <= 2 }, "real-small-native-pages-required")
                try require(snapshot.coverage == .indexedTargetsOnly && snapshot.limitations.contains(.indexFreshnessUnverified), "coverage-widened")
                observations.append(.init(name: name, serviceID: String(describing: ObjectIdentifier(selectedService)),
                    activeSpaceID: try #require(Container.shared.activeSpaceManager().workspaceInfo?.accountSpaceId),
                    requestedSpaceID: space, pageSize: query.pageSize, candidateLimit: query.candidateLimit, targetLimit: query.targetLimit,
                    nativeCandidatesBefore: before, nativeCandidatesAfter: after, calls: calls,
                    rows: snapshot.documents.map { .init(id: $0.id, spaceID: $0.spaceID, objectID: $0.objectID,
                        blockID: $0.blockID, title: $0.title, typeID: $0.typeID, sourceReference: $0.sourceReference,
                        canUnlink: $0.canUnlink, kind: String(describing: $0.kind), updatedAt: $0.updatedAt?.timeIntervalSince1970) },
                    coverage: snapshot.coverage.rawValue, limitations: snapshot.limitations.map { String(describing: $0) }.sorted(), readbacks: readbacks))
            }
            try await observe("baseline", service: service, query: baseQuery, space: spaceID, candidates: ids, inspected: originals)
            try await observe("candidate_cap", service: candidateService, query: candidateQuery, space: spaceID, candidates: ids, inspected: originals)
            try await observe("target_cap", service: targetService, query: targetQuery, space: spaceID, candidates: ids, inspected: originals)
            try await activate(foreignSpaceID)
            mutations["SetActiveSpace", default: 0] += 1
            try await observe("other_space", service: service, query: baseQuery, space: foreignSpaceID,
                              candidates: [foreign.objectID], inspected: [foreign])
            try await activate(spaceID)
            mutations["SetActiveSpace", default: 0] += 1
            try await observe("return_to_original", service: service, query: baseQuery, space: spaceID, candidates: ids, inspected: originals)
            let note = try #require(originals.first { $0.role == "note" })
            for archived in [true, false] {
                _ = try await ClientCommands.objectListSetIsArchived(.with { $0.objectIds = [note.objectID]; $0.isArchived = archived }).invoke()
                mutations["ObjectListSetIsArchived", default: 0] += 1
                try await observe(archived ? "note_archive" : "note_unarchive", service: service, query: baseQuery, space: spaceID,
                    candidates: archived ? ids.filter { $0 != note.objectID } : ids, inspected: originals)
            }
            let page = try #require(originals.first { $0.role == "page_a" })
            var unlinked = try #require(JSONSerialization.jsonObject(with: Data(page.original.canonicalRaw.utf8)) as? [String: Any])
            unlinked["records"] = []
            let unlinkRaw = String(decoding: try JSONSerialization.data(withJSONObject: unlinked, options: [.sortedKeys]), as: UTF8.self)
            for (name, raw) in [("page_unlink", unlinkRaw), ("page_restore", page.original.canonicalRaw)] {
                _ = try await ClientCommands.objectSetDetails(.with {
                    $0.contextID = page.objectID
                    $0.details = [.with { $0.key = page.canonicalKey; $0.value = raw.protobufValue }]
                }).invoke()
                mutations["ObjectSetDetails", default: 0] += 1
                try await observe(name, service: service, query: baseQuery, space: spaceID,
                    candidates: name == "page_unlink" ? ids.filter { $0 != page.objectID } : ids, inspected: originals)
            }
            let blockObject = try #require(originals.first { $0.role == "block" })
            let blockID = try #require(blockObject.targets.first?.blockID)
            _ = try await ClientCommands.blockListDelete(.with { $0.contextID = blockObject.objectID; $0.blockIds = [blockID] }).invoke()
            mutations["BlockListDelete", default: 0] += 1
            try await observe("block_removed", service: service, query: baseQuery, space: spaceID, candidates: ids, inspected: originals)
            try require(observations.count == 10 && mutations == ["SetActiveSpace": 2, "ObjectListSetIsArchived": 2,
                "ObjectSetDetails": 2, "BlockListDelete": 1], "native-sequence-differs")
            _ = try await ClientCommands.accountStop(.with { $0.removeData = false }).invoke()
            do {
                _ = try await ClientCommands.accountPreloadRemainingSpaces().invoke(ignoreLogErrors: .accountIsNotRunning)
                throw T5PaginationFailure.invariant("native-account-remains-running")
            } catch let error as Anytype_Rpc.Account.PreloadRemainingSpaces.Response.Error where error.code == .accountIsNotRunning { }
            _ = try await ClientCommands.appShutdown().invoke()
            try write(T5PaginationReceipt(protocolVersion: "pinkha-t5-native-pagination-v1", status: "PASS_NATIVE_OBSERVATIONS",
                token: token, appSourceSHA: sourceSHA, runID: runID, processID: ProcessInfo.processInfo.processIdentifier,
                runtimeVersion: version, accountID: account.id, spaceID: spaceID, foreignSpaceID: foreignSpaceID,
                rootPathSHA256: hash(Data(root.utf8)), providerID: source.providerID, canonicalReference: source.canonicalReference,
                indexValue: source.indexValue, objects: objects, observations: observations, nativeMutationCounts: mutations,
                accountStopCompleted: true, accountNotRunningConfirmed: true, appShutdownCompleted: true,
                productLookupFlag: "OFF", wholeIndexCompleteness: "NOT_PROVEN", aclRevocation: "NOT_PROVEN"),
                to: privateDirectory.appendingPathComponent("receipt.json"))
            print("T5_NATIVE_PAGINATION observations=10 fixture_objects=10 current_targets=9 product_lookup=OFF")
        } catch {
            _ = try? await ClientCommands.appShutdown().invoke()
            throw error
        }
        #else
        throw T5PaginationFailure.invariant("test-only-native-lookup-flags-required")
        #endif
    }

    private func createFixture(role: String, type: ObjectTypeUniqueKey, spaceID: String, canonicalKey: String,
                               token: String, identity: T5SourceIdentity,
                               associations: AnytypeTorahAssociationRepository) async throws -> T5PaginationObject {
        let object = try await Container.shared.objectActionsService().createObject(name: "T5 pagination " + role + " " + token,
            typeUniqueKey: type, shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceID, origin: .none, templateId: nil)
        var targets: [T5PaginationTarget] = []
        let roles = role == "multi" ? ["document", "block", "quote"] : [role == "block" || role == "quote" ? role : "document"]
        for targetRole in roles {
            var item = identity.item
            var blockID: String?
            if targetRole != "document" {
                let text = "T5 pagination native " + targetRole + " " + token
                let service = Container.shared.blockService()
                let last = try await service.lastBlockId(from: object.id, spaceId: spaceID)
                blockID = try await service.add(contextId: object.id, targetId: last,
                    info: .empty(id: "", content: .text(.plain(text, contentType: .text))), position: .bottom)
                if targetRole == "quote" {
                    item.role = .sourceQuote
                    item.providerPayload = String(decoding: try TorahAssociationPayloadCodec().encodeSourceQuote(.init(
                        providerID: identity.providerID, externalID: identity.canonicalReference, canonicalKey: identity.canonicalReference,
                        labelHe: identity.canonicalReference, snapshotText: text)), as: UTF8.self)
                }
            }
            let target: TorahAssociationTarget = blockID.map { .block(objectId: object.id, blockId: $0) } ?? .object(objectId: object.id)
            let saved = try await associations.addAssociation(item, target: target, spaceId: spaceID)
            targets.append(.init(objectID: object.id, blockID: blockID, associationID: saved.id, role: targetRole))
        }
        let clock = ContinuousClock(); let deadline = clock.now.advanced(by: .seconds(45))
        var original = try await readback(object.id, spaceID: spaceID, canonicalKey: canonicalKey)
        while !(original.projectionReady && original.projectionState == "READY"
                && original.projectionVersion == 1 && original.relatedVersion == 1), clock.now < deadline {
            try await Task.sleep(for: .milliseconds(100))
            original = try await readback(object.id, spaceID: spaceID, canonicalKey: canonicalKey)
        }
        try require(original.projectionReady && original.projectionState == "READY"
            && original.projectionVersion == 1 && original.relatedVersion == 1, "fixture-projection-not-ready")
        try require(!original.isArchived && !original.isDeleted && !original.isReadonly && !original.detailsRestricted,
                    "new-fixture-object-not-writable")
        return .init(role: role, spaceID: spaceID, objectID: object.id, canonicalKey: canonicalKey, targets: targets, original: original)
    }

    private func readback(_ objectID: String, spaceID: String, canonicalKey: String) async throws -> T5PaginationReadback {
        let response = try await show(objectID, spaceID: spaceID)
        let value = try rootDetails(response, objectID: objectID, spaceID: spaceID)
        let raw = try #require(value.values[canonicalKey]?.stringValue)
        let restrictions = MiddlewareObjectRestrictionsConverter.convertObjectRestrictions(middlewareRestrictions: response.objectView.restrictions).objectRestriction
        return .init(objectID: objectID, spaceID: value.spaceId, rootID: response.objectView.rootID, title: value.name,
            typeID: value.type, isArchived: value.isArchived, isDeleted: value.isDeleted, isReadonly: value.isReadonly,
            detailsRestricted: restrictions.contains(.details),
            projectionReady: value.values[TorahNativePropertyDefinition.readinessKey]?.boolValue == true,
            projectionState: value.values[TorahNativePropertyDefinition.statusKey]?.stringValue ?? "",
            projectionVersion: Int(value.values[TorahNativePropertyDefinition.engineVersionKey]?.numberValue ?? -1),
            relatedVersion: Int(value.values["_pinkhaTorahRelatedVersion"]?.numberValue ?? -1), canonicalRaw: raw,
            canonicalSHA256: hash(Data(raw.utf8)), updatedAt: value.lastModifiedDate?.timeIntervalSince1970,
            nodes: response.objectView.blocks.map { .init(id: $0.id, childIDs: $0.childrenIds) })
    }

    private func waitForCandidates(_ spaceID: String, expected: [String], search: any SearchMiddleServiceProtocol) async throws -> [String] {
        let clock = ContinuousClock(); let deadline = clock.now.advanced(by: .seconds(45))
        var filters = SearchHelper.notHiddenFilters()
        filters.append(SearchHelper.templateScheme(include: false))
        filters.append(SearchHelper.spaceIdFilter(spaceID))
        filters.append(.with {
            $0.relationKey = "_pinkhaTorahRelatedSources"; $0.condition = .in; $0.value = [source.indexValue].protobufValue
        })
        repeat {
            let result = try await search.search(spaceId: spaceID, filters: filters,
                keys: ["id", "spaceId", "_pinkhaTorahRelatedVersion"], limit: 50)
            try require(result.allSatisfy { $0.spaceId == spaceID && !$0.id.isEmpty
                && $0.values["_pinkhaTorahRelatedVersion"]?.numberValue == 1 }, "raw-native-index-identity-differs")
            let ids = result.map(\.id).sorted()
            if ids == expected.sorted() { return ids }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw T5PaginationFailure.invariant("native-candidate-membership-did-not-converge")
    }

    private func createSpace(_ name: String) async throws -> String {
        let space = try await Container.shared.workspaceService().createSpace(name: name, iconOption: 1,
            accessType: .private, useCase: .none, withChat: false, spaceType: .regular)
        try require(!space.spaceID.isEmpty, "native-space-missing")
        return space.spaceID
    }

    private func activate(_ spaceID: String) async throws {
        let manager = Container.shared.activeSpaceManager()
        let info = try await manager.setActiveSpace(spaceId: spaceID)
        try require(info?.accountSpaceId == spaceID && manager.workspaceInfo?.accountSpaceId == spaceID, "active-space-not-confirmed")
    }

    private func waitForNoteType(_ spaceID: String) async throws {
        let clock = ContinuousClock(); let deadline = clock.now.advanced(by: .seconds(45))
        repeat {
            let result = try await Container.shared.searchMiddleService().search(spaceId: spaceID, filters: [.with {
                $0.relationKey = BundledPropertyKey.uniqueKey.rawValue; $0.condition = .equal; $0.value = ObjectTypeUniqueKey.note.value.protobufValue
            }], keys: ["id", "spaceId", "uniqueKey"], limit: 2)
            if result.count == 1, let value = result.first, value.spaceId == spaceID,
               ObjectType(details: try await details(value.id, spaceID: spaceID)).uniqueKey == .note { return }
            try await Task.sleep(for: .milliseconds(100))
        } while clock.now < deadline
        throw T5PaginationFailure.invariant("native-note-type-not-ready")
    }

    private func show(_ objectID: String, spaceID: String) async throws -> Anytype_Rpc.Object.Show.Response {
        try await ClientCommands.objectShow(.with { $0.contextID = objectID; $0.objectID = objectID; $0.spaceID = spaceID }).invoke()
    }

    private func details(_ objectID: String, spaceID: String) async throws -> ObjectDetails {
        try rootDetails(try await show(objectID, spaceID: spaceID), objectID: objectID, spaceID: spaceID)
    }

    private func rootDetails(_ response: Anytype_Rpc.Object.Show.Response, objectID: String, spaceID: String) throws -> ObjectDetails {
        try require(response.objectView.rootID == objectID, "native-root-differs")
        let value = try ObjectDetails(protobufStruct: try #require(response.objectView.details.first { $0.id == objectID }?.details))
        try require(value.id == objectID && value.spaceId == spaceID, "native-object-identity-differs")
        return value
    }

    private func write<T: Encodable>(_ value: T, to url: URL) throws {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try encoder.encode(value).write(to: url, options: .withoutOverwriting)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
    }

    private func hash(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    private func require(_ condition: Bool, _ label: String) throws {
        guard condition else { throw T5PaginationFailure.invariant(label) }
    }
}
