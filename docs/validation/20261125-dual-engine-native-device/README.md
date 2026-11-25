# Combined Heart and Any native iOS device slice

## Actual result

The original device build completed successfully on the Scaleway Apple Silicon Mac with Xcode 27 and Go 1.27.4. The generated framework contains the original Heart service, original Any embedded server and required native Tantivy library in **one Go runtime**. The actual generated Swift entry points and NSError bridging typecheck passed against the device SDK.

This is source, native compilation, archive composition and generated ABI evidence. It does not establish successful application compilation, native API acceptance in the application, device installation, Apple Distribution signing or TestFlight availability.

| Item | Exact identity |
| --- | --- |
| Producer controller | 01a9ba2cbcd33f83c4e215a12b38355dff2ffcca |
| Source manifest | 70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683 |
| Verified original source files | 4,852 |
| Heart | ea796999d648e27dcb7ad23a0bbd849d35fadc5a |
| Any | cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3 |
| Any Sync SDK | e195f6c07a053c6588e39ffe72ee4fc44cf3d953 |
| Shared any-sync witness overlay | c005bd6cde8d8f8a6007c35f06894f3d89f9f07c |
| Actual qualified Heart capture and checkpoint bridge | a2916b27eaa16fc291f438fe620b3d09bc0a85e0 |
| Heart Page154 closure | 2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38 |
| Device library SHA256 | 57c6bcbb11979b3956e86455b5fcca50885df18957ed0e14d72fd4105ae3871d |
| Device library bytes | 353,394,464 |
| Device ZIP SHA256 | e00a3147c42dbd4766447483ec53969288d653b6d64d575d85b220018ff3cd52 |
| Original success receipt SHA256 | dcb723cbeebf97026cfb0846a06357d3ebc3a134304c40045e59cb3db52495ad |
| Original evidence archive SHA256 | 0214de8fdffee58d99db681ce1da9b6baabd8bf9b34fef70451a543acf44f78a |

The exact device root is /Users/m1/builds/pinkha-dual-native-v1-70fb5342f2ff-device. The retained original success receipt is evidence-resume-3/receipt.json; the final framework, ZIP, compressed native inputs, source closure and all intermediate failure receipts remain there. Only an inactive repack file whose bytes exactly duplicated the final library was retired after an absence-of-open-handles check; the retirement receipt is in the independent main-build root.

## Preserved failures and bounded corrections

The archive includes all 281 original selected evidence files and their full byte hashes. Every member was rehashed after transfer to Oracle before this commit.

1. The first device bind hit the 2 GiB owned-process disk guard and was stopped. Its original failed receipt and temporary-file inventory are retained. There was no accepted framework from that attempt.
2. The first continuation stopped before gomobile because a warm module cache exposed eight additional GoModSum fields. All 760 module identities, versions, replacements and remaining graph fields matched; the original failure is retained.
3. The eight metadata values were verified through fresh original Go module metadata and SumDB proof material. A control projection that incorrectly expected GoModSum in Go's metadata output also failed and remains retained.
4. The next generated module pass omitted the same eight optional JSON fields. The build stopped again. The controller now requires exact module identity, version and original GoMod path, exact cached go.mod byte hash, and the immutable independently verified proof receipt before accepting only those eight known presentation omissions. Positive controls passed; changed version, checksum and GoMod-path controls correctly rejected. No dependency source, version or authentication requirement was removed.
5. The final actual gomobile bind completed in 410.439 seconds. The existing pinned and verified Tantivy native bytes were repacked into the final archive; the single-runtime symbol check and generated Swift device ABI check then passed. Source closure remained unchanged.

The original embedded-bitcode transform retains all native machine code/data, platform commands, native symbol identities and semantic relocation targets. The pinned original compressed Tantivy releases and transformation evidence remain retained. Go's native validation was not disabled.

## Relationship to other acceptance

The simulator slice was previously built from the same 70fb source manifest; its independent original evidence is in ../20261125-dual-engine-native-simulator/. No simulator result is reclassified as a device result.

The first combined original application build uses source 39f0076780412c77f55c675d69bf7ca1ee35ea89, the same unified simulator library, canonical Hanlin 44bcebf687206a37893cb584cf72c6aafbc5ca48, and the actual 54-pin lock from f797c208f18bb0e59d8da84f8a05fe9dd049d652. That build and all application acceptance remain separate gates.
