# T5 component binary pairing CI

## Why this route exists

The three bounded native source components passed on 2026-11-18, but they did not run an old and a new executable against the same persisted store. This route supplies the missing compiled artifacts to the existing four-process controller.

The canonical controller, fixture, template, control tests and historical README in `Tools/PinkhaNativeDerived/compatibility_pairs/` are copied byte-for-byte from `01025e412e7382cc6bb8107dd11b2ca7e15f5d7d`. The wrapper verifies all five normalized hashes before compilation and after execution. Historical NOT_RUN statements describe the preserved tranche; a new actual run must provide its own receipt.

## Exact recipe

The reusable `pinkha-t5-compatibility-pairs.yml` is selected only by dispatcher route `t5-coverage-proof`, component `compatibility-pairs`. The existing three component routes continue to use their original workflow.

It checks out control at the real dispatch SHA, source/inventories at `947fbde24d5657d0e1229f45bb3993648884a8a1`, and two separate Heart directories at `d98420b1113536afd08cde6de9a5816f6d27ffff`. The exact r14 patch is `fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077`; r15 is `5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2`. Both inventory hashes are immutable.

The same complete musl environment that passed the native tests is used: official Go 1.26.5 Alpine linux/amd64 image digest `111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8`. The source and control mounts are read-only. Native checkout, binary, disposable work and evidence directories are separate. The container has 2 CPUs, 6 GiB RAM and a bounded process count.

For each revision, the already pinned source builder applies/verifies that revision's approved patch. The original Tantivy archive is checked against its fixed checksum. Dependencies selected by the immutable native module files are downloaded once; compilation uses `GOPROXY=off`, `GOTOOLCHAIN=local`, `-mod=readonly` and its own Go workspace containing only that revision's Heart checkout. No current Swift repository Go module replaces old native code.

Two independent `go test -c` invocations compile the actual native spaceindex package with the same unchanged fixture overlay. Each links full native commit, revision summary and fixture SHA; r15 additionally links its separate capability marker. The output binary hashes, resolved modules, commands, flags, environment and source inventories are retained before process execution.

The preserved controller then runs old-create -> new-upgrade -> old-edit -> new-recover as four distinct, completed processes on one controller-created synthetic on-disk store. Its 8 GiB reserve, 180-second process deadline, POSIX process-group isolation, ownership token, nonce/PID checks, exact named-test checks and native close requirements are unchanged.

## Evidence and claim boundary

Small receipts and logs are uploaded separately from the actual two compiled ELF component binaries. The disposable database is not published. Failure receipts and available build logs/artifacts are retained.

Success must be `COMPONENT_STORE_PAIR_PASS`, with two binaries, four distinct native processes and four passing invocations. It must retain `full_F10=NOT_PROVEN`, export and Swift NOT_RUN, and disabled client capability. The wrapper rejects missing phases, duplicated process identities, unclosed stores or receipts that claim broader product acceptance.

This route creates synthetic native Details, not an application account or real editor blocks. It does not prove packaged Apple runtime pairing, same-account recovery, RPC export roundtrips, the new Swift consumer with an old running Heart, actual Inspector navigation or physical iPad acceptance. No app build flag is enabled.

## Checks completed before publishing this route

Windows Python control validation: 18 preserved controller tests and 4 wrapper tests passed. The new wrapper tests include 10 rejection subcases. Python AST, two YAML files and shell syntax parsed successfully. Original logs and normalized hashes of ten implementation/workflow files are retained beside this document.

These are control checks only. Actual two-binary compilation and process pairing are NOT_RUN at this source-publication milestone. A subsequent CI run must retain the real receipts, executable hashes and nonzero native counts.
