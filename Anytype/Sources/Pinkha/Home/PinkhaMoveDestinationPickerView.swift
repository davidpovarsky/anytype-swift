import Foundation
import SwiftUI
import PinkhaKit
import Services
import AnytypeCore

/// Sheet allowing the user to select a destination folder or Move to Root,
/// filtering out the moving item and all its descendants to strictly prevent cycles.
struct PinkhaMoveDestinationPickerView: View {
    let movingNode: PinkhaHierarchyNode
    let snapshot: PinkhaHierarchySnapshot
    let onSelectDestination: (String?) -> Void
    let onDismiss: () -> Void

    private var availableFolders: [PinkhaHierarchyNode] {
        let descendantIds = snapshot.descendantIds(of: movingNode.objectId)
        return snapshot.allNodes.values
            .filter { node in
                node.kind == .folder &&
                node.objectId != movingNode.objectId &&
                !descendantIds.contains(node.objectId) &&
                node.objectId != movingNode.parentId
            }
            .sorted { $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Button {
                        onSelectDestination(nil)
                    } label: {
                        HStack(spacing: 12) {
                            Image(asset: .CustomIcons.home)
                                .frame(width: 20, height: 20)
                                .foregroundStyle(Color.Text.primary)
                            AnytypeText(Loc.Pinkha.Hierarchy.moveToRoot, style: .bodySemibold)
                                .foregroundStyle(Color.Text.primary)
                            Spacer()
                        }
                    }
                    .disabled(movingNode.parentId == nil)
                }

                if !availableFolders.isEmpty {
                    Section(Loc.Pinkha.Home.folders) {
                        ForEach(availableFolders) { folder in
                            Button {
                                onSelectDestination(folder.objectId)
                            } label: {
                                HStack(spacing: 12) {
                                    Image(asset: .CustomIcons.folder)
                                        .frame(width: 20, height: 20)
                                        .foregroundStyle(Color.Text.primary)
                                    AnytypeText(folder.title, style: .bodySemibold)
                                        .foregroundStyle(Color.Text.primary)
                                    Spacer()
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle(Loc.Pinkha.Hierarchy.moveDestination)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(Loc.Pinkha.Folder.cancel) {
                        onDismiss()
                    }
                }
            }
        }
    }
}
