# Apple pair process cancellation controls

New authored run_logged / terminate_owned functions executed in Linux scratch with three real POSIX process tests. Their exact AST source-text SHA-256 values, and the require/write helpers, were then matched to the production controller in this worktree. The complete private controller was not exported. The test source matches after LF normalization with one terminal newline.

Actual KeyboardInterrupt and timeout both preserve original stdout and a finished CANCELLED/TIMED_OUT command receipt, terminate only the subprocess-owned session using TERM followed by bounded KILL even after the parent exits, and leave a separately owned control group alive. A third test verifies an initial process creation failure still retains a receipt and an empty original log.

The existing14 full-controller rejection functions and46 subcases also passed on Windows with zero skips. The reusable Apple workflow now discovers both test files, so all17 functions run against the complete production controller on its POSIX runner. This is process/control validation; Apple compilation and native runtime pairing remain NOT_RUN.
