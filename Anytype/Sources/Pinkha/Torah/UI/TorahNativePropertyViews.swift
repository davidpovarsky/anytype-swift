import Foundation
import AnytypeCore
import Factory
import SwiftProtobuf
import SwiftUI
import Services
import PinkhaKit

/// Adapters for registered native Properties. Option is only the original chip
/// renderer's value model; no Tag option Object is created or looked up.
enum TorahNativePropertyPresentation {
    static func subscriptionKeys(_ keys: [String]) -> [String] {
        guard keys.contains(where: { definition($0) != nil }) else { return keys }
        var result = keys
        for key in [TorahNativePropertyDefinition.labelsKey, TorahNativePropertyDefinition.readinessKey,
                    TorahNativePropertyDefinition.engineVersionKey, TorahNativePropertyDefinition.statusKey]
        where !result.contains(key) { result.append(key) }
        return result
    }

    static func supportsOrdering(_ key: String) -> Bool { definition(key) == nil }

    static func loadLabels(space: String, key: String, ids: [String]) async {
        guard definition(key) != nil else { return }
        for id in ids where !TorahNativeLabelCache.shared.contains(id: id, space: space) {
            guard !Task.isCancelled else { return }
            do {
                let records = try await Container.shared.searchMiddleService().search(
                    spaceId: space, filters: [.with {
                        $0.relationKey = key; $0.format = .tag; $0.condition = .in
                        $0.value = [id].protobufValue
                    }],
                    keys: ["id", "spaceId", TorahNativePropertyDefinition.labelsKey], limit: 1
                )
                guard !Task.isCancelled else { return }
                for record in records where record.spaceId == space {
                    TorahNativeLabelCache.shared.ingest(details: record)
                }
            } catch { /* Keep the intentional human label while offline. */ }
        }
    }

    static func definition(_ key: String) -> TorahNativePropertyDefinition? {
        TorahNativePropertyDefinition.definition(for: key)
    }

    static func property(
        definition: PropertyDetails, details: ObjectDetails,
        isFeatured: Bool, valuesLocked: Bool
    ) -> Property? {
        guard self.definition(definition.key) != nil else { return nil }
        if ["MALFORMED", "UNSUPPORTED"].contains(details.stringValue(for: TorahNativePropertyDefinition.statusKey)) {
            return .text(Property.Text(
                id: definition.id, key: definition.key, name: definition.name,
                isFeatured: isFeatured, isEditable: false,
                canBeRemovedFromObject: definition.canBeRemovedFromObject,
                isDeleted: definition.isDeleted, value: Loc.unsupportedValue
            ))
        }
        TorahNativeLabelCache.shared.ingest(details: details)
        return value(
            definition: definition,
            ids: details.stringArrayValue(for: definition.key),
            isFeatured: isFeatured,
            editable: !valuesLocked && !details.isReadonly && details.boolValue(for: TorahNativePropertyDefinition.readinessKey)
        )
    }

    static func value(
        definition: PropertyDetails, ids: [String], isFeatured: Bool = false,
        editable: Bool = false
    ) -> Property {
        .tag(Property.Tag(
            id: definition.id, key: definition.key, name: definition.name,
            isFeatured: isFeatured, isEditable: editable,
            canBeRemovedFromObject: definition.canBeRemovedFromObject,
            isDeleted: definition.isDeleted,
            selectedTags: ids.map { id in
                Property.Tag.Option(
                    id: id,
                    text: TorahNativeLabelCache.shared.label(
                        id: id, space: definition.spaceId, key: definition.key
                    ),
                    textColor: Color.Text.primary, backgroundColor: Color.Shape.tertiary
                )
            }
        ))
    }
}

/// Bounded, Space-scoped display cache. Canonical IDs stay private. Reopening a
/// document refreshes it from local engine labels; it never owns associations.
final class TorahNativeLabelCache: @unchecked Sendable {
    static let shared = TorahNativeLabelCache()
    private struct Label: Codable { let he: String; let en: String? }
    private let lock = NSLock()
    private var labels: [String: [String: Label]] = [:]

    func contains(id: String, space: String) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return labels[space]?[id] != nil
    }

    func ingest(details: ObjectDetails) {
        let json = details.stringValue(for: TorahNativePropertyDefinition.labelsKey)
        guard let data = json.data(using: .utf8),
              let values = try? JSONDecoder().decode([String: Label].self, from: data) else { return }
        lock.lock()
        defer { lock.unlock() }
        if labels.count > 64 || (labels[details.spaceId]?.count ?? 0) + values.count > 8192 {
            labels.removeAll(keepingCapacity: true)
        }
        labels[details.spaceId, default: [:]].merge(values) { _, new in new }
    }

    func remember(_ item: TorahAssociationItem, space: String) {
        lock.lock()
        defer { lock.unlock() }
        if labels.count > 64 || (labels[space]?.count ?? 0) > 8192 { labels.removeAll() }
        labels[space, default: [:]][TorahDerivedQueryProjection.identity(item)] = Label(
            he: item.labelHe, en: item.labelEn
        )
    }

    func label(id: String, space: String, key: String) -> String {
        lock.lock()
        let label = labels[space]?[id]
        lock.unlock()
        let fallback = TorahNativePropertyDefinition.definition(for: key)?.name ?? Loc.Pinkha.Torah.title
        guard let label else { return fallback }
        return TorahAssociationDisplayFormatter.localized(
            hebrew: label.he, english: label.en, fallback: fallback, locale: .autoupdatingCurrent
        )
    }
}

/// A document-bound editor uses the same repository and picker as the Inspector.
/// Its target is always document.context, including taps on a Set table cell.
struct TorahNativePropertyEditorView: View {
    @State private var session: TorahEditorSession?
    private let definition: TorahNativePropertyDefinition

    init(spaceId: String, objectId: String, key: String, canEdit: Bool) {
        self.definition = TorahNativePropertyDefinition.definition(for: key)!
        let session = try? TorahEditorSession(spaceId: spaceId, objectId: objectId)
        session?.installAssociationEditingPolicy { canEdit }
        _session = State(initialValue: session)
    }

    var body: some View {
        Group {
            if let session {
                TorahNativeDocumentPicker(session: session, definition: definition)
                    .torahEditorHost(session: session)
            } else {
                Text(Loc.Pinkha.Torah.Error.insertionUnavailable)
                    .foregroundStyle(Color.Text.secondary)
            }
        }
    }
}

private struct TorahNativeDocumentPicker: View {
    @State private var presenter: TorahSourcesSearchPresenter

    init(session: TorahEditorSession, definition: TorahNativePropertyDefinition) {
        _presenter = State(initialValue: TorahSourcesSearchPresenter(
            session: session, context: session.documentAssociationContext,
            searchScope: definition.kind.searchScope, fixedScope: true,
            onOpenSelection: session.openResolvedReferenceFromStandaloneSearch
        ))
    }

    var body: some View {
        TorahSourcesSearchContentView(
            presenter: presenter, showsSearchBar: true,
            accessibilityIdentifier: "torah-native-property-picker"
        )
    }
}

/// Selection-only mode resolves provider identities but cannot call link/unlink.
/// Applying the values changes only the native Set predicate via its callback.
struct TorahNativeFilterPickerView: View {
    private let definition: TorahNativePropertyDefinition
    private let spaceId: String
    private let onApply: ([String]) -> Void
    @State private var selected: [String]
    @State private var presenter: TorahSourcesSearchPresenter?
    @State private var labelRevision = 0

    init(spaceId: String, key: String, selected: [String], onApply: @escaping ([String]) -> Void) {
        self.spaceId = spaceId
        self.definition = TorahNativePropertyDefinition.definition(for: key)!
        self.onApply = onApply
        _selected = State(initialValue: selected)
    }

    var body: some View {
        VStack(spacing: 0) {
            ScrollView(.horizontal) {
                HStack {
                    ForEach(selected, id: \.self) { id in
                        Button {
                            selected.removeAll { $0 == id }
                        } label: {
                            HStack {
                                Text(label(id))
                                Image(systemName: "xmark")
                            }
                            .padding(8)
                            .background(Color.Shape.tertiary, in: Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 16)
            }
            if let presenter {
                TorahSourcesSearchContentView(
                    presenter: presenter, showsSearchBar: true,
                    accessibilityIdentifier: "torah-native-set-filter-picker"
                )
            }
            StandardButton(Loc.apply, style: .primaryLarge) { onApply(selected) }
                .padding(.horizontal, 20)
                .padding(.vertical, 10)
        }
        .task {
            guard presenter == nil,
                  let session = try? TorahEditorSession(spaceId: spaceId, objectId: "torah-filter-selection") else { return }
            session.installAssociationEditingPolicy { false }
            presenter = TorahSourcesSearchPresenter(
                session: session, context: session.documentAssociationContext,
                searchScope: definition.kind.searchScope, associations: [], fixedScope: true,
                onSelectValue: { item in
                    TorahNativeLabelCache.shared.remember(item, space: spaceId)
                    let id = TorahDerivedQueryProjection.identity(item)
                    if !selected.contains(id) { selected.append(id) }
                },
                onOpenSelection: { _ in }
            )
            await TorahNativePropertyPresentation.loadLabels(space: spaceId, key: definition.key, ids: selected)
            labelRevision &+= 1
        }
    }

    private func label(_ id: String) -> String {
        _ = labelRevision
        return TorahNativeLabelCache.shared.label(id: id, space: spaceId, key: definition.key)
    }
}

private extension TorahAssociationKind {
    var searchScope: TorahEditorSession.SearchScope {
        switch self { case .ref: .references; case .topic: .topics; case .word: .words }
    }
}
