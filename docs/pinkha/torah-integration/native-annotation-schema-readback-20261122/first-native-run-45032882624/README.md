# First genuine native annotation schema readback: nine new cases PASS

Run [45032882624, attempt 1](https://github.com/davidpovarsky/anytype-swift/actions/runs/45032882624) executed the exact reviewed source `50543a6a3895fb10a03e69e6a39746847b4c7336` on the immutable original Heart `d98420b1113536afd08cde6de9a5816f6d27ffff` with its original native libraries. GitHub concluded success. Independent artifact intake confirmed exactly nine selected new child tests started once and passed, zero failed or skipped, and no earlier cases ran. All eighteen recorded commands returned zero without timeout. Go 1.26.5 formatting equality, native compilation, source/library postchecks, and cleanup passed.

The positive control read eighteen distinct persisted native objects (one annotation type and seventeen longtext relations), actual copied protobuf details and blocks, hidden native attachments, and one dataview with all required columns hidden. Other controls cover copy isolation, no copyout on conflict/changed/cancelled publication, missing attachments, visible columns, uncertain-root preservation without creation, and actual native retirement independently of the asynchronous local index. The index retirement readiness wait is read-only and never repeats the mutation.

## Immutable evidence

* Source: `50543a6a3895fb10a03e69e6a39746847b4c7336`.
* Execution manifest SHA256: `0ea7581ee2de14bbc31b7bb35f7b5650201bc60022956cfa07d1c43441b07178`.
* Artifact ID: `14758163183`, `Otzaria-Annotation-Schema-Readback-45032882624-1`.
* Original ZIP: `Heart_Annotation_Schema_45032882624.zip`, 2,726,085 bytes, SHA256 `dba227ed9f6f3116649a97af9ce0a0c840cfe2067bc76ada68bbd5281e506b7e`.
* ZIP CRC and all forty-three indexed payload hashes/lengths verified independently. The ZIP retains all forty-four artifact files, including the evidence index.
* Thirteen composed product/test source inputs and 11,323 declared native inputs are recorded in the original runner artifact. Native executable hash and process ID are runner observations; executable bytes are not uploaded.

`VERIFIED_RESULT.json` is the independent intake result. `RESULT.json`, `COMMANDS.json`, `EVIDENCE_INDEX.json`, and `annotation-schema-readback.json` are byte-for-byte copies of artifact payloads for direct review. The complete native event stream `18-run-native.stdout` is retained inside the original ZIP. Run the retained verifier without replaying tests:

```sh
python3 verify_schema_artifact.py --archive Heart_Annotation_Schema_45032882624.zip --artifact-id 14758163183 --packet .. --output /tmp/schema-intake-result.json
```

`PEER_REVIEW.json` retains the pre-execution source-only review; its historical NOT_RUN label is intentional. `PUBLICATION_AND_OBSERVER.json` retains the initial queued publication record. `OBSERVER_TERMINAL.json` records the same finite SentinelX observer completing successfully at 2026-11-22 14:37:57 UTC, exit zero, with the exact terminal artifact retained. This does not relabel the previous Heart run's failed watcher.

`SOURCE_PRESERVATION.json` compares the compiled closure with Heart 45027606300: seven old inputs are byte-identical, only the two reviewed observer/replay copyout files differ, and four files are new. All four older native test files are unchanged. Earlier passing evidence remains at its original source/run and was not replayed or claimed anew.

## Acceptance boundary and next dependency

This result qualifies historical native observation and classification over genuine disposable original Heart fixtures. It does not implement production registration/repair, grant write authority from an observation, prove global uniqueness from a local index, or complete Swift/RPC composition, native body mapping, annotation writing, COMMIT, or ACK. Uncertain roots remain preserved. The next source phase must inspect original creation/mutation admission, revalidate actual account/Space/ACL at the mutation boundary, preserve unrelated properties/views, and add only focused controls for that new authority.

This evidence-only publication changes no native source, selector, runner, manifest, or workflow, and cannot match this workflow's push path filters.
