# Lifecycle native gate followup

Base: `36757c8389006c6d30bf8f73997fcd928330601d`. App capability remains OFF and full T2 acceptance remains open.

## Original failures

Registry run [44570367265](https://github.com/davidpovarsky/anytype-swift/actions/runs/44570367265) failed to compile the new objectcache absence regression because `spacestorage.SpaceStorage` has no `HasTree` method. The original ZIP digest, all member digests and all 65 source bindings were verified. Other packages emitted 92 passing test terminals; the registry suite remains failed. The component lane at this source separately passed 98 test terminals, including both new durable target-lease tests.

Client run [44570372111](https://github.com/davidpovarsky/anytype-swift/actions/runs/44570372111) passed the four original offline and disconnected-reopen processes, then stopped with a controller `ValueError` while checking the creator's partitioned REPLACE observation. The actual native history, projection, claim provenance, byte response and local sequence were unchanged between ready and partitioned. No REPLACE append had yet been requested. Cleanup passed. The original archive and published-file hashes were verified.

Raw live Docker inspection outputs and the daemon version were not retained in that archive. Consequently the exact differing live field cannot be reconstructed, and this change does not retrospectively declare that failed native run successful.

## Scoped correction

The native regression now uses the real `TreeStorage` API and requires both `treestorage.ErrUnknownTreeId` and nil storage before and after missing-guard rejection. It still exercises the actual CommonSpace storage provider with an absent private root.

The REPLACE controller compares the `Mounts` collection by unique absolute destination. Every mount field, including unknown fields and nested list order, remains exact; malformed or duplicate destinations fail closed. Other Docker fields and list order remain exact. The observations are deep-copied and never repaired in place.

[Moby's primary-source correction](https://github.com/moby/moby/commit/ff0b471f2091c7b7be351cee44c2a013fb6914d7) documents that mount enumeration can follow nondeterministic map order. An actual local synthetic orchestration against the published pre-correction controller reproduced rejection when only the unchanged mount records were reordered. This establishes a controller defect independently; it does not identify the lost original live observation.

Fixed-schema phase/check names and field-match booleans are retained in the controller receipt. They contain no raw environment, mounts, paths or exception text and trigger no additional native calls. Original signed-history, partition, retry, provenance and materialization checks are retained. All seven native-client Go fixtures are unchanged.

## Validation and limits

All 25 concurrent-controller controls passed on Linux, with zero failures or skips. New controls cover order-only changes, duplicates/malformed destinations, added or removed mounts/fields, changed unknown fields, nested list order, Env/Args/HostConfig order, process replacement, metadata substitution and withholding private diagnostic strings. Both root and the independent reviewer reviewed the exact source hashes; root independently reran the 25 controls. The registration, RPC, account and client source-input pin cascade passes.

The original-failure report and source reviews are included alongside this document. Native registry recompilation and the full concurrent REPLACE lane must pass at the corrective commit before their acceptance can be updated. Historical guard-only `cab855` evidence remains separately scoped.
