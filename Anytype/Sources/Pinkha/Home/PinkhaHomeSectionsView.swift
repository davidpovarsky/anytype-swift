import Foundation
import SwiftUI
import PinkhaKit
import Services
import AnytypeCore
import Factory

/// Main downstream home sections container for Pinkha spaces.
/// Replaces the generic upstream Home sections when `PinkhaRuntime.enabled` is true.
struct PinkhaHomeSectionsView: View {
    private static let initialBootstrapTimeout: TimeInterval = 300

    let spaceId: String
    weak var output: (any CommonWidgetModuleOutput)?

    @State private var bootstrapState: PinkhaSpaceBootstrapState = .uninitialized
    @State private var repository: PinkhaHierarchyRepository? = nil
    @State private var didOpenAcceptanceDocument = false

    init(spaceId: String, output: (any CommonWidgetModuleOutput)?) {
        self.spaceId = spaceId
        self.output = output
    }

    var body: some View {
        VStack(spacing: 0) {
            switch bootstrapState {
            case .ready(let manifest):
                readySections(manifest: manifest)

            case .provisioning, .uninitialized:
                loadingView

            case .failed(let message):
                failedView(message: message)
            }
        }
        .task(id: spaceId) {
            await monitorBootstrapReadiness()
        }
    }

    // MARK: - Sections Layout

    @ViewBuilder
    private func readySections(manifest: PinkhaSpaceManifest) -> some View {
        let repo = repository ?? PinkhaHierarchyRepository(spaceId: spaceId, manifest: manifest)

        // 1. Existing Recently Edited section
        RecentlyEditedSectionView(
            spaceId: spaceId,
            output: output
        )

        // 2. Pinkha Hierarchical Navigation Tree (folders & documents)
        PinkhaHierarchySectionView(
            spaceId: spaceId,
            manifest: manifest,
            repository: repo,
            output: output
        )

        // 3. Primary Writing Types (חידוש, מאמר, מחקר)
        PinkhaWritingTypesSectionView(
            spaceId: spaceId,
            manifest: manifest,
            repository: repo,
            output: output
        )

        // 4. Bin access preserved
        BinLinkWidgetView(
            spaceId: spaceId,
            output: output
        )
        .padding(.top, 24)
    }

    // MARK: - Loading & Error States

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .tint(Color.Text.secondary)
            AnytypeText(Loc.Pinkha.Home.loading, style: .bodyRegular)
                .foregroundStyle(Color.Text.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 48)
    }

    private func failedView(message: String) -> some View {
        VStack(spacing: 12) {
            Image(asset: .X18.redAttention)
                .renderingMode(.template)
                .resizable()
                .frame(width: 28, height: 28)
                .foregroundStyle(Color.Text.primary)

            AnytypeText(Loc.Pinkha.Home.failed, style: .bodySemibold)
                .foregroundStyle(Color.Text.primary)

            Button {
                Task {
                    await retryBootstrap()
                }
            } label: {
                AnytypeText(Loc.Pinkha.Home.retry, style: .bodySemibold)
                    .foregroundStyle(Color.Text.primary)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Color.Background.widget)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            }
            .buttonStyle(.plain)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 36)
    }

    // MARK: - State Management

    private func monitorBootstrapReadiness() async {
        let stateManager = Container.shared.pinkhaBootstrapStateManager()
        let current = stateManager.state(for: spaceId)

        switch current {
        case .ready(let manifest):
            self.repository = PinkhaHierarchyRepository(spaceId: spaceId, manifest: manifest)
            self.bootstrapState = current
            await openAcceptanceDocumentIfRequested(manifest: manifest)
            return
        case .failed:
            self.bootstrapState = current
            return
        case .uninitialized:
            PinkhaBootstrapHook.handleSpaceActivated(spaceId: spaceId)
        case .provisioning:
            break
        }

        self.bootstrapState = .provisioning
        do {
            // A first local-only Space provisions the full Pinkha schema through the real
            // middleware. On slower simulators and devices that sequence can legitimately
            // exceed the old 15-second UI timeout. Keep observing the single in-flight
            // bootstrap instead of freezing the home screen in a stale failure state while
            // the background task continues and eventually becomes ready.
            let manifest = try await stateManager.awaitReadiness(
                spaceId: spaceId,
                timeoutSeconds: Self.initialBootstrapTimeout
            )
            self.repository = PinkhaHierarchyRepository(spaceId: spaceId, manifest: manifest)
            self.bootstrapState = .ready(manifest)
            await openAcceptanceDocumentIfRequested(manifest: manifest)
        } catch {
            self.bootstrapState = .failed(error.localizedDescription)
        }
    }

    private func retryBootstrap() async {
        let stateManager = Container.shared.pinkhaBootstrapStateManager()
        stateManager.setState(.uninitialized, for: spaceId)
        await monitorBootstrapReadiness()
    }

    private func openAcceptanceDocumentIfRequested(manifest: PinkhaSpaceManifest) async {
        guard PinkhaStage1AcceptanceState.isEnabled,
              !didOpenAcceptanceDocument else {
            return
        }
        didOpenAcceptanceDocument = true

        do {
            let state: PinkhaStage1AcceptanceState
            if let storedState = try? PinkhaStage1AcceptanceState.load(),
               storedState.spaceId == spaceId {
                state = storedState
            } else {
                state = try await createAcceptanceState(manifest: manifest)
                try state.save()
            }

            PinkhaDocumentIdentityStorage.shared.registerCreated(
                objectId: state.pinkhaObjectId,
                spaceId: state.spaceId
            )
            let selectedObjectId = state.objectId(
                for: PinkhaStage1AcceptanceState.requestedDocumentKind
            )
            output?.onObjectSelected(
                screenData: .editor(.page(EditorPageObject(
                    objectId: selectedObjectId,
                    spaceId: state.spaceId
                )))
            )
        } catch {
            didOpenAcceptanceDocument = false
            bootstrapState = .failed(error.localizedDescription)
        }
    }

    private func createAcceptanceState(
        manifest: PinkhaSpaceManifest
    ) async throws -> PinkhaStage1AcceptanceState {
        guard let typeId = manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey] else {
            throw PinkhaBootstrapError.manifestStoreError("Missing acceptance writing type")
        }

        let pinkhaDocument = try await PinkhaHierarchyMutationService().createWritingDocument(
            typeId: typeId,
            parentId: nil,
            spaceId: spaceId,
            manifest: manifest,
            existingSiblings: repository?.snapshot.rootNodes ?? []
        )
        try await Container.shared.propertiesService().updateProperty(
            objectId: pinkhaDocument.id,
            propertyKey: BundledPropertyKey.name.rawValue,
            value: PinkhaStage1AcceptanceState.pinkhaDocumentTitle.protobufValue
        )
        repository?.registerPendingCreated(details: pinkhaDocument.updated(by: [
            BundledPropertyKey.name.rawValue:
                PinkhaStage1AcceptanceState.pinkhaDocumentTitle.protobufValue
        ]))

        let objectActions = Container.shared.objectActionsService()
        let note = try await objectActions.createObject(
            name: PinkhaStage1AcceptanceState.noteDocumentTitle,
            typeUniqueKey: .note,
            shouldDeleteEmptyObject: false,
            shouldSelectType: false,
            shouldSelectTemplate: false,
            spaceId: spaceId,
            origin: .none,
            templateId: nil
        )
        let page = try await objectActions.createObject(
            name: PinkhaStage1AcceptanceState.pageDocumentTitle,
            typeUniqueKey: .page,
            shouldDeleteEmptyObject: false,
            shouldSelectType: false,
            shouldSelectTemplate: false,
            spaceId: spaceId,
            origin: .none,
            templateId: nil
        )

        return PinkhaStage1AcceptanceState(
            spaceId: spaceId,
            pinkhaObjectId: pinkhaDocument.id,
            noteObjectId: note.id,
            pageObjectId: page.id
        )
    }
}
