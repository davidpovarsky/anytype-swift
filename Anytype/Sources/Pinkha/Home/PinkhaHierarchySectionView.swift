import Foundation
import SwiftUI
import PinkhaKit
import Services
import AnytypeCore
import Logger

struct PinkhaHierarchySectionView: View {
    private static let log = EventLogger(category: "Pinkha")

    let spaceId: String
    let manifest: PinkhaSpaceManifest
    weak var output: (any CommonWidgetModuleOutput)?

    @ObservedObject var repository: PinkhaHierarchyRepository
    private let mutationService = PinkhaHierarchyMutationService()

    @State private var isSectionExpanded: Bool = true
    @State private var expandedFolderIds: Set<String> = []

    // Alert & sheet states
    @State private var showingCreateRootFolderAlert: Bool = false
    @State private var newRootFolderName: String = ""

    @State private var subfolderTargetParentId: String? = nil
    @State private var newSubfolderName: String = ""

    @State private var renameTargetNode: PinkhaHierarchyNode? = nil
    @State private var renameNodeName: String = ""

    @State private var deleteTargetNode: PinkhaHierarchyNode? = nil
    @State private var showingDeleteConfirmation: Bool = false

    @State private var moveTargetNode: PinkhaHierarchyNode? = nil
    @State private var errorMessage: String? = nil

    init(spaceId: String, manifest: PinkhaSpaceManifest, repository: PinkhaHierarchyRepository, output: (any CommonWidgetModuleOutput)?) {
        self.spaceId = spaceId
        self.manifest = manifest
        self.repository = repository
        self.output = output
    }

    var body: some View {
        mainSectionContent
            .task {
                await repository.start()
            }
            // Native Alerts & Sheets
            .alert(Loc.Pinkha.Folder.newFolder, isPresented: $showingCreateRootFolderAlert) {
                TextField(Loc.Pinkha.Folder.folderName, text: $newRootFolderName)
                Button(Loc.Pinkha.Folder.cancel, role: .cancel) {}
                Button(Loc.Pinkha.Folder.save) {
                    handleCreateRootFolder()
                }
            }
            .alert(Loc.Pinkha.Folder.newSubfolder, isPresented: Binding(
                get: { subfolderTargetParentId != nil },
                set: { if !$0 { subfolderTargetParentId = nil } }
            )) {
                TextField(Loc.Pinkha.Folder.folderName, text: $newSubfolderName)
                Button(Loc.Pinkha.Folder.cancel, role: .cancel) {
                    subfolderTargetParentId = nil
                }
                Button(Loc.Pinkha.Folder.save) {
                    handleCreateSubfolder()
                }
            }
            .alert(Loc.Pinkha.Folder.rename, isPresented: Binding(
                get: { renameTargetNode != nil },
                set: { if !$0 { renameTargetNode = nil } }
            )) {
                TextField(Loc.Pinkha.Folder.folderName, text: $renameNodeName)
                Button(Loc.Pinkha.Folder.cancel, role: .cancel) {
                    renameTargetNode = nil
                }
                Button(Loc.Pinkha.Folder.save) {
                    handleRenameFolder()
                }
            }
            .alert(
                Loc.Pinkha.Folder.deleteFolder,
                isPresented: $showingDeleteConfirmation,
                presenting: deleteTargetNode
            ) { target in
                Button(Loc.Pinkha.Folder.cancel, role: .cancel) {
                    deleteTargetNode = nil
                }
                Button(Loc.Pinkha.Folder.deleteConfirmationAction, role: .destructive) {
                    handleDeleteFolder(target: target)
                }
            } message: { _ in
                Text(Loc.Pinkha.Folder.deleteConfirmationMessage)
            }
            .sheet(item: Binding<PinkhaHierarchyNode?>(
                get: { moveTargetNode },
                set: { moveTargetNode = $0 }
            )) { targetNode in
                PinkhaMoveDestinationPickerView(
                    movingNode: targetNode,
                    snapshot: repository.snapshot,
                    onSelectDestination: { destinationId in
                        handleMoveDestinationSelected(targetNode: targetNode, destinationId: destinationId)
                    },
                    onDismiss: {
                        moveTargetNode = nil
                    }
                )
            }
            .alert(
                Loc.Pinkha.Home.failed,
                isPresented: Binding(
                    get: { errorMessage != nil },
                    set: { if !$0 { errorMessage = nil } }
                )
            ) {
                Button(Loc.Pinkha.Folder.cancel, role: .cancel) {
                    errorMessage = nil
                }
            } message: {
                if let errorMessage {
                    Text(errorMessage)
                }
            }
    }

    private var mainSectionContent: some View {
        VStack(spacing: 0) {
            HomeWidgetsGroupView(
                title: Loc.Pinkha.Home.folders,
                onTap: {
                    withAnimation(.disclosure) {
                        isSectionExpanded.toggle()
                    }
                },
                onCreate: {
                    newRootFolderName = ""
                    showingCreateRootFolderAlert = true
                }
            )

            if isSectionExpanded {
                treeContent
                    .transition(.sectionBody)
            }
        }
    }

    // MARK: - Action Handlers

    private func handleCreateRootFolder() {
        let name = newRootFolderName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else { return }
        Task {
            do {
                let createdDetails = try await mutationService.createFolder(
                    name: name,
                    parentId: nil,
                    spaceId: spaceId,
                    manifest: manifest,
                    existingSiblings: repository.snapshot.rootNodes
                )
                repository.registerPendingCreated(details: createdDetails)
            } catch {
                Self.log.error("Failed to create root folder: \(error)")
                errorMessage = error.localizedDescription
            }
        }
    }

    private func handleCreateSubfolder() {
        guard let parentId = subfolderTargetParentId else { return }
        let name = newSubfolderName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else { return }
        let siblings = repository.snapshot.children(of: parentId)
        Task {
            do {
                let createdDetails = try await mutationService.createFolder(
                    name: name,
                    parentId: parentId,
                    spaceId: spaceId,
                    manifest: manifest,
                    existingSiblings: siblings
                )
                expandedFolderIds.insert(parentId)
                repository.registerPendingCreated(details: createdDetails)
            } catch {
                Self.log.error("Failed to create subfolder: \(error)")
                errorMessage = error.localizedDescription
            }
        }
        subfolderTargetParentId = nil
    }

    private func handleRenameFolder() {
        guard let target = renameTargetNode else { return }
        let name = renameNodeName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else { return }
        Task {
            do {
                repository.applyOptimisticRename(objectId: target.objectId, newName: name)
                try await mutationService.renameFolder(objectId: target.objectId, newName: name)
            } catch {
                Self.log.error("Failed to rename folder: \(error)")
                errorMessage = error.localizedDescription
            }
        }
        renameTargetNode = nil
    }

    private func handleDeleteFolder(target: PinkhaHierarchyNode) {
        Task {
            do {
                repository.applyOptimisticDelete(objectId: target.objectId)
                try await mutationService.deleteFolderSafely(
                    objectId: target.objectId,
                    spaceId: spaceId,
                    manifest: manifest,
                    snapshot: repository.snapshot
                )
            } catch {
                Self.log.error("Failed to delete folder safely: \(error)")
                errorMessage = error.localizedDescription
            }
        }
        deleteTargetNode = nil
    }

    private func handleMoveDestinationSelected(targetNode: PinkhaHierarchyNode, destinationId: String?) {
        Task {
            do {
                let newRank = try await mutationService.move(
                    objectId: targetNode.objectId,
                    newParentId: destinationId,
                    spaceId: spaceId,
                    manifest: manifest,
                    snapshot: repository.snapshot
                )
                if let destinationId {
                    expandedFolderIds.insert(destinationId)
                }
                repository.applyOptimisticMove(
                    objectId: targetNode.objectId,
                    newParentId: destinationId,
                    newRank: newRank
                )
            } catch {
                Self.log.error("Failed to move node: \(error)")
                errorMessage = error.localizedDescription
            }
        }
        moveTargetNode = nil
    }

    // MARK: - Tree View

    private var treeContent: some View {
        let flattened = flattenNodes(
            nodes: repository.snapshot.rootNodes,
            level: 0,
            expandedIds: expandedFolderIds
        )

        return VStack(spacing: 0) {
            if flattened.isEmpty {
                WidgetEmptyView()
                    .frame(maxWidth: .infinity)
                    .frame(height: 72)
            } else {
                ForEach(Array(flattened.enumerated()), id: \.element.node.id) { index, item in
                    treeRow(
                        item: item,
                        showDivider: index < flattened.count - 1
                    )
                }
            }
        }
        .background(Color.Background.widget)
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
    }

    private func treeRow(item: FlattenedItem, showDivider: Bool) -> some View {
        let node = item.node
        let level = item.level
        let hasChildren = item.hasChildren
        let isExpanded = item.isExpanded
        let details = repository.detailsMap[node.objectId]

        return HStack(alignment: .center, spacing: 0) {
            Spacer.fixedWidth(16 * CGFloat(level + 1))

            // Disclosure toggle or spacing
            if hasChildren {
                Image(asset: .X18.Disclosure.right)
                    .rotationEffect(.degrees(isExpanded ? 90 : 0))
                    .foregroundStyle(Color.Text.primary)
                    .frame(width: 20, height: 20)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        withAnimation(.disclosureSmall) {
                            if isExpanded {
                                expandedFolderIds.remove(node.objectId)
                            } else {
                                expandedFolderIds.insert(node.objectId)
                            }
                        }
                    }
            } else {
                Spacer.fixedWidth(20)
            }

            Spacer.fixedWidth(8)

            // Main Row Button
            Button {
                if node.kind == .folder {
                    withAnimation(.disclosureSmall) {
                        if isExpanded {
                            expandedFolderIds.remove(node.objectId)
                        } else {
                            expandedFolderIds.insert(node.objectId)
                        }
                    }
                } else {
                    if let details {
                        output?.onObjectSelected(screenData: details.screenData())
                    } else {
                        output?.onObjectSelected(screenData: .editor(.page(EditorPageObject(objectId: node.objectId, spaceId: spaceId))))
                    }
                }
            } label: {
                HStack(alignment: .center, spacing: 0) {
                    rowIcon(node: node, details: details, isExpanded: isExpanded)
                        .frame(width: 18, height: 18)
                    Spacer.fixedWidth(12)

                    AnytypeText(node.title.isEmpty ? Loc.Pinkha.Folder.folderName : node.title, style: .previewTitle2Medium)
                        .foregroundStyle(Color.Text.primary)
                        .lineLimit(1)
                    Spacer.fixedWidth(12)
                    Spacer()
                }
                .fixTappableArea()
            }
            .buttonStyle(.plain)
        }
        .frame(height: 40)
        .if(showDivider) {
            $0.newDivider(leadingPadding: 16, trailingPadding: 16, color: .Widget.divider)
        }
        .contentShape(.contextMenuPreview, RoundedRectangle(cornerRadius: 12, style: .continuous))
        .contextMenu {
            rowContextMenu(for: node)
        }
    }

    @ViewBuilder
    private func rowIcon(node: PinkhaHierarchyNode, details: ObjectDetails?, isExpanded: Bool) -> some View {
        if node.kind == .folder {
            PinkhaSizedAssetIcon(asset: isExpanded ? .CustomIcons.folderOpen : .CustomIcons.folder, size: 18)
                .foregroundStyle(Color.Text.primary)
        } else if let details {
            IconView(icon: details.objectIconImage)
        } else {
            IconView(icon: .object(.defaultObjectIcon))
        }
    }

    @ViewBuilder
    private func rowContextMenu(for node: PinkhaHierarchyNode) -> some View {
        if node.kind == .folder {
            Button {
                newSubfolderName = ""
                subfolderTargetParentId = node.objectId
            } label: {
                Text(Loc.Pinkha.Folder.newSubfolder)
                Image(asset: .X18.plus)
            }

            Button {
                renameNodeName = node.title
                renameTargetNode = node
            } label: {
                Text(Loc.Pinkha.Folder.rename)
                Image(asset: .CustomIcons.pencil)
            }

            Button {
                moveTargetNode = node
            } label: {
                Text(Loc.Pinkha.Hierarchy.move)
                Image(asset: .CustomIcons.folder)
            }

            reorderButtons(for: node)

            Button(role: .destructive) {
                deleteTargetNode = node
                showingDeleteConfirmation = true
            } label: {
                Text(Loc.Pinkha.Folder.deleteFolder)
                Image(asset: .CustomIcons.trash)
            }
        } else {
            Button {
                moveTargetNode = node
            } label: {
                Text(Loc.Pinkha.Hierarchy.move)
                Image(asset: .CustomIcons.folder)
            }

            reorderButtons(for: node)
        }
    }

    @ViewBuilder
    private func reorderButtons(for node: PinkhaHierarchyNode) -> some View {
        let siblings = repository.snapshot.children(of: node.parentId)
        if let index = siblings.firstIndex(where: { $0.objectId == node.objectId }) {
            if index > 0 {
                Button {
                    moveSibling(node: node, direction: .up, siblings: siblings, index: index)
                } label: {
                    Text(Loc.Pinkha.Hierarchy.moveUp)
                    Image(asset: .X24.Arrow.up)
                }
            }
            if index < siblings.count - 1 {
                Button {
                    moveSibling(node: node, direction: .down, siblings: siblings, index: index)
                } label: {
                    Text(Loc.Pinkha.Hierarchy.moveDown)
                    Image(asset: .X24.Arrow.down)
                }
            }
        }
    }

    private enum MoveDirection { case up, down }

    private func moveSibling(
        node: PinkhaHierarchyNode,
        direction: MoveDirection,
        siblings: [PinkhaHierarchyNode],
        index: Int
    ) {
        let newRank: Double
        switch direction {
        case .up:
            if index == 1 {
                newRank = PinkhaHierarchyOrdering.rankBetween(before: nil, after: siblings[0].order)
            } else {
                newRank = PinkhaHierarchyOrdering.rankBetween(before: siblings[index - 2].order, after: siblings[index - 1].order)
            }
        case .down:
            if index == siblings.count - 2 {
                newRank = PinkhaHierarchyOrdering.rankBetween(before: siblings.last?.order, after: nil)
            } else {
                newRank = PinkhaHierarchyOrdering.rankBetween(before: siblings[index + 1].order, after: siblings[index + 2].order)
            }
        }

        Task {
            do {
                repository.applyOptimisticOrder(objectId: node.objectId, newRank: newRank)
                try await mutationService.updateOrder(objectId: node.objectId, newRank: newRank, manifest: manifest)
                if PinkhaHierarchyOrdering.shouldRebalance(siblings: siblings) {
                    try await mutationService.rebalanceSiblings(siblings: siblings, manifest: manifest)
                }
            } catch {
                Self.log.error("Failed to move sibling: \(error)")
                errorMessage = error.localizedDescription
            }
        }
    }

    // MARK: - Tree Flattening

    private struct FlattenedItem {
        let node: PinkhaHierarchyNode
        let level: Int
        let hasChildren: Bool
        let isExpanded: Bool
    }

    private func flattenNodes(
        nodes: [PinkhaHierarchyNode],
        level: Int,
        expandedIds: Set<String>
    ) -> [FlattenedItem] {
        var result: [FlattenedItem] = []
        for node in nodes {
            let hasChildren = !node.children.isEmpty
            let isExpanded = expandedIds.contains(node.objectId)
            result.append(FlattenedItem(
                node: node,
                level: level,
                hasChildren: hasChildren,
                isExpanded: isExpanded
            ))
            if hasChildren && isExpanded {
                let children = flattenNodes(
                    nodes: node.children,
                    level: level + 1,
                    expandedIds: expandedIds
                )
                result.append(contentsOf: children)
            }
        }
        return result
    }
}
