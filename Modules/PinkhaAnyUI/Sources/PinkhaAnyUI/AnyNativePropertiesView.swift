#if canImport(UIKit) && canImport(SwiftUI)
import Foundation
import SwiftUI
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaAnyHost
import PinkhaTorahPresentation
import TorahInspectorCore
import TorahInspectorUI

private struct AnyPropertyValueSelection: Identifiable {
    var id: AnyNativePropertyKey { row.id }
    let snapshot: AnyNativePropertySnapshot
    let row: AnyNativePropertyRow
    let text: String
}

public struct AnyNativePropertiesView: View {
    @Bindable private var presentation: AnyDocumentPresentation
    @State private var model: AnyNativePropertyPresentation
    @State private var editing: AnyPropertyValueSelection?
    @State private var showsCustomization = false
    @State private var propertyChildReserved = false
    @Environment(\.dismiss) private var dismiss
    @Environment(\.locale) private var locale

    public init(presentation: AnyDocumentPresentation) {
        self.presentation = presentation
        _model = State(initialValue: AnyNativePropertyPresentation(document: presentation,
                                                                  store: presentation.propertyStore))
    }

    public var body: some View {
        NavigationStack {
            List {
                if model.isLoading && model.snapshot == nil { ProgressView() }
                if let snapshot = model.snapshot {
                    Section(AnyUIErrorText.text("סוג המסמך", "Document type")) {
                        Picker(AnyUIErrorText.text("סוג", "Type"),
                               selection: Binding(get: { snapshot.currentTypeID },
                                                  set: { id in Task { await model.setType(id) } })) {
                            if !snapshot.catalog.selectableDocumentTypes.contains(where: { $0.id == snapshot.currentTypeID }) {
                                Text(snapshot.catalog.types.first(where: { $0.id == snapshot.currentTypeID })?.name ??
                                     AnyUIErrorText.text("הסוג הנוכחי", "Current type"))
                                    .tag(snapshot.currentTypeID)
                            }
                            ForEach(snapshot.catalog.selectableDocumentTypes) { type in
                                Text(type.name).tag(type.id)
                            }
                        }
                        .disabled(!model.canWrite)
                        .accessibilityIdentifier("any-native-property-type")
                        .accessibilityValue(Text(snapshot.catalog.types.first(where: { $0.id == snapshot.currentTypeID })?.name ?? snapshot.currentTypeID))
                    }
                    if let source = snapshot.bookmarkSourceRow, let url = snapshot.bookmarkSourceURL {
                        Section(AnyUIErrorText.text("סימנייה", "Bookmark")) {
                            Link(destination: url) {
                                Label(AnyUIErrorText.text("פתיחת האתר", "Open website"),
                                      systemImage: "arrow.up.right.square")
                            }
                            .disabled(!presentation.isMounted || !canPresentPropertyChild || model.needsReview)
                            .accessibilityIdentifier("any-native-bookmark-open-source")
                            .accessibilityValue(Text(source.value?.string ?? ""))
                        }
                    }
                    if !model.visibleRows.isEmpty {
                        Section(AnyUIErrorText.text("מאפייני המסמך", "Document properties")) {
                            ForEach(model.visibleRows) { row in propertyRow(row, snapshot: snapshot) }
                        }
                    }
                }
                if model.derivedIsVisible(.sources) {
                    propertySection(.references, items: presentation.torah.documentPropertyProjection.sources)
                }
                if model.derivedIsVisible(.topics) {
                    propertySection(.topics, items: presentation.torah.documentPropertyProjection.topics)
                }
                if model.derivedIsVisible(.words) {
                    propertySection(.words, items: presentation.torah.documentPropertyProjection.words)
                }
                if let native = presentation.nativeProperties, !native.readiness.complete {
                    Section { Text(AnyUIErrorText.incompleteIndex).font(.footnote).foregroundStyle(.secondary) }
                }
                if model.needsReview {
                    Section {
                        Text(AnyUIErrorText.text("בדוק את הערכים הנוכחיים לפני שינוי נוסף.", "Review the current values before making another change."))
                        Button(AnyUIErrorText.text("טעינת הערכים הנוכחיים", "Review current values")) {
                            Task { await model.load(reviewCurrent: true) }
                        }.accessibilityIdentifier("any-native-property-review")
                    }
                }
                if model.isSaving { ProgressView(AnyUIErrorText.text("שומר…", "Saving…")) }
            }
            .navigationTitle(AnyUIErrorText.text("מאפיינים", "Properties"))
            .accessibilityIdentifier("any-native-properties-list")
            .refreshable { await model.load(reviewCurrent: true) }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        Button(AnyUIErrorText.text("בחירת המאפיינים המוצגים", "Choose visible properties"),
                               systemImage: "slider.horizontal.3") {
                            guard reservePropertyChild() else { return }
                            showsCustomization = true
                        }
                            .disabled(!canPresentPropertyChild)
                            .accessibilityIdentifier("any-native-property-customize")
                        Button(AnyUIErrorText.text("ביטול שינוי במאפיינים", "Undo property change"),
                               systemImage: "arrow.uturn.backward") { Task { await model.undoLastChange() } }
                            .disabled(!model.canUndo)
                    } label: { Image(systemName: "ellipsis.circle") }
                        .accessibilityIdentifier("any-native-property-menu")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(AnyUIErrorText.text("סיום", "Done")) { dismiss() }
                        .accessibilityIdentifier("any-native-property-close")
                }
            }
            .modifier(AnyTorahInspectorLayer(session: presentation.torah, host: .properties,
                onInspectorDismissed: { [ownerID = presentation.mountedOwnerID] in
                    releasePropertyChildIfAbsent()
                    presentation.ownedPresentationDidDismiss(.propertyInspector, ownerID: ownerID)
                }, onSearchDismissed: { [ownerID = presentation.mountedOwnerID] in
                    releasePropertyChildIfAbsent()
                    presentation.ownedPresentationDidDismiss(.propertySearch, ownerID: ownerID)
                }))
            .sheet(isPresented: Binding(get: { presentation.sourceDocumentsTitle != nil },
                set: { if !$0 { presentation.sourceDocumentsTitle = nil } }),
                onDismiss: { [ownerID = presentation.mountedOwnerID] in
                    releasePropertyChildIfAbsent()
                    presentation.ownedPresentationDidDismiss(.sourceDocuments, ownerID: ownerID)
                }) {
                NavigationStack {
                    List(presentation.sourceDocuments) { item in
                        Button {
                            presentation.requestOpenObject(item.objectID, blockID: item.blockID)
                        } label: {
                            Label(item.title.isEmpty ? AnyUIErrorText.text("ללא כותרת", "Untitled") : item.title,
                                  systemImage: item.kind == .note ? "note.text" : "doc.text")
                        }
                        .accessibilityIdentifier("any-native-related-document-" + item.objectID)
                    }
                    .accessibilityIdentifier("any-native-related-documents-list")
                    .navigationTitle(presentation.sourceDocumentsTitle ?? "")
                    .toolbar { ToolbarItem(placement: .confirmationAction) {
                        Button(AnyUIErrorText.text("סיום", "Done")) { presentation.sourceDocumentsTitle = nil }
                    }}
                }
            }
            .sheet(item: $editing, onDismiss: { releasePropertyChildIfAbsent() }) { selection in
                AnyNativePropertyValueEditor(model: model, selection: selection)
            }
            .sheet(isPresented: $showsCustomization,
                   onDismiss: { releasePropertyChildIfAbsent() }) { customization }
            .alert(AnyUIErrorText.text("מאפיינים", "Properties"),
                   isPresented: Binding(get: { model.message != nil }, set: { if !$0 { model.message = nil } })) {
                Button(AnyUIErrorText.text("אישור", "OK"), role: .cancel) { model.message = nil }
            } message: { Text(model.message ?? "") }
            .task { model.activate(); await model.load() }
            .onAppear { presentation.torah.activatePresentationHost(.properties) }
            .onDisappear {
                // Owned child sheets keep this document policy alive.
                if !presentation.showsProperties {
                    model.deactivate()
                    presentation.torah.dismissPropertiesPresentation()
                }
            }
        }
    }

    private var canPresentPropertyChild: Bool {
        AnyNativeDocumentNavigation.canBeginOwnedPresentation(
            isReserved: propertyChildReserved,
            hasInspector: presentation.torah.selection != nil,
            hasSearch: presentation.torah.isSearchPresented,
            hasNativeChild: presentation.sourceDocumentsTitle != nil || editing != nil || showsCustomization,
            isNavigating: presentation.isNavigating)
    }

    private func reservePropertyChild() -> Bool {
        guard canPresentPropertyChild else { return false }
        propertyChildReserved = true
        return true
    }

    private func releasePropertyChildIfAbsent() {
        guard presentation.torah.selection == nil, !presentation.torah.isSearchPresented,
              presentation.sourceDocumentsTitle == nil, editing == nil, !showsCustomization else { return }
        propertyChildReserved = false
    }

    @ViewBuilder private func propertyRow(_ row: AnyNativePropertyRow,
                                          snapshot: AnyNativePropertySnapshot) -> some View {
        if row.isReadOnly {
            LabeledContent(row.definition.name) {
                Text(display(row)).foregroundStyle(.secondary).lineLimit(3)
            }
        } else {
            Button {
                do {
                    let text = try AnyNativePropertyValueCodec.text(row.value, kind: row.definition.kind)
                    guard reservePropertyChild() else { return }
                    editing = .init(snapshot: snapshot, row: row,
                        text: text)
                } catch { model.message = AnyUIErrorText.describe(error) }
            } label: {
                HStack(alignment: .top) {
                    Text(row.definition.name).foregroundStyle(.primary)
                    Spacer()
                    Text(display(row)).foregroundStyle(.secondary).lineLimit(3).multilineTextAlignment(.trailing)
                    Image(systemName: "chevron.forward").font(.caption).foregroundStyle(.tertiary)
                }
            }
            .disabled(!model.canWrite || !canPresentPropertyChild)
            .accessibilityIdentifier(row.id.ownerID == "any" && row.id.propertyID == "name"
                ? "any-native-property-name" : "any-native-property-" + row.id.visibilityKey)
            .accessibilityValue(Text(display(row)))
        }
    }

    private func display(_ row: AnyNativePropertyRow) -> String {
        guard let value = row.value else { return AnyUIErrorText.text("ללא ערך", "No value") }
        if let boolean = value.bool {
            return boolean ? AnyUIErrorText.text("כן", "Yes") : AnyUIErrorText.text("לא", "No")
        }
        return (try? AnyNativePropertyValueCodec.text(value, kind: row.definition.kind)) ??
            AnyUIErrorText.text("ערך שמור", "Stored value")
    }

    private var customization: some View {
        NavigationStack {
            List {
                Section(AnyUIErrorText.text("מקורות", "Sources")) {
                    derivedToggle(.sources, title: TorahEditorSession.SearchScope.references.title)
                    derivedToggle(.topics, title: TorahEditorSession.SearchScope.topics.title)
                    derivedToggle(.words, title: TorahEditorSession.SearchScope.words.title)
                }
                if let snapshot = model.snapshot {
                    Section(AnyUIErrorText.text("מאפיינים מוצגים", "Visible properties")) {
                        ForEach(snapshot.rows) { row in
                            Toggle(row.definition.name, isOn: Binding(get: { row.isVisible }, set: { visible in
                                Task { await model.setVisibility(.init(property: row.id), visible: visible) }
                            })).disabled(!model.canWrite)
                                .accessibilityIdentifier(row.id.ownerID == "any" && row.id.propertyID == "name"
                                    ? "any-native-property-visibility-name" : "any-native-property-visibility-" + row.id.visibilityKey)
                        }
                    }
                }
                if !model.attachableCollections.isEmpty {
                    Section(AnyUIErrorText.text("הוספת קבוצת מאפיינים", "Add property collection")) {
                        ForEach(model.attachableCollections) { collection in
                            Button(collection.name, systemImage: "plus.circle") {
                                Task { await model.setCollection(collection.id, attached: true) }
                            }.disabled(!model.canWrite)
                        }
                    }
                }
                if !model.removableCollections.isEmpty {
                    Section(AnyUIErrorText.text("קבוצות מאפיינים מחוברות", "Attached property collections")) {
                        ForEach(model.removableCollections) { collection in
                            HStack {
                                Text(collection.name)
                                Spacer()
                                Button(role: .destructive) {
                                    Task { await model.setCollection(collection.id, attached: false) }
                                } label: { Image(systemName: "minus.circle") }
                                    .accessibilityLabel(AnyUIErrorText.text("ניתוק", "Detach") + " " + collection.name)
                                    .disabled(!model.canWrite)
                            }
                        }
                    }
                }
                if model.isSaving { ProgressView() }
                if let message = model.message { Text(message).font(.footnote).foregroundStyle(.secondary) }
            }
            .accessibilityIdentifier("any-native-property-customization-list")
            .navigationTitle(AnyUIErrorText.text("בחירת מאפיינים", "Choose properties"))
            .toolbar { ToolbarItem(placement: .confirmationAction) {
                Button(AnyUIErrorText.text("סיום", "Done")) { showsCustomization = false }
                    .accessibilityIdentifier("any-native-property-customization-close")
            }}
        }
    }

    private func derivedToggle(_ field: AnyNativePropertyVisibilityKey.DerivedField, title: String) -> some View {
        Toggle(title, isOn: Binding(get: { model.derivedIsVisible(field) }, set: { visible in
            Task { await model.setVisibility(.init(derived: field), visible: visible) }
        })).disabled(!model.canWrite)
    }

    @ViewBuilder private func propertySection(_ scope: TorahEditorSession.SearchScope,
                                              items: [TorahAssociationItem]) -> some View {
        Section(scope.title) {
            ForEach(items) { item in
                HStack {
                    Text(TorahAssociationDisplayFormatter.label(for: item, locale: locale))
                    Spacer()
                    Menu {
                        if presentation.torah.canOpenAssociation(item) {
                            Button(AnyUIErrorText.text("פתיחת מקור", "Open source")) {
                                guard reservePropertyChild() else { return }
                                presentation.torah.openDocumentAssociation(item)
                                releasePropertyChildIfAbsent()
                            }.disabled(!canPresentPropertyChild)
                        }
                        Button(AnyUIErrorText.text("מסמכים מקושרים", "Related documents")) {
                            guard reservePropertyChild() else { return }
                            Task {
                                await presentation.showDocuments(with: item)
                                releasePropertyChildIfAbsent()
                            }
                        }.disabled(!canPresentPropertyChild)
                        Button(AnyUIErrorText.text("הסרת קישור", "Unlink"), role: .destructive) {
                            Task {
                                do {
                                    _ = try await presentation.torah.unlinkAssociation(
                                        item, from: presentation.torah.documentAssociationContext)
                                } catch {
                                    // Keep the shared session's localized failure
                                    // and supply visible feedback if it has none.
                                    if presentation.torah.message == nil {
                                        presentation.torah.message = AnyUIErrorText.describe(error)
                                    }
                                }
                            }
                        }.disabled(!presentation.canMutate)
                    } label: { Image(systemName: "ellipsis.circle") }
                        .accessibilityIdentifier("any-native-derived-actions-\(item.id)")
                        .accessibilityLabel(Text(verbatim: AnyUIErrorText.text("פעולות עבור ", "Actions for ")
                            + TorahAssociationDisplayFormatter.label(for: item, locale: locale)))
                }
            }
            Button {
                guard reservePropertyChild() else { return }
                presentation.torah.presentSearch(scope: .document, initialCategory: scope, host: .properties)
                releasePropertyChildIfAbsent()
            } label: { Label(AnyUIErrorText.text("הוספה", "Add"), systemImage: "plus") }
                .disabled(!presentation.canMutate || !canPresentPropertyChild)
        }
    }
}

private struct AnyNativePropertyValueEditor: View {
    @Bindable var model: AnyNativePropertyPresentation
    let selection: AnyPropertyValueSelection
    @State private var text: String
    @Environment(\.dismiss) private var dismiss
    @FocusState private var focused: Bool

    init(model: AnyNativePropertyPresentation, selection: AnyPropertyValueSelection) {
        self.model = model; self.selection = selection
        _text = State(initialValue: selection.text)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section(selection.row.definition.name) {
                    switch selection.row.definition.kind {
                    case .boolean:
                        Toggle(selection.row.definition.name,
                               isOn: Binding(get: { text == "true" }, set: { text = $0 ? "true" : "false" }))
                    case .array, .object:
                        TextEditor(text: $text).font(.system(.body, design: .monospaced))
                            .frame(minHeight: 220).focused($focused)
                            .accessibilityIdentifier("any-native-property-value-input")
                        Text(AnyUIErrorText.text("נתונים מובנים בפורמט JSON", "Structured data in JSON format"))
                            .font(.caption).foregroundStyle(.secondary)
                    default:
                        TextField(selection.row.definition.name, text: $text, axis: .vertical)
                            .focused($focused)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled(selection.row.definition.kind != .string)
                            .accessibilityIdentifier("any-native-property-value-input")
                    }
                }
                if selection.row.definition.kind == .datetime {
                    Section {
                        Text(AnyUIErrorText.text("תאריך ושעה בפורמט ISO 8601, כולל אזור זמן.",
                                                "Use an ISO 8601 date and time, including its time zone."))
                            .font(.footnote).foregroundStyle(.secondary)
                        Button(AnyUIErrorText.text("התאריך והשעה הנוכחיים", "Use current date and time")) {
                            text = ISO8601DateFormatter().string(from: Date())
                        }
                    }
                }
                if let message = model.message {
                    Text(message).font(.footnote).foregroundStyle(.secondary)
                }
                if model.needsReview {
                    Button(AnyUIErrorText.text("בדיקת הערכים הנוכחיים", "Review current values")) {
                        Task { await model.load(reviewCurrent: true); dismiss() }
                    }
                }
                if selection.row.value != nil {
                    Button(AnyUIErrorText.text("ניקוי הערך", "Clear value"), role: .destructive) {
                        Task {
                            if await model.clearValue(snapshot: selection.snapshot, row: selection.row) { dismiss() }
                        }
                    }.disabled(!model.canWrite)
                }
            }
            .navigationTitle(selection.row.definition.name)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(AnyUIErrorText.text("ביטול", "Cancel")) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(AnyUIErrorText.text("שמירה", "Save")) {
                        Task {
                            if await model.setValue(snapshot: selection.snapshot, row: selection.row, text: text) { dismiss() }
                        }
                    }.disabled(!model.canWrite || text.utf8.count > 131_072)
                        .accessibilityIdentifier("any-native-property-save")
                }
            }
            .task { focused = true }
        }
    }
}
#endif
