import Foundation
import SwiftUI
import PinkhaKit
import Services
import AnytypeCore
import Factory

/// Main downstream home sections container for Pinkha spaces.
/// Replaces the generic upstream Home sections when `PinkhaRuntime.enabled` is true.
public struct PinkhaHomeSectionsView: View {
    let spaceId: String
    weak var output: (any CommonWidgetModuleOutput)?

    @State private var bootstrapState: PinkhaSpaceBootstrapState = .uninitialized

    public init(spaceId: String, output: (any CommonWidgetModuleOutput)?) {
        self.spaceId = spaceId
        self.output = output
    }

    public var body: some View {
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
        // 1. Existing Recently Edited section
        RecentlyEditedSectionView(
            spaceId: spaceId,
            output: output
        )

        // 2. Pinkha Folder / Hierarchy section
        PinkhaHierarchySectionView(
            spaceId: spaceId,
            manifest: manifest,
            output: output
        )

        // [Extension Point: Torah Sources section will be inserted here in a future phase]

        // [Extension Point: Books section will be inserted here in a future phase]

        // 3. Pinkha Writing Types section (חידוש, מאמר, מחקר)
        PinkhaWritingTypesSectionView(
            spaceId: spaceId,
            manifest: manifest,
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
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 28))
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
        case .ready:
            self.bootstrapState = current
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
            let manifest = try await stateManager.awaitReadiness(spaceId: spaceId, timeoutSeconds: 15.0)
            self.bootstrapState = .ready(manifest)
        } catch {
            self.bootstrapState = .failed(error.localizedDescription)
        }
    }

    private func retryBootstrap() async {
        let stateManager = Container.shared.pinkhaBootstrapStateManager()
        stateManager.setState(.uninitialized, for: spaceId)
        await monitorBootstrapReadiness()
    }
}
