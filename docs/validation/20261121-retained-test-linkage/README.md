# Retained XCTest linkage — 2026-11-21

Original run44942212731 at96173b0afc6b360c8f780ae70c6c80042fda98da compiled the retained app and test sources, then failed while linking AnytypeTests. No selected shared-editor method executed. The original receipt remains FAIL/BUILD and is preserved without relabeling.

The original linker command omitted three products that the test bundle imports directly. All125 undefined symbols belong to those products: PinkhaKit117, Loc5 and TorahInspectorUI3. The target's package-product list and Frameworks phase also omitted them.

The project now declares exactly those three test-target dependencies and links. PinkhaKit and Loc use the existing local product forms; TorahInspectorUI references the existing pinned TorahInspectorKit package. An independent graph review and an object-by-object comparison confirm that only the AnytypeTests target and its Frameworks phase changed, with six new dependency/build-file objects. Application targets, embedding phases, linker flags and package revisions are unchanged.

Actual Apple linkage remains the gate. The original10 methods/15 invocations are still required; they must run in the next existing SDK06 Debug build alongside the seven new acknowledgement methods, avoiding another full application build. No passing test is invalidated or relabeled by this failed build.
