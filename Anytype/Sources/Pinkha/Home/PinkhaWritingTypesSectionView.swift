import Foundation
import SwiftUI
import PinkhaKit
import Services
import AnytypeCore
import Factory
import Logger

struct PinkhaWritingTypesSectionView: View {
    private static let log = EventLogger(category: "Pinkha")

    let spaceId: String
    let manifest: PinkhaSpaceManifest
    @ObservedObject var repository: PinkhaHierarchyRepository
    weak var output: (any CommonWidgetModuleOutput)?

    @State private var isSectionExpanded: Bool = true
    @State private var typeInfos: [ObjectTypeWidgetInfo] = []
    @State private var errorMessage: String? = nil

    private let mutationService = PinkhaHierarchyMutationService()

    @Injected(\.objectTypeProvider)
    private var objectTypeProvider: any ObjectTypeProviderProtocol

    var body: some View {
        VStack(spacing: 0) {
            HomeWidgetsGroupView(
                title: Loc.Pinkha.Home.writing,
                onTap: {
                    withAnimation(.disclosure) {
                        isSectionExpanded.toggle()
                    }
                }
            )

            if isSectionExpanded && !typeInfos.isEmpty {
                ObjectTypesUnifiedWidgetView(
                    typeInfos: typeInfos,
                    canCreateType: false,
                    onCreateType: {},
                    onTap: { info in
                        output?.onObjectSelected(
                            screenData: .editor(.type(EditorTypeObject(objectId: info.objectTypeId, spaceId: info.spaceId)))
                        )
                    },
                    onCreate: { info in
                        try await createWritingDocument(for: info)
                    }
                )
                .transition(.sectionBody)
            }
        }
        .task {
            loadWritingTypes()
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

    private func loadWritingTypes() {
        var infos: [ObjectTypeWidgetInfo] = []
        let roles = [
            PinkhaSchemaRoles.chiddushKey,
            PinkhaSchemaRoles.articleKey,
            PinkhaSchemaRoles.researchKey
        ]

        for role in roles {
            guard let typeId = manifest.registeredDocumentTypes[role],
                  let type = try? objectTypeProvider.objectType(id: typeId) else {
                continue
            }

            let info = ObjectTypeWidgetInfo(
                objectTypeId: type.id,
                spaceId: spaceId,
                name: type.pluralDisplayName,
                icon: type.icon,
                canCreateObject: true
            )
            infos.append(info)
        }

        self.typeInfos = infos
    }

    private func createWritingDocument(for info: ObjectTypeWidgetInfo) async throws {
        do {
            let details = try await mutationService.createWritingDocument(
                typeId: info.objectTypeId,
                parentId: nil,
                spaceId: spaceId,
                manifest: manifest,
                existingSiblings: repository.snapshot.rootNodes
            )
            repository.registerPendingCreated(details: details)
            output?.onObjectSelected(screenData: details.screenData())
        } catch {
            Self.log.error("Failed to create writing document: \(error)")
            errorMessage = error.localizedDescription
            throw error
        }
    }
}
