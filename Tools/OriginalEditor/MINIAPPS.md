# Original editor MiniApps adapter

The existing prepared editor, writer owner, text/block services and original
ObjectShow/protobuf export remain authoritative. No engine or Picker is embedded.

## Durable launch

1. Mount the local annotation session and install setMiniAppsAction(title:handler:)
   for the original text menu. The Host toolbar calls captureMiniAppsContext().
2. The context is Codable. selectionLocation/Length are UTF-16 offsets within
   the native block. documentSelectionLocation is present only for a verified
   contiguous substring in documentText. Noncontiguous selection stays native.
3. captureMiniAppsLaunch(context:maximumBodyBytes:) freezes the retained Host UI,
   drains native writes and returns a complete terminal archive plus context.
4. Save that archive through the original SQLite CAS; retire and reopen the saved row.
5. restoreMiniAppsContext(launch.context) admits exactly r+1 only if the original
   draft journal canonical SHA-256 equals the saved launch body. It maps new
   private native IDs by the complete ordered protobuf graph, never text alone.
6. Persist the restored context before dispatch. Cold return checks the exact
   canonical source and full native mapping. A mismatch preserves the result.
7. Restoring into the same retained native object preserves the original context
   even when unrelated blocks changed. Return validates the affected targets;
   replaceDocument still compares the complete graph. Restoration never advances
   the baseline to silently accept edits inside the original target.

## Return

applyMiniAppsResult(requestID:context:action:text:maximumBodyBytes:) uses original
owned services, verifies native readback and returns the complete terminal rich
capture. It preserves block identity/tree, non-text content and unaffected marks.
The text-only overload remains available. The attachment overload accepts bounded
Data/name/type values. It creates original native file blocks through the owned
file service, verifies FileDownload bytes and the final native export, and never
turns a private file URL into document text. display/custom actions stay in Host UI.

Before terminal launch capture, exportMiniAppsFiles(context:maximumBytes:) reads
selected file blocks (including selected descendants), or the captured document's
files when no selection exists. The Host registers these bytes in the shared
Bridge. No private app URL is exposed across applications.

## File cancellation and replay boundary

Native upload, terminal archive capture and the Host SQLite transaction are
separate operations. File blocks carry the request UUID and file index before
upload; those fields are observations, not an atomic native receipt. Explicit
cancellation checks run around native reads and mutations. Any failure after
attempting a mutation retires that private draft. The caller must not retry it.

A retry reopens the unchanged canonical SQLite archive. The original runtime
creates a new UUID draft journal and a fresh private Space/materialization, so
an uncertain old native draft is never attached to the canonical document.
Unknown old native effects are retained for original lifecycle recovery. If the
SQLite archive+receipt commit succeeded, its receipt suppresses replay before
native apply. A crash/file journey in the actual Maktabah editor remains required.

The original 1 MiB compressed and 8 MiB expanded archive limits remain unchanged.
Returned attachment bytes remain bounded by the original 8 MiB budget; a terminal archive
that exceeds its compressed limit fails without committing or acknowledging the
result. The existing 64 KiB native qualification reader retains its old bound.

Commit the opaque body AND exact Bridge request/result receipt in the SAME
original SQLite CAS transaction before ACK. Native read/check/write is not an
atomic distributed transaction. Failed draft writes never commit the canonical row.

## Acceptance still required

Swift parse/source/surface checks do not prove native operation. Validate rich
marks, table cells, file preservation, emoji/Hebrew UTF-16, original menu/toolbar,
warm/cold return after baseline save, newer edits, source retirement and duplicate
callback in the real framework/Maktabah app from the final source.

## Current SDK build provenance

The MiniApps continuation binds exactly eight Swift changes to reviewed source
e2582894e9141f4a136823d4c7b4a011d1edbd80 after the original revision
continuation a91d572. Source admission verifies all original 733 generated files,
every product tree and each changed byte; its old receipts are retained unchanged.
The lifecycle/batch continuation and reviewed native-file continuation now require
292 public/SPI declarations, including 10 file boundaries and the original 22
qualification SPI members. All earlier requirements remain. Source provenance
alone grants no native or current framework acceptance.

The existing local producer can run on the explicitly owned MiniApps facade
branch with its own real Mac execution UUID. The actual source/tree/path/branch
and host remain bound. No fabricated Actions identity is accepted.

Native ABI reuse independently revalidates its original owner, source, retained
build, exported bytes and native/generated/wrapper/resource input trees. Only
the exact reviewed application Swift delta can differ; application Swift is
not a Go mobile build input. This grants no new native behavior or UI acceptance.
The current SDK must still compile, link, preserve original resources and pass
its real external consumer before a Host can use a new distribution.

The optional --derived-cache-seed accepts only the independently verified
original ABI donor's inactive retained compiler cache. APFS clones isolate all
writes. It reuses dependency/compiler caches only: the current Xcode build,
complete source and dependency checks, symbols, original resources/signatures
and external consumer remain mandatory. No cached test result grants acceptance.
