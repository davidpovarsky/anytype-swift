# Native source capture bridge and shared reader — 25 November 2026

The real native source capture now has a thin gomobile entry point and a shared Swift consumer. The new source is additive. It calls the existing loaded application/account/space capture and retains its native authority, unchanged-checkpoint checks, private original snapshot/file/history custody and explicit semantic gaps. It does not create a session, load a different account, manufacture an ACK, or grant destination write permission.

## Exact candidates and observed proof

- Native Heart base: ea796999d648e27dcb7ad23a0bbd849d35fadc5a.
- Native bridge: 7796b2a4c8e7d80aae82606ca0bcb83acf84506d; six exact files plus a reproducible Git patch are listed in receipt.json. Required tag: pinkha_loaded_account_witness.
- Shared Swift source: 68aa9c7aa05ffe132d1a175e1f30f952202678b3.
- Go capturecontrol package: five top-level methods and five nested refusal cases passed with the race detector. This tests deadline/cancellation ownership, request/capacity validation and immutable private manifest custody. It does not compile the full core/service or execute an actual new capture.
- Swift: five methods passed, zero failures and zero skips. Both immutable original source bundles were actually read through the new descriptor/private-file path: 144 objects/291 members and 156 objects/313 members. Their original manifest hashes matched. The original custom source acceptance failure and semantic blockers remain unchanged.
- The first Swift attempt failed before compilation because it ran under the wrong user for the existing Swift lock. The original log is retained. Running the unchanged source as the established cache owner ubuntu passed; no lock or ownership bypass was used.

## Caller contract

The combined native producer must include the tagged original capture source and the six bridge files. Generated Objective-C names must be verified from its actual header; the expected Go exports are:

    PinkhaCaptureLoadedAccountSource(sessionToken, accountID, spaceID, privateDirectory, requestID string) ([]byte, error)
    PinkhaCancelLoadedAccountSourceCapture(sessionToken, requestID string) bool

The caller creates its own canonical, nonsymlink 0700 parent in application-private storage, uses the current full native session and exact current account/space IDs, and generates a unique ASCII request ID. Capture creates its own native-source-* child. Run the blocking native operation off the main actor. Cancellation must use the same token and request ID; a cancelled operation retains its bounded registry slot until native execution finishes. The ten-minute deadline is cooperative.

Decode returned bytes using AnyHeartNativeCaptureDescriptor(data:expectedAccountID:expectedSpaceID:expectedRequestID:), then call loadBundle(under:) off the main actor. This verifies exact UTF-8 identities/request, duplicate/unknown JSON fields, SHA256, bounded counts and read-only private members. Directory descriptors pin all relative reads; openat/O_NOFOLLOW refuses symlink substitution. All original members still pass the existing complete bundle inventory and digest verifier.

The descriptor's SHA256 is a byte binding, not a digital signature or current session authorization. Keep raw source bundles, native identifiers and encryption/history metadata private. The small public test logs contain only hashes and counts. The current Swift manifest maximum remains 16MiB; an oversized capture is explicitly refused rather than partially parsed.

After reading, build the existing native definition/page composition preview. Do not enable migration execution from this descriptor alone: native current-source revalidation, complete whole-Space semantic mapping, target authorization and comparison remain required. D owns actual combined producer compilation and shipping UI wiring; those results must be recorded independently.

## Count correction and remaining semantic scope

The retained 156-object manifest has 20 type definitions: three Basic0 and **17 non-Basic type instances**, representing 15 distinct non-Basic layout values. The earlier integration README said 16; that prose count was incorrect. This correction changes no source bytes, mapping or test admission. Other exact counts remain 64 readonly/derived property definitions and one non-null string default.

The original bundles still include native home/archive/workspace/widget objects, unsupported type layout behavior, derived/default semantics and retained metadata/history/collections that have not all been mapped to usable target semantics. Default-observation test candidates exist but have not yet executed. This bridge and reader close the source invocation/custody boundary only. Task C remains open; no whole-Space destination write, fresh-process target reopen, full comparison or Apple application capture success is claimed.
