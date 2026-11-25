# Actual Any semantic source link / edit / reopen / unlink / reopen — PASS

**1/1 real UI method passed, zero failures/skips, 393.402 seconds.**

Product/test source: `4b9b381d3f9b8d5a9a358d626a69333c145e3282`.
Controller: `7bdd7386c4b443f9ab83d1946a46b8acd2ef6d70`.
Method: `PinkhaAnyNativeUITests/NativeLaunchTests/testSemanticSourceLinkSurvivesEditAndColdReopen`.
Device: owned iPad Pro13-inchM5, arm64 iOS27.0/build24A434, Xcode27.
Retained root: `/Users/m1/builds/any-semantic-20261125/source-links-unlink3`.
Scope: original verified Any native artifact, Hanlin `6bd6036`; **not final combined-runtime/SDK97 or physical-device acceptance**.

## Actual acceptance

The user journey creates an owned native account/Space/document, types Anchor, selects the complete real UIKit range and creates one native semantic anchor. The actual native link menu opens Sources; live Sefaria Genesis1:1 is explicitly linked. The production canonical repository record is observed through the shared Torah session.

Ordinary per-key typing replaces Anchor with Changed. Native and rendered text retain the same anchor UUID over range0/7. A new app process opens the same native Space/object/block and exactly the same canonical source-record hash, text/marker bytes and saved document revision. A real native tap of the now-visible, hittable unlink control (minimum44×44 assertions passed) removes the source. A second new process reopens the same Changed text and original marker, with no semantic source remaining.

All15 original read-only observations have MATCHED native/rendered marks and zero observer engine calls, mutations or selection changes. Process sequence:95363→96325→96520, with distinct mounted-owner generations. Raw object identities are represented only by hashes in tracked observation records. The canonical source record stays identical through editing and first cold reopen; unlink leaves text/marker source bytes unchanged.

## Preserved evidence and scope

Original app/UI builds, original xcresult, xctestrun, command logs and all872 original Product entries are retained. Every Product entry was hash-verified after retention. Source, actual native binding and all9 package dependencies were unchanged. Cleanup is PASS with no owned process groups remaining; only the owned simulator was removed.

Receipt: `actual-source-ui-pass.json`, SHA256 `576c07404ae961d1e75ff14dcd9c4f78dc7625c69391977836f3827b02a75ef3`.
Original xcresult summary SHA256 `9757804fb6b09ef0d90e4a681e85f07bcd1e8aa8983b8212ff2ac22a9aaf2dd3`; tests SHA256 `457b2268e9d9be1a49bc7967a43f0ea6c24ca9a6058d7bbc00da19644a34f89c`.
The accepted original new native1/1 and shared5/5 component proofs are reused under their unchanged source closures; none was rerun. The earlier menu-identifier and zero-hit-area UI failures remain original FAIL evidence.

A first post-processing-only check incorrectly treated `AnyEditorRead.nativeVersion` as a fixed engine version across the intentional text edit. It is the native markdown document revision (`AnyEditorDocumentStore.swift` assigns `second.version`). That collector failure is retained separately; original XCTest PASS was unchanged, and no tests reran. The reviewed read-only qualifier instead requires immutable Space/object/block identity, an actual document-revision change on text editing, and equal saved revision through both cold opens and unlink. It also revalidates all original Product hashes.

E remains open for the new Heart source-link continuation and actual Page154/Apply/event/readback qualification on D's new combined native runtime. The accepted standalone Heart154 and initial Any anchor UI results remain preserved.
