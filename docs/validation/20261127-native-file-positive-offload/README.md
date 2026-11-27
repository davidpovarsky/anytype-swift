# Positive full-tier Offload, cloud refetch and fresh offline read

This is an evidence-only follow-up to `972f6c2eaed18fdcfa4e5f885d519b3fb18a9aa7`.
The native product and its thirteen SDK overlay paths are unchanged. The actual
new proof uses the already qualified standalone Linux native1616/SDK735 product
(`9282a20d` producer, `cac96a8a` binary) and the original, already backed synthetic
file. It does not rebuild or replay the earlier authority, network or crypto
methods.

## Actual result

The raw [attempt2 receipt](receipts/attempt2-pass.json), SHA256
`75cfb31e711b2653905a76cf6faf3573976d3c88fa0548238b85c1ae916b85fd`,
records `PASS_ONE_BACKED_FULL_TIER_OFFLOAD_CLOUD_REFETCH_AND_COLD_READ_ONLY`.
Job `job_24459fd0443c` ran on 2026-11-27 from 19:46:37 to 19:47:02 UTC;
the controller measured 24.964 seconds. All four native processes exited zero,
were positively absent, and had no forced cleanup or cleanup errors. Each
normal shutdown followed a separately recorded, intentional SIGTERM to its
still-owned unreaped leader; no historical PID was signalled or probed.

| Phase | Observed result |
| --- | --- |
| Current Reader, online | One ledgered `POST .../BEaHYwGfZiM/offload` returned 204; the same full-tier file changed from cached to uncached while its ID, object, root CID, size and durable flag remained exact. |
| Fresh process, OS network denied | Metadata remained uncached and durable. The original native content route returned HTTP 500 with error code `internal`, and delivered zero file plaintext. |
| Fresh process, online | Alice was absent and local/global P2P discovery was disabled. The production network returned the same cloud CID and exactly 8,192 bytes with SHA256 `5b3ad191f3c210b61bd5d1ef5ffc838b7fbabe38e8b42207fa04bf2388831313`; the file became cached. |
| Fresh process, OS network denied | The same 8,192 bytes and hash were available from the restored cache. |

Each phase observed the same account as an active Reader before and after its
operation. Both offline processes showed no-new-privileges, seccomp filter mode
2 and zero network/local/global peers. The protected PNG `ahKeFKn7uta` remained
cached and durable with its exact original root CID, 12,420-byte size, explicit
`image/png`, `variant=thumb` and `variantOf=YhnuHkqoHza` metadata throughout.

The selected binary is genuinely full-tier because its root CID is nonempty and
native metadata reports `inline=false`; size alone is not the tier evidence.
The earlier [two-file cloud receipt](receipts/original-two-file-cloud.json)
`e6446c4f` and [protected-variant receipt](receipts/original-protected-variant.json)
`c23b78e3` bind the same exact identities. Their older processes were not opened,
probed or rerun by this proof or publication.

## Original failure and the narrow correction

The [original attempt1](receipts/original-attempt1-fail.json), SHA256
`875ed86695e1cf5acc8ef38f5b6e553cb8d2fb2ef4cb885e52727d61a0e162da`,
remains FAIL. Its protected-PNG check incorrectly demanded an original-file
identity for an already accepted thumbnail. The target binary had passed its
original-file check. No Offload POST was dispatched. The single original
process became absent after forced cleanup; that is not reclassified as a
normal accepted shutdown.

The successor preserves the binary's original no-variant assertion and requires
the protected PNG's exact historical `thumb`/`YhnuHkqoHza` identity. Its five
literal replacements invert exactly to the original 45,625-byte `58df056c`
controller; the 51,421-byte successor is `2079f987`. Both source artifacts, the
review patch and inverse manifest are retained under the accompanying
`Tools/AnyEngineValidation/native_file_positive_offload/` directory. The
pre-dispatch failure is an explicit successor admission, not a replay of a
completed cache mutation. The [source installation](receipts/attempt2-source-install.json)
`63285b0c` is distinct from the actual runtime proof.

These controllers are historical fixed-attempt artifacts. Their exclusive
output and exact-current-state guards must not be removed to rerun them. A
later operation requires its own reviewed state and output, with any uncertain
effect preserved and no automatic resend.

## Scope and limits

This closes the previously open positive full-tier cache eviction/refetch proof
for one existing backed file. It does not establish all-file cloud custody,
quota recovery, server-internal transport traces, Apple runtime integration or
adoption by Hanlin/MiniApps/Otzaria. The offline response is the original
`500/internal` behavior; it is not a new typed offline-resource UX contract.

No uploads, new accounts, account copies, role/invite mutations, Retry/Pin
calls, retained-account-file reads, private-record exports, CAR-file reads by
the controller, compiler calls or earlier acceptance-method replays occurred.
The native process can maintain its ordinary operational store. The controller
does not claim a fresh complete private-account byte-custody audit, and it did
not write caller plaintext payload files.

The latest retained [quota observation](receipts/historical-account-limits-read1.json)
is historical: storage was fetched at **2026-11-27T05:42:45.579472201Z**,
with `limitBytes=0` and `usageBytes=21070`. This Offload run did not refresh quota
or prove that capacity changed. The image and large-file all-four-cloud gate
remains limited; previously accepted two-file custody is preserved. A native
204 Offload or Retry ACK is not itself a new cloud durability receipt.

## Publication and reuse

The pure public-evidence validator independently binds the exact original and
successor receipts, controller inverse, source installation, native product,
four current-member phases, one mutation, CID/hash/cache transitions and four
normal closed groups. It executes no account, network, process or test action.

Publication adds only its declared evidence/control paths to the existing
owned network branch at exact parent `972f6c2e`. It preserves the complete
undeclared Git tree, runs the original zero-exit source-format gate, uses the
existing shared Git group for new objects, and requires the ordinary
UID1001/GID1002 reader to verify every new reachable object, ref and complete
tree before a normal non-force push. Original receipts and existing runtime
source directories are read-only inputs. No application code changes here.
