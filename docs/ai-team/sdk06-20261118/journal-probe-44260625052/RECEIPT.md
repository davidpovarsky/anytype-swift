# First standalone journal probe: compilation timeout, no filesystem observation

Original run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44260625052

The original GitHub job conclusion is CANCELLED. The original controller receipt separately records FAIL / TimeoutExpired at compile-probe-only, with its configured 240-second allowance. Preserve both facts; neither is a journal functional failure. The compiler log is empty, and the job log reports the controller timeout before the operation-cancelled message. The available evidence does not identify the compiler activity or the reason for workflow cancellation.

The exact Xcode 27.0 / 27A266a and iOS 27.0 / 24A434 checks passed. A fresh owned simulator was created and booted; its shutdown and deletion succeeded. No app executable was launched, no platform filesystem receipt was produced, and no SDK, native write, physical-device protection or durability acceptance is claimed.

The source-only controller correction adds verbose compiler output, a fixed 600-second compile allowance within a 20-minute workflow deadline, command timestamps and flushed progress every 30 seconds. It does not modify JournalFilesystemProbe.swift or any production journal guard. Three real Linux subprocess controls passed (completed exit status, progress for a silent command, fixed deadline with owned-process reaping). A separate read-only peer review confirmed the deadline/cancellation paths; actual Apple execution of the correction remains NOT_RUN.

Original execution.json and compile-probe-only.log were extracted from the verified artifact without rewriting. job.log is the original GitHub job log. provenance.json records original byte counts and SHA256 values.
