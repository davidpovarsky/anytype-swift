# Actual native styled block creation and cold preservation

## Qualified result

The original native executable `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636` accepted twelve one-shot block creations on one new Page, and returned the identical twelve ordered block rows after an actual SIGKILL and a fresh process under OS network denial. The execution took 3.274 seconds. This is one actual native scenario containing twelve block mutations, not twelve independently executed XCTest methods.

The original receipt is retained byte-for-byte in `original/result.json` (SHA-256 `dc3d09497f0f247447d0394407c2b34a1b2cbf8dd357150244d849c5b89926d5`). All thirteen HTTP acknowledgements (one Page and twelve blocks), capabilities, and both complete native row responses are retained without rewriting.

| Case | Native type | Text | Style |
| --- | --- | --- | --- |
| Empty paragraph | paragraph | Empty | Empty |
| Empty heading | heading | Empty | level: 1 |
| Empty quote | quote | Empty | Empty |
| Empty code | code | Empty | lang: swift |
| Empty unordered item | list_item | Empty | ordered: false |
| Empty unchecked item | check_list_item | Empty | checked: false |
| Heading six | heading | Hebrew | level: 6 |
| Code | code | Swift source text | lang: swift |
| Ordered item | list_item | Hebrew | ordered: true, number: 10 |
| Checked item | check_list_item | Hebrew | checked: true |
| Nested paragraph | paragraph | Hebrew | Empty; parent is the exact newly returned heading ID |
| Maximum text | paragraph | 65,536 UTF-8 bytes of Hebrew | Empty |

The controller validates every 201 acknowledgement, unique record ID, change ID, nonempty opaque version, exact native row, and ordering. Empty text and empty style can be omitted in native readback; the controller validates their documented empty meaning without conflating JSON booleans with numbers. Warm and cold response bytes have the same SHA-256 `e809788e7c3884b884e0276e73b2ffb4b3e895a49cf2f6a9a6236b3b610dda5f`.

## Process and custody evidence

The warm PID3517177 was actually killed with SIGKILL and exited -9. The cold PID3517243 was different, performed no create calls, and exited 0. Both had NoNewPrivs=1, Seccomp=2, and zero local, global, and network peers; both process groups were absent at completion. The previously qualified unchanged OS-denial helper and syscall policy are reused, while each new process's actual flags and peer counts are checked again.

Only a fresh owned copy of the exact retained semantic fixture was opened. The source archive SHA-256 `be1806e5c72c3ee30dc2612fb3cb4148747247cb4771262f779303cf6a51b147` remained unchanged. The original account was not opened or changed. Private wallets and account directories are excluded from this publication. Original process logs remain at the recorded Oracle paths and are identified by their complete hashes in the receipt.

## Consumer contract and limits

See `docs/architecture/native-styled-block-creation-contract-20261127.md`. This result qualifies the recorded native HTTP creation/readback contract for the exact1594-file native source closure `12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c`.

It does not execute the Swift Host creator, a UI intent, a gesture, Apple code, or a later native union. Host source SHA `58a3ce0653a8973a07dce7e7dde80e1cb66a8bcce692652a47a8c8c60db684bc` was checked only as a static source pin. There were zero Swift, Go, or Apple builds and zero replays of the accepted182-operation migration. Owner creation here is not an additional ACL revocation acceptance.

Only short ASCII positions A through L were exercised. No position-length boundary, arbitrary style validation, or heading range-rejection claim is made. No file, image, embed, or unsupported block type is inferred from the six accepted kinds.

## Reproduction safety

The published controller `Tools/AnyEngineValidation/native_block_creation/run_native_styles1.py` is the exact executed2a524da7 source. It requires its exclusive output directory to be absent and uses one-shot mutation bookkeeping. Do not rerun it against the retained output or original account. The initial ambiguous transport dispatch was followed by an independent absent-output/absent-process observation before the single confirmed execution; it is not relabeled as a product test failure.
