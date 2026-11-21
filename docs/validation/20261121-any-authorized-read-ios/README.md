# Real iOS authorized-operation read — original run 44954305345

**Qualified scope: one actual iOS method passed. Full T2, two-client acceptance and default runtime activation remain open.**

The original [run 44954305345](https://github.com/davidpovarsky/anytype-swift/actions/runs/44954305345) executed commit `abc1aebfcdebbe801aab928e9576f39ef3c7f0ac` on an owned arm64 iPad mini (A20 Pro) Simulator, iOS 27.2 build 24B8117. The raw result contains exactly `AnyAuthorizedOperationReadRuntimeTests/testManagedNativeAuthorizedReadPreservesBytesAcrossBlockDeletionAndColdReopen()`: **1 passed, 0 failed, 0 skipped**, actual method duration 7.273383 seconds.

Original artifact 14728139061 contains 54 files, 188815 bytes; ZIP SHA-256 `bd88b21312d0a64023159cb8f6c4b9556e71bbfd7a3c2df85e36c8ea649fdc35`. The small originals in `original/` are copied byte-for-byte, including the named receipt `ed9fd933641fbf6426a4882680175ccd71688039b3e00fb81737afad374b89e4`, raw summary and raw tree. The complete ZIP remains in the private build archive. Independent qualification and root peer review agree; neither reran a test or rewrote the original receipts.

## Assertions actually exercised

The original executed source (SHA-256 `9881039e8f4d665616ae66bc57d205dc21a70f29a7f46b89dfa8d0af618ca052`) starts the real C library and managed control/HTTP session, creates a disposable account/Space, and constructs the real owned Host and shared reader. It then verifies:

- A read on a fresh Space returns history unavailable and leaves the protected bundle absent. Installation remains an explicit write; afterward an absent operation returns an empty verified local snapshot.
- A real append is read with exact canonical bytes, including non-UTF-8 payload bytes and Hebrew, matching author, Space, object/block identity, creator, native change ID and a nonempty native ACL head.
- After deleting the block, the original operation remains byte-identical and is classified as unreachable; the native snapshot token changes.
- The actual C runtime stops and starts using the same disk directory. The same disposable account is restored, a fresh owner/session is created, and all operation variants/provenance remain exact.
- The retired old reader refuses access, and its closed owner cannot construct a new reader.
- After the whole target object is deleted, the reader returns target-state unavailable instead of an operation payload.
- The owned Space is removed, the account signs out, the runtime stops, and the temporary directory is deleted.

**Boundary:** runtime stop/start occurs within the **same iOS test process**. This is not an app-process restart. `session.revokeAndDrain()` demonstrates owner retirement; it is **not a signed native ACL revocation test**. No second client, cross-device convergence, pagination/watermark contract or full-T2 claim is added.

## Independent source and binary qualification

All 16 recorded Swift, test, manifest, patch, verifier and workflow hashes match the original producer Git objects. The original named receipt's raw count/tree hashes, owned destination, exact method and native consumer binding were independently checked.

Native artifact 14727569084 has ZIP SHA-256 `cb3874c36e9b330194d3c3a451d5cb4d5ab0071d1a1f58a32ce77c5200d0e6d2`; its inner XCFramework archive hash is `ae3d6bbbe0fcaeadce8d3e40015cb4f7631fb728b973a7d51e198ac8eb875cea`. All 7 original member hashes and both required arm64 device/simulator slices were independently verified. All 54 Any and 41 SDK source records match the exact candidate manifest, whose SHA-256 is `e289b8a79cbc66ec9ffc1d772b2d4bc4ea707a5851de3c963c01f6d5f3101997`.

The complete candidate input manifest stays immutable. Its earlier pending iOS-adapter field is not rewritten to create a new binary identity; this original result records the scoped qualification separately. Default v9/native UI acceptance remains independent.

The archived privacy inspection reports only whether credential-labelled values or bearer-looking tokens were found in the actual runtime log; it does not publish the log or credentials. The full logs/xcresult remain in the original private artifact/build archive.
