# Original Any semantic-source acceptance — native PASS, UI menu lookup FAIL

Product source: `2b2a5611cee18ce7fcb76e7e91d455ca21e1bd3c`.
Controller: `5362a58cd8a1e6e812042cb97a08a57866ae7353`.
Original retained root: `/Users/m1/builds/any-semantic-20261125/source-links1`.
This is the original single-Any runtime and Hanlin `6bd6036` scope, not final combined-runtime or SDK97 acceptance.

The new actual native method `testSemanticSourceLinksPersistCanonicalIdentityAndRejectMissingOrForeignTargets` passed 1/1, with zero skipped/failed cases. It uses the real Any library and native account/document, real Sefaria reference, canonical repository readback, distinct semantic targets for the same verse, editing, foreign/missing-target refusal and canonical removal. The original engine/UI controls were not rerun.

The new actual UI method built successfully and failed at line 2683 after creating the real anchor. The retained read-only observation proves full UIKit selection `(0,6)`, the original marker still matches native and rendered text, and zero observer engine calls/mutations/selection changes. The original accessibility hierarchy contains exactly one native Button with localized Sources label, but UIKit does not expose its `UIAction.identifier`. The test incorrectly queried that identifier. Its failure remains unchanged in the original xcresult and execution record.

The scoped test correction replaces only the two Sources lookups with a unique enabled/hittable native Button or MenuItem matching the actual localized action. All selection, canonical write/readback, edit, cold-open, unlink and cold-removal assertions remain required. No product implementation or accepted method body changes to accommodate the lookup.

Both native and UI original Products were independently cloned and all entries hash-verified before cache reuse. Source and dependencies were unchanged through the run. Cleanup is PASS with no owned process groups remaining. The original simulator was deleted after completion. Raw screen recording/AX/observations stay in the private retained root; only hashes, sizes and scoped verification are tracked.

E remains open; the corrected UI method and Heart/combined-runtime continuation require actual execution.
