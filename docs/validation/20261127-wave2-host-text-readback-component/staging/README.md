# Fixed Host2 materialization and execution handoff

This subtree preserves the reviewed staging wrapper and the exact compressed payload for the Host2 component published at `f6b7d9622af1d9f567a7680a423b8ff7920c8117`. It changes no product file, controller, input, test selection, resource floor, or earlier receipt.

The wrapper is `materialize_and_exec.py`, SHA256 `afefe9a5908eb91f6d06465d400d1fc894ae2d43626f95a14c3a6ff7a3344076`. The gzip payload is 131,419 bytes, SHA256 `ecd195f9ab6156f92dabd14ab26dd16cedfc014aaa54303247a82eeb28e57d67`; its exact decoded envelope is 611,097 bytes, SHA256 `9de9a66c55b60026ec61054094ffc7f12afdf310d8a04139f8376821df8744df`.

The envelope contains the unchanged `ef37ebaa…` packet and its 35 files / 448,292 bytes. The wrapper requires an externally recorded coordination-story argument, original resource admission, an absent physical destination, exact payload and input hashes, exclusive file creation, and positive readback. It prints a materialization receipt, then replaces its interpreter with the exact packet command. A failure retains the partial owned directory and does not retry or overwrite it.

Independent source review `ae9e7408c423746c261ee40d85090bb8879c6d8a02ff52b3425286bf310eeeff` is retained alongside the wrapper. It includes local decoding and byte comparison only. Actual upload, host capacity, filesystem admission, Swift compilation, HTTP fixtures, XCTest, Native, and Apple execution remain unperformed. This packet does not grant a runtime slot.
