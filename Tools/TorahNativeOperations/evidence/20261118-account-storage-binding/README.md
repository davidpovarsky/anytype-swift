# Native account retry: correct the raw storage identity assertion

Run [44235227539](https://github.com/davidpovarsky/anytype-swift/actions/runs/44235227539) at App `b0330ec412606568cfe6c6bccdf920504aafd142` built both native binaries and progressed past the private host factory, append, read and identical retry routine. The new-create phase failed while enumerating raw history: the fixture assumed `StorageChange.TreeId` was hydrated by a read. No lifecycle phase passed and the remaining three phases did not run.

The verified AnySync `v0.13.8` source shows that `GetAfterAddSeq` scopes its query to the storage ID, while `changeFromDoc` reconstructs the ID, raw bytes and parent IDs but omits `TreeId`. Native writes persist `PreviousIds` into the parent field. The correction checks the storage ID, the exact acknowledged change ID and its root parent. It retains the exact two-change count, all raw byte hashes, derived/no-parent/not-deleted head metadata and exact heads. No production storage or registry behavior changes.

The patch was made by a small exact-context edit in the isolated App worktree. Its formatter and diff checks passed. The corrected native execution remains **NOT_RUN** until a fresh source-bound Linux run. App capability is **OFF**; this is not acceptance of two App clients. Four separate new handler draft files in the working tree are not part of this correction.

`verified-failure.json` records the digest-verified GitHub artifact, selected source/ELF/log hashes and the upstream h1. Raw artifacts and account data remain in GitHub/the disposable CI workspace; only metadata is recorded here.
