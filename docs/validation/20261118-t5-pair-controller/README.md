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

## First real pairing attempt and the existing dependency pin

Run 44213836790 on integration 45f890c72edcc8d37802077c353ec4d5a05041ae reached old-binary compilation, then failed at package setup: the obsolete root genproto 202109 module and the split googleapis/rpc module both supplied the status package. No binary or native phase was completed. Original evidence artifact 14387372852 is retained under 44213836790; its verified archive SHA-256 is c38c9a55633283dfdd40f87ef2b1ac7f76bd1a0b3ec8341336fb2be57dfd9106.

The already reviewed source947 integration and compatibility modules both explicitly require google.golang.org/genproto v0.0.0-20241021214115-324edc3d5d38. The three passing native component runs resolved that version. The revised pair wrapper uses a targeted replacement to this same root-module version in each temporary go.work, keeping only the corresponding Heart module in use. Heart go.mod/source, native package selection and the preserved fixture are unchanged. The canonical compatibility declaration is additionally checked by SHA-256 6616b2ae644a325a32edaae1528c5e5c2d41a1ff17c1ed4d1b84beec5242958d.

The exact module and go.mod h1 checksums were read from the official Go checksum database; original lookup bytes are preserved in genproto-sumdb.txt. Before either binary is compiled, the actual go list -m -json selection must match the reviewed module path/version and both checksums. Each role retains that selection and all resolved module metadata in its build receipt.

Six updated CI-control tests passed, including rejection of wrong revision, fork and checksums. Python parse passed. This is control validation; the corrected native pair still needs its own new run and nonzero phase evidence.
