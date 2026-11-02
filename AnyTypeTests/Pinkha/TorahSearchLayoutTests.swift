import CoreGraphics
import PinkhaKit
import Services
import SwiftUI
import Testing
import UIKit
import XCTest
@testable import Anytype

@MainActor
@Suite("Torah search layout", .serialized)
struct TorahSearchLayoutTests {

    @Test("Real Torah SVG glyphs stay inside full and minimal SearchCell slots")
    func torahAssetGlyphsStayInsideSearchCellSlots() async throws {
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
                        let image = try await renderSearchCell(
                            data: data,
                            width: width,
                            direction: direction
                        )
                        let rowHeight = data.isMinimal ? 52.0 : 68.0
                        let glyphBand = CGRect(
                            x: 0,
                            y: (rowHeight - SearchCellIconView.standardAssetGlyphSize - 4) / 2,
                            width: width,
                            height: SearchCellIconView.standardAssetGlyphSize + 4
                        )
                        let bounds = try opaqueContentBounds(image, scanning: glyphBand)
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
    func unrelatedAssetRowsRemainUnchanged() async throws {
        let icon = Icon.asset(.webPage)
        let data = SearchLayoutData(
            iconImage: icon,
            mode: .full(descriptionInfo: nil, callout: nil)
        )
        let searchCellImage = try await renderSearchCell(
            data: data,
            width: 420,
            direction: .leftToRight,
            assetGlyphSize: nil
        )
        let directImage = try await renderHostedCGImage(
            IconView(icon: icon).frame(width: 48, height: 48),
            size: CGSize(width: 48, height: 48),
            direction: .leftToRight
        )
        let searchCellBounds = try opaqueContentBounds(searchCellImage)
        let directBounds = try opaqueContentBounds(directImage)

        #expect(searchCellBounds.size == directBounds.size)
    }

    @Test("Existing associations use one deterministic row for 1, 2, and 12 links")
    func associationStripHasDeterministicHeight() throws {
        #expect(!TorahAssociationPreviewStrip.shouldShow(items: [], persistenceState: .saved))
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

    @Test("Standalone and embedded production compositions contain exactly one search field")
    func productionCompositionsHaveOneSearchField() throws {
        for presentation in TorahSearchLayoutPresentation.allCases {
            let view = try TorahSearchLayoutEvidenceView(
                presentation: presentation,
                scope: .references,
                blockId: nil,
                associations: []
            )
            let controller = UIHostingController(rootView: view)
            let frame = CGRect(x: 0, y: 0, width: 768, height: 640)
            let window = UIWindow(frame: frame)
            window.rootViewController = controller
            window.makeKeyAndVisible()
            controller.view.frame = frame
            controller.view.layoutIfNeeded()
            defer { window.isHidden = true }

            #expect(subviews(of: UITextField.self, in: controller.view).count == 1)
        }
    }

    private func renderSearchCell(
        data: SearchLayoutData,
        width: CGFloat,
        direction: LayoutDirection,
        assetGlyphSize: CGFloat? = SearchCellIconView.standardAssetGlyphSize
    ) async throws -> CGImage {
        if case .asset(let asset)? = data.iconImage {
            _ = try #require(UIImage(asset: asset))
        }
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
        return try await renderHostedCGImage(
            content.frame(width: width, height: height),
            size: CGSize(width: width, height: height),
            direction: direction
        )
    }

    private func renderHostedCGImage<Content: View>(
        _ content: Content,
        size: CGSize,
        direction: LayoutDirection
    ) async throws -> CGImage {
        let controller = UIHostingController(
            rootView: content
                .ignoresSafeArea()
                .environment(\.layoutDirection, direction)
        )
        let window = UIWindow(frame: CGRect(origin: .zero, size: size))
        window.backgroundColor = .clear
        window.isOpaque = false
        window.rootViewController = controller
        window.makeKeyAndVisible()
        defer { window.isHidden = true }

        controller.view.frame = window.bounds
        controller.view.backgroundColor = .clear
        controller.view.isOpaque = false
        controller.view.setNeedsLayout()
        controller.view.layoutIfNeeded()
        await Task.yield()
        controller.view.setNeedsLayout()
        controller.view.layoutIfNeeded()

        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = false
        let renderer = UIGraphicsImageRenderer(size: size, format: format)
        let image = renderer.image { context in
            controller.view.layer.render(in: context.cgContext)
        }
        return try #require(image.cgImage)
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

    func testNativeDocumentSourcesRefreshInLTR() async throws {
        try await assertDocumentSourcesRefresh(missingNativeRow: false, direction: .leftToRight)
    }

    func testNativeDocumentSourcesRefreshInRTL() async throws {
        try await assertDocumentSourcesRefresh(missingNativeRow: false, direction: .rightToLeft)
    }

    func testPresentationDocumentSourcesRefreshInLTR() async throws {
        try await assertDocumentSourcesRefresh(missingNativeRow: true, direction: .leftToRight)
    }

    func testPresentationDocumentSourcesRefreshInRTL() async throws {
        try await assertDocumentSourcesRefresh(missingNativeRow: true, direction: .rightToLeft)
    }

    private func assertDocumentSourcesRefresh(missingNativeRow: Bool, direction: LayoutDirection) async throws {
        let context = TorahAssociationContext(spaceId: "header-space", objectId: "header-object", scope: .document)
        let provider = TorahSearchLayoutProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider], topicProviders: [provider], lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let repository = TorahSearchLayoutRepository(context: context, items: [])
        let session = TorahEditorSession(
            spaceId: context.spaceId, objectId: context.objectId,
            workspace: AnytypeTorahWorkspace(registry: registry), associations: repository
        )
        let document = MockBaseDocument(objectId: context.objectId)
        document.mockSpaceId = context.spaceId
        let nativeInfo = BlockInformation.empty(id: "featuredRelations", content: .featuredRelations)
        document.mockChildren = missingNativeRow ? [] : [nativeInfo]
        let originalTree = document.children
        let row = PinkhaDocumentMetadataRowModel(document: document, session: session, onRelationTap: { _ in })
        let reloadProbe = TorahHeaderReloadProbe()
        let native = FeaturedPropertiesBlockViewModel(
            infoProvider: BlockModelInfomationProvider(
                document: document, info: nativeInfo
            ),
            document: document, collectionController: reloadProbe,
            torahSession: session, onRelationValueTap: { _ in }
        )
        let item: EditorItem = missingNativeRow ? .system(row) : .block(native)
        let rowIdentity = item.hashValue
        let configuration = missingNativeRow
            ? row.makeContentConfiguration(maxWidth: 320)
            : native.makeContentConfiguration(maxWidth: 320)
        let controller = TorahScreenshotContainer()
        controller.view.semanticContentAttribute = direction == .rightToLeft ? .forceRightToLeft : .forceLeftToRight
        controller.traitOverrides.layoutDirection = direction == .rightToLeft ? .rightToLeft : .leftToRight
        let scene = try XCTUnwrap(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let previousKeyWindow = scene.windows.first(where: \.isKeyWindow)
        let window = UIWindow(windowScene: scene)
        window.frame = CGRect(x: 0, y: 0, width: 320, height: 280)
        window.rootViewController = controller
        window.makeKeyAndVisible()
        defer {
            window.isHidden = true
            window.rootViewController = nil
            previousKeyWindow?.makeKey()
        }
        let appearance = await XCTWaiter.fulfillment(of: [controller.appeared], timeout: 5)
        XCTAssertEqual(appearance, .completed, "The native screenshot host must finish appearing before use")
        // UIHostingConfiguration belongs to a real cell, as in the native editor.
        let layout = EditorCollectionFlowLayout()
        let collection = EditorCollectionView(frame: CGRect(x: 0, y: 0, width: 320, height: 280), collectionViewLayout: layout)
        controller.view.addSubview(collection)
        var configurationCount = 0
        let registration = UICollectionView.CellRegistration<EditorViewListCell, EditorItem> { cell, _, _ in
            configurationCount += 1
            cell.contentConfiguration = configuration
        }
        let dataSource = UICollectionViewDiffableDataSource<EditorSection, EditorItem>(collectionView: collection) { collection, indexPath, item in
            collection.dequeueConfiguredReusableCell(using: registration, for: indexPath, item: item)
        }
        layout.dataSource = dataSource
        var snapshot = NSDiffableDataSourceSnapshot<EditorSection, EditorItem>()
        snapshot.appendSections([.main])
        snapshot.appendItems([item])
        await dataSource.apply(snapshot, animatingDifferences: false)
        print("PINKHA_SOURCES_CELL_READY missingNative=\(missingNativeRow) direction=\(direction)")
        var previous = [TorahAssociationItem]()
        var images = [Int: Data]()
        for count in [0, 1, 2, 12, 0] {
            for item in previous {
                try await repository.removeAssociation(associationId: item.id, target: context.target, spaceId: context.spaceId)
            }
            let items = associationFixtures(count: count)
            for item in items { _ = try await repository.addAssociation(item, target: context.target, spaceId: context.spaceId) }
            _ = try await session.associationSnapshot(for: context)
            try await Task.sleep(for: .milliseconds(80))
            controller.view.setNeedsLayout()
            controller.view.layoutIfNeeded()
            collection.layoutIfNeeded()
            XCTAssertEqual(collection.bounds.width, 320, "The narrow native editor viewport must stay fixed even if UIWindowScene resizes its window")
            let content = try XCTUnwrap(collection.cellForItem(at: IndexPath(item: 0, section: 0)))
            print("PINKHA_SOURCES_LAYOUT missingNative=\(missingNativeRow) direction=\(direction) count=\(count) height=\(content.bounds.height) configurations=\(configurationCount)")
            XCTAssertGreaterThanOrEqual(content.bounds.height, 44)
            XCTAssertLessThanOrEqual(content.bounds.height, 280)
            XCTAssertEqual(session.visibleDocumentAssociations.count, count)
            XCTAssertEqual(item.hashValue, rowIdentity)
            XCTAssertEqual(dataSource.snapshot().itemIdentifiers, [item])
            XCTAssertEqual(configurationCount, 1)
            XCTAssertEqual(reloadProbe.reconfigureCount, 0, "Source snapshots must update the hosted view without editor reconfiguration")
            XCTAssertEqual(document.children, originalTree)
            let format = UIGraphicsImageRendererFormat()
            format.scale = 1
            let image = UIGraphicsImageRenderer(bounds: collection.bounds, format: format).image { canvas in
                collection.layer.render(in: canvas.cgContext)
            }
            let data = try XCTUnwrap(image.pngData())
            if count > 0, let empty = images[0] { XCTAssertNotEqual(data, empty) }
            if previous.count > 0, let prior = images[previous.count] {
                XCTAssertNotEqual(data, prior, "Each link/unlink count must change the displayed header")
            }
            if count == 0, let originalEmpty = images[0] {
                XCTAssertEqual(data, originalEmpty, "Unlinking the last sources must restore the original empty header")
            }
            images[count] = data
            addScreenshot(image, name: "sources-\(missingNativeRow ? "presentation" : "native")-\(direction)-\(count)")
            previous = items
        }
        session.presentSearch(scope: .block("previous-block"))
        session.presentSearch(scope: .document)
        XCTAssertEqual(session.associationContext.scope, .document)
        XCTAssertTrue(session.isSearchPresented)
    }

    func testDeterministicTorahSearchLayoutEvidence() async throws {
        for presentation in TorahSearchLayoutPresentation.allCases {
            for scope in TorahEditorSession.SearchScope.allCases {
                let image = try await renderHosted(
                    TorahSearchLayoutEvidenceView(
                        presentation: presentation,
                        scope: scope,
                        blockId: nil,
                        associations: associationFixtures(count: 2)
                    ),
                    size: CGSize(width: 768, height: 640),
                    direction: .rightToLeft
                )
                addScreenshot(
                    image,
                    name: "torah-search-\(presentation.rawValue)-\(scope.rawValue)-ipad-rtl"
                )
            }
        }

        let narrowImage = try await renderHosted(
            TorahSearchLayoutEvidenceView(
                presentation: .embedded,
                scope: .references,
                blockId: nil,
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

@MainActor
private final class TorahHeaderReloadProbe: EditorCollectionReloadable {
    private(set) var reconfigureCount = 0
    func reconfigure(items: [EditorItem]) { reconfigureCount += 1 }
    func itemDidChangeFrame(item: EditorItem) { }
    func scrollToItem(_ item: EditorItem) { }
    func scrollToTopBlock(blockId: String) { }
    func scrollToTextViewIfNotVisible(textView: UITextView) { }
    func textBlockDidBeginEditing(firstResponderView: UIView) { }
    func textBlockWillBeginEditing() { }
    func blockDidFinishEditing() { }
}

private struct SearchLayoutData: SearchDataProtocol {
    let id = UUID().uuidString
    let iconImage: Icon?
    let title = ""
    let mode: SerchDataPresentationMode
}

private enum TorahSearchLayoutPresentation: String, CaseIterable {
    case standalone
    case embedded
}

private struct TorahSearchLayoutEvidenceView: View {
    @State private var presenter: TorahSourcesSearchPresenter
    private let presentation: TorahSearchLayoutPresentation

    init(
        presentation: TorahSearchLayoutPresentation,
        scope: TorahEditorSession.SearchScope,
        blockId: String?,
        associations: [TorahAssociationItem]
    ) throws {
        let context = TorahAssociationContext(
            spaceId: "layout-space",
            objectId: "layout-object",
            scope: blockId.map(TorahAssociationContext.Scope.block) ?? .document
        )
        let provider = TorahSearchLayoutProvider()
        let registry = try TorahProviderRegistry(
            referenceProviders: [provider],
            topicProviders: [provider],
            lexicalProviders: [provider],
            defaultProviderID: provider.providerID
        )
        let repository = TorahSearchLayoutRepository(context: context, items: associations)
        let session = TorahEditorSession(
            spaceId: context.spaceId,
            objectId: context.objectId,
            workspace: AnytypeTorahWorkspace(registry: registry),
            associations: repository
        )
        let result = TorahEditorSession.SearchResult(
            id: scope.rawValue,
            scope: scope,
            providerValue: scope.rawValue,
            labelHe: "תוצאה ארוכה בעברית לבדיקת פריסה",
            labelEn: "Long English layout result",
            fallbackTitle: "Layout result",
            fallbackSubtitle: "Secondary metadata"
        )
        self.presentation = presentation
        _presenter = State(initialValue: TorahSourcesSearchPresenter(
            session: session,
            context: context,
            searchScope: scope,
            searchQuery: "בדיקה",
            searchState: .results([result]),
            associations: associations,
            persistenceState: .saved,
            onOpenSelection: { _ in }
        ))
    }

    var body: some View {
        Group {
            switch presentation {
            case .standalone:
                SearchViewShell(
                    title: TorahSourcesSearchCopy.contextTitle(
                        blockId: presenter.associationTargetBlockID
                    ),
                    placeholder: Loc.Pinkha.Torah.searchPlaceholder,
                    searchText: $presenter.searchQuery
                ) {
                    productionContent(showsSearchBar: false)
                }
            case .embedded:
                productionContent(showsSearchBar: true)
            }
        }
        .background(Color.Background.secondary)
    }

    private func productionContent(showsSearchBar: Bool) -> some View {
        TorahSourcesSearchContentView(
            presenter: presenter,
            showsSearchBar: showsSearchBar,
            accessibilityIdentifier: "torah-search-layout-evidence"
        )
    }
}

private struct TorahSearchLayoutProvider: ReferenceProvider, TopicProvider, LexicalProvider {
    let providerID = "layout-provider"

    func suggestReferences(query: String, limit: Int) async throws -> [ReferenceCandidate] {
        [ReferenceCandidate(id: query, label: "תוצאה ארוכה בעברית לבדיקת פריסה")]
    }

    func resolveReference(_ input: String) async throws -> ResolvedReference {
        ResolvedReference(canonical: input, labelHe: input)
    }

    func suggestTopics(query: String, limit: Int) async throws -> [TopicCandidate] {
        [TopicCandidate(id: query, displayTitle: "תוצאה ארוכה בעברית לבדיקת פריסה")]
    }

    func resolveTopic(id: String) async throws -> ResolvedTopic {
        ResolvedTopic(slug: id, displayTitle: id)
    }

    func refreshTopicIndexIfNeeded() async throws {}

    func suggestWords(prefix: String, context: TorahLexicalContext?) async throws -> [WordCandidate] {
        [WordCandidate(id: prefix, surface: prefix, headword: prefix, lexicon: "fixture")]
    }

    func resolveWord(surface: String, context: TorahLexicalContext?) async throws -> [ResolvedWord] {
        [ResolvedWord(candidate: try await suggestWords(prefix: surface, context: context)[0])]
    }
}

private actor TorahSearchLayoutRepository: AnytypeTorahAssociationSnapshotRepository {
    private var records: [TorahStoredAssociationRecord]

    init(context: TorahAssociationContext, items: [TorahAssociationItem]) {
        records = items.map {
            TorahStoredAssociationRecord(
                location: TorahAssociationLocation(spaceId: context.spaceId, target: context.target),
                item: $0
            )
        }
    }

    func listAssociationRecords(objectId: String, spaceId: String) async throws -> [TorahStoredAssociationRecord] {
        records
    }

    func listDocumentAssociations(objectId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        records.filter { $0.blockId == nil }.map(\.item)
    }

    func listBlockAssociations(objectId: String, blockId: String, spaceId: String) async throws -> [TorahAssociationItem] {
        records.filter { $0.blockId == blockId }.map(\.item)
    }

    func addAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        records.append(TorahStoredAssociationRecord(
            location: TorahAssociationLocation(spaceId: spaceId, target: target),
            item: item
        ))
        return item
    }

    func upsertAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        records.removeAll { $0.item.id == item.id }
        return try await addAssociation(item, target: target, spaceId: spaceId)
    }

    func updateAssociation(_ item: TorahAssociationItem, target: TorahAssociationTarget, spaceId: String) async throws -> TorahAssociationItem {
        try await upsertAssociation(item, target: target, spaceId: spaceId)
    }

    func removeAssociation(associationId: String, target: TorahAssociationTarget, spaceId: String) async throws {
        records.removeAll { $0.item.id == associationId }
    }
}

@MainActor
private func renderHosted<Content: View>(
    _ content: Content,
    size: CGSize,
    direction: LayoutDirection
) async throws -> UIImage {
    let controller = UIHostingController(
        rootView: content
            .environment(\.layoutDirection, direction)
            .environment(\.locale, Locale(identifier: direction == .rightToLeft ? "he" : "en"))
    )
    let scene = try XCTUnwrap(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
    let previousKeyWindow = scene.windows.first(where: \.isKeyWindow)
    let window = UIWindow(windowScene: scene)
    let container = TorahScreenshotContainer()
    container.addChild(controller)
    container.view.addSubview(controller.view)
    controller.view.frame = CGRect(origin: .zero, size: size)
    controller.view.autoresizingMask = []
    controller.didMove(toParent: container)
    window.rootViewController = container
    window.makeKeyAndVisible()
    defer {
        controller.willMove(toParent: nil)
        controller.view.removeFromSuperview()
        controller.removeFromParent()
        window.isHidden = true
        window.rootViewController = nil
        previousKeyWindow?.makeKey()
    }
    let appearance = await XCTWaiter.fulfillment(of: [container.appeared], timeout: 5)
    XCTAssertEqual(appearance, .completed, "Do not carry unfinished hosting-controller transitions into the next test")
    controller.view.setNeedsLayout()
    controller.view.layoutIfNeeded()
    XCTAssertTrue(controller.view.window === window)
    XCTAssertEqual(controller.view.bounds.size, size)

    let renderer = UIGraphicsImageRenderer(size: size)
    let image = renderer.image { context in
        controller.view.layer.render(in: context.cgContext)
    }
    return image
}

@MainActor
private final class TorahScreenshotContainer: UIViewController {
    let appeared = XCTestExpectation(description: "Native screenshot container appeared")

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        appeared.fulfill()
    }
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

private func opaqueContentBounds(
    _ image: CGImage,
    scanning scanRect: CGRect? = nil
) throws -> CGRect {
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
    let scanRect = (scanRect ?? CGRect(x: 0, y: 2, width: width, height: height - 4))
        .intersection(CGRect(x: 0, y: 0, width: width, height: height))
        .integral
    let minScanX = max(0, Int(scanRect.minX))
    let maxScanX = min(width, Int(scanRect.maxX))
    let minScanY = max(0, Int(scanRect.minY))
    let maxScanY = min(height, Int(scanRect.maxY))
    for y in minScanY..<maxScanY {
        for x in minScanX..<maxScanX where pixels[(y * bytesPerRow) + (x * 4) + 3] > 8 {
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

private func subviews<ViewType: UIView>(
    of type: ViewType.Type,
    in root: UIView
) -> [ViewType] {
    var matches = root is ViewType ? [root as! ViewType] : []
    for subview in root.subviews {
        matches.append(contentsOf: subviews(of: type, in: subview))
    }
    return matches
}

private enum TorahSearchLayoutTestError: Error {
    case couldNotReadPixels
    case noOpaquePixels
}
