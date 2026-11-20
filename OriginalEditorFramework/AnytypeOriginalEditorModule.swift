import Foundation
import UIKit
import CoreText
import CryptoKit
import Assets
import DesignKit
import Loc

/// Import/link/resource inspection for the original editor module.
///
/// This prerequisite deliberately exposes no document constructor, service
/// factory, editable controller, mount operation, or persistence format. Those
/// require the separately qualified host-owned document and writer boundary.
public enum AnytypeOriginalEditorModule {
    public struct Inspection: Codable, Sendable {
        public let moduleBundleIdentifier: String
        public let moduleBundleURL: String
        public let originalTypeNames: [String]
        public let imageWidth: Double
        public let imageHeight: Double
        public let imagePNGBytes: Int
        public let imagePNGSHA256: String
        public let lightTextRGBA: [Double]
        public let darkTextRGBA: [Double]
        public let fontName: String
        public let fontResourceURL: String
        public let fontBytes: Int
        public let fontSHA256: String
        public let localizedCancel: String
    }

    public enum InspectionError: Error {
        case missingModuleBundle
        case missingOriginalImage
        case unresolvedOriginalColor
        case unresolvedOriginalFont
        case invalidOriginalFontResource
    }

    /// Calls the untouched generated package accessors. It never creates an
    /// AppDelegate, Factory service, account, Space, document or editor instance.
    @MainActor
    public static func inspectResources() throws -> Inspection {
        let moduleBundle = Bundle(for: OriginalEditorBundleMarker.self)
        guard moduleBundle.bundleIdentifier == "org.otzaria.anytype.original-editor",
              moduleBundle.bundleURL.pathExtension == "framework" else {
            throw InspectionError.missingModuleBundle
        }
        guard let image = UIImage(asset: ImageAsset.TextEditor.BlocksOption.copy),
              image.size.width > 0, image.size.height > 0,
              let png = image.pngData(), !png.isEmpty else {
            throw InspectionError.missingOriginalImage
        }
        func rgba(_ style: UIUserInterfaceStyle) throws -> [Double] {
            let value = UIColor.Text.primary.resolvedColor(with: UITraitCollection(userInterfaceStyle: style))
            var red: CGFloat = 0, green: CGFloat = 0, blue: CGFloat = 0, alpha: CGFloat = 0
            guard value.getRed(&red, green: &green, blue: &blue, alpha: &alpha),
                  [red, green, blue, alpha].allSatisfy({ $0.isFinite }) else {
                throw InspectionError.unresolvedOriginalColor
            }
            return [red, green, blue, alpha].map(Double.init)
        }
        let font = FontFamily.IBMPlexMono.regular.font(size: 17)
        let coreFont = CTFontCreateWithName(font.fontName as CFString, font.pointSize, nil)
        guard let fontURL = CTFontCopyAttribute(coreFont, kCTFontURLAttribute) as? URL,
              fontURL.isFileURL else {
            throw InspectionError.unresolvedOriginalFont
        }
        let properties = try fontURL.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
        guard properties.isRegularFile == true, properties.isSymbolicLink != true,
              let size = properties.fileSize, size > 0, size <= 1_048_576 else {
            throw InspectionError.invalidOriginalFontResource
        }
        let fontData = try Data(contentsOf: fontURL, options: .mappedIfSafe)
        guard fontData.count == size else { throw InspectionError.invalidOriginalFontResource }
        return Inspection(
            moduleBundleIdentifier: moduleBundle.bundleIdentifier!,
            moduleBundleURL: moduleBundle.bundleURL.standardizedFileURL.path,
            originalTypeNames: [String(reflecting: EditorPageController.self),
                                String(reflecting: EditorPageModuleAssembly.self),
                                String(reflecting: PreparedEditorPageSession.self),
                                String(reflecting: EditorDocumentWriteOwner.self)],
            imageWidth: Double(image.size.width), imageHeight: Double(image.size.height),
            imagePNGBytes: png.count, imagePNGSHA256: hex(SHA256.hash(data: png)),
            lightTextRGBA: try rgba(.light), darkTextRGBA: try rgba(.dark),
            fontName: font.fontName, fontResourceURL: fontURL.standardizedFileURL.path,
            fontBytes: fontData.count, fontSHA256: hex(SHA256.hash(data: fontData)),
            localizedCancel: Loc.cancel)
    }

    private static func hex(_ digest: SHA256.Digest) -> String {
        digest.map { String(format: "%02x", $0) }.joined()
    }
}

private final class OriginalEditorBundleMarker: NSObject {}
