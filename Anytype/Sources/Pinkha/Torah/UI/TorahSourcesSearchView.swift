import SwiftUI

struct TorahSourcesSearchView: View {
    @Bindable var session: TorahEditorSession

    @State private var disposableSpaceConfirmed = false
    @State private var freshDocumentConfirmed = false
    @State private var confirmation = ""

    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {
                mutationGate

                associationPreview

                Picker("סוג חיפוש", selection: $session.searchScope) {
                    ForEach(TorahEditorSession.SearchScope.allCases) { scope in
                        Text(scope.title).tag(scope)
                    }
                }
                .pickerStyle(.segmented)

                TextField("חיפוש בספריא", text: $session.searchQuery)
                    .textFieldStyle(.roundedBorder)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("torah-sources-search-field")

                results
            }
            .padding(16)
            .navigationTitle("תורה / מקורות")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("סגור") { session.isSearchPresented = false }
                }
            }
        }
        .frame(idealWidth: 460, idealHeight: 640)
        .task(id: SearchTaskID(scope: session.searchScope, query: session.searchQuery)) {
            do {
                try await Task.sleep(for: .milliseconds(300))
                await session.performSearch()
            } catch {
            }
        }
        .task { await session.refreshAssociations() }
    }

    private var associationPreview: some View {
        GroupBox {
            if session.currentAssociations.isEmpty {
                Text(session.associationTargetBlockId == nil
                     ? "אין עדיין קשרים תורניים במסמך"
                     : "אין עדיין קשרים תורניים בבלוק")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                ScrollView(.horizontal) {
                    HStack {
                        ForEach(session.currentAssociations) { item in
                            HStack(spacing: 6) {
                                Button(item.labelHe) {
                                    session.openAssociation(item)
                                }
                                .buttonStyle(.plain)
                                .lineLimit(1)
                                .disabled(!session.canOpenAssociation(item))
                                Button {
                                    Task { await session.unlinkAssociation(item) }
                                } label: {
                                    Image(systemName: "xmark.circle.fill")
                                }
                                .buttonStyle(.plain)
                                .disabled(!session.mutationOptIn)
                                .accessibilityLabel("בטל קשר")
                            }
                            .font(.caption)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(.secondary.opacity(0.12), in: Capsule())
                        }
                    }
                }
            }

            if let persistenceState = session.persistenceState {
                Text(persistenceLabel(persistenceState))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        } label: {
            Label(
                session.associationTargetBlockId == nil ? "קשר תורני במסמך" : "קשר תורני בבלוק",
                systemImage: "link"
            )
        }
    }

    private func persistenceLabel(_ state: TorahAssociationPersistenceState) -> String {
        switch state {
        case .waiting: "ממתין לשמירה"
        case .saving: "שומר…"
        case .saved: "נשמר ואומת בקריאה חוזרת"
        case .conflict: "התנגשות כתיבה"
        case .uncertain: "מצב השמירה אינו ודאי"
        case .error: "שגיאת שמירה"
        }
    }

    private var mutationGate: some View {
        GroupBox {
            if session.mutationOptIn {
                HStack {
                    Label("כתיבה ניסיונית פעילה למסמך זה בלבד", systemImage: "exclamationmark.shield.fill")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(.orange)
                    Spacer()
                    Button("כבה") { session.disableMutations() }
                }
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    Text("ברירת המחדל היא קריאה בלבד. הפעל כתיבה רק ב‑Space חד־פעמי ובמסמך חדש וריק ללא מידע בעל ערך.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                    Toggle("זהו Space חד־פעמי חדש", isOn: $disposableSpaceConfirmed)
                    Toggle("זהו מסמך חדש וריק", isOn: $freshDocumentConfirmed)
                    TextField("הקלד DISPOSABLE", text: $confirmation)
                        .textFieldStyle(.roundedBorder)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                    Button("הפעל כתיבה ניסיונית") {
                        session.enableMutations(
                            disposableSpaceConfirmed: disposableSpaceConfirmed,
                            freshDocumentConfirmed: freshDocumentConfirmed,
                            confirmation: confirmation
                        )
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!disposableSpaceConfirmed || !freshDocumentConfirmed)
                    .accessibilityIdentifier("torah-mutation-opt-in")
                }
            }
        } label: {
            Label("מגבלת בטיחות T2‑L", systemImage: "lock.shield")
        }
    }

    @ViewBuilder
    private var results: some View {
        if session.isSearching {
            ProgressView("מחפש…")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if session.searchResults.isEmpty {
            ContentUnavailableView(
                "חפש מקור, נושא או מילה",
                systemImage: "text.book.closed",
                description: Text("התוצאות מגיעות מספק המקורות המוגדר, ללא נתוני דמה.")
            )
        } else {
            List(session.searchResults) { result in
                VStack(alignment: .leading, spacing: 6) {
                    Text(result.title)
                        .font(.body.weight(.medium))
                    if let subtitle = result.subtitle, !subtitle.isEmpty {
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                    HStack {
                        if result.scope == .references {
                            Button("פתח במפקח") {
                                Task { await session.openReference(result) }
                            }
                            .buttonStyle(.borderedProminent)
                        }
                        Button("קשר למסמך") {
                            Task { await session.link(result) }
                        }
                        .buttonStyle(.bordered)
                        .disabled(!session.mutationOptIn)
                    }
                    .controlSize(.small)
                }
                .padding(.vertical, 4)
            }
            .listStyle(.plain)
        }
    }
}

private struct SearchTaskID: Equatable {
    let scope: TorahEditorSession.SearchScope
    let query: String
}
