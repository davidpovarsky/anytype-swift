# Preserve original importer request compatibility

The actual Go1.26.5 Darwin importer compile-only run 45044056210 at 1788d475 failed because the diagnostic field added to ImportRequest broke original positional test literals. No original test body was executed or changed. The complete failed compiler evidence and root review are retained here.

This correction restores the exact original five-field ImportRequest declaration. The unchanged NewProcessor constructor stays default-off; a separate unexported constructor opts a private processor into the already-reviewed observation. Two guards now read that private flag. There is no RPC or production callsite. The mapping builder, converter, complete-drain eligibility, readResults, metadata and original r14 remap are preserved. The original 50-control result remains historical at 20cb8998; it is not relabeled as execution of changed source.

Seven new compatibility controls compiled and executed once using Go1.25.6 Windows, all PASS with no skips/failures. They use the actual changed request, constructors and guard/helper fragments with explicitly retained dependency fixtures. They establish source-layout and default/explicit opt-in behavior only. Full original-module Go1.26.5 compile/link remains required; no native import, full file-completion drain, account lifetime, body equality or ACK is claimed.

The unchanged strict installer uses all six corrected afterimages only after the exact original/r14 preimages have been verified. This packet is independent from the new source-only owned uploader design.
