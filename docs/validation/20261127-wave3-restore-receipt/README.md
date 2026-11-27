# Preserve original restore-qualification receipts

This narrow successor is based on a70e94f9647df16ce8962894b1973ba5a5a35163. It changes only the downstream filesystem qualification controller and adds one focused control. The original atomic native792 restore implementation, its four filesystem test methods, f8cc receipt/log, custody378c and addendum9e79 remain unchanged.

The old qualifier checked that result.json was absent inside try, then always saved in finally. A second invocation could replace an existing result after that check failed. The successor reserves result.json atomically with O_CREAT|O_EXCL before entering any cleanup/persistence path. An occupied path stops before native custody reads. After a successful claim the original qualification body is byte-identical. literal-inverse.json reconstructs the full original wrapper.

One actual local Linux disposable-filesystem method passed: the exact candidate runs with an existing synthetic receipt, reports FileExistsError with no normal stdout, preserves bytes and inode/mode/owner/mtime/ctime/link count, and creates no other files. existing-result-control.json and its original log bind source, argv, platform and absent owned process group. This is not an Oracle native test, product acceptance or an actual native restore. The original four filesystem methods were not rerun.

The new focused source can be run directly with Python against its adjacent candidate wrapper in a fresh disposable directory. The .py.txt files are exact retained original local producer/reviewer bytes, not new native execution entry points. Do not run the real qualifier over any retained receipt.

The independent review also binds the a935 historical network reuse ledger and a70 original exclusive-restore evidence. Historical12 network,2 fixed object-authority and2 Linux P2P methods retain their original source/platform scope. The1594→1599 source delta is explicit; no current mixed-version, FilesV2 revoked-read, Apple UI or release PASS is inferred. Root retains final integration ownership.
