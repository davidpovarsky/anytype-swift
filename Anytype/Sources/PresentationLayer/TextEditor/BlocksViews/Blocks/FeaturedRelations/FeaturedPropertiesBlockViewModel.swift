import UIKit
import Services
import Combine
import SwiftUI
import PinkhaKit

@MainActor
final class FeaturedPropertiesBlockViewModel: BlockViewModelProtocol {
    let infoProvider: BlockModelInfomationProvider
    nonisolated var info: BlockInformation { infoProvider.info }
    let className = "FeaturedPropertiesBlockViewModel"

    private let document: any BaseDocumentProtocol
    private var featuredRelations: [Property]
    private var isEligible: Bool
    private let onRelationTap: (Property) -> Void
    private let collectionController: any EditorCollectionReloadable
    private weak var torahSession: TorahEditorSession?
    
    private var cancellables = [AnyCancellable]()
    
    init(
        infoProvider: BlockModelInfomationProvider,
        document: some BaseDocumentProtocol,
        collectionController: some EditorCollectionReloadable,
        torahSession: TorahEditorSession? = nil,
        onRelationValueTap: @escaping (Property) -> Void
    ) {
        self.infoProvider = infoProvider
        self.document = document
        self.featuredRelations = document.featuredRelationsForEditor
        self.collectionController = collectionController
        self.torahSession = torahSession
        self.onRelationTap = onRelationValueTap

        let typeId = document.details?.type ?? ""
        self.isEligible = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
            typeId: typeId, spaceId: document.spaceId
        )
        
        Publishers.Merge3(
            document.featuredRelationsForEditorPublisher.map { _ in () }.eraseToAnyPublisher(),
            document.detailsPublisher.map { _ in () }.eraseToAnyPublisher(),
            NotificationCenter.default.publisher(for: PinkhaTorahPropertyPolicy.canonicalIdentityDidChangeNotification).map { _ in () }.eraseToAnyPublisher()
        )
        .receiveOnMain()
        .sink { [weak self] _ in
            guard let self else { return }
            let newRelations = self.document.featuredRelationsForEditor
            let currentTypeId = self.document.details?.type ?? ""
            let newEligibility = PinkhaTorahPropertyPolicy.shared.isTargetEligibleForNativeProperties(
                typeId: currentTypeId, spaceId: self.document.spaceId
            )
            guard self.featuredRelations != newRelations || self.isEligible != newEligibility else { return }
            self.featuredRelations = newRelations
            self.isEligible = newEligibility
            DispatchQueue.main.async { [weak self] in
                guard let self else { return }
                self.collectionController.reconfigure(items: [.block(self)])
            }
        }.store(in: &cancellables)
    }
    
    func makeContentConfiguration(maxWidth _: CGFloat) -> any UIContentConfiguration {
        return UIHostingConfiguration {
            EditorFeaturedPropertiesView(
                relations: featuredRelations,
                torahSession: torahSession,
                isEligible: isEligible,
                onRelationTap: onRelationTap
            )
        }
        .minSize(height: 0)
        .margins(.vertical, 0)
        .margins(.horizontal, 20)
    }
    
    func didSelectRowInTableView(editorEditingState: EditorEditingState) {}
}
