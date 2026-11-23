# Loaded-account native profile: source freeze only

This packet proposes one offline native build and four new method invocations.
It does not repeat the qualified source query, codec completion, earlier Witness
methods, native lifetime methods, or structural census methods. The four methods
are still NOT_RUN. No mount, cache copy, container, build, or test was started
while authoring this packet.

## Fixed source and observed graph

The Heart candidate is 24dc6393b30e6d1d80ec28ff624060af9bb4327a. The tracked any-sync
candidate is c005bd6cde8d8f8a6007c35f06894f3d89f9f07c. Both production additions use
pinkha_loaded_account_witness; the four controls additionally require
pinkha_loaded_account_witness_acceptance. Original go.mod/go.sum and the original
module/cache trees stay unchanged. The candidate modfile contains only the
already-reviewed local any-sync replacement.

The source-stage qualification is 2fe6dc18b127cf6411a9b458230ab50523ac8eaa49146ab70eee884b8871eef8.
Its graph has 1,455 package records, 204 module records and 11,627 input rows.
The 11,626 ordinary rows total 173,483,934 bytes; the largest is 9,029,884 bytes.
These are explicitly later offline observations. The single generated test main
retains its original query metadata and separately preserved 3,282 bytes. The
native phase checks current ordinary rows again and captures the actual build's
generated source separately. It never calls an old RAM inode a current inode.

The original projected query returned zero with complete stdout. Its aggregate
wrapper failure remains FAILED. The offline completion also retains its original
aggregate FAILED result; its graph/source equality was separately qualified.
The later 28-row controller audit does not recreate historical missing loaded-
after or current-after observations.

## Actual compiler prerequisite failure

The selected image is
sha256:f2f98726820d0342055351c6e9d36e705f5bfffb3dd53ff556325114b08afb6d.
It was qualified for the source-only query, not for native compilation. Root's
separate read-only inspection found an immutable postgres repository digest and
Linux ARM64 platform. This does not establish gcc, g++, assembler/linker support,
musl development headers, or the final Tantivy link.

The new manifest marks this compiler support BLOCKED_COMPILER_SUPPORT. The root
immutable-layer reader found no gcc/g++/cc/c++/ld/as/ar/ranlib in the image PATH.
Its original 11,930-byte result SHA is
ca681802575e0fd0d135be251184b89949dde0f46a957755ff2c019fa5013a76.
The compiler absence guard refuses before RAM/cache/container/build activity.
The prior docker-save reader failure remains separately preserved by root.
Before any native
execution, an exact immutable compiler/image support receipt is required and must
be reviewed with the final execution profile. A successful Go list, a warm cache,
or available Go tool binaries cannot satisfy this prerequisite. The current
packet is not native execution admission.

## Resource profile

| Resource | Proposed bound |
| --- | --- |
| Oracle build admission | 2,950,000,000 free bytes |
| Oracle active stop | 2,600,000,000 free bytes |
| Oracle final reserve | 2,500,000,000 free bytes plus the bounded final receipt |
| Host memory before new RAM/cache | 9 GiB MemAvailable |
| Memory immediately before build or each method | 5 GiB MemAvailable |
| Active/final host memory stop | 1 GiB MemAvailable |
| Controller address space | 512 MiB |
| Container memory / memory+swap | 4 GiB / 4 GiB |
| Container Go memory target | 3 GiB |
| CPU / process ceiling | 1 CPU / 256 PIDs |
| New RAM cache | 4.25 GiB, 262,144 inodes, noexec |
| Original cache bytes admitted to clone | at most 3.75 GiB |
| New RAM compiler temporary files | 512 MiB, 32,768 inodes |
| New RAM product | 256 MiB, 1,024 inodes |
| Cache copy, inventory and independent readback | 120 seconds |
| Native build | 900 seconds after its preflight |
| Each native method | 210-second Go timeout; 240-second command budget |
| One stage / external execution window | 1,350 seconds / at most 1,500 seconds |
| Build stdout / stderr | 1 MiB / 8 MiB |
| Each method stdout / stderr | 8 MiB / 1 MiB |
| Combined retained metadata | 16 MiB |
| Observed Oracle attempt bytes | 160 MiB |
| Final result preservation | at most 512 KiB per original result |

All RAM mounts are new, fixed, private, nodev/nosuid tmpfs mounts. Cache is noexec;
compiler temporary and product mounts permit execution. Ownership is the exact
ordinary UID/GID 1001. No old cache is mounted writable.

The host-memory estimate is a ceiling plan, not a measured build peak:
3.75 GiB copied host cache + 4 GiB container allocation + 0.5 GiB controller
address-space ceiling = 8.25 GiB. The 9 GiB start leaves at least 0.75 GiB before
other activity. New cache pages, compiler temporary files and product pages
allocated by the container are also subject to its memory cgroup. The cache
tmpfs maximum is larger than the allowed initial clone, leaving at least
0.5 GiB before its own hard limit; this is not an estimate that the build fits.

Native command output files have hard byte limits. The combined Oracle fixture/
receipt limit is an observed limit checked during command polling, source
checks and finalization; it is not a filesystem quota. A native write may occur
between observations. The 2.60 GB stop margin, exact owned container stop and
separate first-error retention remain necessary. Source/metadata authoring used
the separately authorized small-write profile and does not lower these gates.

Streamed file_row byte counts, explicit fixed_bytes rereads, cache-copy byte
counts, raw event reads and independent private-frame reads have distinct scopes.
No one counter is described as all physical I/O. The fixed source graph and
tool manifest bound the before/after input sets. Native tool availability is
recorded separately from actual executed binary/tool provenance.

## Process and storage ownership

The process enters through sudo with the exact fixed IDs/groups, adopts ordinary
real/effective UID 1001 before project imports or file/Git operations, and retains
saved UID zero only for the reviewed registered-Popen cleanup primitive.
The unchanged cd5e projected helper is imported only for owned operations; its
query/main functions are never called. Only its current operation-receipt root
and actual entry-credential receipt are bound by this adapter.

Every native command has a caller-owned record before launch. The controller
binds actual Popen PID=PGID, exact container name/CID, source label, image ID,
entrypoint, argv, full mount map, fixed environment and resource options.
Only that exact container can be killed; container quiescence precedes CLI group
cleanup. Privilege restoration and group absence are separately observed.
The original command failure stays primary; later cleanup/audit/capacity errors
cannot replace it. A source/receipt failure after launch cannot erase its launch
record.

The image is the entire build/test environment. No PostgreSQL service is started.
Its declared data volume is covered by the fixed empty read-only mount. Source,
Go root, Tantivy and module cache are read-only. The real account databases and
private fixtures remain on Oracle, not RAM, preserving actual disk-backed native
storage semantics.

Fresh RAM/cache paths are validated by canonical path, mount ID/device, parent
and directory inode, exact flags, owner, capacity and inode ceiling. Cache
copy records every original tuple and SHA, independently reads back each copy,
and compares the original inventory before/after. It neither evicts nor rewrites
the original cache.

## Two stages, exact four methods

Build creates one binary with the fixed offline go test -c command, fixed
modfile/tags and -work -x. An observed WORK line distinguishes actual Go build
entry from merely attempting to launch Docker. The ELF is required to be ARM64;
the binary's hash/full tuple, Go version metadata and actual generated main are
retained. The available tool map is not represented as all tools actually loaded.

Execute requires the exact original successful build receipt hash and unchanged
binary, source, dependency and RAM identities. It invokes that same binary once
for each literal method:

1. TestLoadedAccountWitnessBindsActualAccountSessionAndHead
2. TestLoadedAccountWitnessRefusesUnboundSessionsAndLoadFallback
3. TestLoadedAccountWitnessACLAndSessionCancellationReleaseActualLocks
4. TestLoadedAccountWitnessRejectsForeignOwnerStoredHeadAndStoppedApp

Each method runs in its own fixed owned container. The original package has no
TestMain or test-file init entrypoint. Other test sources may be compiled into
the binary, but their methods are not selected. Real named starts, terminals,
package result and safe observation markers must agree.

A failed method retains its actual outcome. Remaining never-run methods may
proceed only with complete owned cleanup and resource admission. A method that
already passed is never automatically rerun. Any source correction requiring
another build is a separate review and attempt.

## Independent private evidence

native_audit.py reads only the fresh private fixture for the selected method and
its original stdout. It checks exact typed observation/completion shapes,
account/full-session/local-permission flags, source/native receipt hashes and
the independent length-framed decoded-value witness.

Every captured collection and row, including empty/unknown collections, is
parsed and accounted for. Typed row IDs remain byte-sensitive. The state ACL
ID and one captured heads.h value must join the held ACL hash in the receipt.
The original fixture assertions remain actual test outcomes, not synthetic
success inputs.

All raw native logs, wallet/store files, row values, keys and private frames stay
under the private 0700 boundary. Public summaries contain only fixed labels,
counts and hashes. The third method's stack observation is explicitly test-only;
it does not prove the later session closer had already blocked.

## Finalization and custody

Current source, ordinary graph inputs, available tools and actual loaded Python
origins are checked before and after each stage. Final disk/memory/attempt and
metadata observations occur after those audits and before classification. Actual
named passes remain visible if the aggregate receipt fails.

The controller never unmounts RAM, deletes a cache, removes its containers, or
discards a product. BUILD_PASS_RAM_CUSTODY_PENDING and
FOUR_NATIVE_METHODS_PASS_RAM_CUSTODY_PENDING intentionally retain that open
custody stage. The original binary and any failed compiler partials must be
copied to private immutable storage and independently read back before a later
separately reviewed exact cleanup. Original clone bytes remain reconstructible
from the preserved unchanged cache and full clone receipt; new/changed cache
entries and unexpected temporary files must be explicitly accounted for.
No unknown payload is silently discarded.

## Scope after these controls

Even four actual passes would qualify only the opt-in current application,
account-directory lease, full unassociated session, already-loaded Space,
current local ACL and same-native-store snapshot boundary. They would not
establish whole-Space semantic reconstruction, replay/signature validity,
complete file-payload coverage, remote freshness, migration write admission,
or destination behavior. Original D/E/F/SDK/device gates remain separate.

A portable ARM64 CI profile would require a distinct host-origin adapter and
new actual physical records. It must not spoof Oracle inode/UID observations or
publish private account fixtures in a public repository artifact. No CI route
or dispatch is part of this packet.
