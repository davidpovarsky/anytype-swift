# Hierarchy drag source ownership

Two original encoded frames from the source-bound failure show the concrete interaction. During the intended drag, the document row has its native context menu open. Shortly afterward the menu is dismissed and both original rows remain root siblings. The original event stream does not publish a library drop or native move event, so this does not prove whether any drop callback ran.

The existing draggable modifier was attached to the outer Button that also owns the context menu. The candidate registers the same String payload on the Button label and gives that full-width label a rectangular interaction shape. The context menu remains on the outer Button. Apple demonstrates label-level drag composition in its Adopting drag and drop using SwiftUI sample.

The drop handler and context-menu blocks are byte-identical. The native move/authorization path, list onMove operation, titles, row identifiers and navigation closure are unchanged. The entire UITest source is unchanged from the preceding Hanlin-only fixture commit, including the real gesture, timing, drop-readback, native body and cold-reopen assertions.

This is a product candidate, not a claimed UI pass. Swift syntax parsing passed;0 XCTest methods ran. The failed HierarchyDrag journey is the necessary real gate. Root must explicitly review the inactive drag-registration delta before retaining journeys that use unchanged row taps.
