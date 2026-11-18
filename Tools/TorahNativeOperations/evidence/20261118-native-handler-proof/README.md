# Native handler controls — verified Linux result

Run [44239002534](https://github.com/davidpovarsky/anytype-swift/actions/runs/44239002534), attempt 1, completed successfully on exact integrated source `f8cf3551eb66c725d9241917d778b52a647c71c2` (development source `1f0c134c7986dd637540569eb1bd1192919070b4`). Heart remains pinned to `d98420b1113536afd08cde6de9a5816f6d27ffff`.

The registry suite has **18 top-level + 21 subcase PASS (39 total), 0 FAIL, 0 SKIP**. The component suite has **23 top-level + 45 subcase PASS (68 total), 0 FAIL, 2 helper SKIP**. The skipped parent-process helpers are recorded by name in `verified-summary.json`; they are not counted as passes.

The three new core controls prove version rejection, missing-account rejection, and read-shape/cancellation rejection before account access. The fourth new control uses actual signed ACL membership to check current reader authority. These tests compile the new typed native boundary and verify its covered negative paths; they do not execute its successful append/read path through a real account.

Artifact digests, source bindings and raw Go test event counts were verified in memory on the connected host. The metadata here is a verification summary, not a copy of the raw evidence. Raw artifacts remain on the linked GitHub run.

## Acceptance still open

Generated RPC and App binding are not implemented/enabled. Real-account handler happy-path acceptance, two App clients, iOS and full T2 remain unaccepted. Existing transport evidence is limited to two isolated native processes over the loopback protocol. The separate account lifecycle run `44237407166` failed at the private ObjectExport assertion before saving its Result; this pass does not change that failure or establish private export safety.
