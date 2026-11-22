"""Compose the observed native cached-read fix over immutable corrected r15.

This adds one current-authority publication rule to ObjectSearch/ObjectShow.
It preserves every r15 lookup/attachment patch section and creates a separate
candidate identity; it does not replace the retained runtime or its approvals.
"""
from __future__ import annotations

from dataclasses import dataclass
import difflib
import json
from pathlib import Path
import subprocess

import attachment_runtime as base

VARIANT = "r15-attachment-current-read-v1"
BASE_VARIANT = "r15-attachment-v1"
OVERLAY = "Tools/PinkhaNativeDerived/read_authority/overlay"
BEFORE = {
    "core/object.go": "ce7a2c4c8a0690814a915e16833c0ec214f7f8787dccbf20adc08ee64a3cee34",
    "core/block.go": "44f03ff2601d060cddf83aca13bdb185b6bf3d90765768571276e3168afd3d75",
    "space/clientspace/space.go": "9d013f65a61ddd3c436622b9809d37e67fdd8246130005d21461e51a89416f32",
}
ADDITIONS = (
    "core/application/pinkha_current_read.go",
    "core/application/pinkha_current_read_test.go",
    "core/pinkha_current_read.go",
    "space/clientspace/pinkha_current_read.go",
    "space/clientspace/pinkha_current_read_test.go",
)
PRODUCT_PATHS = tuple(sorted((*BEFORE, *(p for p in ADDITIONS if not p.endswith("_test.go")))))


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError("Native current-read anchor changed: " + old[:100])
    return text.replace(old, new)


def edit_method(source: str, method: str, edit) -> str:
    begin = source.index("func (mw *Middleware) " + method + "(")
    end = source.index("\nfunc ", begin + 1)
    original = source[begin:end]
    return source[:begin] + edit(original) + source[end:]


def search_method(source: str) -> str:
    source = replace_once(source, "\tvar total int64\n", "\tvar total int64\n\tvar readScope *pinkhaCurrentReadScope\n")
    source = replace_once(source,
        "\t\tm := &pb.RpcObjectSearchResponse{Error: &pb.RpcObjectSearchResponseError{Code: code}, Records: records, Total: total}",
        """\t\tif readScope != nil {
\t\t\trelease, authorityErr := readScope.acquirePublication(cctx)
\t\t\tif authorityErr != nil {
\t\t\t\tcode, err = pb.RpcObjectSearchResponseError_BAD_INPUT, authorityErr
\t\t\t} else {
\t\t\t\tdefer release()
\t\t\t}
\t\t}
\t\tif err != nil {
\t\t\trecords, total = nil, 0
\t\t}
\t\tm := &pb.RpcObjectSearchResponse{Error: &pb.RpcObjectSearchResponseError{Code: code}, Records: records, Total: total}""")
    source = replace_once(source,
        """\tif mw.applicationService.GetApp() == nil {
\t\treturn response(pb.RpcObjectSearchResponseError_BAD_INPUT, nil, fmt.Errorf("account must be started"))
\t}
""",
        """\treadApp := mw.applicationService.GetApp()
\tif readApp == nil {
\t\treturn response(pb.RpcObjectSearchResponseError_BAD_INPUT, nil, fmt.Errorf("account must be started"))
\t}
\tvar scopeErr error
\treadScope, scopeErr = mw.pinkhaBeginCurrentSpaceRead(cctx, readApp, req.SpaceId, "")
\tif scopeErr != nil {
\t\treturn response(pb.RpcObjectSearchResponseError_BAD_INPUT, nil, scopeErr)
\t}
""")
    source = replace_once(source, "mw.applicationService.GetApp().MustComponent(indexer.CName)", "readApp.MustComponent(indexer.CName)")
    source = replace_once(source, "mw.applicationService.GetApp().MustComponent(objectstore.CName)", "readApp.MustComponent(objectstore.CName)")
    # Use the exact captured native Space service for the complete read. This
    # avoids accidentally switching apps through a later mustService(GetApp).
    source = replace_once(source,
        "records, req.Filters, ds, mustService[space.Service](mw))",
        "records, req.Filters, ds, readScope.spaces)")
    return source


def show_method(source: str) -> str:
    source = replace_once(source, "\tvar obj *model.ObjectView\n", "\tvar obj *model.ObjectView\n\tvar readScope *pinkhaCurrentReadScope\n")
    source = replace_once(source,
        "\t\tm := &pb.RpcObjectShowResponse{Error: &pb.RpcObjectShowResponseError{Code: code}}",
        """\t\tif readScope != nil {
\t\t\trelease, authorityErr := readScope.acquirePublication(cctx)
\t\t\tif authorityErr != nil {
\t\t\t\tcode, err = pb.RpcObjectShowResponseError_BAD_INPUT, authorityErr
\t\t\t} else {
\t\t\t\tdefer release()
\t\t\t}
\t\t}
\t\tm := &pb.RpcObjectShowResponse{Error: &pb.RpcObjectShowResponseError{Code: code}}""")
    source = replace_once(source,
        """\tid := domain.FullID{
\t\tSpaceID:  req.SpaceId,
\t\tObjectID: req.ObjectId,
\t}
\terr := mw.doBlockService(func(bs *block.Service) (err error) {
\t\tobj, err = bs.ShowBlock(id, req.IncludeRelationsAsDependentObjects)
\t\treturn err
\t})""",
        """\treadApp := mw.applicationService.GetApp()
\tif readApp == nil {
\t\treturn response(pb.RpcObjectShowResponseError_UNKNOWN_ERROR, ErrNotLoggedIn)
\t}
\tvar scopeErr error
\treadScope, scopeErr = mw.pinkhaBeginCurrentSpaceRead(cctx, readApp, req.SpaceId, req.ObjectId)
\tif scopeErr != nil {
\t\treturn response(pb.RpcObjectShowResponseError_BAD_INPUT, scopeErr)
\t}
\tid := domain.FullID{
\t\tSpaceID:  readScope.spaceID,
\t\tObjectID: req.ObjectId,
\t}
\tbs := readApp.MustComponent(block.CName).(*block.Service)
\tvar err error
\tobj, err = bs.ShowBlock(id, req.IncludeRelationsAsDependentObjects)""")
    return source


def space_source(source: str) -> str:
    source = replace_once(source, "type space struct {\n\tobjectcache.Cache",
        "type space struct {\n\tcurrentRead currentReadPublicationGate\n\tobjectcache.Cache")
    return replace_once(source,
        """func (s *space) Close(ctx context.Context) error {
\tif s == nil {
\t\treturn nil
\t}
""",
        """func (s *space) Close(ctx context.Context) error {
\tif s == nil {
\t\treturn nil
\t}
\ts.retireCurrentReadPublications()
""")


def patch_section(path: str, before: bytes | None, after: bytes) -> bytes:
    header = "diff --git a/" + path + " b/" + path + "\n"
    if before is None:
        header += "new file mode 100644\n"
    difference = "".join(difflib.unified_diff(
        [] if before is None else before.decode().splitlines(keepends=True),
        after.decode().splitlines(keepends=True),
        fromfile="/dev/null" if before is None else "a/" + path,
        tofile="b/" + path,
    ))
    if not difference:
        raise ValueError("Current-read source did not change: " + path)
    return (header + difference).encode()


def version(patch_sha: str) -> str:
    return base.runtime_version(BASE_VARIANT, patch_sha) + "-pinkha-current-read-v1-" + patch_sha


@dataclass(frozen=True)
class RuntimeSource(base.RuntimeSource):
    @property
    def version(self) -> str:
        return version(self.patch_sha256)

    @property
    def lookup_capability(self) -> int:
        return 1


def compose(retained: base.RuntimeSource, originals: dict[str, bytes], additions: dict[str, bytes]) -> RuntimeSource:
    if retained.variant != BASE_VARIANT or set(originals) != set(BEFORE) or set(additions) != set(ADDITIONS):
        raise ValueError("Unreviewed native authority source paths")
    expected = base.VARIANTS[BASE_VARIANT]
    if retained.patch_sha256 != expected["corrected_patch_sha256"] or retained.inventory_sha256 != expected["corrected_inventory_sha256"]:
        raise ValueError("Current-read candidate requires the exact retained corrected r15")
    parts = base.sections(retained.patch)
    inventory = json.loads(retained.inventory)
    files = base.file_inventory(inventory)
    if set(parts) != set(files) or set((*BEFORE, *ADDITIONS)) & set(parts):
        raise ValueError("Current-read fix would replace an existing r15 section")
    for path, expected in BEFORE.items():
        before = base.checked_digest(originals[path], expected, path)
        if path == "space/clientspace/space.go":
            after = space_source(before.decode()).encode()
        else:
            method, edit = ("ObjectSearch", search_method) if path == "core/object.go" else ("ObjectShow", show_method)
            after = edit_method(before.decode(), method, edit).encode()
        parts[path] = patch_section(path, before, after)
        files[path] = dict(path=path, before_sha256=expected, after_sha256=base.sha256(after))
    for path in ADDITIONS:
        after = base.normalized(additions[path])
        if not after.endswith(b"\n") or not after.startswith(b"package "):
            raise ValueError("Invalid native authority overlay: " + path)
        parts[path] = patch_section(path, None, after)
        files[path] = dict(path=path, before_sha256=None, after_sha256=base.sha256(after))
    patch = b"".join(parts[path] for path in sorted(parts))
    digest = base.sha256(patch)
    inventory.update(
        status="SOURCE_COMPOSED_CURRENT_AUTHORITY_NATIVE_NOT_RUN",
        runtime_variant=VARIANT, patch_sha256=digest,
        previous_patch_sha256=retained.patch_sha256,
        expected_app_get_version=version(digest),
        features=dict(inventory.get("features", {}), current_authority_read_fence=1),
        files=[files[path] for path in sorted(files)],
        product_source_changes=len(PRODUCT_PATHS),
        client_enablement="DISABLED_PENDING_NATIVE_AND_RUNTIME_PROOF",
        current_authority_provenance=dict(
            observed_failure_run_id="44961084863",
            observed_failure_source_sha="cce67545ec284aed02c36314eeb7b41c582a3128",
            observed_failure_artifact_id="14729761820",
            observed_failure_artifact_sha256="0b5d456f7b5b03a8873771802aec4d80f904ad67386c4e7b4ab280f5a790c5ba",
            product_paths=list(PRODUCT_PATHS),
            component_tests=["TestCurrentAppReadPublicationLease", "TestCurrentSpaceReadPublicationLease"],
            unchanged_r15_paths=sorted(base.sections(retained.patch)),
            default_runtime_unchanged=True,
            network_revocation="NOT_RUN", offline_unknown_revocation="NOT_PROVEN",
            swift_ui="NOT_RUN", full_t5_acceptance=False,
        ),
    )
    return RuntimeSource(VARIANT, patch, base.json_bytes(inventory))


def prepare(source: Path, control: Path, heart: Path) -> RuntimeSource:
    retained = base.prepare(source, control, BASE_VARIANT)
    head = subprocess.check_output(["git", "-C", str(heart), "rev-parse", "HEAD"], text=True).strip()
    if head != base.HEART_SHA:
        raise ValueError("Unexpected original Heart source for the authority fix")
    originals = {path: subprocess.check_output(["git", "-C", str(heart), "show", head + ":" + path]) for path in BEFORE}
    additions = {path: (control / OVERLAY / path).read_bytes() for path in ADDITIONS}
    return compose(retained, originals, additions)
