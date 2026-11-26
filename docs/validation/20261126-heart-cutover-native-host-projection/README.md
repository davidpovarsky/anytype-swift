# Compiled native cutover host and projection controls

The complete actual Heart torahops production package, including the additive cutover host, was compiled against the exact retained 410b source closure. The previously qualified eight Go workspace checksum additions were reused unchanged. Every materialized source file stayed byte-identical during this run.

Eight new pure state-machine methods passed, zero failed/skipped. They cover required full source and phase-two coverage, two authors retaining every physical import, a durable seal surviving later unlink, late offline import becoming an explicit conflict, older-writer legacy divergence, mismatched receipt refusal, same-author changed retry conflict, and the guarded ordinary-operation admission rules. They use the actual shared Swift codec vectors from the separate coverage qualification. Component receipt values in these tests are deliberately labeled component-only; they are not claimed to be signed native receipts.

The native host compiles but was not invoked in this run. It binds separate v2 metadata to the actual signed v1 histories, retains exact source bytes, and uses the existing native durable-commit guard. Source/settings, metadata, v1 and current ACL locks have an explicit order. Current membership and account/target lifetime remain necessary; the upcoming native tests must prove them.

The original v1 Append body is extracted into a private function with an optional post-prepare validation callback. The original v1 entry passes nil and retains its original behavior; the explicit cutover entry supplies its real held source/target validator. The exact small source delta is retained in `original-v1-shared-body.patch`. Original v1 signature/ACL/commit/lifetime regression methods still require affected qualification before activation.

This checkpoint has zero actual native calls, zero peers, zero App builds and zero replayed accepted tests. No private type registration, RPC, generated wire code or production Heart repository activation is included. It is not evidence of complete E/T2 or a shipping cutover.
