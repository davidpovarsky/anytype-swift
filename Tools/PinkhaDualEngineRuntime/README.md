# One native runtime for the shipping app

This producer builds Heart service/core and Any's original mobile bridge in one
gomobile invocation. The generated Lib framework owns one Go runtime; the Swift
shipping host reaches both engines through ProtobufMessages. It must not link the
standalone AnyLib framework as well.

## Frozen input closure

The current source manifest is
`3a8c9db276aa039b281c6fbcb10cd23f78fbaf38fef453874d0d9e128bf597c1`
(4,852 exact source files). It includes Heart
`ea796999d648e27dcb7ad23a0bbd849d35fadc5a`, the original Page154 closure, the
loaded-account capture/revalidation bridge product delta
`169b39b3e76f89a76b23bd8e3f4515d6ae3150ca`, Any
`cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3`, SDK
`e195f6c07a053c6588e39ffe72ee4fc44cf3d953`, and the exact any-sync ACL witness
donor `c005bd6cde8d8f8a6007c35f06894f3d89f9f07c`.
The two iOS Tantivy v1.0.6 archives are a separate explicitly hashed dependency
closure. Their original releases remain retained. Only embedded legacy LLVM
metadata is removed, using the helper committed by C at
`a8f8e687147d5d3b0564481d6bc1f086c01dacde`. Native code/data, symbols, relocation
targets and platform load commands must all be identical. Go's LTO checks remain
enabled. The Mac independently compares actual native symbols before compiling.

The shim preserves the original four-module workspace as the compile authority.
It executes and retains gomobile's real tidy step, then compiles the owned bridge
as a fifth main module in a private derived workspace. Every original module
path, version and original checksum is checked against the actual graph. Neither
source modules nor shared module caches are rewritten. This was verified by the
actual Mac module-graph probe under source26:
`generated-module-probe-5/result.json`. The earlier standalone graph mismatches
remain recorded as failed attempts, with no native build claim.

## Required execution checks

Run `build_apple.py` only on the Apple Silicon Mac, with a fresh fixed source-hash
root containing the exact source archive, dependency archive and committed
controller files. The producer records its real local-Mac execution kind,
controller commit, command logs, owned process groups, source/module/dependency
identities and both device and simulator slices. It verifies all exported
Heart/Any/capture/semantic/authorized-read entries, the single Go runtime symbol
set, and the actual Swift import surface. Source files are checked again after
compilation. Pinned Tantivy machine code is repacked into the two static slices.

The 8GiB initial admission and 2GiB emergency stop apply only to this measured
native phase. Go's normal keyed cache may be shared with the coordinated C lane;
source/work/tmp roots and command journals are private.

A generated framework is **not app or migration acceptance**. The producer
receipt explicitly reports zero app builds and zero acceptance tests. The new C
bridge still requires actual authorized capture/revalidation execution; semantic
migration admission stays closed until its real coverage is proved. The shipping
app must separately compile and exercise both engines, switching, existing
features and affected adapters before signing.
