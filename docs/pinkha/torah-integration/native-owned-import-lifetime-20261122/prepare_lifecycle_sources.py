#!/usr/bin/env python3
"""Prepare only the isolated source afterimages for owned import retirement."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sources = {
    "application.go": HERE / "original/core/application/application.go",
    "account_create.go": HERE / "original/core/application/account_create.go",
    "account_create_from_export.go": HERE / "original/core/application/account_create_from_export.go",
    "account_move.go": HERE / "original/core/application/account_move.go",
    "account_select.go": HERE.parent / "original/anytype-heart/core/application/account_select.go",
    "account_stop.go": HERE.parent / "original/anytype-heart/core/application/account_stop.go",
}
guard = '''
	releaseOwnedRetirement, ownedErr := s.beginOwnedImportRetirement()
	if ownedErr != nil {
		RETURN
	}
	defer releaseOwnedRetirement()
'''
headers = {
    "application.go": [("func (s *Service) Stop() error {", "return ownedErr")],
    "account_create.go": [("func (s *Service) AccountCreate(ctx context.Context, req *pb.RpcAccountCreateRequest) (newAcc *model.Account, err error) {", "return nil, ownedErr")],
    "account_create_from_export.go": [("func (s *Service) RecoverFromLegacy(req *pb.RpcAccountRecoverFromLegacyExportRequest) (response RecoverFromLegacyResponse, err error) {", "return RecoverFromLegacyResponse{}, ownedErr")],
    "account_move.go": [("func (s *Service) AccountMove(req *pb.RpcAccountMoveRequest) (err error) {", "return ownedErr")],
    "account_select.go": [("func (s *Service) AccountSelect(ctx context.Context, req *pb.RpcAccountSelectRequest) (*model.Account, error) {", "return nil, ownedErr")],
    "account_stop.go": [
        ("func (s *Service) AccountStop(req *pb.RpcAccountStopRequest) error {", "return ownedErr"),
        ("func (s *Service) AccountChangeNetworkConfigAndRestart(ctx context.Context, req *pb.RpcAccountChangeNetworkConfigAndRestartRequest) error {", "return ownedErr"),
    ],
}
manifest = []
for name, source in sources.items():
    before = source.read_bytes()
    binding = json.loads(source.with_name(source.name + ".binding.json").read_bytes())
    assert len(before) == binding["bytes"] and hashlib.sha256(before).hexdigest() == binding["sha256"]
    assert hashlib.sha1(b"blob " + str(len(before)).encode() + b"\0" + before).hexdigest() == binding["sha"]
    text = before.decode()
    for header, returned in headers[name]:
        assert text.count(header) == 1
        text = text.replace(header, header + guard.replace("RETURN", returned))
    if name == "application.go":
        assert hashlib.sha256(before).hexdigest() == "e889d58b2d9afa11ba5bc8b03cbef5f58c01100a9a2faef0902ba9be2f2e3255"
        text = text.replace("type Service struct {\n\tlock sync.RWMutex", "type Service struct {\n\tlock sync.RWMutex\n\townedImports ownedImportRegistry")
    relative = "core/application/" + name
    original = HERE / "source-preimages" / relative
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(before)
    after = HERE / "candidate/native" / relative
    after.parent.mkdir(parents=True, exist_ok=True)
    after.write_text(text)
    inverse = text
    for header, returned in headers[name]:
        inverse = inverse.replace(header + guard.replace("RETURN", returned), header)
    if name == "application.go":
        inverse = inverse.replace("type Service struct {\n\tlock sync.RWMutex\n\townedImports ownedImportRegistry", "type Service struct {\n\tlock sync.RWMutex")
    assert inverse.encode() == before
    manifest.append({"path": relative, "preimage_sha256": hashlib.sha256(before).hexdigest(),
                     "preimage_git_blob": hashlib.sha1(b"blob " + str(len(before)).encode() + b"\0" + before).hexdigest(),
                     "lifecycle_entries": [header for header, _ in headers[name]],
                     "exact_inverse_before_formatting": True})
(HERE / "LIFECYCLE_INSERTION_PREPARATION.json").write_text(json.dumps({"status": "SOURCE_ONLY_NOT_FORMATTED_OR_EXECUTED", "files": manifest,
    "entries": sum(len(rows) for rows in headers.values()), "product_tests_executed": 0}, indent=2) + "\n")
print(json.dumps({"existing_source_files": len(manifest), "guarded_entrypoints": sum(len(rows) for rows in headers.values()), "original_method_bodies_byte_exact_after_inverse": True}))
