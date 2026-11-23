# Typed Heart semantic capture candidate

The product boundary uses native plain text and every ordered protobuf mark. It shares the existing canonical anchor identity with PinkhaKit without editing PinkhaKit or converting text through inline Markdown.

The exact native Page154 source manifest is 2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38. Its two actual native Page methods passed, including signed stored-change decoding and different-process recovery. Their safe request/reply/protobuf bytes are copied without modification into the new test resources, with origin SHA and hashes in SOURCE.json.

## Product path

1. A downstream App adapter accepts the existing PinkhaSemanticTextAnchor identity and native block selection, then obtains the unforgeable current owner/Space lease.
2. The typed client validates actual AppGetVersion against the exact154 profile, reads current ObjectShow, and compares the complete native block before queuing the mutation.
3. The additive Lib call sends only version, Space/object/block/anchor identity, UTF16 range and full text/ordered-mark CAS input. The native writer lifetime and ACL remain authoritative.
4. The reply boundary rejects duplicate keys, invalid UTF8/UTF16 escapes, unknown fields, noninteger versions, noncanonical base64, malformed receipts and byte-identity mismatches. It validates one exact mark-only native ResponseEvent for the expected context and Space.
5. The actual returned native event is sent through InvocationSettings.handler.eventHandler, followed by current ObjectShow ownership, digest, complete-mark and non-mark-field readback. No alternate event publisher or automatic retry exists.

Cancellation is honored before queuing. After queuing, an owned task completes publication/readback; cancellation cannot turn a committed mutation into a blind retry. A consumed intent cannot be submitted twice. Owner retirement at every asynchronous boundary prevents an unverified result from becoming a verified receipt.

Readback tolerates only unchanged upstream Base.Diff's absent/present-empty Restrictions message normalization; meaningful restriction fields and every other block field remain compared. No claim is made that arbitrary preexisting blocks preserve raw nil-message presence.

## Source ownership and activation

New PinkhaHeartSemanticAnchor source files, matching controls and AnytypeHeartSemanticAnchorService are downstream-owned additions. ProtobufMessages/Package.swift is a narrow shared-integration change for the exact154 candidate define and new test resources. No generated protocol, schema, Heart source, PinkhaKit source, upstream editor or existing invocation reducer is edited. Live upstream develop was observed at d857b23ea540be33d6faab4f7a7a1a260ab578c1 before this isolated worktree was created from d254a4a1ccd9288f585ff9374088cbaf965b36b4.

The candidate define requires both PINKHA_NATIVE_T2_AUTHORIZED_READ_V1=1 and PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1 set to the exact manifest SHA above. The enabled bridge directly references Lib.ServicePinkhaSemanticAnchorCapture, so current139 Lib cannot compile that path. Runtime AppGetVersion must also match pinkha-semantic-anchor-native-page-candidate-v1-<exact154manifest> before mutation. The App target must receive the same Swift defines when its candidate adapter is compiled. Shipping capability remains OFF.

## Oracle controls

run_controls.py copies exactly695 current source files: unchanged685 generated protocol files, existing lifetime/Invocation protocol support, and the five new boundary files. It includes only the22 newly authored methods listed below and the exact native Page2 artifacts. It does not invoke any earlier qualified XCTest or Go method. The native SDK body is inactive in this Linux composition; actual154 Objective-C header, binary symbol, Swift typecheck, App compilation and mounted selection/Apply are separate Apple gates.

The host profile is Swift6.4.3 on aarch64 Linux, SwiftProtobuf c6fe6442e6a64250495669325044052e113e990c, SwiftCrypto3.12.3 at e8d6eba1fef23ae5b359c46b03f7d94be2f41fed, and host-only SwiftASN1 1.7.4 at917b472dbe53ba699cbb0495f9a95a084bc6364d. The latter matches the already used Oracle Crypto cache; this fixture profile does not change the App's frozen Package.resolved. Apple uses CryptoKit for this source.

Use a clean exact source SHA and separate run/build/cache paths under /mnt/development. Modes are prepare, verify, resolve, build and test; each receives --run RUN --build-root BUILD --shared-cache CACHE --expected-app-sha SHA. Build is -j1 and compile-only; test uses --skip-build with the22-method selector. All copied sources, dependency revisions and both actual Swift6.4 test runner/module plus bundled resources are checked, and original command logs and named XCTest events are retained. No source-only completion or Apple/mounted result is implied.

## Selected new controls

- PinkhaHeartSemanticAnchorClientTests.testCancellationAfterDispatchCompletesPublicationAndReadback
- PinkhaHeartSemanticAnchorClientTests.testCancellationBeforeDispatchLeavesIntentUnconsumed
- PinkhaHeartSemanticAnchorClientTests.testChangedCurrentNativeBlockPreventsMutation
- PinkhaHeartSemanticAnchorClientTests.testDivergentReadbackOrRetiredOwnerNeverReturnsVerifiedReceipt
- PinkhaHeartSemanticAnchorClientTests.testForeignSpaceCannotAcquirePendingIntentFromOwnedLease
- PinkhaHeartSemanticAnchorClientTests.testOwnerRetiredInsideNativeCallPreventsPublicationAndRetry
- PinkhaHeartSemanticAnchorClientTests.testRefusedAndMalformedRepliesNeverPublishOrRetry
- PinkhaHeartSemanticAnchorClientTests.testRetiredOwnerBeforeDispatchHasNoNativeCall
- PinkhaHeartSemanticAnchorClientTests.testSuccessfulPendingIntentCannotBeSubmittedAgain
- PinkhaHeartSemanticAnchorClientTests.testUnsupportedRuntimeAndMissingPublicationPreventMutation
- PinkhaHeartSemanticAnchorClientTests.testVerifiedFixturePublishesReturnedEventBeforeReadbackOnce
- PinkhaHeartSemanticAnchorWireTests.testActualNativePageRequestDigestsEventAndColdReadback
- PinkhaHeartSemanticAnchorWireTests.testCanonicalSnapshotUsesGoStringEscapingAndEmptyMarkArray
- PinkhaHeartSemanticAnchorWireTests.testFixedRefusalsCannotCarrySuccessReceiptsOrEvents
- PinkhaHeartSemanticAnchorWireTests.testNativeEventRejectsWrongOwnerExtraMutationAndChangedMarks
- PinkhaHeartSemanticAnchorWireTests.testNativeLinksOrderedMarksAndUnicodeByteIdentityRemainDistinct
- PinkhaHeartSemanticAnchorWireTests.testNativeSnapshotRejectsMissingUnknownAndUnsupportedMarkFields
- PinkhaHeartSemanticAnchorWireTests.testReadbackAllowsOnlyUpstreamEmptyRestrictionPresenceNormalization
- PinkhaHeartSemanticAnchorWireTests.testReadbackRejectsIdentityMissingBlockAndEveryOpaqueFieldMutation
- PinkhaHeartSemanticAnchorWireTests.testReplyRejectsUnknownFieldsWrongShapesAndNoncanonicalBase64
- PinkhaHeartSemanticAnchorWireTests.testRequestEnforcesUTF8MarksAndGraphemeSelectionBounds
- PinkhaHeartSemanticAnchorWireTests.testStrictJSONPreservesDuplicatesAndUTF16EscapeEvidence

Current host status: **22 actual methods PASS at fbbfe7100425482e3d9f8b6623bb2d1920f56528**. Original test-only compiler failures and the Swift6.4 runner/module lookup correction are preserved in docs/validation/20261123-semantic-heart-swift. The successful compiled runner/module and resources were retained before future cache reuse. Actual App/native SDK call and mounted acceptance remain separate; retirement during the async App publication chain is an identified next scope.
