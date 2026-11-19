# Original logout presentation and bootstrap lifetime

Failed original UI: https://github.com/davidpovarsky/anytype-swift/actions/runs/44450816123
Exact source6a478f0a8eba0687406d0690cbb86eb84cd90f79, native build/preparation passed, original UI1FAIL/0PASS/0SKIP.
All22 native receipt checks were true and original ApplicationState reached auth. The final original Login/Join hit test correctly failed. The actual screenshot and raw AX show two retained Add a Channel Home sheets over auth plus a Middle.ObjectShow / validateTypeExists / not logged in banner.

Full artifact14500723157:103780597bytes, SHA256138dd4a67710d7fcb6cecdaeedbe9ec60d4a9c848774986552caaf010bef0b40. Original outer/nested CRCs verified. Native failure summary SHA256e99416cba8565dab1366c1d10b9eb968586ea6d54d8aef95b446d41f06a8927a. Original runtime probe PID5426 differs from actual UI receiptPID6592; every_launch_verified=false. No same-PID mapped-runtime claim is made.

## Actual owner corrections

The original HomeWidgetsCoordinatorViewModel combines its existing participant stream with the original ApplicationState publisher. It clears its own sheet binding outside home and when that view task ends. Cancellation cannot turn the old sheet back on. The original popup remains available while its authenticated owner is active.

The original downstream PinkhaSpaceBootstrapService now routes both full and canonical bootstrap calls through one task-lifetime gate. Account retirement rejects new admissions and waits for the original accepted operations, including their nested provisioning tasks, to complete. The original auth decorator performs this drain before create/select replaces an account and before middleware logout. It reopens admission only after successful native create/select. Existing engine, manifest writer, incremental persistence, error identity and Heart implementation are unchanged.

The original bootstrap status manager gives each provisioning claim an identity. Account reset invalidates claims; an old completion cannot publish into a replacement claim for the same Space. The original hook uses that identity and treats closed admission as no admitted work. It does not suppress an error from an operation that actually reached middleware.

All original UI22 assertions and time budgets remain byte-for-byte present. The final auth helper additionally rejects the exact old popup and observed not-logged-in banner. No test-side popup dismissal, automatic consent or retry was added.

## Verification and source boundary

The exact production gate and its three checked-in Swift Testing cases compiled and ran on Windows Swift6.3.3:3PASS/0FAIL. Held operations prove actual drain-before-logout ordering, rejected late work, failed original operation propagation and retained-writer ownership after caller cancellation. A prior long-path SwiftPM attempt failed before compilation and is retained separately. Short-path successful log SHA256176f15e4606522efa2f5e19d6ad18f52876c6c260eaf3c7b1a51bd281c6b60f1.

All9 changed Swift files passed syntax parsing only; this is not Apple typechecking. The original SDK06 native scope retains all76 existing declarations and includes the two actual bootstrap claim cases:78 methods/79 expanded cases across5 suites. The actual tracked source inventory was checked. Existing CI controller tests:46 methods,44PASS with2 pre-existing POSIX-only skips on Windows. Their synthetic receipts do not claim product acceptance.

One upstream-owned file changes: HomeWidgetsCoordinatorViewModel.swift, to bind its existing presentation to its existing app state. The private model owns the binding; an external wrapper cannot retire that binding. This is general original-owner cleanup, with no Pinkha or SDK behavior inserted into its UI. Upstream develop was freshly observed atd857b23ea540be33d6faab4f7a7a1a260ab578c1, merge base d5650321577a209505a3277c8437b7608cff1cb9. Remaining product changes are in the existing downstream Pinkha service/auth composition and PinkhaKit.

The owner's current standing authorization covers these focused source/CI changes and native runs. Other sessions/worktrees, imported Heart, protobuf, immutable SDK116cc6be, provider settings and user data are untouched.

Native current-source UI22 and SDK06 results remain pending. Broader ActiveSpaceManager races, full account/Space switching lifecycle, provider/model, physical signing and language/device matrix are not accepted by these scoped fixes.
