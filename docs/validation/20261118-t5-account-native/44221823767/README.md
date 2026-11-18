# Original same-account attempt and Note installation precondition

Run 44221823767 used integration source 9f600ac63041543b1093a2aea34fb6529c4e6fa3.
Original evidence artifact14391207184 is retained byte-for-byte as original-artifact.zip,
verified against GitHub SHA-256:
a145ea32e628f84c1c52550f2de50efd44b43b85288b230175892bc0d541ff07.

Both exact Linux native RPC binaries compiled with unchanged r14/r15 inventories.
One native test invocation started in old-create and failed at fixture line226
with ObjectCreate error code1. Zero phases passed and zero export proofs completed.
The original log has no document index or type key: it establishes failure in the
first account-pair phase, not failure of the first document creation. A confirmed
root cause cannot be inferred from that old error alone.

Source review identified a missing fixture precondition. Heart d98420b
space/clientspace/space.go installs bundle.SystemTypes for a fresh Space;
core/block/object/objectcreator/creator.go resolves the recommended layout from
the actual Space index. The existing application test
TorahNativeDerivedProductIntegrationTests.verifyUniversalProperties explicitly
installs _otnote through workspaceObjectListAdd before creating a Note. The Linux
fixture omitted that native installation.

The follow-up invokes the same original WorkspaceObjectListAdd RPC once, waits
only on the read-only type-index prerequisite, verifies type/Space and custom-type
object identity, and performs each ObjectCreate exactly once. It prints only a
failed ObjectCreate's index, type key and native error description, never wallet
request/response dumps. The secret scan and evidence allowlist remain unchanged.
The controller requires one initial installation and rejects later installations.

The original failure remains a failure. The follow-up needs a new real native run
to establish whether the identified precondition resolves it. No native source,
canonical schema, immutable inventory, product flag or existing acceptance
assertion was weakened. Actual Apple pairing and full F10 remain unproven.
