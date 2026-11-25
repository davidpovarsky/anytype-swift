# Shared immutable-record journal and verifier

Actual source 39a854d804b8af9a69fb6d41e41c0a4aeb72fa32 compiled and ran 22 selected Swift component methods: seven new immutable-record controls, nine unchanged executor methods and six unchanged content-verification methods. All passed, with zero failures/skips. The complete original output and exact source census hashes are retained.

The executor checkpoints the authenticated native schema descriptor and native-normalized SHA before preparation. A resumed journal reconstructs the original intent; it cannot silently refresh schema or signed bytes. The driver rejects changed native store/schema/record/change identities. The verifier reads the ordinary native dataset and compares its complete planned record census, source values and runtime-derived creator/createTime stamps.

The old optional journal encoding and all source/admission guards remain intact. This component proof includes an explicitly simulated lost-ACK transport test. It does not replace the independent actual Go/native HTTP qualification at49dc01a1, or prove the pending end-to-end Swift/native executor and cold-process comparison. The original156-source obligation and actual app capture remain open.

Earlier infrastructure-only attempts ran no tests. A wrong command user created three zero-byte SwiftPM locks. Exact time/inode/owner and no-process/no-open-file checks permitted retiring only those failed-command locks; no cache permissions or product assertions changed. The successful run used the cache's existing owner.
