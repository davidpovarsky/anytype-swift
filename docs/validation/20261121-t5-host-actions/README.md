# Pending T5 host actions in the corrected runtime build

The historical authorization ledger explicitly records Apple host tests as
NOT_RUN. The current complete `TorahRelatedDocumentActionTests` suite has eleven
methods and twelve literal cases, including both `isNote` values. This change
adds those pending tests to the already planned corrected T5 Release App build;
it creates no extra App build and executes no old native pagination scenarios.

The controller checks the tracked Swift declaration/argument inventory before
compilation. It makes a fresh sibling `.xctestrun` copy containing only the
actual `AnytypeTests` target and the whole pending suite, retaining original
product and skip settings. Before execution it enumerates that exact copy and
requires the eleven complete Swift Testing identifiers. The same copy then runs.

Original raw xcresult, summary, tree, commands, exact source hashes, product
hashes and selected-configuration binding are retained in `host-actions/`.
The existing raw argument validator requires all eleven methods and two distinct
actual Bool cases; an aggregate count cannot substitute for case nodes. Failed,
skipped, duplicate, missing, extra or foreign-destination evidence fails closed.

Only after this host gate passes does the controller enter the unchanged native
fixture and UI journey, on their separate disposable simulator. The original
native type/delete proof and UI count contracts remain required. Host callback
checks do not prove atomic native ACL enforcement, storage persistence or a real
signed membership revocation. Those boundaries remain separately reported.

Validation at source preparation: six new Python controller tests PASS in
0.129 seconds with Python3.12, zero failures, covering
actual tracked declarations, exact compiled selection, raw argument cases,
summary variants, failure/extra/missing/skip/foreign-device rejection. Actual
Apple execution is NOT_RUN until the replacement CI run supplies its receipt.
