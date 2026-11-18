# First two-native-client run — original failure evidence

Run [44272980092](https://github.com/davidpovarsky/anytype-swift/actions/runs/44272980092) used exact integration `a7305fb510d70129724f7fe98daf1471058cdb91`, containing client source `f43ab23dda7f1ae5d7f1b06528aeaa7b7fa5fe40`. It failed during the first recovered client's private-history read. It is not two-client acceptance.

The original artifact `14412789700` was checked in RAM on the connected owner host: 80,755 bytes, 59 files, ZIP SHA256 `4ed2be84dedb4b53bbf89740efa10efe6ec447cb5f8ee8176df18af0834cd54a`. Raw artifacts and native logs remain in GitHub; `verified-summary.json` records selected metadata, actual terminal counts and source-bound hashes.

Generation and compilation passed. The raw logs contain 35 passing Python controls and 13 passing native boundary terminals (2 top-level methods and 11 subcases), with no failure or skip. The retained account-wire baseline again passed all four sequential native processes across two binaries, with eight actual ordinary-object export files. Those passes have their existing scope.

The creator reached ready with its original signed private history. The recovered client completed native cold account selection and WorkspaceOpen, reached the native server check, and then returned INTERNAL_ERROR/code 1 from the first private read. The strict readiness predicate failed at fixture line 311 after 2.21 seconds. The original log does not record the issue enums, so the underlying internal cause is not established. No generic/internal error was accepted as a transient prefix or convergence. There is no recovered ready receipt or final receipt for either client.

The controller removed only its two owned containers and owned internal network, and passed its exact-allowlist secret scan before publishing the diagnostic evidence. No application capability, user data, device-key seeding, external node or release was introduced. Offline concurrency, process restart, two App clients, iOS and full T2 acceptance remain unproved.
