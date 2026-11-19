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

The original-failure report and source reviews are included alongside this document. Historical guard-only `cab855` evidence remains separately scoped. The corrective commit `16b7493fa05bdc3abbae190c6e6c364c81874eea` has now passed the following original-artifact qualifications:

| Exact-source run | Verified result | Original archive SHA256 |
|---|---|---|
| [44576342081](https://github.com/davidpovarsky/anytype-swift/actions/runs/44576342081), component | 98 PASS terminals, all 37 required names; 0 FAIL; 2 expected process-helper SKIPs | `4222e70f33e20754aa581298f6080c3e12d0e14602498b904c28b554692d96f7` |
| Same run, registry | 96 PASS, all 60 required names across 14 packages; 0 FAIL/SKIP | `712ed7e6ce047db3f7fc1297962d2f9e88d990da1923d9c1f9a4c711e4dded11` |
| [44576585262](https://github.com/davidpovarsky/anytype-swift/actions/runs/44576585262), dedicated generated RPC | All 7 methods + 11 subcases = 18 PASS; 0 FAIL/SKIP; 6 Python controls | `122fe87d59f1b2de26821a8c02fcae5c9737fb757c06187e6f6818eab170bebf` |
| [44576349959](https://github.com/davidpovarsky/anytype-swift/actions/runs/44576349959), concurrent REPLACE | Original 4-process offline/reopen baseline, then 2 additional native PASS; signed 8→9 each→10 merged; all 6 retries unchanged | `e1086dc8efe4e535d8e992990c40db4d178b6f860f7daee8bc9b926f58d97a86` |
| [44580495418](https://github.com/davidpovarsky/anytype-swift/actions/runs/44580495418), process crash | Original baseline, then actual owned SIGKILL before ACK and one new recovery PASS; 276-byte exact retry preserves 9 signed entries, complete snapshot and sequence | `b506f9fd0a724d1fa5b6904d7668792268e7092c95c97f9270a0de11a1606f7c` |
| [44580502296](https://github.com/davidpovarsky/anytype-swift/actions/runs/44580502296), observed REMOVE/re-ADD | Original baseline, then 2 additional native PASS; signed 8→9→10→11; three independently encoded identical 334-byte REMOVE entries; removed claims stay removed | `15a7b5f8d4866de172e984ec8b89ba60186a1c6b5a5e5f8b584d474587871a81` |

Each client run also separately passed the four-process account baseline and eight ordinary exports. The three tail runs retained 42 common native boundary controls; the crash run adds 12 native crash controls. Actual Python counts are 59+25 for REPLACE, 59+8 for crash, and 59+14 for observed removal. They are controls and are not added to the actual account/client process counts. The killed crash invocation has no normal PASS/FAIL/SKIP terminal and is explicitly counted as zero PASS.

All original ZIP digests match GitHub; CRCs, retained member hashes, source/fixture pin cascades, phase receipt hashes, signed-history parent/hash observations, exact retry invariants, native logs and owned cleanup were rechecked. Each client composition binds 108 source paths, including 73 generated registry/RPC paths and the separate 35-file legacy composition. The component and registry bind 65 source paths. Reports named `VERIFIED_*` contain the detailed counts and all member hashes.

Runtime executable bytes and historical live Docker inspections are not retained in these evidence ZIPs. Qualification verifies their original source/build/phase receipt chain, not a new independent binary rebuild or reconstruction of historical OS state. No power-loss, causal display ordering, complete target/ACL/account race matrix, standalone Space.Close, iOS, new-engine parity or full T2 acceptance follows from these scoped results. `REMAINING_ACCEPTANCE.md` records those boundaries and missing product APIs. App capability stays OFF.
