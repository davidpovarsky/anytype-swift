# Native Heart snapshot semantic view

The consumer source is 025ca15eb104e1d331a83ab191a5762d7c19d6ba, based on the earlier qualified semantic-conversion branch d70704e1cca4dc094ec0fdda51d5be48833daef2.

## Actual bounded validation

Oracle Swift 6.4.3, 2026-11-24 18:06:29 UTC: six new NativeSnapshotViewTests methods passed, zero failures/skips; 89.26 seconds to build and 0.047 seconds in the selected suite. Original compiler/test log SHA256 is e6cf7f30ef3197ed0bb6a6e43c5dc5ea5c611678e59081d3249f6cc89d9f96a5. Only these six methods were executed. The three exact source files were unchanged before/after execution.

These are explicitly synthetic wire/parser controls, not native source admission. The separate native producer contract is pinkha-native-snapshot-json-v1 from the captured NativeRawObject.JSONView() implementation; its actual cross-language fixture control is pending.

## Behavior

The view binds the exact original protobuf bytes and JSON envelope to the expected Space/object, SHA256 and size. It retains both original byte streams, every JSON field, property detail and relation-link row. It reads the native child hierarchy in original order, refuses cycles/multiple parents and canonically equivalent identity aliases, and reports disconnected rows and unknown fields without dropping them.

Native text is already visible Unicode: it is not reparsed as export Markdown. Native UTF16 mark ranges are validated against surrogate boundaries before the existing destination text converter is used. Unsupported native mark kinds, code-with-marks and unsupported rendering semantics remain explicit failures. The object grants no authority or destination write capability; complete semantic mapping, native producer fixture validation and the full-Space executor remain separate gates.

No App, native framework or UI runner build was performed. No shipping source was merged into the shared branch by this evidence commit.
