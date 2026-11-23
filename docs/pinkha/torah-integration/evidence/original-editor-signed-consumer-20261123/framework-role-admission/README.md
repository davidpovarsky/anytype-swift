# Original signed consumer: authenticated framework-role admission

## Actual failure and diagnosis

Run `45106338448`, attempt 1, control source `4aa7b02b8e4cb8c124dd59ddb656746481d9aa6a`, job `137468395144` failed during **INPUT_ADMISSION** with `Retained signed consumer uses a different framework: Lib.framework`. Exact source-control admission, original producer/job/artifact upload proofs, all three original downloads, the original Xcode 27.0 / Swift 6.4 / simulator SDK 27.0 match, retained app restoration, strict codesign verification and original relocatable install-name checks had succeeded. There were zero simulator attempts, zero EN/HE runtime observations and zero producer or consumer builds.

The original producer at `de63125b97cd5b91a1fa4f4b71d03738076e735f` selected dynamic frameworks from actual `otool -hv` output in `run_framework_acceptance.py`. Its unchanged `framework_products.consumer_project` embeds that dynamic set only. The complete original distribution contains 17 framework directories, including the static Lib and Sentry archives. The signed app contains exactly the 15 original DYLIB framework directories. A comparison demanding all 17 directories inside the signed app was therefore inconsistent with the original producer.

`DIAGNOSIS.json` is a derived analysis, not an authority input. The helper derives the partition anew from the original archive's authenticated command/stream records. All 17 original command receipts, stdout and stderr are retained unchanged under `original-headers/`. The complete original distribution manifest and consumer-retention receipt are also retained. The unaltered failing artifact ZIP, authenticated intake and actual execution/install-name evidence remain in this packet.

## Bounded source repair

Only three source paths change: existing `run_signed_consumer_continuation.py`, new `signed_consumer_framework_roles.py`, and its new focused test module. Original application/framework/native source, the signed consumer, original distribution and workflow bytes do not change.

Within the already size/digest-authenticated original evidence archive, each indexed header record must bind the original framework name and executable path, the exact otool command, successful non-timeout exit and both stream SHA256s. Only unambiguous Mach-O DYLIB rows, or Archive containers consisting entirely of OBJECT rows, are accepted. Unknown, mixed or differently named binaries are rejected. The derived dynamic set must also match the exact original signed-app file and directory inventory.

After the original signed app and full distribution have been restored under their existing complete byte/mode commitments, the runtime driver requires exactly the derived dynamic framework directory set in the app. For every distribution framework, its current files must still match the original manifest. Every dynamic embed must then match the entire corresponding distribution inventory, including resources, metadata and signatures. Static archives must remain in the complete distribution and absent from the signed app. This is not a static-name exemption or a relaxed executable-only comparison.

The existing 2,528-file distribution restoration, complete signed app restoration, strict codesign, install-name/rpath, original toolchain/source/API/resource, PID/nonce, owned lifetime, deadline and cleanup gates remain. No framework re-signing, binary modification, product rebuild or automatic retry is added. The new role/binding receipts explicitly carry no runtime-qualification claim.

## Verification and evidence reuse

The six new source controls passed once. They cover the authentic 17-header/15-DYLIB/2-static partition; missing/tampered/misbound/failed original receipts; unknown or mixed image kinds; missing/extra/static app embeds; dynamic member/size/hash/resource mutations; and static inventory, role/name or alias mutations.

The metadata/classification positive case consumes the retained authentic original records. Filesystem inventory cases use clearly marked tiny **unit fixtures**, real filesystem hashing and the actual inventory implementation; they do not represent compiled original frameworks or a successful signed/native runtime.

`FRAMEWORK_ROLE_CONTROLS.json` binds the actual current source and complete command/test output. The original six metadata and two raw log-capture controls were **not reexecuted**. Their original receipts remain verbatim under `prior-control-receipts/`. `SOURCE_CORRESPONDENCE.json` proves unchanged exact tested functions, test module and subprocess helper, unchanged restoration functions and unchanged runtime tail. Current full-file admission hashes are updated with that explicit retained-evidence relationship, not relabeled as new executions.

The original failed result remains FAIL. No Stage B pin or source activation is inferred from these source controls. The next permitted action is root review of this exact diff, records and prepared source identity; only then may one actual retained-consumer runtime continuation execute. Any genuine runtime result must still be taken from its own immutable source/run/artifact.
