# SDK06 document and selection entry trace

## Proven gap in the published source

Normal document navigation is a push. `SpaceHubCoordinatorViewModel` handles
`.editor` by pushing the `EditorScreenData`; the registered destination in
`SpaceHubCoordinatorView` builds `EditorCoordinatorView` inside the existing
`FullScreenSwipeNavigationController`. The Home Hanlin entry's requirement that
the root has no presented controller does not, by itself, prevent this normal
document path. Runtime confirmation on both form factors remains required.

Selection is a different, concrete missing path. `EditorPageController` changes
to non-editing collection selection mode for `.selecting` and calls
`EditorBottomNavigationManager.multiselectActive(true)`. That manager explicitly
hides the Home panel. `HomeBottomPanelContainer` then sets its opacity to zero
and disables hit testing. Meanwhile `EditorNavigationBarHelper` replaces its
right controls with only Done for both `.selecting` and
`.simpleTablesSelection`. The sole Home Hanlin button therefore cannot be
activated while those selected block IDs are retained. There is no phone/pad
branch in these conditions.

## Scoped correction

The actual SpaceHub editor destination now explicitly injects its owner into
the editor's SwiftUI environment, including across the separately constructed
UIHostingController root. `EditorSwiftUIViewContainer` passes that exact owner
to the already assembled `EditorPageController`, which retains it weakly.

The original selection toolbar keeps Done and adds a 44-point Hanlin button.
It is hidden when no SpaceHub owner was supplied and disabled for an empty
selection. Its action supplies that same controller directly to the canonical
host presentation builder. The existing mounted-controller guard checks the
actual scene, visible navigation/tab ancestry, onscreen view and absence of a
covering presentation. The live editor must still be in a nonempty block or
table selection state. The existing NativeAccess then derives and validates
account, Space, document, selection and revision from that editor.

The action does not call Done, switch editing state, clear selection, search
other windows/controllers, fall back to a document-free context, change source
permissions, or consent on the user's behalf. The canonical Hanlin engine/chat
and the existing explicit context-read prompt remain the execution path.

Native hooks are confined to SpaceHubCoordinatorView, EditorSwiftUIViewContainer,
EditorPageController and EditorNavigationBarHelper. T5's TorahEditorSession and
EditorPageCoordinatorViewModel are unchanged by this correction.

## Acceptance still required

After the actual Apple build succeeds, exercise a disposable real document on
iPhone and iPad: enter block multi-selection, retain the selected IDs, open
`pinkha.hanlin.open.selection`, and verify the canonical chat's context prompt
uses that exact document and selection. Check table selection, empty-selection
disabled state, close/reopen, account/Space changes and scene/background
invalidation. No model call or user-data write is needed to verify entry and
consent lifetime. This source trace and syntax parse do not claim native UI
acceptance.
