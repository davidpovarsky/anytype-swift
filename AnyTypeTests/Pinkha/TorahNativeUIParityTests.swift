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

    @Test("Measured fit calculates 2-control toolbar width accurately")
    func navigationFitUsesMeasuredWidths() {
        let rightWidth = EditorNavigationBarEditingControls.requiredWidth(
            controlWidths: [44, 44]
        )
        #expect(rightWidth == 96)
        #expect(EditorNavigationBarFit.canFit(
            contentWidth: 356,
            leftButtonWidth: 44,
            titleWidth: 200,
            rightButtonWidth: rightWidth,
            titleSpacing: 8
        ))
        #expect(!EditorNavigationBarFit.canFit(
            contentWidth: 355,
            leftButtonWidth: 44,
            titleWidth: 200,
            rightButtonWidth: rightWidth,
            titleSpacing: 8
        ))
    }

    @Test("Settings and sync are physically ordered in RTL with no redundant book icon")
    func rtlControlOrder() {
        let sync = fixedControl()
        let settings = fixedControl()
        let stack = EditorNavigationBarEditingControls.makeStack(
            syncStatus: sync,
            settings: settings
        )
        stack.semanticContentAttribute = .forceRightToLeft
        stack.frame = CGRect(x: 0, y: 0, width: 96, height: 44)
        stack.layoutIfNeeded()

        let physicalOrder = stack.arrangedSubviews.sorted { $0.frame.minX < $1.frame.minX }
        #expect(physicalOrder[0] === settings)
        #expect(physicalOrder[1] === sync)
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
        let presentation = PinkhaDocumentSourcesPresentation(associations: associations, canEdit: true)

        #expect(presentation.visibleAssociations.map(\.id) == Array(associations.prefix(2)).map(\.id))
        #expect(presentation.remainingCount == max(0, count - 2))
        #expect(presentation.remainingAssociations.map(\.id) == Array(associations.dropFirst(2)).map(\.id))
        #expect(presentation.visibleAssociations.count + presentation.remainingCount == count)
        #expect(presentation.showsEmptyPlaceholderAdd == (count == 0))
        #expect(presentation.showsCompactAdjacentAdd == (count > 0))
        #expect(presentation.showsOverflowMenu == (count > 2))
        #expect(presentation.hasAnyAddControl == true)

        let readOnlyPresentation = PinkhaDocumentSourcesPresentation(associations: associations, canEdit: false)
        #expect(!readOnlyPresentation.showsEmptyPlaceholderAdd)
        #expect(!readOnlyPresentation.showsCompactAdjacentAdd)
        #expect(!readOnlyPresentation.hasAnyAddControl)
        #expect(readOnlyPresentation.showsOverflowMenu == (count > 2))
    }

    @Test("Compact source-chip + control keeps visual pill compact while expanding hit target to >= 44x44")
    func compactSourceAddButtonGeometry() {
        #expect(PinkhaDocumentSourcesPresentation.compactAddVisualSize == CGSize(width: 22, height: 18))
        #expect(PinkhaDocumentSourcesPresentation.compactAddLayoutSize == CGSize(width: 22, height: 26))
        let hitWidth = PinkhaDocumentSourcesPresentation.compactAddLayoutSize.width
            - PinkhaDocumentSourcesPresentation.compactAddHitTestingInsets.leading
            - PinkhaDocumentSourcesPresentation.compactAddHitTestingInsets.trailing
        let hitHeight = PinkhaDocumentSourcesPresentation.compactAddLayoutSize.height
            - PinkhaDocumentSourcesPresentation.compactAddHitTestingInsets.top
            - PinkhaDocumentSourcesPresentation.compactAddHitTestingInsets.bottom
        #expect(hitWidth >= 44)
        #expect(hitHeight >= 44)
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

    @Test("Policy blocks both canonical storage and internal סדר order storage while allowing user properties and הורה")
    func policyCanonicalAndOrderStorageDistinction() {
        let manifest = PinkhaSpaceManifest(
            spaceId: "space-1",
            parentPropertyId: "parent-prop-id",
            parentPropertyKey: "parent-prop-key",
            orderPropertyId: "order-prop-id",
            orderPropertyKey: "order-prop-key",
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

        // Canonical storage is recognized and blocked from generic editing, header, picker, rename, delete
        #expect(policy.isCanonicalStorage(propertyId: "canonical-prop-id", key: "other-key", spaceId: "space-1"))
        #expect(policy.isCanonicalStorage(propertyId: "other-id", key: "canonical-prop-key", spaceId: "space-1"))
        #expect(policy.isInternalProperty(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space-1"))
        #expect(!policy.canEditGenericPropertyValue(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space-1"))
        #expect(!policy.shouldRenderInHeader(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space-1"))
        #expect(!policy.canEditPropertyDefinition(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space-1"))
        #expect(!policy.canDeletePropertyDefinition(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "space-1"))

        // Order storage (סדר) is recognized as internal and blocked from generic editing, header, picker, rename, delete,
        // while preserving canonical-only routing distinction (isCanonicalStorage == false for סדר)
        #expect(policy.isOrderStorage(propertyId: "order-prop-id", key: "other-key", spaceId: "space-1"))
        #expect(policy.isOrderStorage(propertyId: "other-id", key: "order-prop-key", spaceId: "space-1"))
        #expect(policy.isInternalProperty(propertyId: "order-prop-id", key: "other-key", spaceId: "space-1"))
        #expect(policy.isInternalProperty(propertyId: "other-id", key: "order-prop-key", spaceId: "space-1"))
        #expect(!policy.isCanonicalStorage(propertyId: "order-prop-id", key: "order-prop-key", spaceId: "space-1"))
        #expect(!policy.canEditGenericPropertyValue(propertyId: "order-prop-id", key: "order-prop-key", spaceId: "space-1"))
        #expect(!policy.shouldRenderInHeader(propertyId: "order-prop-id", key: "order-prop-key", spaceId: "space-1"))
        #expect(!policy.canEditPropertyDefinition(propertyId: "order-prop-id", key: "order-prop-key", spaceId: "space-1"))
        #expect(!policy.canDeletePropertyDefinition(propertyId: "order-prop-id", key: "order-prop-key", spaceId: "space-1"))
        #expect(!policy.shouldDisplayInPicker(propertyId: "order-prop-id", key: "order-prop-key", target: .library, spaceId: "space-1"))

        // User-visible hierarchy field הורה (parentPropertyId) must NOT be hidden as internal
        #expect(!policy.isInternalProperty(propertyId: "parent-prop-id", key: "parent-prop-key", spaceId: "space-1"))
        #expect(policy.shouldRenderInHeader(propertyId: "parent-prop-id", key: "parent-prop-key", spaceId: "space-1"))

        // User-made properties with the same Hebrew display names "הקשר תורני" or "סדר" but DIFFERENT IDs/keys
        // must not be falsely hidden or blocked
        let userPropId = "user-custom-id"
        let userPropKey = "userCustomKey"
        #expect(!policy.isCanonicalStorage(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))
        #expect(!policy.isOrderStorage(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))
        #expect(!policy.isInternalProperty(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))
        #expect(policy.canEditGenericPropertyValue(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))
        #expect(policy.shouldRenderInHeader(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))
        #expect(policy.canEditPropertyDefinition(propertyId: userPropId, key: userPropKey, spaceId: "space-1"))

        // Wrong space does not match internal properties
        #expect(!policy.isCanonicalStorage(propertyId: "canonical-prop-id", key: "canonical-prop-key", spaceId: "wrong-space"))
        #expect(!policy.isOrderStorage(propertyId: "order-prop-id", key: "order-prop-key", spaceId: "wrong-space"))
        #expect(!policy.isInternalProperty(propertyId: "order-prop-id", key: "order-prop-key", spaceId: "wrong-space"))

        // Native definitions are available to every normal document Type.
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-chiddush", spaceId: "space-1"))
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-article", spaceId: "space-1"))
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-research", spaceId: "space-1"))
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "note", spaceId: "space-1"))
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "page", spaceId: "space-1"))

        // Dataview eligibility: single writing Type or writing-only filteredSetOf is eligible;
        // Page/Note Set or mixed Set (Chiddush + Page) is NOT eligible
        #expect(policy.isDataviewEligible(typeDetails: nil, filteredSetOf: ["type-chiddush"], spaceId: "space-1"))
        #expect(policy.isDataviewEligible(typeDetails: nil, filteredSetOf: ["type-chiddush", "type-article", "type-research"], spaceId: "space-1"))
        #expect(policy.isDataviewEligible(typeDetails: nil, filteredSetOf: ["page"], spaceId: "space-1"))
        #expect(policy.isDataviewEligible(typeDetails: nil, filteredSetOf: ["type-chiddush", "page"], spaceId: "space-1"))
        #expect(policy.isDataviewEligible(typeDetails: nil, filteredSetOf: [], spaceId: "space-1"))
    }

    @Test("Internal identity resolution handles tri-state loading, failure retry, and known settlement without hiding user properties permanently")
    func internalIdentityResolutionTriStateAndRecovery() async {
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
            orderPropertyId: "order-cold-id",
            orderPropertyKey: "order-cold-key",
            documentAssociationsPropertyId: "canon-cold-id",
            documentAssociationsPropertyKey: "canon-cold-key",
            registeredDocumentTypes: [
                "chiddush": "type-chiddush",
                "article": "type-article",
                "research": "type-research"
            ]
        )

        let coldProbe = DelayBootstrapProbe(manifest: nil)
        let coldPolicy = PinkhaTorahPropertyPolicy(bootstrapService: coldProbe)

        // While unready: actions fail closed
        #expect(!coldPolicy.canEditGenericPropertyValue(propertyId: "any-prop", key: "any-key", spaceId: "space-cold"))
        #expect(!coldPolicy.canEditPropertyDefinition(propertyId: "any-prop", key: "any-key", spaceId: "space-cold"))
        #expect(!coldPolicy.canDeletePropertyDefinition(propertyId: "any-prop", key: "any-key", spaceId: "space-cold"))

        // Await failure -> status becomes .unavailable (not stuck in .loading forever)
        let failedStatus = await coldPolicy.awaitInternalIdentity(spaceId: "space-cold")
        if case .unavailable = failedStatus {
            // Expected
        } else {
            Issue.record("Expected .unavailable when manifest fails to load, got \(failedStatus)")
        }

        // Manifest becomes available -> awaiting again automatically retries and settles to .known
        coldProbe.manifestToReturn = settledManifest
        let settledStatus = await coldPolicy.awaitInternalIdentity(spaceId: "space-cold")
        #expect(settledStatus == .known(PinkhaInternalPropertyIdentities(
            canonicalPropertyId: "canon-cold-id",
            canonicalPropertyKey: "canon-cold-key",
            orderPropertyId: "order-cold-id",
            orderPropertyKey: "order-cold-key"
        )))

        // Both canonical and order properties are strictly blocked, while user properties are allowed
        #expect(!coldPolicy.canEditGenericPropertyValue(propertyId: "canon-cold-id", key: "canon-cold-key", spaceId: "space-cold"))
        #expect(!coldPolicy.canEditGenericPropertyValue(propertyId: "order-cold-id", key: "order-cold-key", spaceId: "space-cold"))
        #expect(coldPolicy.canEditGenericPropertyValue(propertyId: "user-id", key: "user-key", spaceId: "space-cold"))
        #expect(coldPolicy.canEditPropertyDefinition(propertyId: "user-id", key: "user-key", spaceId: "space-cold"))
        #expect(coldPolicy.canDeletePropertyDefinition(propertyId: "user-id", key: "user-key", spaceId: "space-cold"))

        for def in TorahNativePropertyDefinition.all {
            #expect(!coldPolicy.canEditPropertyDefinition(propertyId: "native-id", key: def.key, spaceId: "space-cold"))
            #expect(!coldPolicy.canDeletePropertyDefinition(propertyId: "native-id", key: def.key, spaceId: "space-cold"))
        }
    }

    @Test("Native property catalog matches empty search, Hebrew variants, and English variants while enforcing strict identity guards")
    func nativeCatalogSearchAndIdentityGuards() {
        let spaceId = "space-catalog"
        for def in TorahNativePropertyDefinition.all {
            let valid = PropertyDetails(
                id: "id-\(def.key)",
                key: def.key,
                name: def.name,
                format: .tag,
                isHidden: false,
                isReadOnly: false,
                isReadOnlyValue: true,
                objectTypes: [],
                maxCount: 0,
                sourceObject: "_br" + def.key,
                isDeleted: false,
                spaceId: spaceId
            )
            #expect(PinkhaTorahNativePropertyCatalog.isVerifiedNativeDescriptor(valid, definition: def, spaceId: spaceId))
            #expect(PinkhaTorahNativePropertyCatalog.matchesSearchQuery(property: valid, query: ""))
            #expect(PinkhaTorahNativePropertyCatalog.matchesSearchQuery(property: valid, query: def.name))
            #expect(PinkhaTorahNativePropertyCatalog.matchesSearchQuery(property: valid, query: def.englishName))
            #expect(PinkhaTorahNativePropertyCatalog.matchesSearchQuery(property: valid, query: def.key))

            // Forged/invalid descriptors are rejected by identity guard
            let editableFake = PropertyDetails(
                id: "fake-\(def.key)",
                key: def.key,
                name: def.name,
                format: .tag,
                isHidden: false,
                isReadOnly: false,
                isReadOnlyValue: false,
                objectTypes: [],
                maxCount: 0,
                sourceObject: "_br" + def.key,
                isDeleted: false,
                spaceId: spaceId
            )
            #expect(!PinkhaTorahNativePropertyCatalog.isVerifiedNativeDescriptor(editableFake, definition: def, spaceId: spaceId))
        }

        let sourcesProp = PropertyDetails(
            id: "id-sources",
            key: TorahNativePropertyDefinition.all[0].key,
            name: "מקור/ות",
            format: .tag,
            isHidden: false,
            isReadOnly: false,
            isReadOnlyValue: true,
            objectTypes: [],
            maxCount: 0,
            sourceObject: "_brpinkhaTorahSources",
            isDeleted: false,
            spaceId: spaceId
        )
        for query in ["מקור/ות", "מקורות", "מקור", "Source(s)", "Sources", "Source"] {
            #expect(PinkhaTorahNativePropertyCatalog.matchesSearchQuery(property: sourcesProp, query: query))
        }

        let topicsProp = PropertyDetails(
            id: "id-topics",
            key: TorahNativePropertyDefinition.all[1].key,
            name: "נושא",
            format: .tag,
            isHidden: false,
            isReadOnly: false,
            isReadOnlyValue: true,
            objectTypes: [],
            maxCount: 0,
            sourceObject: "_brpinkhaTorahTopics",
            isDeleted: false,
            spaceId: spaceId
        )
        for query in ["נושא", "נושאים", "Topic(s)", "Topics", "Topic"] {
            #expect(PinkhaTorahNativePropertyCatalog.matchesSearchQuery(property: topicsProp, query: query))
        }

        let wordsProp = PropertyDetails(
            id: "id-words",
            key: TorahNativePropertyDefinition.all[2].key,
            name: "מילה / ערך",
            format: .tag,
            isHidden: false,
            isReadOnly: false,
            isReadOnlyValue: true,
            objectTypes: [],
            maxCount: 0,
            sourceObject: "_brpinkhaTorahWords",
            isDeleted: false,
            spaceId: spaceId
        )
        for query in ["מילה / ערך", "מילה", "ערך", "מילים", "ערכים", "Word / entry", "Words", "Entry", "Entries"] {
            #expect(PinkhaTorahNativePropertyCatalog.matchesSearchQuery(property: wordsProp, query: query))
        }
    }

    @Test("Fresh eligible document renders native Torah property rows as editable by the canonical Torah picker even before associations exist")
    func freshDocumentNativeRowIsEditableByCanonicalPicker() {
        let def = TorahNativePropertyDefinition.all[0]
        let propDetails = PropertyDetails(
            id: "native-sources-id",
            key: def.key,
            name: def.name,
            format: .tag,
            isHidden: false,
            isReadOnly: false,
            isReadOnlyValue: true,
            objectTypes: [],
            maxCount: 0,
            sourceObject: "_br" + def.key,
            isDeleted: false,
            spaceId: "space-fresh"
        )
        let freshDocDetails = ObjectDetails(id: "fresh-chiddush-doc")
        guard case .tag(let rendered) = TorahNativePropertyPresentation.property(
            definition: propDetails,
            details: freshDocDetails,
            isFeatured: false,
            valuesLocked: false
        ) else {
            Issue.record("Expected native .tag property row for fresh document")
            return
        }
        #expect(rendered.isEditable == true)
        #expect(rendered.selectedTags.isEmpty)

        guard case .tag(let lockedRendered) = TorahNativePropertyPresentation.property(
            definition: propDetails,
            details: freshDocDetails,
            isFeatured: false,
            valuesLocked: true
        ) else {
            Issue.record("Expected native .tag property row when locked")
            return
        }
        #expect(lockedRendered.isEditable == false)
    }

    @Test("Type availability includes Page, Note and custom Types")
    func headerVisibilityReactiveToTypeEligibility() {
        let manifest = PinkhaSpaceManifest(
            spaceId: "space-reactive",
            documentAssociationsPropertyId: "canon-id",
            documentAssociationsPropertyKey: "canon-key",
            registeredDocumentTypes: [
                "chiddush": "type-chiddush",
                "article": "type-article",
                "research": "type-research"
            ]
        )
        let probe = PolicyBootstrapProbe(manifest: manifest)
        let policy = PinkhaTorahPropertyPolicy(bootstrapService: probe)

        // Writing types are strictly eligible
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-chiddush", spaceId: "space-reactive"))
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-article", spaceId: "space-reactive"))
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-research", spaceId: "space-reactive"))

        // Note and Page are eligible without being registered writing Types.
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-note", spaceId: "space-reactive"))
        #expect(policy.isTargetEligibleForNativeProperties(typeId: "type-page", spaceId: "space-reactive"))
        #expect(!policy.isTargetEligibleForNativeProperties(typeId: "", spaceId: "space-reactive"))
        #expect(!policy.isTargetEligibleForNativeProperties(typeId: "type-chiddush", spaceId: "wrong-space"))

        // Canonical storage check does not depend on type eligibility:
        // Canonical data is ALWAYS protected and NEVER erased
        #expect(policy.isCanonicalStorage(propertyId: "canon-id", key: "canon-key", spaceId: "space-reactive"))
    }

    @Test("Presentation hides permanent add label when one or more sources exist and exposes compact adjacent + control (Defect C)")
    func presentationSourcesNoPermanentAddLabelAndSeparateCompactAdd() {
        let singleSource = [
            TorahAssociationItem(
                id: "src-1",
                kind: .ref,
                role: .context,
                providerID: "sefaria",
                externalID: "Genesis 1:1",
                canonicalKey: "Genesis 1:1",
                labelHe: "בראשית א:א"
            )
        ]
        let presentation = PinkhaDocumentSourcesPresentation(associations: singleSource, canEdit: true)
        #expect(presentation.visibleAssociations.count == 1)
        #expect(presentation.remainingCount == 0)
        #expect(presentation.visibleAssociations.first?.id == "src-1")
        #expect(!presentation.showsEmptyPlaceholderAdd)
        #expect(presentation.showsCompactAdjacentAdd)
        #expect(!presentation.showsOverflowMenu)

        let threeSources = (1...3).map { idx in
            TorahAssociationItem(
                id: "src-\(idx)",
                kind: .ref,
                role: .context,
                providerID: "sefaria",
                externalID: "Genesis 1:\(idx)",
                canonicalKey: "Genesis 1:\(idx)",
                labelHe: "בראשית א:\(idx)"
            )
        }
        let pres3 = PinkhaDocumentSourcesPresentation(associations: threeSources, canEdit: true)
        #expect(pres3.visibleAssociations.count == 2)
        #expect(pres3.remainingCount == 1)
        #expect(pres3.remainingAssociations.map(\.id) == ["src-3"])
        #expect(!pres3.showsEmptyPlaceholderAdd)
        #expect(pres3.showsCompactAdjacentAdd)
        #expect(pres3.showsOverflowMenu)
    }

    @Test("Catalog live Type relation cache and PropertiesBuilder pipeline preserve all three native rows on zero-association documents and respect hide/reveal")
    func catalogLiveTypeRelationsAndZeroAssociationPropertiesSheet() {
        let spaceId = "space-live-sheet"
        let chiddushTypeId = "type-chiddush-live"
        let manifest = PinkhaSpaceManifest(
            spaceId: spaceId,
            orderPropertyId: "order-id-live",
            orderPropertyKey: "orderKeyLive",
            documentAssociationsPropertyId: "canon-id-live",
            documentAssociationsPropertyKey: "canonKeyLive",
            registeredDocumentTypes: [
                PinkhaSchemaRoles.chiddushKey: chiddushTypeId,
                PinkhaSchemaRoles.articleKey: "type-article-live",
                PinkhaSchemaRoles.researchKey: "type-research-live"
            ]
        )
        let probe = PolicyBootstrapProbe(manifest: manifest)
        let policy = PinkhaTorahPropertyPolicy(bootstrapService: probe)
        let catalog = PinkhaTorahNativePropertyCatalog(policy: policy)

        let nativeDetails = TorahNativePropertyDefinition.all.map { def in
            PropertyDetails(
                id: "id-\(def.key)",
                key: def.key,
                name: def.name,
                format: .tag,
                isHidden: false,
                isReadOnly: false,
                isReadOnlyValue: true,
                objectTypes: [],
                maxCount: 0,
                sourceObject: "_br" + def.key,
                isDeleted: false,
                spaceId: spaceId
            )
        }

        // Record live Type relations (simulating post-bootstrap / post-updateTypeProperties state)
        catalog.recordUpdatedTypeRelations(
            typeId: chiddushTypeId,
            spaceId: spaceId,
            recommendedIds: nativeDetails.map(\.id),
            featuredIds: [],
            hiddenIds: []
        )

        // Even when fallbackRecommended is empty (stale ObjectTypeProvider), resolvedTypeRelationIds returns the 3 attached IDs
        let unselected = catalog.resolvedTypeRelationIds(
            typeId: "ordinary-unconfigured-page", fallbackRecommended: [], fallbackFeatured: [], fallbackHidden: [], spaceId: spaceId
        )
        #expect(unselected.recommended.isEmpty && unselected.featured.isEmpty && unselected.hidden.isEmpty)
        let resolvedInitial = catalog.resolvedTypeRelationIds(
            typeId: chiddushTypeId,
            fallbackRecommended: [],
            fallbackFeatured: [],
            fallbackHidden: [],
            spaceId: spaceId
        )
        #expect(resolvedInitial.recommended == nativeDetails.map(\.id))
        #expect(resolvedInitial.hidden.isEmpty)

        // Hiding the first native property moves it to hidden and removes it from recommended without losing the other two
        let hiddenId = nativeDetails[0].id
        let remainingIds = Array(nativeDetails.dropFirst().map(\.id))
        catalog.recordUpdatedTypeRelations(
            typeId: chiddushTypeId,
            spaceId: spaceId,
            recommendedIds: remainingIds,
            featuredIds: [],
            hiddenIds: [hiddenId]
        )
        let resolvedAfterHide = catalog.resolvedTypeRelationIds(
            typeId: chiddushTypeId,
            fallbackRecommended: [],
            fallbackFeatured: [],
            fallbackHidden: [],
            spaceId: spaceId
        )
        #expect(resolvedAfterHide.recommended == remainingIds)
        #expect(resolvedAfterHide.hidden == [hiddenId])

        // Build ParsedProperties for a zero-association document via PropertiesBuilder
        let docId = "fresh-chiddush-doc-live"
        let docDetails = ObjectDetails(
            id: docId,
            values: [
                KeyValue(key: BundledPropertyKey.id.rawValue, value: docId.protobufValue),
                KeyValue(key: BundledPropertyKey.spaceId.rawValue, value: spaceId.protobufValue),
                KeyValue(key: BundledPropertyKey.type.rawValue, value: chiddushTypeId.protobufValue),
                KeyValue(key: TorahNativePropertyDefinition.engineVersionKey, value: TorahNativePropertyDefinition.engineVersion.protobufValue)
            ]
        )
        let detailsStorage = ObjectDetailsStorage()
        detailsStorage.update(with: [docDetails])
        let parsed = Container.shared.propertiesBuilder().parsedProperties(
            objectProperties: [],
            objectFeaturedProperties: [],
            recommendedProperties: nativeDetails,
            recommendedFeaturedProperties: [],
            recommendedHiddenProperties: [],
            objectId: docId,
            propertyValuesIsLocked: false,
            storage: detailsStorage
        )
        #expect(Set(parsed.sidebarProperties.map(\.key)) == Set(TorahNativePropertyDefinition.all.map(\.key)))

        let mockDoc = MockBaseDocument(objectId: docId, spaceId: spaceId)
        mockDoc.details = docDetails
        mockDoc.parsedProperties = parsed
        let torahModel = PinkhaTorahPropertiesModel(document: mockDoc, session: nil, bootstrap: probe, policy: policy)
        #expect(torahModel.isEligible == true)
        #expect(torahModel.usesNativeProperties == true)
        #expect(torahModel.showsLegacyProjectionRows == false)
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
