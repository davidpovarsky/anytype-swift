#if canImport(CoreTransferable)
import CoreTransferable
#endif
import Foundation
#if canImport(UniformTypeIdentifiers)
import UniformTypeIdentifiers

public extension UTType {
    static let torahSource = UTType(exportedAs: "com.gloiiire.pinkha.torahSource")
}
#endif

public struct TorahSourceTransfer: Codable, Hashable, Sendable, Identifiable {
    public var id: String { "\(providerID):\(canonicalRef)" }
    public let providerID: String
    public let canonicalRef: String
    public let hebrewRef: String?
    public let sectionRef: String?
    public let text: String
    public let versionTitle: String?
    public let license: String?
    public let direction: String?
    public let rawProviderPayload: String
    public let retrievedAt: Date

    public init(
        providerID: String,
        canonicalRef: String,
        hebrewRef: String?,
        sectionRef: String? = nil,
        text: String,
        versionTitle: String? = nil,
        license: String? = nil,
        direction: String? = nil,
        rawProviderPayload: String = "{}",
        retrievedAt: Date = Date()
    ) {
        self.providerID = providerID
        self.canonicalRef = canonicalRef
        self.hebrewRef = hebrewRef
        self.sectionRef = sectionRef
        self.text = text
        self.versionTitle = versionTitle
        self.license = license
        self.direction = direction
        self.rawProviderPayload = rawProviderPayload
        self.retrievedAt = retrievedAt
    }

    public init(segment: TorahTextSegment, document: TorahTextDocument) {
        self.init(
            providerID: document.providerID,
            canonicalRef: segment.canonicalRef,
            hebrewRef: segment.hebrewRef,
            sectionRef: document.sectionRef,
            text: segment.text,
            versionTitle: document.version.versionTitle,
            license: document.version.license,
            direction: document.version.direction,
            rawProviderPayload: document.rawProviderPayload
        )
    }

#if canImport(UniformTypeIdentifiers) && !os(Windows)
    public var itemProvider: NSItemProvider {
        let data = (try? JSONEncoder().encode(self)) ?? Data()
        let provider = NSItemProvider()
        provider.registerDataRepresentation(forTypeIdentifier: UTType.torahSource.identifier, visibility: .ownProcess) { completion in
            completion(data, nil)
            return nil
        }
        provider.registerObject(text as NSString, visibility: .all)
        return provider
    }

    public static func decode(_ providers: [NSItemProvider], completion: @escaping @Sendable (TorahSourceTransfer) -> Void) {
        guard let provider = providers.first(where: { $0.hasItemConformingToTypeIdentifier(UTType.torahSource.identifier) }) else { return }
        _ = provider.loadDataRepresentation(forTypeIdentifier: UTType.torahSource.identifier) { data, _ in
            guard let data, let decoded = try? JSONDecoder().decode(TorahSourceTransfer.self, from: data) else { return }
            completion(decoded)
        }
    }
#endif
}

#if canImport(CoreTransferable) && canImport(UniformTypeIdentifiers)
extension TorahSourceTransfer: Transferable {
    public static var transferRepresentation: some TransferRepresentation {
        CodableRepresentation(contentType: .torahSource)
        ProxyRepresentation(exporting: \TorahSourceTransfer.text)
    }
}
#endif
