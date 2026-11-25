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
