# New property-modal portable controls

## Frozen source and execution status

This packet targets the thirteen-file modal delta `377ef209aa567db9f95728f54be101726befea96b2e2cc36b28d0ca3a8bb729d` at Anytype base `fc03fcd713e2c449ad97c5d1e604a9433c2a309b`. Those thirteen outputs are unchanged in the combined sixteen-file delta `90605b0cb2576c87c3102729ef4784733fc4e24989045acd756b3b9d1f6d5a25`.

The packet is **source-reviewed and packaged; it has not been compiled or executed by its authors**. Root owns the one subsequent portable compile/run. No prior passing suite is included or rerun. The separate combined sixteen-file syntax job is not a result of this packet.

The controls have fourteen meaningful case identities, derived from six canonical-input groups and eight Owner-composition cases. The malformed canonical-input group contains eighteen individual variants. This is a description of the actual scope, not an acceptance-count target.

## What executes when root runs the packet

| Case family | Actual production code | Explicit inputs and limit |
|---|---|---|
| Canonical result and internal identities | Full original `PinkhaSpaceManifest` Codable/value type; exact `PinkhaInternalPropertyIdentities`; new post-read validator from `OriginalEditorPropertyScope` | Already-decoded manifest values. No canonical service read occurs in this family. |
| Missing, malformed and ambiguous roots | Exact original final discovery filter and `ManifestDiscoveryError.ambiguous` | Already-decoded candidate projections containing ID, Space and description string. Search queries and protobuf decoding do not run. |
| Exact source/Space/scope | Exact new snapshot issuer check, exact post-read UTF-8 Space check, actual Owner/current-source boundary | Immutable disposable document values and a currentness observation. No actual account or document is opened. |
| UI reservation and parent/child composition | Actual Owner, lifetime, operation, dispatch binding and permit; exact Scope `withCurrent`, `withActionCallback`, `prepareAction` | Explicit effect log at actual permit `begin`/`finish`. Actual child Owner derives from the original parent binding; no child Factory is substituted. |
| Account change during an admitted read | Actual Owner/read/permit and captured account generation, paused using continuations | The effect is a disposable `ObjectShow`-named read probe, not Lib. Its completion must be retained while successful publication is rejected. |

The packet has seventeen Swift input files, including unchanged core inputs and the explicit entry point. `INPUTS.json` is the authority for the exact file list and case identities.

## Causal checks

The canonical controls require a successful actual JSON roundtrip, preservation of all four raw internal IDs/keys, and the original internal matcher. They reject absent/in-progress/unsupported manifests, absent/empty/NUL root ID, and empty/NUL/trim-normalized forms of each internal ID/key. A canonically equal Unicode Space with different UTF-8 bytes is rejected. A snapshot cannot move to another Scope instance, nor revive after the original currentness check retires its Owner. Discovery separately rejects foreign result Space, foreign payload Space, malformed/missing description and mismatched canonical root; two valid roots produce the original ambiguity error.

The Owner controls reserve a named mutation before creating its Task, reject read-to-write upgrades, demonstrate valid parent-add → selected-child-write → parent-publication ordering, and reject parent reentry while the child holds passive parent tracking. Rejected write intent remains visible to the actual exclusive-capture barrier. Missing list permission, source replacement before Task start, and source replacement between permit preparation and begin cannot reach the disposable effect. A completed read under a replaced account generation cannot publish success.

The actual `withSelectedModalProperty` body is preserved as a hashed source region, with bounded source-order assertions binding these causal Owner probes to the frozen production sequence. **The entire modal method is not executed through a fabricated Factory.**

## Exact extraction and preservation

`build_controls.py` only materializes and packages inputs; it never invokes Swift. It checks the thirteen frozen source hashes against their manifest and the sixteen-file join, verifies the immutable core Git blobs, and records every copied production region with byte offsets and SHA256.

`Owner.swift` and `Operation.swift` lose only the `ProtobufMessages` import so the actual shared binding can compile in the same portable module. Lifetime, Binding and `PreparedEditorPageDocument` are unchanged actual sources. The last file's current Git blob is `37ff035f30c0b2f17c2ce75b4c7a7f1acbbb78a2`; it is not a replacement validator. `OriginalTypePermissionProbe.swift` supplies the pre-existing explicit portable model values required by those real sources. The actual marked participant-role region is present only because current Owner references its type; no old role suite is run.

The Scope envelope receives an actual Owner and disposable document directly. It does not implement a `PreparedEditorPageSession`, Factory, service, account, catalog, engine or storage layer. Its copied methods and validator body are exact. Test-only methods expose the private guard/result without editing production. `PRODUCTION_REGIONS.json` and `PRODUCTION_INPUTS.json` state the source identities; full relevant originals remain in this source packet's `production/` directory.

## Explicitly not qualified

This packet grants no Apple typecheck, native editor, property UI, actual service RPC, Heart, catalog bootstrap, persistence, event-delivery, child acquisition or provider acceptance. In particular, `ObjectCreateRelation`, `ObjectRelationAdd`, `ObjectSetDetails`, archive payloads, real returned `PropertyDetails`, selected-child permissions and UI publication still require their real original Apple/Native route. The actual SearchMiddleService binding and ObjectSearch/ObjectShow calls are source-reviewed, not executed here. No seed body, replacement renderer or replacement dispatcher exists in this packet.

## Root-owned execution

Extract `property-modal-controls.zip` into one new owned build directory. Verify the archive SHA256/CRC and every `INPUTS.json` file hash before compiling. Compile the seventeen listed Swift files once using the existing Swift 6.3.3 Foundation route, `-swift-version 5 -strict-concurrency=complete -parse-as-library -j 1 -whole-module-optimization -Onone`, then run the resulting executable once with a bounded timeout. No external package or SDK dependency build is needed.

The executable reports the exact fourteen case identities only after all throwing assertions finish. A nonzero compile/run exit, missing final JSON, unexpected identity, skipped case or changed input is not a pass. Retain the actual command, compiler output, executable hash and run JSON beside this packet. Do not replace the declared `NOT_RUN` native/service fields with portable credit.
