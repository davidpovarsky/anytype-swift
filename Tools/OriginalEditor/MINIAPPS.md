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
The current result facade accepts text; display/custom actions stay in Host UI.

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
The full public compiler contract now requires 198 declarations, including all
23 new MiniApps boundaries; it preserves every original public/SPI requirement.

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
