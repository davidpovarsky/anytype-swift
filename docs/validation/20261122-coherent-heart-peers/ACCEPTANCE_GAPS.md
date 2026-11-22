# T2, migration, application and editor acceptance: actionable remainder

## Result of this review

The smallest executable next T2 step is implemented as a separate **coherent
native peer authorized-read → real network detach → cold offline reopen** route.
It closes a source-specific gap if its real CI run succeeds: existing peer
proofs precede the new coherent 139-path runtime, while the new coherent native
proof uses a local signed-authority fixture. Neither establishes that the new
authorized read is the first private read on a freshly recovered second peer.

The candidate is ready for parent integration from `implementation/`, using the
exact seven-file SHA256 manifest `COHERENT_PEERS_FILES.json`. Native compilation
and execution remain **NOT_RUN** in this handoff. No existing task was completed,
no remote file or Asana task was changed, and no old Go/Swift/Apple suite was
rerun during this child task.

## Exact task mapping and stale-note reconciliation

| Work item | Asana record | Current interpretation |
| --- | --- | --- |
| Full T2 | [1219604770636937](https://app.asana.com/0/0/1219604770636937) | Open. Its 2026-11-22 header records coherent native run 45026227924 and the independently audited originals. It explicitly excludes iOS, network ACL transport and automatic T2→T5 projection. |
| Two clients | [1219604672452040](https://app.asana.com/0/0/1219604672452040) | Open. The November 20 header still cites the old failed Space.Close setup; the later November 22 single-writer record qualifies 44943962391. The old failed run is retained, but the current close/reopen boundary is not still blocked by its old module-cache failure. |
| T2 architecture | [1219604675985609](https://app.asana.com/0/0/1219604675985609) | Open. Earlier text saying no sanctioned host/fixture exists is historical; exact native peer/retry/crash/observed-remove lanes now exist. This does not mean their full acceptance matrix is complete. |
| Single writer / device acceptance | [1219610263458741](https://app.asana.com/0/0/1219610263458741) | Open. The current header qualifies Space.Close 44943962391 and authorized-read 44954793488 in their stated scopes. Physical document-link/relaunch acceptance is separate and still open. |
| MIG-01 | [Any C: 1220709844846577](https://app.asana.com/0/0/1220709844846577) | Capability-inventory ID, owned by storage/schema/migration work. No separate exact-name MIG-01 task was found in the inspected project task inventories. |
| APP-01 | [Any D: 1220709922704118](https://app.asana.com/0/0/1220709922704118) | Capability-inventory ID, owned by application/UI integration. Whole-app parity remains a wider gate than an engine adapter or an individual UI journey. |
| EDITOR-02 | [Any D: 1220709922704118](https://app.asana.com/0/0/1220709922704118), plus [semantic anchor: 1219610432822791](https://app.asana.com/0/0/1219610432822791) | Captured UTF16 offsets and an excerpt are distinct from durable semantic anchors. The dedicated anchor task remains planned; it explicitly requires native mark persistence and edit/split/merge/undo/reopen proof. |

The acceptance IDs and their exact source definitions are in
[CAPABILITY_INVENTORY.json at b2fc380](https://github.com/davidpovarsky/anytype-swift/blob/b2fc3804426067dd1ec8318d6ea92a4bcb8e9545/docs/any-engine-port/CAPABILITY_INVENTORY.json).
The reviewed Asana snapshots, including modification times and comments, are
retained locally under `asana/`; `ACCEPTANCE_GAPS.json` records their digests.
The parent subsequently reported shared head
`e073b6ac48d15af1b0a630940b1440e3f65a45ac` with controller-only changes and no
Module/native source changes; this report does not promote those new runs to
success before execution.

## Existing results to retain without repetition

| Existing result | Scoped evidence retained |
| --- | --- |
| [44357252751](https://github.com/davidpovarsky/anytype-swift/actions/runs/44357252751) | Two complete native clients with empty stores and ordinary native LAN recovery. |
| [44382390827](https://github.com/davidpovarsky/anytype-swift/actions/runs/44382390827) | Actual partition, conflicting updates, reconnect/convergence and cold offline reopen on the then-qualified runtime. |
| [44387476318](https://github.com/davidpovarsky/anytype-swift/actions/runs/44387476318) | Lost client-byte response and identical retry; not a packet-loss or power-loss claim. |
| [44404120932](https://github.com/davidpovarsky/anytype-swift/actions/runs/44404120932) | Owned-process SIGKILL after durable commit before ACK; same-store offline recovery and unchanged identical retry. The killed process is not counted as PASS. |
| [44412158135](https://github.com/davidpovarsky/anytype-swift/actions/runs/44412158135) | Observed REMOVE/re-ADD, original claim preservation and retry; scoped source and original logs. |
| [44590443646](https://github.com/davidpovarsky/anytype-swift/actions/runs/44590443646) | Three actual generated-native target/account races. Does not by itself establish every settings, account-switch or network membership race. |
| [44943962391](https://github.com/davidpovarsky/anytype-swift/actions/runs/44943962391) | Later successful Space.Close and cold-reopen scope, superseding the obsolete setup blocker without rewriting the failed historical result. |
| [44954793488](https://github.com/davidpovarsky/anytype-swift/actions/runs/44954793488) | Authorized read: four new cases plus retained 67, two fresh processes over the same account/store history, read before replay, deletion/cleanup and stopped denial. Not simultaneous distinct stores over a LAN. |
| [45026227924](https://github.com/davidpovarsky/anytype-swift/actions/runs/45026227924) | Exact coherent 139-path closure, 10 methods/19 terminals, zero fail/skip, local same-account owner→reader→removed authority. Network membership delivery remains unexecuted. |

These entries are derived from the retained Asana/current handoff records and
original coherent audit. This task did not independently redownload every
historical artifact or execute any historical suite.

## What the new route actually adds

One new test method executes in three isolated complete native processes:
A and B simultaneously, then B's cold replacement. A appends one operation;
B receives only a recovery key and public identity/digest seed, recovers through
the actual owned LAN, and uses `PinkhaTorahAuthorizedOperationRead` as its first
private read family. Exact canonical bytes, claim, target, creator, native change,
ACL-head provenance and signed-history hashes must agree. Old ReadTarget and
append retry cannot prime B's read.

The host then disconnects B at Docker's actual network boundary, independently
inspects the daemon, and waits for native code to observe no non-loopback IPv4
interface. One offline read must retain the variant. After real AccountStop and
AppShutdown, a new process starts with B's same native store and `--network none`;
its first private read must succeed once with no retry or peer repair. The
controller requires different live host PIDs/namespaces/device IDs for A/B,
independent database inodes, and B's same persisted device ID after reopening.

Only this new method is selected. The original source patch is applied directly;
protobuf generation and prior account/control suites are not re-executed.
The known-good helper source and owner-labelled cleanup are reused. The new
receipt cannot say PASS if raw wire, original method log, source/binary identity,
secret screening, owned cleanup or publication finalization fails.

No external test account or physical device is needed for this step: it creates
and removes synthetic local-only native accounts within its owned stores and
internal network. A successful run would be a native two-device proof under
current known authority, not two iOS application clients.

## Remaining gaps and next ownership

| Gap | Concrete next requirement | Why the new route does not close it |
| --- | --- | --- |
| Network membership revoke/role delivery | Distinct member identities, an actual authorized native membership operation transported to the reader, then old snapshot/current read denial with nil private payload and exact cache invalidation. Own disposable account/Space fixtures only. | Same-account devices do not exercise transport of a different member's authority change. Local signed ACL mutation already has its own proof. |
| Unknown revocation while offline | State a bounded product policy for last-known authority versus deliberately unavailable protected reads; test actual disconnect, authority change elsewhere, reconnection and immediate fence. | Physical disconnection cannot communicate an unseen remote change. A cached known-authority read is not proof of unseen revocation denial. |
| Mixed-version/downgrade | Explicitly select two qualified binaries, bind each to source/patch/receipt, and preserve/refuse unsupported records through old edit, retry and reopen. Reuse original passing cases without changing the historical r14 failure. | Both new peers use the exact same coherent139 binary. Corrected-r15/coherent compatibility needs its own source-specific run. |
| T2 application/device gate | Two mounted application clients plus actual account/Space switching, document/block presentation and relaunch, and the remaining bounds/race matrix. | Linux generated-byte clients and shared Swift decoders cannot establish mounted UI or physical hardware behavior. |
| MIG-01 full Heart migration | Dry-run a complete Space/object/block map; identify unsupported body/file/Type/property cases before writes; preserve unknown data and provenance; perform idempotent explicit apply with native final readback. | Existing canonical association transfer is already scoped and proven. Whole-Space/body/file/Type conversion is additional software work, currently being separately reviewed by the parent/other agent. |
| APP-01 parity | Complete the exact original/custom application flow inventory, preserve engine identity and no cross-engine fallback writes, qualify remaining mounted Apple journeys and physical iPad. | Separate Any entry and individual passing flows do not certify all application systems. The parent owns current Apple/UI integration and runs. |
| EDITOR-02 anchors | Audit a stable native mark/anchor and versioned association identity; prove edit before/within/after, combining Hebrew/emoji, split/merge, copy/paste, undo and reopen. | Safe captured offsets/excerpts and block links are not durable selected-phrase anchors. Implementing a new durable identity model would exceed a narrow acceptance harness. |

Physical-device evidence is genuinely separate: the record contains an earlier
user iPad observation where block links survived reopen and document links were
missing from the UI. No later complete physical document-link/relaunch result
was available in this review. This is an outstanding device acceptance item,
not a claim that current source definitively loses stored document data and not
a reason to stop the executable native/Apple work already authorized.

## Integration instructions for the parent

1. Verify and copy exactly the seven owned paths from `COHERENT_PEERS_FILES.json`
   into the authorized shared branch; preserve all existing original evidence.
2. Add one dispatcher route `coherent-heart-peers` to the new reusable workflow,
   pass its reviewed full source SHA, and permit `contents: read` and `actions: read`.
3. Run that new native route once. Qualify original build/source maps, three
   exact method terminals, raw positive/stopped protobufs, peer/store isolation,
   actual detachment, cold first-read count and final owner/secret/publication gates.
4. Update full T2, two-client, architecture and evidence/handoff records with the
   actual commit/run/artifact digests and a narrow result. Leave every unrelated
   incomplete item and the explicit NOT_RUN/NOT_PROVEN scope fields open.
