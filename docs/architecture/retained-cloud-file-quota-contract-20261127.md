# Retained cloud FilesV2 quota contract — 27 November2026

## Preserve native state and freshness

The consumer should read the current native account-limits response and retain `limitBytes`, `usageBytes`, and `fetchedAt` together. Missing storage information must remain unknown. A successful HTTP response without a fresh numeric storage answer is not permission to infer free capacity or cloud custody.

For the existing synthetic production test account, the actual fresh response reported limit0 and usage21,070, while the original image and8MiB file independently remained `limited` with `storage limit exceeded`. A conservative displayed remainder is max(0,limit−usage). This observation does not identify a billing entitlement, the user's main account, or a remediation credential.

## Nondurable local files

`cached` and `durable` describe different facts. A cached nondurable file must retain its local encrypted CAR and usable plaintext read path; a cloud refusal must not be converted into local deletion. The original image and large-file CARs remain byte-exact. The earlier actual native quota scenario also verified `409 file.not_durable` for attempted offload of both files.

An explicit retry is one requested retry, not evidence of successful custody. A204 retry acknowledgement must be followed by the native status and durable proof appropriate to that operation. Do not create a replacement file or silently loop retries to mask a limit refusal. The fresh observation performs no retry.

## Cross-account and Offline boundaries

The accepted P2P-disabled cloud evidence covers only the existing8192-byte binary and12420-byte thumbnail, with sender stopped, independent recipient download, Reader write refusal, and subsequent OS-offline cache reopening. It does not cover the original image or8MiB cloud object.

The separately qualified original-account LAN FilesV2 scenario covers the original larger files, image, thumbnail, range/crash/resume/full-cold paths under its own0796 native source closure. LAN transfer is not production-cloud quota recovery. Current read revocation and the coherent final Apple/native union remain separately qualified work.

## Evidence and handoff

Fresh quota receipt: `docs/validation/20261127-wave1-cloud-quota-observation/original/result.json` (aa61aadc).
Exact source: native1dc1803,1594-file manifest12ad65cd, unchanged before/after.
Earlier quota attempt: Oracle `/var/lib/pinkha-w1-cloud-filesv2-20261127/attempt5/result.json` (84810888).
Earlier two-small-file cloud attempt: Oracle `/var/lib/pinkha-w1-cloud-filesv2-20261127/attempt6-small-cloud/result.json` (e6446c4f).

Hanlin, MiniApps, and other consumers should use the existing Host status/retry/offload adapters with current account/Space authority and post-response lifetime checks. This handoff changes no other application. Quota restoration requires an actual newly admitted allowance and successful original-file custody evidence; neither is claimed here.
