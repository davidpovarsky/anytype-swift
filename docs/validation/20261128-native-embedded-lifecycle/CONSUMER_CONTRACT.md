# Embedded lifecycle contract

Status: reviewed source, not compiled or executed.

## Native callers

Start and StartBound share one process-wide reservation from admission through startup and running lifetime. ErrAlreadyRunning includes a pending start. A caller may cancel a pending attempt using Stop or StopNow; an unsuccessful bound start returns the empty BoundStartResult and cannot borrow another generation's network identity.

A start admitted while a previous generation is draining waits for that complete drain. If it is cancelled while waiting, its completion still depends on its predecessor. Successive cancellations cannot shorten the teardown chain. This may delay the cancelled Start caller; it does not make StopNow wait.

Both stop modes cancel the current generation and retain its completion barrier. Stop(true) waits for the generation it observes, including an already pending hard-stop drain. StopNow initiates cancellation and returns without waiting on completion. Hosts still own their lifecycle policy and must not interpret cancellation initiation as completed native drain.

A late Ready or completion from an older generation cannot replace or clear a newer reservation. Successful Start returns the listener for its admitted generation. Its returned identity remains immutable; a later host stop or runtime exit can still end that generation.

## Binding, authority and downstream consumers

The f372 expectedNetworkID contract remains in force. Expected network identity is resolved from the same exact native nodeconf used for that boot. Account/run authority must still come from the current bound HTTP response and signed current membership, with independent expected account/network checks.

This lifecycle fix does not replace N24's captured HTTP engine lifetime, request acknowledgments or READ/ACL enforcement. It does not provide a retry rule for uncertain mutations. Hanlin, MiniApps and Otsaria consumers must retain the current owner, wait for their own producer/write drains, and reject retired or mismatched account/Space/run state under their existing contracts.

No source-only carrier admits old8ac as a matching binary. W3 must produce and qualify the combined native product and exact ABI/profile; W2 and W3 retain their own UI and application acceptance work.

## Qualification scope

The new private runner seam is a test seam only. Its controlled interleavings prove nothing until selected tests execute successfully against the exact source. The real-export test and the four affected old lifecycle tests also remain pending.

Before runtime, bind complete input source and modes, exact native toolchain, selected method discovery, resource floors, deadlines, process-group custody and final source/product evidence. Test selection is explicit in test-selection.json. No acceptance, authorization or identity assertion is weakened by this delivery.
