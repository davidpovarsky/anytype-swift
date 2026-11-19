import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost

/// One exact namespace policy assembled from verified native workspace roles.
public enum AnyNativePropertyPolicies {
    public static func workspace(schema: AnyHierarchySchema,
                                 noteMarker: AnyNativeNoteMarker) throws -> AnyNativePropertyPolicy {
        let parent = try AnyNativePropertyKey(ownerID: schema.collectionID, propertyID: schema.parentPropertyID)
        let position = try AnyNativePropertyKey(ownerID: schema.collectionID, propertyID: schema.positionPropertyID)
        let folder = try AnyNativePropertyKey(ownerID: schema.collectionID, propertyID: schema.folderPropertyID)
        let type = try AnyNativePropertyKey(ownerID: "any", propertyID: "type")
        let collections = try AnyNativePropertyKey(ownerID: "any", propertyID: "collections")
        let template = try AnyNativePropertyKey(ownerID: "any", propertyID: "template")
        return try .init(hiddenPropertyKeys: [position, type, collections, template],
            managedPropertyKeys: [parent, position, folder],
            hiddenCollectionIDs: [noteMarker.collectionID,
                                  AnyNativePropertyStore.presentationCollectionID])
    }
}

/// Structured values are edited explicitly. The exact source JSON is checked
/// against the actual typed encoder before a property mutation can be prepared.
public enum AnyNativePropertyValueCodec {
    public static func text(_ value: AnyJSON?, kind: AnyNativePropertyDefinition.Kind?) throws -> String {
        guard let value else { return "" }
        if kind == .string, let value = value.string { return value }
        if kind == .datetime, let value = value["$date"]?.string { return value }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes, .prettyPrinted]
        guard let text = String(data: try encoder.encode(value), encoding: .utf8) else {
            throw AnyNativePropertyError.invalidProperty
        }
        return text
    }

    public static func parse(_ text: String, kind: AnyNativePropertyDefinition.Kind?) throws -> AnyJSON {
        guard text.utf8.count <= 131_072 else { throw AnyNativePropertyError.invalidProperty }
        if kind == .string { return .string(text) }
        if kind == .datetime, !text.trimmingCharacters(in: .whitespacesAndNewlines).hasPrefix("{") {
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let date = formatter.date(from: text) ?? ISO8601DateFormatter().date(from: text)
            guard date != nil else { throw AnyNativePropertyError.invalidProperty }
            return .object(["$date": .string(text)])
        }
        let source = Data(text.utf8)
        let value = try JSONDecoder().decode(AnyJSON.self, from: source)
        switch kind {
        case .number:
            guard value.integer != nil || { if case .number(let n) = value { return n.isFinite }; return false }() else {
                throw AnyNativePropertyError.invalidProperty
            }
        case .boolean:
            guard value.bool != nil else { throw AnyNativePropertyError.invalidProperty }
        case .array:
            guard value.array != nil else { throw AnyNativePropertyError.invalidProperty }
        case .object:
            guard value.object != nil else { throw AnyNativePropertyError.invalidProperty }
        case .datetime:
            guard let fields = value.object, Set(fields.keys) == ["$date"],
                  fields["$date"]?.string != nil || fields["$date"]?.integer != nil else {
                throw AnyNativePropertyError.invalidProperty
            }
        default: throw AnyNativePropertyError.readOnly
        }
        let encoded = try JSONEncoder().encode(value)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: source, encoded: encoded)
        return value
    }
}

#if canImport(SwiftUI)
import Observation
import SwiftUI

@MainActor @Observable
public final class AnyNativePropertyPresentation {
    public private(set) var snapshot: AnyNativePropertySnapshot?
    public private(set) var isLoading = false
    public private(set) var isSaving = false
    public private(set) var needsReview = false
    public var message: String?
    @ObservationIgnored private weak var document: AnyDocumentPresentation?
    @ObservationIgnored private let store: AnyNativePropertyStore?
    @ObservationIgnored private var epoch = UUID()
    @ObservationIgnored private var isActive = false
    @ObservationIgnored private var readRequest: UInt64 = 0
    @ObservationIgnored private var pendingEdit: AnyPreparedPropertyEdit?
    @ObservationIgnored private var undo: AnyPreparedPropertyEdit?

    public init(document: AnyDocumentPresentation, store: AnyNativePropertyStore?) {
        self.document = document; self.store = store
    }

    public var canWrite: Bool {
        isActive && document?.canMutate == true && snapshot?.canWrite == true && !isSaving && !needsReview
    }
    public var canUndo: Bool { canWrite && undo != nil }
    public var visibleRows: [AnyNativePropertyRow] { snapshot?.rows.filter(\.isVisible) ?? [] }
    public var hiddenRows: [AnyNativePropertyRow] { snapshot?.rows.filter { !$0.isVisible } ?? [] }
    public var attachableCollections: [AnyNativePropertyOwner] {
        guard let snapshot, let store else { return [] }
        return snapshot.catalog.collections.filter {
            !$0.hidden && !snapshot.collectionIDs.contains($0.id) &&
            !store.policy.isManagedCollection($0.id)
        }
    }
    public var removableCollections: [AnyNativePropertyOwner] {
        guard let snapshot, let store else { return [] }
        return snapshot.catalog.collections.filter {
            snapshot.collectionIDs.contains($0.id) && !store.policy.isManagedCollection($0.id)
        }
    }

    public func derivedIsVisible(_ field: AnyNativePropertyVisibilityKey.DerivedField) -> Bool {
        snapshot?.hiddenPropertyKeys.contains(AnyNativePropertyVisibilityKey(derived: field).rawValue) != true
    }

    public func activate() {
        guard !isActive else { return }
        isActive = true; epoch = UUID()
    }
    public func deactivate() { isActive = false; epoch = UUID(); readRequest &+= 1 }

    public func load(reviewCurrent: Bool = false) async {
        guard isActive, let document, let store else {
            message = AnyUIErrorText.text("יש לפתוח את המאפיינים מתוך מרחב שהוגדר.", "Open properties from a configured workspace.")
            return
        }
        let expected = epoch, mounted = document.mountedOwnerID
        readRequest &+= 1; let request = readRequest
        isLoading = true
        defer { if request == readRequest { isLoading = false } }
        do {
            let objectID = document.objectID
            let result = try await document.nativeSession.perform { lease in
                try await store.read(objectID: objectID, lease: lease)
            }
            try requireActive(expected, mounted: mounted)
            guard request == readRequest else { return }
            snapshot = result
            if reviewCurrent { needsReview = false; pendingEdit = nil; undo = nil }
        } catch {
            guard expected == epoch, request == readRequest, isActive else { return }
            message = AnyUIErrorText.describe(error)
        }
    }

    public func setValue(snapshot captured: AnyNativePropertySnapshot,
                         row: AnyNativePropertyRow, text: String) async -> Bool {
        guard canWrite, let store else { return false }
        do {
            let value = try AnyNativePropertyValueCodec.parse(text, kind: row.definition.kind)
            return await commit(try store.prepareSetValue(captured, key: row.id, value: value))
        } catch { message = AnyUIErrorText.describe(error); return false }
    }

    public func clearValue(snapshot captured: AnyNativePropertySnapshot,
                           row: AnyNativePropertyRow) async -> Bool {
        guard canWrite, let store else { return false }
        do { return await commit(try store.prepareSetValue(captured, key: row.id, value: .null)) }
        catch { message = AnyUIErrorText.describe(error); return false }
    }

    public func setType(_ id: String) async {
        guard canWrite, let store, let snapshot, id != snapshot.currentTypeID else { return }
        do { _ = await commit(try store.prepareSetType(snapshot, typeID: id)) }
        catch { message = AnyUIErrorText.describe(error) }
    }

    public func setCollection(_ id: String, attached: Bool) async {
        guard canWrite, let store, let snapshot else { return }
        do {
            let edit = try (attached ? store.prepareAttachCollection(snapshot, collectionID: id)
                                     : store.prepareDetachCollection(snapshot, collectionID: id))
            _ = await commit(edit)
        } catch { message = AnyUIErrorText.describe(error) }
    }

    public func setVisibility(_ key: AnyNativePropertyVisibilityKey, visible: Bool) async {
        guard canWrite, let store, let snapshot, let document else { return }
        let expected = epoch, mounted = document.mountedOwnerID
        let authorize = authorization(expected, mounted: mounted)
        isSaving = true
        defer { isSaving = false }
        do {
            let receipt = try await document.nativeSession.perform { lease in
                try await store.setVisibility(snapshot, key: key, visible: visible,
                                               lease: lease, authorize: authorize)
            }
            try requireActive(expected, mounted: mounted)
            accept(receipt)
        } catch {
            guard isActive, expected == epoch else { return }
            needsReview = true
            message = AnyUIErrorText.describe(error)
        }
    }

    public func undoLastChange() async {
        guard canUndo, let undo else { return }
        _ = await commit(undo)
    }

    private func commit(_ edit: AnyPreparedPropertyEdit) async -> Bool {
        guard canWrite, let document, let store else { return false }
        let expected = epoch, mounted = document.mountedOwnerID
        let authorize = authorization(expected, mounted: mounted)
        pendingEdit = edit; isSaving = true
        defer { isSaving = false }
        do {
            let receipt = try await document.nativeSession.perform { lease in
                try await store.apply(edit, lease: lease, authorize: authorize)
            }
            try requireActive(expected, mounted: mounted)
            accept(receipt)
            if receipt.readback == .verifiedCurrent {
                await document.load()
                try requireActive(expected, mounted: mounted)
                return true
            }
            return false
        } catch {
            guard isActive, expected == epoch else { return false }
            needsReview = true
            message = AnyUIErrorText.describe(error)
            return false
        }
    }

    private func accept(_ receipt: AnyPropertyEditReceipt) {
        guard receipt.readback == .verifiedCurrent, let value = receipt.snapshot else {
            needsReview = true
            message = AnyUIErrorText.uncertainWrite
            return
        }
        snapshot = value; undo = receipt.undo; pendingEdit = nil; needsReview = false
    }

    private func requireActive(_ expected: UUID, mounted: UUID) throws {
        guard isActive, epoch == expected, let document else { throw AnyHostError.sessionClosed }
        try document.requireMounted(mounted)
    }

    private func authorization(_ expected: UUID, mounted: UUID) -> @Sendable () async throws -> Void {
        { [weak self] in
            guard let self else { throw AnyHostError.sessionClosed }
            try await self.requireActive(expected, mounted: mounted)
        }
    }
}
#endif
