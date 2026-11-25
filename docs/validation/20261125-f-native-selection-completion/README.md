# Native empty-row selection completion

The first actual F editor lane on App commit 0c5ffc51 failed its original preparation method in four assertions. The first empty row used RTL defaults. Each subsequent real Return created and focused a distinct empty row with a right-side caret but LTR typing direction before the first delegate call. The actual accepted input delegate then restored RTL. The original test, including pre-insertion assertions, is unchanged.

Apple documents that a selection change clears UITextView typing attributes:
https://developer.apple.com/documentation/uikit/uitextview/typingattributes

The existing shared adapter already handles the selection delegate, focus and insertion boundaries. The candidate now also handles completion of both public selection setters in TextViewWithPlaceholder, after the original UIKit setter returns. It reuses the same guarded restoration and leaves both getters as native getters. No getter manufactures the expected value, no selection or focus is replayed, and no delayed task changes a later input owner. The existing guard preserves nonempty text, marked composition, detached or unfocused rows, and explicit alignment.

This is a source correction, pending actual compilation and the unchanged original preparation and editor acceptance. The four original failures remain failures. The original xcresult and complete command/evidence directory archive were copied and SHA-256 verified on Oracle; this repository contains a bounded failure description, not private account storage.
