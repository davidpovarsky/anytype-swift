# Canonical description in imported type presentation

The source migration mapper already binds the qualified Heart description relation to the original Any `any.description` native field. The imported presentation adapter previously accepted only `any.name`, so a migrated type recommending description was rejected as an invalid catalog even when the actual native data and descriptor were correct.

The adapter now accepts the two qualified synced string fields `name` and `description`. Unknown builtins, wrong native kinds/scopes, foreign owner references, duplicated property addresses, reader writes and unqualified layouts remain refused. No source/destination migration admission gate changed.

Actual Oracle Swift execution: all **9 distinct tests passed**, zero failures/skips. Six existing controls were affected by the adapter change; three new controls cover actual canonical address selection, empty-description edits, native version/sequence fences, visibility persistence/reopen and refusal of derived/account/wrong-kind descriptors. This is a shared component result, not a new Apple UI or whole-space migration acceptance claim.

Original log SHA-256: `681e5ab20aa6d94d0ec822f1016085a7890809db6cd96e3c793dd4832815f5b8`. Source hashes, exact command, original complete log and result are retained alongside this README. Source was unchanged during execution.
