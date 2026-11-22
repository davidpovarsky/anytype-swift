# T5 current-authority read candidate

## Observed failure and bounded correction

The original signed-revocation run44961084863 at cce67545ec284aed02c36314eeb7b41c582a3128 executed one real native scenario and failed: current permission was none after signed removal/read-key rotation, but ObjectSearch returned one row and ObjectShow returned its cached payload. Exact originals and hashes are preserved separately in `../20261121-t5-signed-revocation/44961084863/`.

This candidate adds a single common native authority fence to those two existing read APIs. The principal comes from the actual native Space's `GetAclIdentity`, including genuine Guest identities. Only current signed Reader/Guest/Writer/Admin/Owner permissions authorize reading; historical read membership never does.

The fence captures the signed ACL head before the native read. Once the complete response is ready, it requires the same native app and Space instance and the same signed ACL head, and rechecks current permissions. Every failure returns zero rows, zero total and no ObjectView. No command schema, canonical data, mutation behavior or write guard is replaced.

## Native publication and retirement

The final response holds locks in this order: application lifecycle, Space publication, ACL. No object or Space loading, network call or native service callback runs under those final leases. In particular, the ACL is never held while ShowBlock acquires object locks.

`application.Service.AcquireCurrentAppRead` uses the existing lifecycle RW lock only for publication, so AccountStop/Select cannot complete during publication. It does not hold a lifecycle lock while waiting for a Space/object.

The concrete native Space has a small publication gate. Its existing Close entry marks the instance retired and drains active publications, then releases its writer before the existing cache/common cleanup. This closes the post-Get SpaceClose race without widening the Space interface or changing generated mocks. A failed cleanup cannot reactivate that instance.

Cancellation is checked again after waiting for the app/Space leases and after the final ACL lease. A request cancelled during either wait releases its leases and returns no payload.

The examined signed-ACL updater path dispatches controller retirement asynchronously before calling Close; it does not synchronously acquire the publication gate while holding the ACL. The application/Space/block path does not call GetApp from the final lease. The registered concrete native marketplace remains an explicitly public virtual-space exception. An arbitrary nil ACL or missing authority fails closed.

## Shared presentation error contract

The retained protobuf has no permission enum for ObjectSearch/Show. The candidate therefore uses existing BAD_INPUT=2 and exact machine descriptions:

| Description | Native meaning | Shared presentation action |
| --- | --- | --- |
| PINKHA_CURRENT_SPACE_READ_DENIED_V1 | Verified current read permission is absent | Retire cached related results |
| PINKHA_CURRENT_SPACE_READ_INVALIDATED_V1 | Native owner, Space, principal or signed snapshot is unavailable/changed | Retire that result; require a new native read |

These exact code/description pairs are separate from ordinary provider/query failures. Swift/Kit and Any mappings are a separate coordinated source slice; no UI result is certified here.

## Separate source identity and efficient proof

`r15-attachment-current-read-v1` composes over the exact retained corrected r15. Every existing r15 lookup and attachment section remains byte-identical. The new patch inventory, complete AppGetVersion marker and candidate provenance are source-bound. The original corrected runtime, original approvals and default client capability stay unchanged.

The fixed reusable workflow accepts only the original profile or this named candidate profile. Candidate selection adds exactly two new component methods, followed by the original failed real signed scenario:

| Method | Scope |
| --- | --- |
| TestCurrentAppReadPublicationLease | Real native lifecycle RW-lock exclusion and replacement retirement; no account fixture |
| TestCurrentSpaceReadPublicationLease | Actual native Space.Close entry retires before cleanup; only unrelated cache/common cleanup is inert |
| TestT5NativeCachedQueriesAfterSignedRevocation | Actual generated RPCs, real account/Space/cache/index, original owner and Reader positive controls, signed removal and read-key rotation, exact typed denial with no payload |

The same native updater remains installed. No former account identity is swapped, no teardown is suppressed, and no historical pagination/T2/Space.Close/attachment regression suite is selected. Compatible compiled dependencies may be reused; changed-source binaries and test results are freshly produced.

Receipt protocolv2 additionally requires exact native authority descriptions. An unrelated nonzero error cannot masquerade as successful revocation enforcement. The original protocolv1 failure remains immutable and is interpreted using its original source.

The real signed-removal callback can asynchronously retire the native Space before the follow-up RPC. Therefore this candidate's contract, fixed before corrected native execution, accepts either exact DENIED_V1 or INVALIDATED_V1 with BAD_INPUT=2. Both require Search rows=0 and total=0, and Show ObjectView=nil. Success-with-empty, generic errors, descriptions with a suffix, or payload hidden behind an error still fail. Owner/Reader positive controls, signed transitions, same account, populated cache, unchanged updater and actual native terminal records remain mandatory.

## Verification status

Eight new or affected source/controller methods passed in the isolated source review; no old native suite was executed. The complete candidate patch applied cleanly to a separate exact Heart checkout. Its eight changed/additive Go files match the inventory and parse as canonical gofmt bytes. The first formatting check reported Windows CRLF materialization; its original failure record remains preserved. The follow-up compared the exact LF bytes described by the candidate inventory and passed without changing product code or repeating the eight successful controls.

Candidate patch SHA256: `977f485e13892d259da5f47b9c96bdcf3b34b23defff25271b22af43ac91b9f9`.
Candidate inventory SHA256: `d7ff255272a947c008b2bbbf951fff863b4b2469a37954c60a7cc22b0fa8301f`.

Native candidate component and real-account execution: NOT_RUN. iOS runtime, shared UI retirement, remote ACL transport, offline-unknown revocation and full T5 acceptance remain unproven. The next fixed selection is the two new native publication methods plus the original failed signed-removal scenario, with fresh results for this exact candidate.
