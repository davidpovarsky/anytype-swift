# Native ordinary-edit property attachment correction

The fully qualified original diagnostic 44587184541 at47ca found one public projection difference after an old-client name-only edit of firstPage: `_pinkhaTorahAttachedProperties` changed from an empty list to `pinkhaTorahSources`. The two builds, old-create and new-upgrade passed; old-edit failed. Recovery, freshness and UI were not reached. Both controlled native-container transitions preserved their observed private data bytes.

The existing basic UpdateDetails method clones CombinedDetails, which includes local native projections, and automatically adds relation links for all those keys. The maintained downstream generator now filters only the three keys recognized by torah.IsProperty from that automatic step. It preserves ordinary user relations, similar-looking user keys, existing explicit attachments and the separate native explicit-attachment operation. No original compatibility assertion is relaxed.

Two focused native fixture methods exercise real basic/detailservice implementations, real state and indexed store. Four ordinary-edit cases cover SetDetails and UpdateDetails, with and without an existing Source attachment. The explicit native attacher must remain effective and idempotent.

The new t5-native-attachment lane first executes all tests in both native packages, then reruns the four ordinary-edit cases using the exact original r14 details.go through a single-file compile overlay. All four must fail for the specific expected attachment assertion. Unrelated runtime or compilation failure is not a passing counterexample. The reviewed generated patch and inventory are frozen in the generated subdirectory; CI must independently reproduce them before execution.

Source review and15 portable rejection controls passed independently. Native Go execution, a corrected Apple runtime and the complete compatibility/UI journey remain pending. Original r14/r15 approval inventories and runtime constants are unchanged; this candidate cannot establish compatibility with an unmodified old binary. The original diagnostic and each evidence limit remain recorded separately.
