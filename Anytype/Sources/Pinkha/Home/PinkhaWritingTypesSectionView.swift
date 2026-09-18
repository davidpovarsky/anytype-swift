import Foundation
import SwiftUI
import PinkhaKit
import Services
import AnytypeCore
import Factory

struct PinkhaWritingTypesSectionView: View {
    let spaceId: String
    let manifest: PinkhaSpaceManifest
    weak var output: (any CommonWidgetModuleOutput)?

    @State private var isSectionExpanded: Bool = true
    @State private var typeInfos: [ObjectTypeWidgetInfo] = []

    @Injected(\.objectTypeProvider)
    private var objectTypeProvider: any ObjectTypeProviderProtocol

    @Injected(\.objectActionsService)
    private var objectActionsService: any ObjectActionsServiceProtocol

    @Injected(\.propertiesService)
    private var propertiesService: any PropertiesServiceProtocol

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
        let type = try objectTypeProvider.objectType(id: info.objectTypeId)
        let role = manifest.role(forTypeId: info.objectTypeId) ?? ""
        let templateId = manifest.defaultTemplateIds[role] ?? type.defaultTemplateId

        let details = try await objectActionsService.createObject(
            name: "",
            typeUniqueKey: type.uniqueKey,
            shouldDeleteEmptyObject: true,
            shouldSelectType: false,
            shouldSelectTemplate: false,
            spaceId: spaceId,
            origin: .none,
            templateId: templateId
        )

        // Assign initial order rank if order property exists
        if !manifest.orderPropertyKey.isEmpty {
            let initialRank = PinkhaHierarchyOrdering.initialRank
            try? await propertiesService.updateProperty(
                objectId: details.id,
                propertyKey: manifest.orderPropertyKey,
                value: initialRank.protobufValue
            )
        }

        output?.onObjectSelected(screenData: details.screenData())
    }
}
