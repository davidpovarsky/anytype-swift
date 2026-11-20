import XCTest

XCTMain([
    testCase([
        ("testExactQualifiedKeysCannotCollideAtSeparatorsAndDerivedKeysAreDistinct", NativePropertyStoreTests.testExactQualifiedKeysCannotCollideAtSeparatorsAndDerivedKeysAreDistinct),
        ("testRawUnknownNamespacesAndNativeDerivedMetadataSurviveProjection", NativePropertyStoreTests.testRawUnknownNamespacesAndNativeDerivedMetadataSurviveProjection),
        ("testSingleValuePatchCapturesExactVersionAndInverseWithoutEchoingOtherNamespaces", NativePropertyStoreTests.testSingleValuePatchCapturesExactVersionAndInverseWithoutEchoingOtherNamespaces),
        ("testGenericSetCannotBypassTypeMembershipHierarchyOrUnsupportedScope", NativePropertyStoreTests.testGenericSetCannotBypassTypeMembershipHierarchyOrUnsupportedScope),
        ("testReaderSnapshotCannotPrepareAnyMutation", NativePropertyStoreTests.testReaderSnapshotCannotPrepareAnyMutation),
        ("testTypePickerUsesEligibilityAndPreservesOriginalNamespaces", NativePropertyStoreTests.testTypePickerUsesEligibilityAndPreservesOriginalNamespaces),
        ("testCollectionMembershipDoesNotDeleteValuesOrBypassManagedCollections", NativePropertyStoreTests.testCollectionMembershipDoesNotDeleteValuesOrBypassManagedCollections),
        ("testVisibilityPreservesFutureKeysAndChangesOnlyPreferenceNamespace", NativePropertyStoreTests.testVisibilityPreservesFutureKeysAndChangesOnlyPreferenceNamespace),
        ("testVisibilityAttachmentAndDerivedPanelRemainExplicit", NativePropertyStoreTests.testVisibilityAttachmentAndDerivedPanelRemainExplicit),
        ("testMalformedOrOverflowingVisibilityNeverSilentlyDropsValues", NativePropertyStoreTests.testMalformedOrOverflowingVisibilityNeverSilentlyDropsValues),
        ("testCatalogRejectsDuplicatesButAllowsLegitimateCrossCatalogID", NativePropertyStoreTests.testCatalogRejectsDuplicatesButAllowsLegitimateCrossCatalogID),
        ("testNativeProofRequiresExactPolicyWorkspaceReadinessAndCapabilityVersion", NativePropertyStoreTests.testNativeProofRequiresExactPolicyWorkspaceReadinessAndCapabilityVersion),
        ("testPropertyKindMismatchCannotBecomeAnUnconditionalOrWholeRecordWrite", NativePropertyStoreTests.testPropertyKindMismatchCannotBecomeAnUnconditionalOrWholeRecordWrite)
    ]),
    testCase([
        ("testSnapshotRejectsMissingOrInexactApplySequence", NativePropertyFenceTests.testSnapshotRejectsMissingOrInexactApplySequence),
        ("testEveryPreparedMutationRetainsTheSameObservedFence", NativePropertyFenceTests.testEveryPreparedMutationRetainsTheSameObservedFence),
        ("testPreparedEditRejectsLateCommutativeSequenceChangeWithIdenticalVersionAndValues", NativePropertyFenceTests.testPreparedEditRejectsLateCommutativeSequenceChangeWithIdenticalVersionAndValues),
        ("testApplySequenceAboveDoublePrecisionIsPreservedExactlyOnWire", NativePropertyFenceTests.testApplySequenceAboveDoublePrecisionIsPreservedExactlyOnWire),
        ("testAcceptedWriteRequiresExactPositiveSequenceAndOriginalRun", NativePropertyFenceTests.testAcceptedWriteRequiresExactPositiveSequenceAndOriginalRun),
        ("testLaterReadbackWithSameVersionAndRequestedValueCannotMintUndo", NativePropertyFenceTests.testLaterReadbackWithSameVersionAndRequestedValueCannotMintUndo),
        ("testExactAcknowledgementBindsUndoToItsSequenceWithoutChangingOriginalIntent", NativePropertyFenceTests.testExactAcknowledgementBindsUndoToItsSequenceWithoutChangingOriginalIntent),
        ("testReadbackFromDifferentOwnerEpochOrTargetCannotCertifyTheWrite", NativePropertyFenceTests.testReadbackFromDifferentOwnerEpochOrTargetCannotCertifyTheWrite),
        ("testPendingEditAndUndoRefuseReplacedAccountSpaceRunAndGenerationBeforeTransport", asyncTest(NativePropertyFenceTests.testPendingEditAndUndoRefuseReplacedAccountSpaceRunAndGenerationBeforeTransport)),
        ("testPendingEditAndUndoHonorRevokedLeaseWithoutReplacingCapturedFence", asyncTest(NativePropertyFenceTests.testPendingEditAndUndoHonorRevokedLeaseWithoutReplacingCapturedFence))
    ])
])
