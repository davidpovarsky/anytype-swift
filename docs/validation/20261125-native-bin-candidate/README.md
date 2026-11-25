# Native library Bin and restore candidate

The library now exposes a Bin navigation destination backed by actual native collection membership. It reads only archived members of the installed writing library, with the existing account, current schema, complete bounded query and before/after native membership checks. No native system-root object ID is fabricated.

Restore uses the same existing native conditional-membership operation as archive, retaining the captured row fence and every other ordered collection membership. It performs a fresh authorized native object read before refreshing Bin and library state. Retired UI owners cannot publish the result or start another restore; duplicate button submissions are fenced locally. The Bin view supports folders and writing documents with localized Hebrew/English labels and an explicit accessible restore action.

Two new acceptance methods were added: one actual native model roundtrip with exact original object/block/collection preservation and retired-presentation refusal, and one real UI archive/first cold reopen/restore/second cold reopen journey. Every original test method and fixture byte is unchanged; source-review.json proves the inverse insertion for both existing files.

The candidate passed only Swift grammar parsing, both with and without PINKHA_DUAL_ENGINE_RUNTIME. Apple typechecking, actual native execution and actual UIKit execution are still pending. This candidate did not enter the already-running94d8 app producer and must not be reported accepted yet.
