# Prepared native components on the dedicated Mac

This is a separate qualification candidate: `v0.5.0-pinkha.prepared.components.1`, selected only by `PINKHA_ANY_NATIVE_ARTIFACT=verified-prepared-components-v1`. It preserves the unexecuted file-only candidate 40211869 and all original runtime modes.

The exact native manifest pins any-sync-sdk ef63bcaed93064c8de24ed656842f3e56ed34008 and Any 1b17da42fccc2f092cbedd48e0991a203584bc85. It carries complete binary Git patches from the original upstream revisions; no any-sync or any-store source is changed. The immutable native policies include objects, blocks, full files, type/collection/property definitions and one atomic part/dataset/field/index batch. Linux component evidence is retained separately; Apple execution is still required.

Root Swift definition wrapper commits eda51b21bc154e71244b06582302b67c9ed1000f and 30892c5c37dc5521700bf67acedc444273ccb59b are included byte-for-byte. The new selected test is `AnyPreparedComponentsRuntimeTests/testManagedDefinitionsBlocksAndFullFilesSurviveReopen`. It uses the actual embedded C runtime, managed HTTP authorization and public Swift wrappers in one disposable account/Space:

1. Prepare/commit an actual custom type, collection, six-record atomic part with editor and records datasets, two fields and an index, and two custom properties.
2. Read compiled definitions through ordinary native APIs. Create two documents of the migrated custom type, with both type and collection property values, then create actual editor paragraphs.
3. Prepare distinct 4096-byte and 2097152-byte full files. Reopen the native runtime/store, reconcile the same signed reservations, commit, and read every original plaintext byte through ordinary HTTP.
4. Reopen again, reconcile every definition/object/block/file without replacement and reread the exact native schema, property values, text, filenames, MIME and plaintext hashes.
5. Require three actual runtime/application-owner generations, two orderly reopens, independent original XCTest result admission, source/product immutability and cleanup of the owned simulator and disposable native data.

The five definition plans, two documents, two blocks, two files and their ordinary readbacks are admitted independently by proof.py. Observation attachments alone do not establish a pass. The original passing XCTest must be the sole selected method in the owned iOS27 ARM64 result, with zero skips/failures. Runtime evidence is bound to the source SHA, real local UUID, nonce, native manifest/archive and actual compiler/SDK receipts. Local runs never borrow GitHub Actions identity.

Use native_artifact.py once to build the two required ARM64 native slices with the verified Go1.27.4 toolchain and `/Applications/Xcode.app/Contents/Developer`. Then run run_host.py on a fresh owned consumer work directory. A later Swift-only correction may reuse the original native artifact only when the producer is an ancestor and all native inputs remain byte-identical; preserve original failures and producer identity.

Scope remains component acceptance. Source census/admission, complete source-to-destination migration, native history replay, network delivery, lost HTTP acknowledgement injection, OS-process crash and physical-device acceptance are not asserted by this Apple journey. Earlier Linux crash controls remain separate evidence.
