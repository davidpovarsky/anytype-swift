# Original MiniApps runtime hydration — 25 November 2026

The first actual build-for-testing attempt stopped at package resolution with
exit 74 because the local NodeMobile and Python binary targets were absent.
The original failure, log, command and result remain unchanged.

The exact runtime archive already retained on Oracle was transferred and verified
on both hosts (86,253,335 bytes; SHA256 in receipt.json). The original
prepare-runtime-core.sh completed successfully, including its original Host
preparation controls: 177 PASS, 0 FAIL, 1 original opt-in SKIP from 178 selected.
These are Host preparation controls, not native/App/UI acceptance.

That original preparation regenerated the Host ZIP and therefore its first
finalization attempt failed the exact canonical ZIP gate. All 28,791 members
were compared: only two absolute installation-command directory strings in
MiniAppSDK/miniapp-sdk.json differed. A strict two-string substitution reconstructs
the regenerated descriptor byte-for-byte; all other member payloads are exact.
The regenerated ZIP and the failed preparation receipt remain preserved.
The qualified canonical ZIP was restored from its still-exact original, and the
unchanged original runtime preflight then passed. All 7,693 source-file hashes,
the original source diff and Config03d remain unchanged.

A separate finalization receipt records these actual results. The failed first
hydration helper's testsExecuted=0 field counted its own native/App test actions;
the final receipt explicitly distinguishes the 177 passed Host preparation
controls from zero native/App tests.

The second build uses only the owned DerivedData left by the exit-74 attempt.
Admission verifies there were no compiler actions or app products before reuse,
retains the failed attempt, and requires the original compile, actual Worklets
code generation, signature, resource and immutable export gates. The new build
is running at this checkpoint; it has no acceptance credit yet.

All 122 original evidence files and both Host archive variants were retained in
the private Oracle archive, then every file was read and SHA256 verified after
transfer. See receipt.json for exact hashes and location. This does not recover
the missing historical build04 product ZIP and does not relabel older builds.
