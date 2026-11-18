# Exact native registry and transport evidence

Run [44227963678, attempt 1](https://github.com/davidpovarsky/anytype-swift/actions/runs/44227963678)
completed successfully on app source `e95fc4e391afa42efd66d4b8e6b6a92b96862412`.
Heart is `d98420b1113536afd08cde6de9a5816f6d27ffff`, Go is `1.26.5`, and the
registration patch hash is `8706ff898474ca227947caa0f199300919b7bc93b954cb7ef9e3d1a9ad0ece10`.

| Suite | Top-level PASS | Subcase PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: | ---: |
| Component and isolated two-process loopback transport | 22 | 45 | 0 | 2 helper entry points |
| Native private registry/source/factory/import boundaries | 15 | 21 | 0 | 0 |

The component suite exercises actual StoreState/any-store and signed AnySync
transport. The registry suite exercises private type/source/factory/storage and
generic-import boundaries, with controlled target State lookup. These are not
full middleware account lifecycle, old-client preservation, two App clients,
application RPC binding, or iOS acceptance. App capability remains OFF.

`verified-summary.json` records the precise GitHub artifact IDs, archive,
receipt and event-log SHA-256 values, counts and source identity. Verification
read both ZIPs in memory on the connected host, compared all 38 resulting source
paths with the exact Git-bound inventory and all 27 overlay blobs with that Git
commit, checked every evidence-file hash and compared receipt counts with raw Go
JSON events. Both archive hashes matched GitHub's artifact metadata.

Raw ZIP/log export was rejected by automatic approval review because a bulk
transfer could expose repository logs or other sensitive contents. The safer
read-only verification emitted only the selected metadata, hashes and counts;
no ZIP or raw log was copied into this evidence directory. The original raw
evidence remains in the linked GitHub artifacts (retained until 2026-12-02).

This run predates the byte-identical initializer filename rename in `7463aff`.
Its inventory therefore names `smartblock/pinkha_torah.go`; the new composable
source names `smartblock/pinkha_torah_operations.go` to avoid r14/r15 overlap.
The rename is not claimed as having been compiled by this earlier run.
