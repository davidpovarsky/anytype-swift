import PinkhaKit
import Services
import Testing
import UIKit
@testable import Anytype

@MainActor
@Suite("Torah native UI parity")
struct TorahNativeUIParityTests {

    @Test("Block ornament is a compact glyph with a deterministic transparent hit target")
    func compactBlockOrnamentGeometry() {
        let button = TorahBlockAccessoryButton()
        button.frame = CGRect(origin: .zero, size: TorahBlockAccessoryButton.hitTargetSize)
        button.layoutIfNeeded()

        #expect(button.intrinsicContentSize == CGSize(width: 44, height: 44))
        #expect(button.iconView.bounds.size == CGSize(width: 20, height: 20))
        #expect(button.backgroundColor == .clear)
    }

    @Test("Block ornament clears action and accessibility state on reuse")
    func blockOrnamentReuse() {
        let contentView = TextBlockContentView()
        var invocationCount = 0
        contentView.updateTorahAccessory(
            TorahBlockAccessoryConfiguration(
                accessibilityLabel: "Open Torah source",
                accessibilityValue: "10",
                accessibilityIdentifier: "torah-linked-source-block-a",
                action: { invocationCount += 1 }
            )
        )

        #expect(!contentView.torahAccessoryButton.isHidden)
        #expect(contentView.torahAccessoryButton.accessibilityValue == "10")
        contentView.torahAccessoryButton.sendActions(for: .touchUpInside)
        #expect(invocationCount == 1)

        contentView.updateTorahAccessory(nil)
        #expect(contentView.torahAccessoryButton.isHidden)
        #expect(contentView.torahAccessoryButton.accessibilityLabel == nil)
        #expect(contentView.torahAccessoryButton.accessibilityValue == nil)
        #expect(contentView.torahAccessoryButton.accessibilityIdentifier == nil)
        contentView.torahAccessoryButton.sendActions(for: .touchUpInside)
        #expect(invocationCount == 1)
    }

    @Test("Navigation placement is exclusive across availability and editor modes")
    func navigationPlacementIsExclusive() {
        #expect(EditorTorahNavigationPlacement.resolve(
            isAvailable: false,
            allowsEntry: true,
            fitsInline: true
        ) == .hidden)
        #expect(EditorTorahNavigationPlacement.resolve(
            isAvailable: true,
            allowsEntry: false,
            fitsInline: true
        ) == .hidden)
        #expect(EditorTorahNavigationPlacement.resolve(
            isAvailable: true,
            allowsEntry: true,
            fitsInline: true
        ) == .bar)
        #expect(EditorTorahNavigationPlacement.resolve(
            isAvailable: true,
            allowsEntry: true,
            fitsInline: false
        ) == .overflow)
    }

    @Test("Measured fit keeps a readable title before admitting the third control")
    func navigationFitUsesMeasuredWidths() {
        let rightWidth = EditorNavigationBarEditingControls.requiredWidth(
            controlWidths: [44, 44, 44]
        )
        #expect(rightWidth == 148)
        #expect(EditorNavigationBarFit.canFit(
            contentWidth: 408,
            leftButtonWidth: 44,
            titleWidth: 200,
            rightButtonWidth: rightWidth,
            titleSpacing: 8
        ))
        #expect(!EditorNavigationBarFit.canFit(
            contentWidth: 407,
            leftButtonWidth: 44,
            titleWidth: 200,
            rightButtonWidth: rightWidth,
            titleSpacing: 8
        ))
    }

    @Test("Book remains physically between settings and sync in RTL")
    func rtlControlOrder() {
        let sync = fixedControl()
        let book = fixedControl()
        let settings = fixedControl()
        let stack = EditorNavigationBarEditingControls.makeStack(
            syncStatus: sync,
            torahSources: book,
            settings: settings
        )
        stack.semanticContentAttribute = .forceRightToLeft
        stack.frame = CGRect(x: 0, y: 0, width: 148, height: 44)
        stack.layoutIfNeeded()

        let physicalOrder = stack.arrangedSubviews.sorted { $0.frame.minX < $1.frame.minX }
        #expect(physicalOrder[0] === settings)
        #expect(physicalOrder[1] === book)
        #expect(physicalOrder[2] === sync)
    }

    @Test("Navigation action resolves the active document at invocation time")
    func navigationActionUsesCurrentDocument() {
        var activeDocument = "document-a"
        var dispatchedDocuments = [String]()
        let state = EditorTorahNavigationState(isAvailable: true) {
            dispatchedDocuments.append(activeDocument)
        }
        state.update(allowsEntry: true, fitsInline: true)

        state.performAction()
        activeDocument = "document-b"
        state.performAction()

        #expect(dispatchedDocuments == ["document-a", "document-b"])
        #expect(!state.showsOverflowAction)

        state.update(allowsEntry: true, fitsInline: false)
        #expect(state.showsOverflowAction)
    }

    @Test("Document header bounds chips and keeps every remaining source reachable", arguments: [0, 1, 2, 3, 12])
    func boundedDocumentSources(count: Int) {
        let associations = (0..<count).map { index in
            TorahAssociationItem(
                id: "source-\(index)",
                kind: .ref,
                role: .context,
                providerID: "sefaria",
                externalID: "Genesis 1:\(index + 1)",
                canonicalKey: "Genesis 1:\(index + 1)",
                labelHe: "בראשית א"
            )
        }
        let presentation = PinkhaDocumentSourcesPresentation(associations: associations)

        #expect(presentation.visibleAssociations.map(\.id) == Array(associations.prefix(2)).map(\.id))
        #expect(presentation.remainingCount == max(0, count - 2))
        #expect(presentation.remainingAssociations.map(\.id) == Array(associations.dropFirst(2)).map(\.id))
        #expect(presentation.visibleAssociations.count + presentation.remainingCount == count)
    }

    private func fixedControl() -> UIView {
        let view = UIView()
        view.widthAnchor.constraint(equalToConstant: 44).isActive = true
        view.heightAnchor.constraint(equalToConstant: 44).isActive = true
        return view
    }

    @Test("Missing native metadata gets one stable system row; a native row suppresses it")
    func metadataPresentationPlacement() throws {
        #expect(PinkhaDocumentMetadataRowModel.insertionIndex(in: []) == 0)
        let document = MockBaseDocument(objectId: "metadata-document")
        let nativeInfo = BlockInformation.empty(id: "featuredRelations", content: .featuredRelations)
        let native = FeaturedPropertiesBlockViewModel(
            infoProvider: BlockModelInfomationProvider(document: document, info: nativeInfo),
            document: document,
            collectionController: MetadataReloadProbe(),
            onRelationValueTap: { _ in }
        )
        #expect(PinkhaDocumentMetadataRowModel.insertionIndex(in: [.block(native)]) == nil)
    }

    @Test("Policy blocks canonical storage while allowing legitimate user properties")
    func policyCanonicalStorageDistinction() {
        let manifest = PinkhaSpaceManifest(
            spaceId: "space-1",
            documentAssociationsPropertyId: "canonical-prop-id",
            documentAssociationsPropertyKey: "canonical-prop-key",
            registeredDocumentTypes: [
                "chiddush": "type-chiddush",
                "article": "type-article",
                "research": "type-research"
            ]
        )
        let probe = PolicyBootstrapProbe(manifest: manifest)
        let policy = PinkhaTorahPropertyPolicy(bootstrapService: probe)

        // H01, H02: Canonical storage is recognized and blocked from generic editing
        #expect(policy.isCanonicalStorage(propertyId: "canonical-prop-id", key: "other-key", spaceId: "space-1"))
        #expect(policy.isCanonicalStorage(propertyId: "other-id", key: "canonical-prop-key", spaceId: "space-1"))
        #expect(!policy.canEditGenericPropertyValue(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space-1"))
        #expect(!policy.shouldRenderInHeader(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space-1"))
        #expect(!policy.canEditPropertyDefinition(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space-1"))
        #expect(!policy.canDeletePropertyDefinition(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space-1"))

        // H03: A user-made property has the same Hebrew display name "הקשר תורני" but DIFFERENT ID/key:
        // must not be falsely hidden or blocked
        let userPropId = "user-custom-id"
        let userPropKey = "userCustomKey"
        #expect(!policy.isCanonicalStorage(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))
        #expect(policy.canEditGenericPropertyValue(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))
        #expect(policy.shouldRenderInHeader(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))
        #expect(policy.canEditPropertyDefinition(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))

        // H04: Wrong space does not match canonical property
        #expect(!policy.isCanonicalStorage(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "wrong-space"))

        // H01, H17: Target eligibility: Writing types eligible, ordinary Note is NOT eligible
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-chiddush", spaceId: "space-1"))
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-article", spaceId: "space-1"))
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-research", spaceId: "space-1"))
        #expect(!policy.isTargetEligibleForNativeProperties(typeId: "note", spaceId: "space-1"))
        #expect(!policy.isTargetEligibleForNativeProperties(typeId: "page", spaceId: "space-1"))
    }

    @Test("Canonical identity resolution handles tri-state loading, known settlement, and fail-closed gate")
    func canonicalIdentityResolutionTriState() async {
        final class DelayBootstrapProbe: PinkhaSpaceBootstrapServiceProtocol, @unchecked Sendable {
            var manifestToReturn: PinkhaSpaceManifest?
            var bootstrapCallCount = 0
            private let lock = NSLock()

            init(manifest: PinkhaSpaceManifest?) {
                self.manifestToReturn = manifest
            }

            func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? {
                lock.lock()
                defer { lock.unlock() }
                return manifestToReturn
            }

            func bootstrapCanonicalSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
                lock.lock()
                bootstrapCallCount += 1
                let m = manifestToReturn
                lock.unlock()
                if let m {
                    return m
                }
                throw PinkhaBootstrapError.invalidManifest("Manifest not ready")
            }

            func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest {
                try await bootstrapCanonicalSpace(spaceId: spaceId)
            }

            func isBootstrapped(spaceId: String) -> Bool {
                manifest(forSpaceId: spaceId) != nil
            }
        }

        let settledManifest = PinkhaSpaceManifest(
            spaceId: "space-cold",
            documentAssociationsPropertyId: "canon-cold-id",
            documentAssociationsPropertyKey: "canon-cold-key",
            registeredDocumentTypes: [
                "chiddush": "type-chiddush",
                "article": "type-article",
                "research": "type-research"
            ]
        )

        // Case 1: Manifest absent initially -> status is loading / unavailable, actions fail closed
        let coldProbe = DelayBootstrapProbe(manifest: nil)
        let coldPolicy = PinkhaTorahPropertyPolicy(bootstrapService: coldProbe)

        // While unready: canEditGenericPropertyValue returns false (fail closed! does not leak editable text)
        #expect(!coldPolicy.canEditGenericPropertyValue(propertyId: "any-prop", key: "any-key", spaceId: "space-cold"))
        #expect(!coldPolicy.canEditPropertyDefinition(propertyId: "any-prop", key: "any-key", spaceId: "space-cold"))
        #expect(!coldPolicy.canDeletePropertyDefinition(propertyId: "any-prop", key: "any-key", spaceId: "space-cold"))

        // Case 2: Manifest resolves -> status settles to .known
        coldProbe.manifestToReturn = settledManifest
        coldPolicy.invalidateCache(spaceId: "space-cold")

        let settledStatus = await coldPolicy.awaitCanonicalIdentity(spaceId: "space-cold")
        #expect(settledStatus == .known(propertyId: "canon-cold-id", propertyKey: "canon-cold-key"))

        // Now canonical property is strictly blocked, but user property is allowed!
        #expect(!coldPolicy.canEditGenericPropertyValue(propertyId: "canon-cold-id", key: "canon-cold-key", spaceId: "space-cold"))
        #expect(coldPolicy.canEditGenericPropertyValue(propertyId: "user-id", key: "user-key", spaceId: "space-cold"))
        #expect(coldPolicy.canEditPropertyDefinition(propertyId: "user-id", key: "user-key", spaceId: "space-cold"))
        #expect(coldPolicy.canDeletePropertyDefinition(propertyId: "user-id", key: "user-key", spaceId: "space-cold"))

        // Native derived property definitions cannot be renamed or deleted
        for def in TorahNativePropertyDefinition.all {
            #expect(!coldPolicy.canEditPropertyDefinition(propertyId: "native-id", key: def.key, spaceId: "space-cold"))
            #expect(!coldPolicy.canDeletePropertyDefinition(propertyId: "native-id", key: def.key, spaceId: "space-cold"))
        }

        // Space switch / cache invalidation test
        coldPolicy.invalidateCache(spaceId: "space-cold")
        #expect(coldPolicy.canonicalIdentityStatus(spaceId: "space-cold") == .known(propertyId: "canon-cold-id", propertyKey: "canon-cold-key"))
    }
}

private struct PolicyBootstrapProbe: PinkhaSpaceBootstrapServiceProtocol {
    let manifest: PinkhaSpaceManifest

    func bootstrapSpace(spaceId: String) async throws -> PinkhaSpaceManifest { manifest }
    func bootstrapCanonicalSpace(spaceId: String) async throws -> PinkhaSpaceManifest { manifest }
    func manifest(forSpaceId spaceId: String) -> PinkhaSpaceManifest? {
        manifest.spaceId == spaceId ? manifest : nil
    }
    func isBootstrapped(spaceId: String) -> Bool { manifest.spaceId == spaceId }
}

@MainActor
private final class MetadataReloadProbe: EditorCollectionReloadable {
    func reconfigure(items: [EditorItem]) { }
    func itemDidChangeFrame(item: EditorItem) { }
    func scrollToItem(_ item: EditorItem) { }
    func scrollToTopBlock(blockId: String) { }
    func scrollToTextViewIfNotVisible(textView: UITextView) { }
    func textBlockDidBeginEditing(firstResponderView: UIView) { }
    func textBlockWillBeginEditing() { }
    func blockDidFinishEditing() { }
}
