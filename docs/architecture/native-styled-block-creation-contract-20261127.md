# Native styled block creation contract — 27 November2026

## Route and scope

The qualified route is the current-writer native block creation route used by the exact executed controller in `Tools/AnyEngineValidation/native_block_creation/run_native_styles1.py`. The caller must first bind the current account, exact Space, active membership, and capability `currentWriterBlockCreate == 1`. The observed fixture has Owner authority; other roles require their own retained ACL evidence.

A request carries the native `type`, text, style object, and `nav` with exact parent ID and position. The accepted native names are `paragraph`, `heading`, `quote`, `code`, `list_item`, and `check_list_item`. The qualified style encodings are heading `level`, code `lang`, list `ordered` and optional `number`, and checklist `checked`. They are JSON values with their original types preserved.

A successful native response is201 with one fresh record ID, a nonempty change ID, and a nonempty opaque version. A consumer must retain the native-returned identity, verify exact readback, and avoid generating a replacement identity or automatically repeating an uncertain dispatched create. The Page201 response returns the actual object ID. These rules complement the existing Host account-generation and one-shot intent checks.

## Empty blocks, hierarchy, and limits

Empty text is a valid native create input for all six qualified kinds. An empty native row may omit text and an empty style object; consumers must interpret that representation consistently. A nonempty style must retain its exact typed values. In particular, false is not numeric zero.

The parent must be the actual native block ID in the same target object; the scenario uses the returned heading ID for one child paragraph and verifies it after a crash. Native positions determine the row order and are treated as opaque identifiers.

The exact native source admits at most65,536 UTF-8 bytes of text and at most256 UTF-8 bytes each for parent and position. The qualified scenario exercises the inclusive text limit using Hebrew and uses short ASCII positions. It does not execute the parent/position boundary. The currently pinned generic Host position validation permits up to1024 UTF-8 bytes, so consumers must apply the narrower native256-byte contract; that Host mismatch is an open source correction, not a qualified broader native limit.

The accepted heading levels1 and6 demonstrate these two representations. They do not establish that native code validates the entire heading range, and the style object is not claimed to be a closed schema.

## Crash and Offline acceptance

The native response, returned ID, text, exact style, hierarchy, and order must survive an actual process crash and a different process reopening the same copied local store under OS-level network denial. The actual result is recorded in `docs/validation/20261127-wave1-native-block-styles/original/result.json`: twelve unique rows, zero cold writes, and byte-identical warm/cold response SHA `e809788e7c3884b884e0276e73b2ffb4b3e895a49cf2f6a9a6236b3b610dda5f`.

The source artifact is native1dc1803 /1594-file manifest12ad65cd. This does not qualify a different executable or an Apple engine union. The source archive and original account remain preserved.

## Wave2 and Wave3 integration

Wave2 owns Add-block presentation, insertion location, focus, and gestures. Wave3 owns final target registration and the coherent Apple/native union. This contract supplies the native payload and persistence evidence. The Swift Host creator, UI dispatch, real native union, and visual interaction still require their respective qualified paths; native-only success is not substituted for those gates.
