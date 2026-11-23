# First exact Heart Swift control compile

Source commit: `55b781591de6d91d680d1190f62a580c3b8d60f7`.
Status: **FAIL_BUILD; zero methods executed, zero passed**.

The original compiler completed the 695-file product source graph and rejected
the new client test at two XCTest expected-value expressions: each call to
`event.serializedData()` needed its own `try`. The correction changes only
those two test expressions. The original source, logs, manifest and command
receipts are retained byte-for-byte here. No product source, native154 input,
protobuf schema, SDK, account store or existing qualified test was changed.

The external launcher recorded the failing build and stopped before tests,
although its Python process returned zero; the actual build receipt and log
are authoritative and this attempt is not a pass. The next launcher propagates
the failing stage code.

The three actual SwiftPM checkouts were inspected after this failure and were
clean at the exact pinned revisions: Protobuf c6fe6442, Crypto e8d6eba1 and ASN1
917b472d. The controller now verifies those full checkout revisions and clean
state at every dependency boundary.

To avoid rebuilding unchanged generated protocol sources, the next evidence
attempt may explicitly reuse the same package directory. Before replacing any
input, the controller verifies every old input against the prior manifest and
copies all of them into the new attempt's immutable prior-package-sources
snapshot. It preserves unchanged paths/mtimes, rejects extra sources/resources,
and emits a fresh exact source manifest. Original receipts remain unchanged.

The native SDK body remains inactive in Linux controls. App wrapper typecheck,
actual Apple Lib call, publication-generation fencing and mounted editor
acceptance are not established by this failed compile.
