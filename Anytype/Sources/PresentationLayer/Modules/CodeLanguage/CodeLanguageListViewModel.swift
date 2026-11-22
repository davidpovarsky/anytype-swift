import Foundation
import Services

struct CodeLanguageListData: Identifiable, Hashable {
    let documentId: String
    let spaceId: String
    let blockId: String
    
    var id: Int { hashValue }
}

@MainActor
@Observable
final class CodeLanguageListViewModel {

    // MARK: - DI
    @ObservationIgnored
    @Injected(\.blockService)
    private var blockService: any BlockServiceProtocol

    private let data: CodeLanguageListData
    private let document: any BaseDocumentProtocol
    @ObservationIgnored
    private let documentWriteOwner: EditorDocumentWriteOwner?
    private var selectedLanguage: CodeLanguage?

    // MARK: - State

    var rows: [CodeLanguageRowModel] = []
    var dismiss: Bool = false
    
    init(data: CodeLanguageListData, documentWriteOwner: EditorDocumentWriteOwner? = nil) {
        self.data = data
        self.documentWriteOwner = documentWriteOwner
        
        let documentsProvider = Container.shared.documentsProvider()
        self.document = documentsProvider.document(objectId: data.documentId, spaceId: data.spaceId)
        
        let info = try? withCurrentDocument { document.infoContainer.get(id: data.blockId) }
        selectedLanguage = info?.fields.codeLanguage
        updateRows(searchText: "")
    }
    
    func onChangeSearch(text: String) {
        updateRows(searchText: text)
    }
    
    // MARK: - Private
    
    private func updateRows(searchText: String) {
        
        let languages = searchText.isEmpty
            ? CodeLanguage.allCases
            : CodeLanguage.allCases.filter { $0.title.localizedStandardContains(searchText) }
        
        rows = languages.map { language in
            CodeLanguageRowModel(
                id: language.rawValue,
                title: language.title,
                isSelected: language == selectedLanguage
            ) { [weak self] in
                self?.onTapCodeLanguage(language)
            }
        }
    }
    
    private func onTapCodeLanguage(_ language: CodeLanguage) {
        scheduleOriginalEditorMutation(owner: documentWriteOwner, contextId: data.documentId) { [self] in
            guard let info = try withCurrentDocument({ document.infoContainer.get(id: data.blockId) }) else { return }
            let fields = CodeBlockFields(language: language)
            let newInfo = info.addFields(fields.asMiddleware())
            let service: any BlockServiceProtocol
            if let documentWriteOwner {
                service = DocumentOwnedBlockService(owner: documentWriteOwner, service: blockService)
            } else {
                service = blockService
            }
            try await service.setFields(objectId: document.objectId, blockId: data.blockId, fields: newInfo.fields)
            try withCurrentDocument { dismiss.toggle() }
        }
    }

    private func withCurrentDocument<Value>(_ operation: () throws -> Value) throws -> Value {
        guard let documentWriteOwner else { return try operation() }
        return try documentWriteOwner.performSynchronousOperation(
            contextId: data.documentId, spaceId: data.spaceId, requiresEditing: false
        ) {
            try documentWriteOwner.validateDocument(document)
            return try operation()
        }
    }
    
    
}
