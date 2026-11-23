# SDK06 actual preload-order correction

## Actual failure

Run 45237901921, attempt 1, source 1a09867d88f475fd2b3192fabc4dd803986e5281 stopped in current-controller admission before archive restoration. The one selected original job log and the artifact are preserved under original-failure. The immutable originals retain their exact bytes, including the empty stderr.

The unchanged loader requires the preload list to equal the sorted declared production module list. The compile-support addition had the correct 67-name set but appended sdk06_compile_support at zero-based index 66 instead of index 33. The guard correctly refused. The artifact's sole lifecycle receipt is NO_OWNED_CREATION, with zero cleanup commands. No simulator, component build, test method, or UI build started in this failed attempt.

## Source correction

The only production delta moves that one JSON list entry into its sorted position. The 85 input records, 70 module mappings, remaining manifest fields, and every Python source byte are unchanged. exact-source-inverses.json recovers the entire original manifest through two literal inverse hunks.

## New qualification scope (NOT_RUN at source freeze)

One new method executes from a byte-identical frozen control copy outside the checkout, so the control itself is not misreported as a production module. It imports the actual sdk06_original_native_continuation entrypoint, whose unchanged top-level admission checks 86 physical/Git members including its contract. It then calls the unchanged preload_current_sources twice: the retained original unsorted contract must be refused before any new import, and the corrected contract must load the complete fixed 68 production module origins including the entrypoint. The two old test modules must remain unimported.

This control binds all 86 production members plus four control/profile/fixture files. The input manifest itself is compared with frozen Git bytes. The source maps and actual loaded maps are retained before and after; named events, first error, original log and separate owned process cleanup are preserved. There is no branch-identity substitute, generic loader override, mocked production import, or invocation of restoration/admit/worker/main.

The finite profile permits only this Python source-admission/import check: 1 GiB free floor, 8 MiB logical and allocated output including directories, 256 KiB per-file cap, 60 seconds execution and 10 seconds owned group cleanup. Only the three exact readonly Git commands needed by actual entrypoint admission are permitted during the method. Previous control and native/Mac gates remain unchanged.

## Ownership and integration

The isolated branch starts at the exact failed-run source. Root owns main integration, publication, CI and any product build. The prior compile-support donor remains immutable. No old control is replayed and no product acceptance is claimed by this source freeze or the proposed control.
