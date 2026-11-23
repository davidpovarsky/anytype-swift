# Read-only full-archive migration dry run

This is a downstream consumer of the existing AnyHeartSpaceArchive inspector.
It inventories the complete supplied archive and explicit schema mapping
proposals. It does not claim a complete native Space or implement apply.

## Boundary

AnyHeartSpaceMigrationDryRun accepts an already inspected archive, an explicit
AnyTorahWorkspace destination, and type/property mapping proposals. It has no
transport, native service, store, callback, filesystem or executor argument.
Both permitsDestinationWrites and hasNativeSourceAdmission are always false.
Every original inspection issue is retained, including nativeSnapshotProofRequired
and nativeIdentityCensusRequired. A retained sidecar cannot satisfy either gate.

No existing product file, package manifest, inspector or qualified destination
primitive is changed. The original canonical association migration remains
separate. This source does not select or activate a native runtime.

## Coverage and proposals

Every inspected object, each object-scoped block, each file identity, every
property definition and every property value/legend use gets a typed source
identity. Referenced unknown property keys also receive unresolved inventory
rows. Type references and native object_type declarations are joined by their
exact internal keys; duplicate declarations remain ambiguous. Objects without
a native type key require an explicit object-specific type proposal. A display
name cannot substitute for a source type identity.

Identity equality and report symbols use length-framed raw UTF-8, including
kind, source Space and optional owning object. A block ID in another object,
a file ID and an object ID are different identities. The consumer rechecks
every property value/legend/spelling/definition join by exact UTF-8. File
manifest identities and payload paths, property-dictionary paths and entry
digests also require exact raw membership. Swift's canonically equivalent
String dictionary lookup cannot establish a source identity or source location.
Unmatched manifest file identities receive separate unresolved rows. Missing
raw paths never receive an invented JSON-pointer location; all original values
and entries remain distinguishable.

Mappings are proposals only. Wrong-Space, wrong-kind, malformed and duplicate
requests refuse. Unbound proposals remain visible. Distinct type/property
identities proposing the same destination schema identity are explicitly
ambiguous; assigning the same ordinary type to separate untyped objects is
allowed as a reference proposal. Missing source definitions and current native
schema/authority compatibility remain unverified.

All source entries, typed values, unknown metadata, original bytes and digests
remain available. Entry coverage includes opaque/unclassified files and
retained sidecars. Block source parent/order are retained without producing
native positions or converted body text. File content is classified as missing,
remote-only, within the existing prepared inline byte bound, or needing another
storage path. A 0-4095-byte classification is not file import admission. File
owner mapping, metadata conversion and native source recovery remain required.

The plan digest binds exact inspected source content, destination account/Space
and order-independent explicit proposals. Report symbols are not native IDs.
No native object/block/file IDs, intents or signed bytes are fabricated.

The archive keeps its existing bounds. This consumer additionally refuses more
than 300,000 recognized entities or 60,000 explicit mapping requests before
returning a report. Coverage describes the supplied archive only; an empty
archive never becomes proof of an empty native Space.

## New qualification scope

Eighteen new focused XCTest methods cover complete identity/entry accounting,
owner and kind namespaces, block hierarchy, property ambiguity/unused metadata,
exact Unicode identity, malformed/duplicate proposals, target aliasing, duplicate
type declarations, file boundaries/recovery/owner refusal, byte and numeric
preservation, opaque sidecars, deterministic destination-bound plans, unsupported
cases and bounded inputs. They do not execute the qualified archive-inspection,
destination object/block, inline native, HTTP, Swift client or Apple methods.

Source is frozen before the new control execution. Original command/log/event,
source/dependency and compiler identities will be recorded separately. Build
success is not native, Apple, network, device or full migration acceptance.

## Source ownership

Base: 67809875752085047a395be4a751ace5dcbc7ad8.
Fresh upstream develop: d857b23ea540be33d6faab4f7a7a1a260ab578c1.
New source/test and this validation directory are downstream-owned. No upstream,
Heart, schema, protobuf, App fixture, mounted admission or default route changed.
The writer is a minimal sparse isolated worktree on Oracle. Shared integration
and Asana updates remain owned by the root task.
