import AnytypeCore
import PinkhaKit
import Services
import Testing
import UIKit
@testable import Anytype

@Suite("Pinkha Stage 1 real-app acceptance preparation", .serialized)
struct PinkhaStage1AcceptancePreparationTests {
    @Test("Creates disposable Pinkha, ordinary Note and ordinary Page documents")
    func prepareRealApplicationState() async throws {
        let propertyFixturesRequested = ProcessInfo.processInfo.environment["PINKHA_PROPERTIES_PREPARE"] == "1"
        Container.shared.serverConfigurationStorage().setupCurrentConfiguration(config: .localOnly)

        let auth = Container.shared.authService()
        let mnemonic = try await auth.createWallet()
        try Container.shared.seedService().saveSeed(mnemonic)
        let account = try await auth.createAccount(
            name: "Pinkha Stage 1 Acceptance",
            iconOption: 1,
            imagePath: ""
        )
        #expect(!account.id.isEmpty)

        let workspace = try await Container.shared.workspaceService().createSpace(
            name: PinkhaStage1AcceptanceState.spaceName,
            iconOption: 1,
            accessType: .private,
            useCase: .none,
            withChat: false,
            spaceType: .regular
        )
        let spaceId = workspace.spaceID
        #expect(!spaceId.isEmpty)
        // Use the same activation path as SpaceLoadingContainer. Besides opening the Space,
        // this starts the real type/property subscriptions and records it as the active Space
        // for the subsequent application launch.
        _ = try await Container.shared.activeSpaceManager().setActiveSpace(spaceId: spaceId)

        // Join the production bootstrap owner instead of racing its asynchronous activation hook.
        PinkhaBootstrapHook.handleSpaceActivated(spaceId: spaceId)
        let manifest = try await Container.shared.pinkhaBootstrapStateManager().awaitReadiness(
            spaceId: spaceId, timeoutSeconds: 60
        )
        let typeId = try #require(
            manifest.registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey]
        )
        let requiredWritingTypeIDs = propertyFixturesRequested
            ? Set([PinkhaSchemaRoles.chiddushKey, PinkhaSchemaRoles.articleKey, PinkhaSchemaRoles.researchKey]
                .compactMap { manifest.registeredDocumentTypes[$0] })
            : Set([typeId])
        // Note is no longer a bundled system type in current Anytype. Provision the
        // native Note layout only in this disposable fixture Space, using original APIs.
        let noteType = try await Container.shared.typesService().createType(
            name: "Acceptance Native Note", pluralName: "Acceptance Native Notes",
            icon: nil, color: nil, spaceId: spaceId
        )
        try await Container.shared.propertiesService().updateProperty(
            objectId: noteType.id,
            propertyKey: BundledPropertyKey.recommendedLayout.rawValue,
            value: DetailsLayout.note.rawValue.protobufValue
        )
        let noteTemplateID = try await Container.shared.templatesService().createTemplateFromObjectType(
            objectTypeId: noteType.id, spaceId: spaceId
        )
        try await Container.shared.templatesService().setTemplateAsDefaultForType(
            objectTypeId: noteType.id, templateId: noteTemplateID
        )

        // Read this Space's real index directly; a UI cache can switch active Spaces.
        let indexClock = ContinuousClock()
        let indexDeadline = indexClock.now.advanced(by: .seconds(30))
        var indexedTypes = [ObjectType]()
        repeat {
            indexedTypes = try await Container.shared.searchMiddleService().search(
                spaceId: spaceId, filters: [SearchHelper.layoutFilter([.objectType])],
                keys: ObjectType.subscriptionKeys.map(\.rawValue), limit: 0
            ).map(ObjectType.init(details:))
            if requiredWritingTypeIDs.isSubset(of: Set(indexedTypes.map(\.id))),
               indexedTypes.contains(where: { $0.id == noteType.id }),
               indexedTypes.contains(where: { $0.uniqueKey == .page }) { break }
            try await Task.sleep(nanoseconds: 100_000_000)
        } while indexClock.now < indexDeadline
        let pinkhaType = try #require(indexedTypes.first { $0.id == typeId })
        let indexedNoteType = try #require(indexedTypes.first { $0.id == noteType.id })
        _ = try #require(indexedTypes.first { $0.uniqueKey == .page })
        #expect(indexedNoteType.recommendedLayout == .note)
        print("PINKHA_ACCEPTANCE_TYPES_READY pinkha=\(pinkhaType.id) note=\(indexedNoteType.id) builtinNotePresent=\(indexedTypes.contains { $0.uniqueKey == .note })")

        let objectActions = Container.shared.objectActionsService()
        let document = try await objectActions.createObject(
            name: PinkhaStage1AcceptanceState.pinkhaDocumentTitle,
            typeUniqueKey: pinkhaType.uniqueKey,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceId, origin: .none,
            templateId: manifest.defaultTemplateIds[PinkhaSchemaRoles.chiddushKey]
        )
        await MainActor.run {
            PinkhaDocumentIdentityStorage.shared.registerCreated(objectId: document.id, spaceId: spaceId)
        }
        let note = try await objectActions.createObject(
            name: PinkhaStage1AcceptanceState.noteDocumentTitle,
            typeUniqueKey: indexedNoteType.uniqueKey,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceId, origin: .none, templateId: noteTemplateID
        )
        let page = try await objectActions.createObject(
            name: PinkhaStage1AcceptanceState.pageDocumentTitle,
            typeUniqueKey: .page,
            shouldDeleteEmptyObject: false,
            shouldSelectType: false,
            shouldSelectTemplate: false,
            spaceId: spaceId,
            origin: .none,
            templateId: nil
        )

        // Verify real native document shapes independently of UI-test diagnostic labels.
        #expect(Set([document.id, note.id, page.id]).count == 3)
        let fixtures: [(String, DetailsLayout, Bool)] = [
            (document.id, .basic, true),
            (note.id, .note, false),
            (page.id, .basic, true)
        ]
        for (objectID, layout, hasTitle) in fixtures {
            let nativeDocument = Container.shared.documentsProvider().document(
                objectId: objectID, spaceId: spaceId, mode: .preview
            )
            try await nativeDocument.open()
            let details = try #require(nativeDocument.details)
            #expect(details.resolvedLayoutValue == layout)
            if objectID == document.id { #expect(details.type == typeId) }
            let tree = nativeDocument.infoContainer.recursiveChildren(of: objectID)
            let featuredCount = tree.filter { $0.content == .featuredRelations }.count
            let actualHasTitle = tree.contains { $0.textContent?.contentType == .title }
            #expect(featuredCount == 1)
            #expect(actualHasTitle == hasTitle)
            print("PINKHA_ACCEPTANCE_NATIVE_SHAPE object=\(objectID) layout=\(details.resolvedLayoutValue.rawValue) featuredRelations=\(featuredCount) title=\(actualHasTitle)")
            try await nativeDocument.close()
        }

        // Ordinary Note/Page documents intentionally have no Sources header until
        // the native property is attached. Use the real Add Property path in this
        // disposable Space before the UI suite exercises document-source search.
        for objectID in [note.id, page.id] {
            try await attachSourcesForDocumentSearch(objectID: objectID, spaceID: spaceId)
        }

        if propertyFixturesRequested {
            try await prepareTorahPropertyFixtures(manifest: manifest, indexedTypes: indexedTypes)
        }

        let inputProbe = try await objectActions.createObject(
            name: "Native input lifecycle probe", typeUniqueKey: .page,
            shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
            spaceId: spaceId, origin: .none, templateId: nil
        )
        try await exerciseOriginalEditorInput(objectId: inputProbe.id, spaceId: spaceId)

        try PinkhaStage1AcceptanceState(
            spaceId: spaceId,
            pinkhaObjectId: document.id,
            noteObjectId: note.id,
            pageObjectId: page.id
        ).save()
        try await Container.shared.authMiddleService().preloadRemainingSpaces()

        print(
            "PINKHA_STAGE1_ACCEPTANCE_READY space=\(spaceId) "
            + "pinkha=\(document.id) note=\(note.id) page=\(page.id)"
        )
    }

    @MainActor
    private func attachSourcesForDocumentSearch(objectID: String, spaceID: String) async throws {
        let document = Container.shared.openedDocumentProvider().document(objectId: objectID, spaceId: spaceID)
        try await document.open()
        do {
            let typeID = try #require(document.details?.type)
            await PinkhaTorahNativePropertyCatalog.shared.ensureSpaceAndTypeReady(spaceId: spaceID, typeId: typeID)
            let sourceKey = TorahNativePropertyDefinition.all[0].key
            try #require(!document.parsedProperties.installed.contains { $0.key == sourceKey })
            try #require(!PinkhaTorahPropertyPolicy.shared.presentsSources(on: document))

            let coordinator = PropertiesListCoordinatorViewModel(document: document, output: nil)
            let model = ObjectPropertiesViewModel(document: document, output: coordinator)
            let subscription = Task { await model.setupSubscriptions() }
            defer { subscription.cancel() }
            try await waitForNativeFixtureState { document.permissions.canEditRelationValues }
            model.onAddPropertyTap()
            let picker = PropertyCreationViewModel(data: try #require(model.relationsSearchData))
            await picker.search(text: "")
            let matches = picker.rows.flatMap(\.searchData).compactMap { row -> PropertyDetails? in
                if case .existing(let property) = row, property.key == sourceKey { return property }
                return nil
            }
            try #require(matches.count == 1)
            let source = try #require(matches.first)
            try await picker.addPropertyToObject(objectId: objectID, relation: source)
            try await waitForNativeFixtureState {
                model.sections.flatMap(\.relations).contains { $0.key == sourceKey } &&
                    PinkhaTorahPropertyPolicy.shared.presentsSources(on: document)
            }

            // The subsequent UI process must observe persisted native installation,
            // not merely this preparation process's live property view model.
            try await document.close()
            try await document.open()
            try await waitForNativeFixtureState {
                document.parsedProperties.installed.contains { $0.key == sourceKey } &&
                    PinkhaTorahPropertyPolicy.shared.presentsSources(on: document)
            }
            try #require(document.details?.stringArrayValue(for: sourceKey).isEmpty == true)
            print("PINKHA_ACCEPTANCE_NATIVE_SOURCES_ATTACHED object=\(objectID) space=\(spaceID)")
        } catch {
            try? await document.close()
            throw error
        }
        try await document.close()
    }

    @MainActor
    private func waitForNativeFixtureState(_ condition: () -> Bool) async throws {
        let clock = ContinuousClock()
        let deadline = clock.now.advanced(by: .seconds(15))
        repeat {
            if condition() { return }
            try await Task.sleep(for: .milliseconds(50))
        } while clock.now < deadline
        try #require(condition(), "The actual native property fixture did not become ready")
    }

    @MainActor
    private func prepareTorahPropertyFixtures(manifest: PinkhaSpaceManifest, indexedTypes: [ObjectType]) async throws {
        var environment = [
            "PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED": "1",
            "PINKHA_PROPERTIES_SPACE_ID": manifest.spaceId
        ]
        var nativePropertyLabels = [String: [String]]()
        for role in [PinkhaSchemaRoles.chiddushKey, PinkhaSchemaRoles.articleKey, PinkhaSchemaRoles.researchKey] {
            let typeID = try #require(manifest.registeredDocumentTypes[role])
            let type = try #require(indexedTypes.first { $0.id == typeID })
            let created = try await Container.shared.objectActionsService().createObject(
                name: "Torah properties acceptance \(role)", typeUniqueKey: type.uniqueKey,
                shouldDeleteEmptyObject: false, shouldSelectType: false, shouldSelectTemplate: false,
                spaceId: manifest.spaceId, origin: .none, templateId: manifest.defaultTemplateIds[role]
            )
            let document = Container.shared.documentsProvider().document(
                objectId: created.id, spaceId: manifest.spaceId, mode: .preview
            )
            try await document.open()
            #expect(document.details?.type == typeID)
            #expect(document.details?.resolvedLayoutValue == .basic)
            await PinkhaTorahNativePropertyCatalog.shared.ensureSpaceAndTypeReady(spaceId: manifest.spaceId, typeId: typeID)
            let nativeKeys = Set(TorahNativePropertyDefinition.all.map(\.key))
            try await waitForNativeFixtureState {
                let sections = PropertiesSectionBuilder().buildObjectSections(parsedProperties: document.parsedProperties)
                return nativeKeys.isSubset(of: Set(sections.flatMap(\.relations).map(\.key)))
            }
            for key in nativeKeys {
                try #require(document.details?.stringArrayValue(for: key).isEmpty == true)
            }
            let sections = PropertiesSectionBuilder().buildObjectSections(parsedProperties: document.parsedProperties)
            nativePropertyLabels[created.id] = sections.filter { !$0.isExpandable }.flatMap(\.relations)
                .filter {
                    !TorahDocumentPropertyEligibility.isCanonicalProperty(
                        id: $0.id, key: $0.key, spaceId: manifest.spaceId, manifest: manifest
                    )
                }.map(\.name)
            #expect(nativePropertyLabels[created.id]?.isEmpty == false)
            try await document.close()
            environment["PINKHA_PROPERTIES_\(role.uppercased())_ID"] = created.id
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        environment["PINKHA_PROPERTIES_NATIVE_PROPERTY_LABELS"] = String(decoding: try encoder.encode(nativePropertyLabels), as: UTF8.self)
        let json = String(decoding: try encoder.encode(environment), as: UTF8.self)
        print("PINKHA_PROPERTIES_ACCEPTANCE_FIXTURE_JSON \(json)")
    }

    /// Runs the original assembly, cursor manager, keyboard handler, virtual row and real
    /// middleware in the disposable Space. No no-op TextBlock actions stand in for input.
    @MainActor
    private func exerciseOriginalEditorInput(objectId: String, spaceId: String) async throws {
        // A test-target-wide UITextView override previously made every row report
        // first-responder status and prevented the real native focus path from running.
        // An unattached ordinary UIKit view must retain UIKit's actual responder state.
        try #require(!UITextView().isFirstResponder, "Native preparation requires unmodified UIKit responder semantics")
        let state = EditorPageModuleAssembly().buildStateModel(
            data: EditorPageObject(objectId: objectId, spaceId: spaceId),
            output: nil, showHeader: true, torahSession: nil
        )
        let controller = state.viewController
        let navigation = UINavigationController(rootViewController: controller)
        navigation.view.semanticContentAttribute = .forceRightToLeft
        controller.view.semanticContentAttribute = .forceRightToLeft
        let scene = try #require(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let previousKey = scene.windows.first(where: \.isKeyWindow)
        let window = UIWindow(windowScene: scene)
        window.rootViewController = navigation
        window.makeKeyAndVisible()
        let focusObservation = PinkhaStage1AcceptanceDiagnostics.beginFocusObservation()
        defer {
            PinkhaStage1AcceptanceDiagnostics.endFocusObservation(focusObservation)
            controller.view.endEditing(true)
            window.isHidden = true
            window.rootViewController = nil
            previousKey?.makeKey()
        }
        let document = Container.shared.openedDocumentProvider().document(
            objectId: objectId, spaceId: spaceId, mode: .handling
        )
        // A nonempty collection can still contain only the loading shimmer. Wait for
        // the native document's editable state and its actual rendered title before
        // dispatching the one empty-area tap; the production handler ignores a tap
        // while canEditBlocks is false. Never repair focus or replay the tap here.
        let probeTitle = "Native input lifecycle probe"
        var inputReady = false
        var readinessObservation = ""
        for _ in 0..<200 {
            let nativeTitleReady = document.details?.name == probeTitle
                && document.infoContainer.recursiveChildren(of: objectId).contains {
                    $0.textContent?.contentType == .title
                }
            let renderedTitleReady = inputTextViews(in: controller.collectionView).contains {
                $0.text == probeTitle && $0.window === window && !$0.isHidden && $0.alpha > 0
                    && $0.bounds.width.isFinite && $0.bounds.width > 1 && $0.bounds.height > 1
            }
            let hostReady = scene.activationState == .foregroundActive && window.isKeyWindow
                && !window.isHidden && controller.view.window === window
                && controller.collectionView.window === window
                && controller.collectionView.bounds.width.isFinite
                && controller.collectionView.bounds.width > 1 && controller.collectionView.bounds.height > 1
            // Match the original empty-area gesture gate; do not dispatch an input while
            // the controller is still applying a native loading/readonly transition.
            let gestureReady = controller.collectionView.isEditing && !controller.collectionView.isLocked
            inputReady = document.isOpened && document.permissions.canEditBlocks
                && nativeTitleReady && renderedTitleReady && hostReady && gestureReady
            readinessObservation = "opened=\(document.isOpened) canEditBlocks=\(document.permissions.canEditBlocks) "
                + "nativeTitle=\(nativeTitleReady) renderedTitle=\(renderedTitleReady) hostReady=\(hostReady) "
                + "keyWindow=\(window.isKeyWindow) sceneActive=\(scene.activationState == .foregroundActive) "
                + "collectionEditing=\(controller.collectionView.isEditing) collectionLocked=\(controller.collectionView.isLocked)"
            if inputReady { break }
            try await Task.sleep(for: .milliseconds(50))
        }
        try #require(document.isOpened)
        try #require(inputReady, "Original editor input readiness failed: \(readinessObservation)")
        print("PINKHA_NATIVE_EDITOR_READY \(readinessObservation)")
        state.model.tapOnEmptyPlace(isBelowContent: true)
        var textView = try await focusedEmptyTextView(in: controller.view, phase: "initial-empty-area-tap")
        let lines = ["שלום בדיקת הקלדה", "English input lifecycle", "שורה שלישית", "Fourth native line", "שלום 👩🏽‍💻 final"]
        for (index, line) in lines.enumerated() {
            try requireNativeInputTarget(textView, in: controller)
            let emptyCaret = textView.caretRect(for: textView.beginningOfDocument)
            #expect(emptyCaret.midX > textView.bounds.midX)
            #expect((textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle)?.baseWritingDirection == .rightToLeft)
            let directionPairID = UUID().uuidString
            recordNativeInputDirectionBoundary(
                textView, in: controller, line: index + 1, pairID: directionPairID,
                phase: "before-first-delegate", accepted: nil
            )
            var recordedFirstDelegate = false
            for character in line {
                try requireNativeInputTarget(textView, in: controller)
                let replacement = String(character)
                let accepted = textView.delegate?.textView?(
                    textView, shouldChangeTextIn: textView.selectedRange, replacementText: replacement
                ) ?? false
                if !recordedFirstDelegate {
                    recordedFirstDelegate = true
                    recordNativeInputDirectionBoundary(
                        textView, in: controller, line: index + 1, pairID: directionPairID,
                        phase: "after-first-delegate", accepted: accepted
                    )
                }
                try #require(accepted, "Ordinary probe input must follow the actual accepted native delegate path")
                textView.insertText(replacement)
                try await Task.sleep(for: .milliseconds(10))
            }
            // Wait for the original document event stream, not merely the live view value.
            for _ in 0..<200 {
                if document.infoContainer.recursiveChildren(of: objectId).contains(where: { $0.textContent?.text == line }) { break }
                try await Task.sleep(for: .milliseconds(50))
            }
            #expect(textView.text == line, "Native echo must not reorder or discard rapid input")
            #expect(textView.selectedRange == NSRange(location: line.utf16.count, length: 0), "A caret observation must not replay an old focus offset")
            #expect(document.infoContainer.recursiveChildren(of: objectId).filter { $0.textContent?.text == line }.count == 1)
            print("PINKHA_NATIVE_EDITOR_INPUT line=\(index + 1) length=\(textView.text.utf16.count) caret=\(textView.selectedRange.location)")
            let previous = textView
            try requireNativeInputTarget(textView, in: controller)
            let acceptedReturn = textView.delegate?.textView?(
                textView, shouldChangeTextIn: textView.selectedRange, replacementText: "\n"
            ) ?? true
            #expect(!acceptedReturn, "The original keyboard handler must own Return and create the next block")
            textView = try await focusedEmptyTextView(
                in: controller.view, excluding: previous, phase: "return-after-line-\(index + 1)"
            )
        }
        for line in lines {
            #expect(document.infoContainer.recursiveChildren(of: objectId).filter { $0.textContent?.text == line }.count == 1)
        }
        controller.view.endEditing(true)
        try await document.close()
    }

    /// Read-only observations around the first real delegate call on each fixed input line.
    /// Keep the original pre-insertion expectations and accepted-input guard unchanged.
    @MainActor
    private func recordNativeInputDirectionBoundary(
        _ textView: UITextView, in controller: EditorPageController,
        line: Int, pairID: String, phase: String, accepted: Bool?
    ) {
        let selection = textView.selectedRange
        let paragraphStyle = textView.typingAttributes[.paragraphStyle] as? NSParagraphStyle
        let typingDirection = paragraphStyle.map { String($0.baseWritingDirection.rawValue) } ?? "missing"
        let typingAlignment = paragraphStyle.map { String($0.alignment.rawValue) } ?? "missing"
        let interfaceDirection = PinkhaTextDirectionUIKitAdapter.effectiveInterfaceDirection(for: textView)
        let sameWindow = textView.window != nil && textView.window === controller.viewIfLoaded?.window
        let acceptedValue = accepted.map { $0 ? "true" : "false" } ?? "not-called"
        print("PINKHA_NATIVE_EDITOR_DIRECTION_BOUNDARY schema=1 line=\(line) pair=\(pairID) phase=\(phase) "
              + "storageLength=\(textView.textStorage.length) "
              + "selectionLocation=\(selection.location) selectionLength=\(selection.length) "
              + "firstResponder=\(textView.isFirstResponder) "
              + "controllerFirstResponder=\(controller.firstResponderView === textView) sameWindow=\(sameWindow) "
              + "markedRange=\(textView.markedTextRange != nil) "
              + "semanticAttribute=\(textView.semanticContentAttribute.rawValue) "
              + "interfaceDirection=\(interfaceDirection == .rightToLeft ? "rtl" : "ltr") "
              + "textAlignment=\(textView.textAlignment.rawValue) "
              + "typingDirection=\(typingDirection) typingAlignment=\(typingAlignment) accepted=\(acceptedValue)")
    }

    @MainActor
    private func inputTextViews(in root: UIView) -> [UITextView] {
        (root as? UITextView).map { [$0] } ?? root.subviews.flatMap { inputTextViews(in: $0) }
    }

    @MainActor
    private func requireNativeInputTarget(_ textView: UITextView, in controller: EditorPageController) throws {
        let responders = inputTextViews(in: controller.view).filter(\.isFirstResponder)
        try #require(responders.count == 1 && responders.first === textView,
                     "Native input must address the editor's unique actual first responder")
        try #require(controller.firstResponderView === textView,
                     "The original editor must observe the same text view beginning editing")
        try #require(textView.window != nil && textView.window === controller.view.window,
                     "Native input must not continue in a detached or replaced row")
    }

    @MainActor
    private func focusedEmptyTextView(
        in root: UIView, excluding previous: UITextView? = nil, phase: String
    ) async throws -> UITextView {
        for _ in 0..<200 {
            let responders = inputTextViews(in: root).filter(\.isFirstResponder)
            if responders.count == 1, let view = responders.first,
               view !== previous, view.textStorage.length == 0,
               view.window != nil, view.window === root.window {
                return view
            }
            try await Task.sleep(for: .milliseconds(50))
        }
        let views = inputTextViews(in: root)
        for (index, textView) in views.enumerated() {
            print("PINKHA_NATIVE_EDITOR_FOCUS_ROW index=\(index) "
                  + PinkhaStage1AcceptanceDiagnostics.focusObservation(in: textView))
        }
        let observation = "phase=\(phase) textViews=\(views.count) "
            + "firstResponders=\(views.filter(\.isFirstResponder).count) "
            + "emptyTextViews=\(views.filter { $0.textStorage.length == 0 }.count) "
            + "keyWindow=\(root.window?.isKeyWindow == true) previousFocused=\(previous?.isFirstResponder == true)"
        print("PINKHA_NATIVE_EDITOR_FOCUS_FAILED \(observation)")
        Issue.record("The real editor did not focus a distinct empty block; \(observation)")
        throw NativeInputProbeError.missingFocusedBlock
    }
}

private enum NativeInputProbeError: Error { case missingFocusedBlock }
