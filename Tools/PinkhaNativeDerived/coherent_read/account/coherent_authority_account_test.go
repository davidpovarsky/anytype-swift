package service

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/anytype-heart/core/block/editor/torahops"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/clientspace"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

const coherentAuthorityProtocol = "pinkha-coherent-signed-authority-v1"

func coherentAuthorityWriteBytes(t *testing.T, path string, raw []byte) {
	t.Helper()
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	require.NoError(t, err)
	_, err = file.Write(raw)
	require.NoError(t, err)
	require.NoError(t, file.Sync())
	require.NoError(t, file.Close())
}

// This proves shared runtime/account/Space authority for two real RPC families.
// T2's private immutable projection and T5's canonical property are distinct;
// this test does not claim automatic T2-to-T5 materialization.
func TestCoherentNativeReadsAfterSignedRevocation(t *testing.T) {
	nonce := os.Getenv("PINKHA_T5_ACL_NONCE")
	operationID := nonce
	payload := []byte("synthetic coherent authority operation")
	var originalApp *app.App
	var originalSpace clientspace.Space
	var accountID, spaceID, objectID, blockID, claimID, changeID string
	var canonical []byte
	var ownerVariant *pb.PinkhaTorahAuthorizedOperationReadVariant
	var ownerWire, readerWire, removedWire []byte
	var deniedCode int32
	stages := []string{}
	calls := map[string]int{}
	call := func(name string, entry func([]byte) []byte, request, response proto.Message) []byte {
		t.Helper()
		input, err := proto.Marshal(request)
		require.NoError(t, err)
		calls[name]++
		output := entry(input)
		require.LessOrEqual(t, len(output), torahops.MaxAuthorizedOperationReadBytes)
		require.NoError(t, proto.Unmarshal(output, response))
		return output
	}
	read := func() (*pb.PinkhaTorahAuthorizedOperationReadResponse, []byte) {
		t.Helper()
		response := &pb.PinkhaTorahAuthorizedOperationReadResponse{}
		raw := call("PinkhaTorahAuthorizedOperationRead", PinkhaTorahAuthorizedOperationRead,
			&pb.PinkhaTorahAuthorizedOperationReadRequest{ProtocolVersion: 1, SpaceId: spaceID, OperationId: operationID}, response)
		require.Equal(t, uint32(1), response.ProtocolVersion)
		require.NotNil(t, response.Error)
		return response, raw
	}
	positive := func() (*pb.PinkhaTorahAuthorizedOperationReadVariant, []byte) {
		t.Helper()
		response, raw := read()
		require.Equal(t, int32(0), int32(response.Error.Code))
		require.Empty(t, response.Error.Description)
		require.NotNil(t, response.Snapshot)
		value := response.Snapshot
		require.Equal(t, torahops.AuthorizedOperationReadContract, value.Contract)
		require.Equal(t, accountID, value.AccountId)
		require.Equal(t, spaceID, value.SpaceId)
		require.Equal(t, operationID, value.OperationId)
		require.True(t, value.Complete)
		require.Len(t, value.NativeSnapshotToken, 64)
		require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_FOUND, value.Outcome)
		require.Len(t, value.Variants, 1)
		variant := value.Variants[0]
		require.Equal(t, claimID, variant.ClaimId)
		require.Equal(t, operationID, variant.OperationId)
		require.Equal(t, spaceID, variant.SpaceId)
		require.Equal(t, accountID, variant.AuthorId)
		require.NotNil(t, variant.Target)
		require.Equal(t, objectID, variant.Target.ObjectId)
		require.Equal(t, blockID, variant.Target.BlockId)
		require.Equal(t, canonical, variant.CanonicalBytes)
		require.Equal(t, pb.PinkhaTorahAuthorizedOperationRead_LIVE_BLOCK, variant.Reachability)
		require.Len(t, variant.Provenance, 1)
		require.Equal(t, accountID, variant.Provenance[0].Creator)
		require.Equal(t, changeID, variant.Provenance[0].NativeChangeId)
		require.NotEmpty(t, variant.Provenance[0].NativeAclHeadId)
		return variant, raw
	}
	runCoherentT5SignedRevocation(t, func(stage, actualAccount, actualSpace, actualObject, actualBlock string) {
		stages = append(stages, stage)
		currentApp := mw.GetApp()
		require.NotNil(t, currentApp)
		keys := app.MustComponent[accountservice.Service](currentApp).Account()
		require.Equal(t, actualAccount, keys.SignKey.GetPublic().Account())
		var currentSpace clientspace.Space
		var err error
		if stage != "removed" {
			currentSpace, err = app.MustComponent[space.Service](currentApp).Get(context.Background(), actualSpace)
			require.NoError(t, err)
			require.Equal(t, actualSpace, currentSpace.Id())
		}
		if stage == "owner" {
			originalApp, originalSpace = currentApp, currentSpace
			accountID, spaceID, objectID, blockID = actualAccount, actualSpace, actualObject, actualBlock
			require.NotEmpty(t, blockID)
			canonical, err = (torahops.Operation{Version: 1, SpaceID: spaceID, OperationID: operationID,
				AuthorID: accountID, Kind: torahops.Add, Target: torahops.Target{ObjectID: objectID, BlockID: blockID},
				Source: torahops.Source{ProviderID: "sefaria", CanonicalRef: "Genesis 3:3"}, Payload: payload}).CanonicalBytes()
			require.NoError(t, err)
			created := &pb.RpcPinkhaTorahOperationsAppendResponse{}
			call("PinkhaTorahOperationsAppend", PinkhaTorahOperationsAppend,
				&pb.RpcPinkhaTorahOperationsAppendRequest{ProtocolVersion: 1, SpaceId: spaceID, OperationId: operationID,
					Kind: pb.RpcPinkhaTorahOperations_ADD, Target: &pb.RpcPinkhaTorahOperationsTarget{ObjectId: objectID, BlockId: blockID},
					Source: &pb.RpcPinkhaTorahOperationsSource{ProviderId: "sefaria", CanonicalRef: "Genesis 3:3"}, Payload: payload}, created)
			require.NotNil(t, created.Error)
			require.Equal(t, int32(0), int32(created.Error.Code))
			require.NotNil(t, created.Receipt)
			require.Equal(t, pb.RpcPinkhaTorahOperations_CREATED, created.Receipt.Disposition)
			claimID, changeID = created.Receipt.ClaimId, created.Receipt.ChangeId
			require.NotEmpty(t, claimID)
			require.NotEmpty(t, changeID)
			ownerVariant, ownerWire = positive()
			return
		}
		require.Same(t, originalApp, currentApp)
		require.Equal(t, []string{accountID, spaceID, objectID, blockID}, []string{actualAccount, actualSpace, actualObject, actualBlock})
		if stage == "reader" {
			require.Same(t, originalSpace, currentSpace)
			var variant *pb.PinkhaTorahAuthorizedOperationReadVariant
			variant, readerWire = positive()
			require.True(t, proto.Equal(ownerVariant, variant), "signed bytes and provenance survive the real Reader downgrade")
			return
		}
		require.Equal(t, "removed", stage)
		// The native updater is allowed to retire the Space after removal. Both
		// typed denial and typed snapshot invalidation must release no payload.
		response, raw := read()
		removedWire = raw
		deniedCode = int32(response.Error.Code)
		require.Contains(t, []int32{4, 9}, deniedCode)
		if deniedCode == 4 {
			require.Equal(t, "native permission denied", response.Error.Description)
		} else {
			require.Equal(t, "native candidate closure changed", response.Error.Description)
		}
		require.Nil(t, response.Snapshot)
		require.False(t, bytes.Contains(raw, canonical))
		require.False(t, bytes.Contains(raw, payload))
		require.False(t, bytes.Contains(raw, []byte(claimID)))
	})
	require.Equal(t, []string{"owner", "reader", "removed"}, stages)
	require.Equal(t, map[string]int{"PinkhaTorahOperationsAppend": 1, "PinkhaTorahAuthorizedOperationRead": 3}, calls)
	require.Nil(t, mw.GetApp(), "the shared fixture must finish actual AccountStop")
	parent := filepath.Dir(os.Getenv("PINKHA_T5_ACL_REPORT"))
	coherentAuthorityWriteBytes(t, filepath.Join(parent, "coherent-owner.pb"), ownerWire)
	coherentAuthorityWriteBytes(t, filepath.Join(parent, "coherent-reader.pb"), readerWire)
	coherentAuthorityWriteBytes(t, filepath.Join(parent, "coherent-removed.pb"), removedWire)
	t5ACLWrite(t, filepath.Join(parent, "coherent-observation.json"), map[string]any{
		"protocol": coherentAuthorityProtocol, "nonce": nonce, "pid": os.Getpid(), "heart_sha": vcs.GitCommit,
		"runtime_version": vcs.GitSummary, "fixture_sha256": t5ACLFixtureSHA,
		"account_id_sha256": t5ACLHash([]byte(accountID)), "space_id_sha256": t5ACLHash([]byte(spaceID)),
		"object_id_sha256": t5ACLHash([]byte(objectID)), "block_id_sha256": t5ACLHash([]byte(blockID)),
		"canonical_sha256": t5ACLHash(canonical), "claim_id_sha256": t5ACLHash([]byte(claimID)),
		"native_change_id_sha256": t5ACLHash([]byte(changeID)),
		"owner_wire_sha256":       t5ACLHash(ownerWire), "reader_wire_sha256": t5ACLHash(readerWire), "removed_wire_sha256": t5ACLHash(removedWire),
		"same_runtime_account_space_target": true, "owner_positive": true, "reader_positive": true,
		"exact_signed_bytes_and_provenance": true, "removed_error_code": deniedCode, "removed_has_payload": false,
		"account_stop_verified": true, "rpc_calls": calls, "stages": stages,
		"automatic_t2_to_t5_projection": "NOT_PROVEN", "network_acl_transport": "NOT_RUN", "ios_acceptance": "NOT_RUN",
		"status": "PASS_COHERENT_SIGNED_AUTHORITY",
	})
}
