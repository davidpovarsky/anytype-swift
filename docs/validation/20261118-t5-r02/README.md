# T5 R02 query and exact block navigation

Four preserved production/helper test files are reused byte-for-byte from `4cb4e5c7816ff388e021bb64c72bfbbe3bbe39f1`. Their paths and SHA-256 hashes are in `handoff.json`. The old worktrees remain untouched.

`T5ExpandedRelatedDocumentsQuery` connects the existing canonical target collector to bounded native candidate pagination. It requires explicit runtime capability, fresh candidate reads on each execution, canonical record validation, exact reachable block membership, independent candidate/target caps, and cancellation/error propagation. It never turns an invalid or removed block into a document-level result. Source quotes remain read-only. A stored private version alone cannot grant runtime capability.

The app's existing editor supports `EditorPageObject.blockId`. The T5 host previously dropped that ID. The host callback now carries `(objectID, blockID?)` to the coordinator. Empty/root block targets, a foreign Space and stale presenter lifetimes are rejected; Note creation/opening requests a document with nil block. This is proof of the callback contract only, not confirmation that the destination UI displayed its requested block.

## Executed checks

- Windows Swift 6.3.3 exact-source component: **26 test functions / 27 cases in 3 suites passed**, zero failures. The eight new query test functions cover nine cases; 18 preserved helper tests also ran. The compiler's separate XCTest harness reports zero XCTest cases because these are Swift Testing tests; the complete Swift Testing output reports the nonzero counts above.
- All copied source bytes matched before and after execution. The manifest names the exact PinkhaKit/InspectorCore sources and tests; no app or native component was substituted.
- Swift parser accepted all 10 changed/new Swift files. Source whitespace validation passed.
- One already-recorded warning in the unselected Note test file concerns a MainActor test variable captured by a sendable closure. The complete compiler output is retained.

## Remaining acceptance

The Apple host action tests and the native integration test were updated for the callback signature but **not run on Apple here**. Native index/RPC/compatibility and real Inspector navigation remain separate gates. The expanded query is not yet connected to the app's active fetch path, and native r15 client capability remains disabled. The existing active UI continues to disclose indexed-document-only coverage. The next host integration must verify the runtime marker, read canonical ObjectShow data and block graph, and disclose indexed-target-only coverage without claiming complete freshness.
