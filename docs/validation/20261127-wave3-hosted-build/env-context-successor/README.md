# Runner output path context repair

The actual e98 export dispatch reached GitHub and returned HTTP 422 before any run. The original response is retained as dispatch-e98.original.json, SHA256 eb889ec8290b13cc02137478ba86e3fe8d14033e507e448b6054134685f5c0f5. GitHub rejected runner.temp in three job-level environment values: EXPORT_ROOT, BUILD_ROOT and RETAIN_ROOT.

This successor moves only those three bindings into one initial shell step per new job. Each writes the same runner temporary directory, run ID and attempt path through GITHUB_ENV using quoted shell variables. Existing later steps, output paths, artifact names, source checks, permissions, concurrency and timeouts remain unchanged. Step-level artifact paths retain their supported contexts.

The two replacements reverse byte for byte to e98. The existing e98 inverse then restores the complete original654 dispatcher. The same50 reusable workflow references remain. Both small shell snippets pass bash syntax parsing; no shell body, Python control, compiler, test, account or signing operation was executed. All four Python hashes and their prior15-control receipt remain unchanged. GitHub dispatch and actual native export remain separate root-owned gates.
