# Exact original compiler roots during postbuild continuation

Postbuild03 failed at the Clang declaration ownership guard because its actual compiler products remained under Device292-Work while the fresh distribution correctly belonged to Device292-Postbuild03-Work. The original sibling-root guard could not express this already source-bound continuation. The failed execution, products and original compiler descriptor are retained unchanged.

`release_continuation_roots.admit_roots` admits distinct roots only after verifying the exact on-disk graph collection, continuation and original compiler descriptor, source identity, UUIDs, receipt digests and owned paths. Direct builds keep the original sibling-root route. The Clang package, module-map, header and source checks are unchanged. After the existing preserved move, ownership uses the actual original checkout path for Git alternates, with an exact move receipt and absent original path; no directory is deleted.

The driver passes its actual original derived path and the postbuild controller pins the reviewed new driver digest. The original compiler descriptor/driver digest and SDK source remain unchanged.

## Validation and limits

Twelve pure controls passed, including exact distinct-root admission, unchanged direct build, missing proof, changed descriptor/terminal/graph/continuation receipts, foreign or aliased roots, source/UUID mismatch and preserved-move rejection cases. These controls are fixtures and confer no native acceptance.

The actual Mac read-only admission used Postbuild03 collection c779c3205ec833bdf1c98f0187264f1e7de756d946a1f2f5d334f29357d4a330, continuation 729303dd8f605affe8c7126682e4d2b193b89c3b68426081d5e6385a86f9ebe6 and original compiler descriptor bdf76198c991e74fb59623ad8448ee401269e07f64364bc89230740d53dc1865. It passed. Six protected receipts and metadata for all 302 evidence and 1,272 distribution entries were identical before and after. Original terminal failure d28dc6ca5aa65f52da7bc4aa382aa313643ff212d1bbd293817cd151023ef383 remains unchanged.

This packet proves root admission only. It does not claim that a fresh full Clang export, external consumer, Release ownership, app UI, device signing or TestFlight upload passed. Those original gates still run in the real downstream continuation.
