# Native derived recommendations — focused regression

The migration definition planner already mapped Heart creator, createdDate,
lastModifiedDate and lastModifiedBy to the original native Any author,
createdAt, modifiedAt and modifiedBy descriptors. The imported-type parser
rejected these exact canonical descriptors. The added branch accepts only
byte-equivalent native descriptors; scope, kind, format and extra keys remain
strict. It creates no writable replacement and changes no native permission.

The actual pre-fix run executed three new methods: two failed with
invalidCatalog, and the mutation-refusal control passed. The failed original
receipt and log are retained. After the fix, all three new methods and all
17 affected Basic/Bookmark methods passed, without failures or skips.

The new methods check native-root values against forged shadow values,
readonly behavior, reader restrictions, hidden defaults and explicit reopen,
plus 24 changed-descriptor refusals (four roles by six mutations).

Both runs used Oracle ARM64 Swift 6.4.3 and the exact pinned dependencies in
the receipts. Each source inventory was equal before and after its run.
The first compile took 492.36 seconds; the incremental qualified run took
23.81 seconds including compilation and execution. This is a correctness
qualification, not a performance comparison.

No native process, Apple build or historical 182-operation preservation
scope was executed for this regression. Functional Bookmark/native process
evidence is tracked separately. All original source admission, whole-space
migration and unsupported-layout gates remain unchanged.

The qualification file records the exact base commit plus SHA256 of each
changed source file; the enclosing Git commit preserves those same bytes.
