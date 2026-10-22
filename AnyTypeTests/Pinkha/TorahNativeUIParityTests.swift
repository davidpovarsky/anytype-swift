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

    private func fixedControl() -> UIView {
        let view = UIView()
        view.widthAnchor.constraint(equalToConstant: 44).isActive = true
        view.heightAnchor.constraint(equalToConstant: 44).isActive = true
        return view
    }
}
