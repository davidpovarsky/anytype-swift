# Two original durable files delivered through production cloud

This evidence continues the same retained synthetic production account pair after
the quota-limited attempt5. The sender remained stopped; local and global direct
peers were disabled. The original receiver was an active Reader connected to the
production network, with both selected files uncached before reading.

| Original file | Plaintext bytes | Actual cloud read seconds |
| --- | ---: | ---: |
| cloud-binary.bin | 8192 | 1.510 |
| cloud-thumb.png | 12420 | 0.581 |

Both native file IDs, object ID, root CIDs, MIME values, content bytes and SHA256
digests matched the original attachment records. Reading the original image's
variant=thumb resolved the exact PNG thumbnail. A real Reader attachment attempt
returned HTTP403 space.read_only; all four original file IDs remained unchanged.

The first recipient process exited cleanly and its process group was positively
absent. A second distinct native PID inherited OS-enforced NoNewPrivs1/Seccomp2,
reported zero network peers, and read both exact cached plaintexts plus the
thumbnail resolver again. It also exited cleanly with its process group absent.
No native rebuild, account initialization, join, grant, quota retry or new
successful attachment was performed.

The exact executed controller is preserved, including its inherited introductory
comment. Its executable scope and the observed receipt select only the two
already-durable files; the introduction does not add acceptance.

## Limits

This is selected-file cloud custody, cross-account plaintext, Reader write denial
and cold offline acceptance. The original image and 8MiB object remain subject to
the separately retained cloud quota refusal. This run does not accept all four
files, large-file ranges, crash/resume, cryptographic negative controls, full
quota recovery, or Apple runtime. Those require their own exact evidence.
The separate LAN experiment uses independent account copies and is not cloud
custody evidence.

observed-result.json preserves the exact original receipt bytes. result.json
states the accepted scope and source envelope. The original private process logs
and all account data remain under the receipt's original Oracle directory.
