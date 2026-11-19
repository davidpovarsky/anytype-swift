# Restore empty native row typing direction at editing boundaries

Original Apple run 44586429599 at0996 built successfully but failed its one native editor preparation method with10 issues. Initial focus and all five distinct empty Return targets reached the actual attached first-responder gates. Four subsequent empty rows reported LTR typing attributes where RTL was required. The first typed line also lost text; the three selected UI methods did not run. The qualified original report records these distinct failures and their evidence limits.

This correction uses the existing cached application-direction adapter for empty native inputs at three production boundaries: after setFocus restores host typing attributes, after direct native begin editing, and before the original first-insertion delegate action. Existing IME and explicit-formatting guards remain. It does not change characters, caret, persistence, responder retry policy or the existing delegate action ordering.

Two actual UIKit test methods add four mandatory LTR/RTL cases. The programmatic-focus case isolates presentation-only assertions after initial UIKit acquisition; the row case exercises direct begin and late host attribute reset before the original insertion action. All previous55 method declarations and83 parameter cases are retained. The strict component inventory now requires57 methods and87 invocations, including each new argument.

Root and independent review each passed58 portable controller controls. Exact c787 base blobs, unchanged adapter/delegate dependencies, all six test inventories and all previous direction-suite bytes were verified. Windows Swift grammar parsing passed for all three changed Swift files; this is not Apple typechecking or UIKit execution.

Actual Apple component, editor preparation and UI execution remain required. Rapid-input ownership and native echo ordering are separate pending work; this change alone does not claim to fix lost text or establish full editor or release acceptance. The source commit applies cleanly on the later cb0 Properties-only correction without touching its files.
