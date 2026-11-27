# FilesV2 metadata and cache authority — qualified native successor

This packet adds the final metadata and cache-effect authority layer to the
previously published current-reader/lifetime layer at
`e330c0230f352cadff76b4fa0feafd1032fa142e`. It preserves the original Any and SDK
sources through exact before-images and a thirteen-path SDK overlay. The
standalone Linux producer and separate current-member HTTP18 qualification
have both completed. Every original failed receipt remains intact, including
the capacity admission that initially stopped before any account process.

## Production contract

`Files.Get`, `Files.List`, `Files.Status`, and `Files.Stats` require current signed
read authority and the captured account/Space lifetime before preparation and
again before publishing the materialized result. A changed signed ACL head,
removed identity, retired lifetime, or cancellation conceals the result, including
an error that would otherwise disclose a revoked member's cached object.

`SubscribeStatus` admits each event through the same authority and lifetime
boundary. Queued events after removal, retirement, or unsubscribe are withheld.
User callbacks execute without ACL, lifetime, or event locks. A callback already
admitted before cancellation may finish; the contract does not promise to drain
external callback execution when unsubscribe returns.

`Pin`, `Retry`, and `Offload` require current **read** authority. Readers legitimately
manage their local cache, and Guest permission is evaluated through the actual
signed ACL identity. The final admission occurs before the first queue/store
effect. Work then executes outside ACL locks. Original results and errors after
an admitted effect remain intact, including a partially completed Retry. Inline
and no-work paths still require admission. The layer does not cancel older
queued work or claim to erase previously released plaintext.

The original broker-facing `Query` and sealed `Payloads` interfaces retain their
documented public transport scope. No authenticated member metadata is added to
those broker interfaces by this patch.

## Exact source and product

| Item | Identity |
| --- | --- |
| Original Any commit | `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` |
| Original SDK commit | `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9` |
| Standalone Sync module | `github.com/anyproto/any-sync@v0.13.8` |
| Qualified base native source, 1,607 files | `aa43f853a28c2cd0e125b70cdcc01b05a4748f0c25541f5ed86cea511e6b8dd1` |
| Final thirteen-path candidate manifest | `71c0b47b5aea45a9ab0a2498f56361b0b7239fab183e37af7bb365dfb9b2ee81` |
| Final SDK patch | `9088b91cd098124b68d794185898aaf29d829a0e1b44ad3e8e06c914f4bb0350` |
| Actual tested SDK source, 735 files | `c70cea6f04851ccbbb6b312a4e760bfd3659351927439ec9632b71f81dbe3b82` |
| Actual native source, 1,616 files | `773f0a25422b3460a375182fb6f839fd71d7246ad8b489b6c20418bfab3b2471` |
| Actual Linux executable, 78,107,649 bytes | `cac96a8ab3edb6a2e908f423c45726818bcf3cc223d57aa4018869702be0ee21` |

Apply this overlay to the exact 1,607-file Any/SDK source admitted by the parent
reader qualification. The four changed existing SDK files must match their
manifest before-images; the other nine paths must be absent. The current original
reader/lifetime patch `874220977c12a789d77acbd7a86fa4889693a5196c32ef52effac20207dcc32f`
is unchanged. The thirteen-path union includes production, documentation, and
test inputs; it is not thirteen new production hooks.

Heart is a distinct producer. The Any executable above does not embed the
separate Heart core/RPC/FullSpace/account-run source, and this packet does not
qualify Apple bindings or an Apple runtime. Wave 3 must preserve both producer
closures when assembling its coherent source tuple.

## Actual qualification chain

| Stage | Actual result and scope |
| --- | --- |
| Original final34 attempt4 | Overall **FAIL** `173fdab404efc5340035151022946ae2324543cb7f10889fc47257efa79f24df`. The two owned commands closed normally. All 32 unit events passed; measurement JSON was split by `go test -json` output framing and the controller attempted to parse an incomplete fragment. No fresh SDK method started. |
| Completion attempt5 | Overall **FAIL** `eaa488134480fff5972d3cd6320966228f61b20805d7374a5cc14ee0cff7113c`. A composition-local variable shadowed the retained receipt. This failed before any child, test, or account. |
| Completion attempt6 | **PASS** `4be8657cd077774edc76767195a79f5e6b97fc10704dce12dc8f05f973a2d622`. Independently requalifies the retained exact 32 events and runs only the missing two fresh SDK methods. One new owned group closed normally. |
| Single final native producer | **PASS** `9282a20d65d2dc3006a9a256e6fbeda926089b84efc770609d4e32b54cb89602`. One build plus two metadata commands, all three normal/absent; zero account, native CLI, or test launches. |
| Current original-member metadata HTTP18 | **PASS** `8aaaf6fd04eb535bea79116ceaeac5a0dab6293d2d40bb1202616a6cef1c94ee`. Exactly eighteen typed403/acl.forbidden decisions in24.18 seconds; three normal0/positively absent native groups, source1616/SDK735/base unchanged. The preceding blocked capacity admission remains preserved. |

The aggregate34 is explicit: metadata16, cache-effect17, and one cached-stream
measurement. It comprises fourteen unit parents, eighteen named child cases,
and two fresh actual SDK methods. Each selected event is required exactly once,
with no fail or skip. The old unit process is never replayed or presented as a
new process. Original35, original fresh Files.Open2, original content HTTP14,
deadline2, and process-owner lifecycle5 receipts are reused with their exact
source scopes.

The new fresh SDK methods create only their own identities and data, install
the existing OS outbound policy before SDK initialization, and apply real
signed ACL removal through the original verifier. They cover member metadata
refusal, callback suppression, and nine denied cache-effect calls. Positive
Offload is presently an **inline** success. Full unsigned data still retains
the original `ErrFileNotBackedUp` protection; successful full-tier eviction and
redownload is a separate remaining proof.

## Bounded performance observation

The retained measurement reads exactly 64 MiB through each path in 1,024 calls
of 64 KiB, with the same expected byte hash. The original in-memory reader took
41,577,841 ns; the signed-lifetime guard took 137,442,559 ns in that one ordered
observation. The guard's additional allocation was 67,920,240 bytes and 19,459
allocations. The observation includes the private guarded buffer, and excludes
fixture creation, Open/Close, GC, and caller-buffer allocation.

These figures describe an ordered in-memory experiment, not native file-store,
disk, network, cloud, or device throughput. The ten-second condition is a finite
execution bound, not a calibrated regression threshold. There is no inferred
throughput PASS or claim that a 3.31× timing ratio meets an unprovided target.

## HTTP boundary and remaining limits

The original content-only receipt
`7efa899783f5cabb54b2693dca0a22a9571d499ef4b9838749dfb8e677784099`
recorded fourteen content denials but also five cached metadata GET200 results.
That receipt remains valid for content only and remains the explicit metadata
baseline. The reviewed GET18 controller actually required five metadata Gets,
two Lists, one Status, and one Stats denial online, then the same nine in a fresh
OS-offline process. It verified removed/none self-membership before and after
each phase, actual NoNewPrivs1/Seccomp2 and zero peers in the offline process.
Unexpected status stops before reading a body. No roles,
invitations, uploads, cache operations, restoration, private-store inspection,
or old content14 replay is allowed.

The production cloud's observed quota limit of zero and LIMITED files remain
unchanged constraints. No all-file cloud durability or quota bypass is claimed.
The prior twelve network scenarios, two ACL controls, two P2P controls, nine
crypto/integrity controls, and original migration proofs are preserved rather
than rerun without a source-related reason.

## Publication safety

The new publication is prepared on an isolated branch from the exact parent
commit. It adds only its two new source/evidence prefixes, preserves the full
undeclared Git tree, and uses normal commit and explicit non-force push. Git
children use the existing `chatgpt-agent` effective group 1002. Before push, the
ordinary `ubuntu` reader must read the complete new object closure and exact
candidate tree, including any already packed objects. No shared directory,
reference, config, private account, or other lane's source permissions change.

Original candidate manifests and failed receipts retain their original bytes
and source-only/FAIL labels. Current acceptance is supplied by separate actual
receipts; historical documents are not rewritten to manufacture success.

## Lossless historical controller artifacts

The first publication attempt stopped at the unchanged Git whitespace check
with exit2 because three historical Python qualifier artifacts contain extra
blank lines at EOF. Its original FAIL receipt and staged tree remain retained.
The historical source bytes are preserved, including those blank lines.

Only those three artifact copies are represented as deterministic gzip streams
with mtime0. `historical-qualifier-archives.json` binds each logical raw path,
original qualified Oracle source, raw length/SHA256, encoded length/SHA256, and
verified inverse. All thirteen SDK overlay paths and every actual test receipt
keep their original bytes. The publication's original Git whitespace check must
return zero; no formatting or functional acceptance exception is introduced.

The source packet now contains52 files: the former51, with the three historical
`.py` artifact paths replaced by `.py.gz`, plus the inverse map. `FILES.json`
describes the actual encoded publication. `publication-inputs.json` remains the
unchanged original logical input plan. Decompress historical controllers only
to exclusive new paths and verify the map before any use; this publication does
not re-run them. The original raw controllers and both publication attempts are
retained independently, and the unchanged evidence validator still consumes its
original logical raw-file dictionary.
