import CoreGraphics
import PinkhaKit
import SwiftUI
import Testing
import UIKit
import XCTest
@testable import Anytype

@MainActor
@Suite("Torah search layout")
struct TorahSearchLayoutTests {

    @Test("Real Torah SVG glyphs stay inside full and minimal SearchCell slots")
    func torahAssetGlyphsStayInsideSearchCellSlots() throws {
        let icons: [Icon] = [
            .asset(.CustomIcons.book),
            .asset(.CustomIcons.pricetag),
            .asset(.CustomIcons.text)
        ]

        for icon in icons {
            for mode in [SerchDataPresentationMode.full(descriptionInfo: nil, callout: nil), .minimal] {
                for width in [420.0, 768.0] {
                    for direction in [LayoutDirection.leftToRight, .rightToLeft] {
                        let data = SearchLayoutData(iconImage: icon, mode: mode)
                        let image = try renderSearchCell(
                            data: data,
                            width: width,
                            direction: direction
                        )
                        let bounds = try opaqueContentBounds(image)
                        let slotSize = data.isMinimal ? 24.0 : 48.0
                        let slotMinX = direction == .leftToRight
                            ? 16.0
                            : width - 16.0 - slotSize
                        let slotMaxX = slotMinX + slotSize

                        #expect(bounds.width <= SearchCellIconView.standardAssetGlyphSize + 1)
                        #expect(bounds.height <= SearchCellIconView.standardAssetGlyphSize + 1)
                        #expect(bounds.minX >= slotMinX - 1)
                        #expect(bounds.maxX <= slotMaxX + 1)
                    }
                }
            }
        }
    }

    @Test("SearchCell keeps intrinsic asset behavior unless a caller opts into scaling")
    func unrelatedAssetRowsRemainUnchanged() throws {
        let icon = Icon.asset(.webPage)
        let data = SearchLayoutData(
            iconImage: icon,
            mode: .full(descriptionInfo: nil, callout: nil)
        )
        let searchCellImage = try renderSearchCell(
            data: data,
            width: 420,
            direction: .leftToRight,
            assetGlyphSize: nil
        )
        let directRenderer = ImageRenderer(
            content: IconView(icon: icon).frame(width: 48, height: 48)
        )
        directRenderer.scale = 1
        directRenderer.proposedSize = ProposedViewSize(width: 48, height: 48)
        let directImage = try #require(directRenderer.cgImage)
        let searchCellBounds = try opaqueContentBounds(searchCellImage)
        let directBounds = try opaqueContentBounds(directImage)

        #expect(searchCellBounds.size == directBounds.size)
    }

    @Test("Existing associations use one deterministic row for 1, 2, and 12 links")
    func associationStripHasDeterministicHeight() throws {
        let variants = [1, 2, 12]
        for count in variants {
            for direction in [LayoutDirection.leftToRight, .rightToLeft] {
                for typeSize in [DynamicTypeSize.large, .accessibility3] {
                    let image = try renderAssociationStrip(
                        items: associationFixtures(count: count),
                        persistenceState: .saved,
                        width: 360,
                        direction: direction,
                        dynamicTypeSize: typeSize
                    )
                    #expect(image.height == Int(TorahAssociationPreviewStrip.height))
                }
            }
        }
    }

    @Test("A long association list remains horizontally reachable")
    func longAssociationStripScrollsHorizontally() throws {
        let strip = TorahAssociationPreviewStrip(
            items: associationFixtures(count: 12),
            persistenceState: nil,
            locale: Locale(identifier: "he"),
            canOpen: { _ in true },
            onOpen: { _ in },
            onUnlink: { _ in }
        )
        .environment(\.layoutDirection, .rightToLeft)
        .dynamicTypeSize(.accessibility3)

        let host = UIHostingController(rootView: strip)
        let frame = CGRect(x: 0, y: 0, width: 360, height: TorahAssociationPreviewStrip.height)
        let window = UIWindow(frame: frame)
        window.rootViewController = host
        window.makeKeyAndVisible()
        host.view.frame = frame
        host.view.layoutIfNeeded()
        defer { window.isHidden = true }
        let scrollView = try #require(firstSubview(of: UIScrollView.self, in: host.view))

        #expect(scrollView.contentSize.width > scrollView.bounds.width)
        #expect(host.view.bounds.height == TorahAssociationPreviewStrip.height)
    }

    @Test("Saved state never creates a permanent standalone row")
    func savedStateDoesNotCreateStandaloneRow() {
        #expect(!TorahAssociationPreviewStrip.shouldShow(items: [], persistenceState: nil))
        #expect(!TorahAssociationPreviewStrip.shouldShow(items: [], persistenceState: .saved))
        #expect(TorahAssociationPreviewStrip.visiblePersistenceLabel(.saved) == nil)
        #expect(TorahAssociationPreviewStrip.shouldShow(items: [], persistenceState: .waiting))
        #expect(TorahAssociationPreviewStrip.shouldShow(items: [], persistenceState: .saving))
        #expect(TorahAssociationPreviewStrip.shouldShow(
            items: [],
            persistenceState: .conflict("Resolve the conflicting write")
        ))
        #expect(TorahAssociationPreviewStrip.shouldShow(
            items: [],
            persistenceState: .uncertain("Verify the latest write")
        ))
        #expect(TorahAssociationPreviewStrip.shouldShow(
            items: [],
            persistenceState: .error("Retry the operation")
        ))
    }

    @Test("Pending and failure states remain visible without growing beyond one row")
    func persistenceFeedbackRemainsInline() throws {
        let states: [TorahAssociationPersistenceState] = [
            .waiting,
            .saving,
            .conflict("A conflicting write needs attention"),
            .uncertain("The readback is uncertain"),
            .error("Retry linking this source")
        ]

        for state in states {
            let image = try renderAssociationStrip(
                items: [],
                persistenceState: state,
                width: 320,
                direction: .rightToLeft,
                dynamicTypeSize: .accessibility3
            )
            #expect(image.height == Int(TorahAssociationPreviewStrip.height))
            #expect(TorahAssociationPreviewStrip.visiblePersistenceLabel(state)?.isEmpty == false)
        }
    }

    @Test("Document and block contexts keep distinct localized actions")
    func documentAndBlockCopyRemainDistinct() {
        #expect(TorahSourcesSearchCopy.contextTitle(blockId: nil) == Loc.Pinkha.Torah.documentLinks)
        #expect(TorahSourcesSearchCopy.contextTitle(blockId: "block") == Loc.Pinkha.Torah.blockLinks)
        #expect(TorahSourcesSearchCopy.linkTitle(blockId: nil) == Loc.Pinkha.Torah.linkToDocument)
        #expect(TorahSourcesSearchCopy.linkTitle(blockId: "block") == Loc.Pinkha.Torah.linkToBlock)
    }

    private func renderSearchCell(
        data: SearchLayoutData,
        width: CGFloat,
        direction: LayoutDirection,
        assetGlyphSize: CGFloat? = SearchCellIconView.standardAssetGlyphSize
    ) throws -> CGImage {
        let height = data.isMinimal ? 52.0 : 68.0
        let content: AnyView
        if let assetGlyphSize {
            content = AnyView(SearchCell(
                data: data,
                assetGlyphSize: assetGlyphSize
            ))
        } else {
            content = AnyView(SearchCell(data: data))
        }
        let renderer = ImageRenderer(content: content
            .frame(width: width)
            .environment(\.layoutDirection, direction))
        renderer.scale = 1
        renderer.proposedSize = ProposedViewSize(width: width, height: height)
        return try #require(renderer.cgImage)
    }

    private func renderAssociationStrip(
        items: [TorahAssociationItem],
        persistenceState: TorahAssociationPersistenceState?,
        width: CGFloat,
        direction: LayoutDirection,
        dynamicTypeSize: DynamicTypeSize
    ) throws -> CGImage {
        let renderer = ImageRenderer(
            content: TorahAssociationPreviewStrip(
                items: items,
                persistenceState: persistenceState,
                locale: Locale(identifier: direction == .rightToLeft ? "he" : "en"),
                canOpen: { _ in true },
                onOpen: { _ in },
                onUnlink: { _ in }
            )
            .frame(width: width)
            .environment(\.layoutDirection, direction)
            .dynamicTypeSize(dynamicTypeSize)
        )
        renderer.scale = 1
        renderer.proposedSize = ProposedViewSize(
            width: width,
            height: TorahAssociationPreviewStrip.height
        )
        return try #require(renderer.cgImage)
    }
}

@MainActor
final class TorahSearchLayoutScreenshotTests: XCTestCase {

    func testDeterministicTorahSearchLayoutEvidence() throws {
        for scope in TorahEditorSession.SearchScope.allCases {
            let image = try renderHosted(
                TorahSearchLayoutEvidenceView(
                    scope: scope,
                    blockId: nil,
                    associations: associationFixtures(count: 2)
                ),
                size: CGSize(width: 768, height: 640),
                direction: .rightToLeft
            )
            addScreenshot(image, name: "torah-search-\(scope.rawValue)-ipad-rtl")
        }

        let narrowImage = try renderHosted(
            TorahSearchLayoutEvidenceView(
                scope: .references,
                blockId: "block-1",
                associations: associationFixtures(count: 12)
            ),
            size: CGSize(width: 420, height: 640),
            direction: .rightToLeft
        )
        addScreenshot(narrowImage, name: "torah-search-12-links-stage-manager-rtl")
    }

    private func addScreenshot(_ image: UIImage, name: String) {
        let attachment = XCTAttachment(image: image)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}

private struct SearchLayoutData: SearchDataProtocol {
    let id = UUID().uuidString
    let iconImage: Icon?
    let title = ""
    let mode: SerchDataPresentationMode
}

private struct TorahSearchLayoutEvidenceView: View {
    @State private var query = ""

    let scope: TorahEditorSession.SearchScope
    let blockId: String?
    let associations: [TorahAssociationItem]

    private var rows: [TorahSearchCellData] {
        [TorahSearchCellData(
            result: TorahEditorSession.SearchResult(
                id: scope.rawValue,
                scope: scope,
                providerValue: scope.rawValue,
                labelHe: "תוצאה ארוכה בעברית לבדיקת פריסה",
                labelEn: "Long English layout result",
                fallbackTitle: "Layout result",
                fallbackSubtitle: "Secondary metadata"
            ),
            locale: Locale(identifier: "he")
        )]
    }

    var body: some View {
        SearchViewShell(
            title: TorahSourcesSearchCopy.contextTitle(blockId: blockId),
            placeholder: Loc.Pinkha.Torah.searchPlaceholder,
            searchText: $query
        ) {
            Picker(Loc.Pinkha.Torah.searchType, selection: .constant(scope)) {
                ForEach(TorahEditorSession.SearchScope.allCases) { value in
                    Text(value.title).tag(value)
                }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .divider()

            TorahAssociationPreviewStrip(
                items: associations,
                persistenceState: .saved,
                locale: Locale(identifier: "he"),
                canOpen: { _ in true },
                onOpen: { _ in },
                onUnlink: { _ in }
            )
            .divider()

            PlainList {
                ForEach(rows) { row in
                    SearchCell(
                        data: row,
                        onSelect: {},
                        assetGlyphSize: SearchCellIconView.standardAssetGlyphSize
                    ) {
                        Button {} label: {
                            Image(asset: .X24.linkToExistingObject)
                                .renderingMode(.template)
                                .frame(width: 20, height: 20)
                                .foregroundStyle(Color.Control.secondary)
                                .frame(width: 44, height: 44)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
        .background(Color.Background.secondary)
    }
}

@MainActor
private func renderHosted<Content: View>(
    _ content: Content,
    size: CGSize,
    direction: LayoutDirection
) throws -> UIImage {
    let controller = UIHostingController(
        rootView: content
            .environment(\.layoutDirection, direction)
            .environment(\.locale, Locale(identifier: direction == .rightToLeft ? "he" : "en"))
    )
    let window = UIWindow(frame: CGRect(origin: .zero, size: size))
    window.rootViewController = controller
    window.makeKeyAndVisible()
    controller.view.frame = window.bounds
    controller.view.setNeedsLayout()
    controller.view.layoutIfNeeded()

    let renderer = UIGraphicsImageRenderer(size: size)
    let image = renderer.image { context in
        controller.view.layer.render(in: context.cgContext)
    }
    window.isHidden = true
    return image
}

private func associationFixtures(count: Int) -> [TorahAssociationItem] {
    (0..<count).map { index in
        let kind = TorahAssociationKind.allCases[index % TorahAssociationKind.allCases.count]
        return TorahAssociationItem(
            id: "association-\(index)",
            kind: kind,
            role: .context,
            providerID: "sefaria",
            externalID: "fixture-\(index)",
            canonicalKey: "Fixture \(index)",
            labelHe: index.isMultiple(of: 2)
                ? "מקור עברי ארוך מספר \(index + 1)"
                : "",
            labelEn: index.isMultiple(of: 2)
                ? "Long English source \(index + 1)"
                : "English source \(index + 1)"
        )
    }
}

private func opaqueContentBounds(_ image: CGImage) throws -> CGRect {
    let width = image.width
    let height = image.height
    let bytesPerRow = width * 4
    var pixels = [UInt8](repeating: 0, count: height * bytesPerRow)
    let rendered = pixels.withUnsafeMutableBytes { bytes -> Bool in
        guard let context = CGContext(
            data: bytes.baseAddress,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: bytesPerRow,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return false }
        context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        return true
    }
    guard rendered else { throw TorahSearchLayoutTestError.couldNotReadPixels }

    var minX = width
    var minY = height
    var maxX = -1
    var maxY = -1
    for y in 2..<(height - 2) {
        for x in 0..<width where pixels[(y * bytesPerRow) + (x * 4) + 3] > 8 {
            minX = min(minX, x)
            minY = min(minY, y)
            maxX = max(maxX, x)
            maxY = max(maxY, y)
        }
    }
    guard maxX >= minX, maxY >= minY else { throw TorahSearchLayoutTestError.noOpaquePixels }
    return CGRect(
        x: minX,
        y: minY,
        width: maxX - minX + 1,
        height: maxY - minY + 1
    )
}

private func firstSubview<ViewType: UIView>(
    of type: ViewType.Type,
    in root: UIView
) -> ViewType? {
    if let match = root as? ViewType { return match }
    for subview in root.subviews {
        if let match = firstSubview(of: type, in: subview) { return match }
    }
    return nil
}

private enum TorahSearchLayoutTestError: Error {
    case couldNotReadPixels
    case noOpaquePixels
}
