# Original current-authority HTTP acceptance

The corrected Any/Anytwo product passed **14 actual HTTP content denials** for the original removed member. The owner first confirmed the same account, Space, object, file metadata and removed membership. The member then received seven typed denials online and the same seven denials after a new process opened the existing account under the qualified OS outbound-denial policy. No role, invitation, upload, retry, initialization or restoration was dispatched.

## Actual result

| Item | Exact result |
|---|---|
| Status | `PASS_ORIGINAL_CURRENT_AUTHORITY_HTTP14_ONLY` |
| SentinelX job | `job_a3a0e12f272f` |
| Finished | `2026-11-27T13:52:18.494539Z` |
| Controller duration | 18.351 seconds |
| Outer exit | 0 |
| Receipt | `receipts/current-authority-http14.json` |
| Original receipt path | `/var/lib/pinkha-c-filesv2-20261126/current-authority-http-20261127/attempt1/result.json` |
| Raw receipt bytes / SHA-256 | 44,376 / `7efa899783f5cabb54b2693dca0a22a9571d499ef4b9838749dfb8e677784099` |
| Controller SHA-256 | `2bbda0f4d389aef369d1df1459d2e5d03ba9648121211619aa028b99a0990ac5` |
| Installation envelope SHA-256 | `db521e996a40a93b26acb79d1f211bdc0b37d168e41edd65e59ffdb1d859206c` |
| Native binary | `1b25764f9af1af854a928b3c445044a6906cb3477b64b4da6689b9e29997e639` |
| Native producer receipt | `e26587d911cec570f9215db8bc424f9faa7fe2d09c4354f71cdb772e6fafd394` |
| Complete 1,607-file source manifest | `aa43f853a28c2cd0e125b70cdcc01b05a4748f0c25541f5ed86cea511e6b8dd1` |

Each of these routes returned **HTTP 403 and `error.code == "acl.forbidden"`** in both member phases. A 200, a different denial code, an incomplete response, or a timeout would fail; the controller does not explicitly consume an unexpected successful content body.

| Route | Requested content |
|---|---|
| `E9ZfwB8Biag/content` | Entire 8,192-byte revocation canary |
| `E9ZfwB8Biag/content`, Range `bytes=0-31` | Canary prefix |
| `hs6LTsotxAY/content`, Range `bytes=200000-232767` | Partial read of the 8 MiB file |
| `9DSkw6W3eqv/content` | PNG image |
| `SbLLxZDbq59/content` | Direct thumbnail |
| `9DSkw6W3eqv/content?variant=thumb` | Thumbnail resolved from its parent |
| `AEhbwaXwY7S/content` | Earlier successful member-authored file |

The fixed account, Space, object and complete file bindings are in the raw receipt. The member's self-membership was `removed/none` both before and after each phase. The owner independently observed that removal before and after its metadata checks. All five member metadata rows still reported `cached=true`; this acceptance therefore includes denial of newly served content from an existing cache. It does not claim removal of plaintext the member had previously received, and it makes no claim that the canary was still uncached.

## Fresh process, network policy and cleanup

The three native processes were sequential: owner PID 844356, online member PID 844564 and fresh offline member PID 844844. Each exited 0 after its one recorded graceful stop. The qualified owner retained leader identity through group cleanup and recorded positive absence for every group. There were no forced cleanups or cleanup errors.

The offline native process was exec-launched through the exact 3,701-byte policy helper `6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1`. Its live process had `NoNewPrivs` and seccomp filter mode 2. The original qualified filter library remained `3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19`; native sync status reported `offline` with zero local, global and network peers. The original independent syscall controls were reused rather than rerun.

The complete source closure and all admitted public inputs matched before and after execution. Initial free storage was 2,368,307,200 root bytes and 33,895,342,080 development bytes. Minimum root free space was 2,367,676,416 bytes, above the unchanged 2 GiB floor; development remained above its 512 MiB floor. The owned output peaked at 159,744 bytes. No compiler or additional native build ran.

## Preserved boundary and original failure

The original failure `ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab` remains immutable: one removal was acknowledged, membership became removed/none, and the old native product subsequently served the canary with HTTP 200. That insecure GET was not replayed. The corrected product was accepted against the preserved removed state with GETs only.

The controller did not open, copy, inventory or export private account files. The native application opened its existing stores through ordinary startup, which may perform its normal operational store writes. Historical custody `792268b4d7448d9c9b6665ee6388f26c18e5de0635aa05f1b390db7f20a5567d` is prior lineage, not a new byte-level account audit or independent export of a seventh signed record. Restoration count remains zero.

This receipt qualifies the ordinary HTTP boundary. Held SDK readers are separately qualified by the two fresh synthetic `Files.Open` methods and the 35 signed-ACL/lifetime events in this handoff. No Apple runtime, UI, role restoration or all-file cloud durability is inferred from this result.
