//go:build pinkha_loaded_account_witness && pinkha_loaded_account_witness_acceptance && pinkha_native_file_peer_acceptance

package application

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/anyproto/any-sync/accountservice"
	"github.com/anyproto/any-sync/app"
	"github.com/anyproto/any-sync/commonspace/object/acl/list"
	"github.com/anyproto/any-sync/commonspace/object/acl/syncacl"
	"github.com/anyproto/any-sync/consensus/consensusproto"
	"github.com/anyproto/any-sync/net/peer"
	"github.com/anyproto/any-sync/util/cidutil"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/stretchr/testify/require"

	"github.com/anyproto/anytype-heart/core/block"
	"github.com/anyproto/anytype-heart/core/block/cache"
	sb "github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/core/files"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/space"
	"github.com/anyproto/anytype-heart/space/spaceinfo"
)

func nativeFilePeerCaptureRequest(f *loadedAccountFixture) LoadedAccountSpaceWitnessRequest {
	return LoadedAccountSpaceWitnessRequest{Source: f.request(), PrivateDirectory: f.dir, MaxFileBytes: 16 << 20,
		FileLimits: files.NativeFileCaptureLimits{MaxVariantBytes: 8 << 20, MaxTotalBytes: 16 << 20, MaxDAGNodes: 4000, MaxDAGBytes: 32 << 20}}
}

// Each immutable note retains a refused attempt; no rejected capture is reused.
func nativeFilePeerCapture(t *testing.T, f *loadedAccountFixture, root, stage string) (*LoadedAccountSpaceWitness, error) {
	t.Helper()
	return loadedCaptureFreshAttempts(f.ctx, func() (*LoadedAccountSpaceWitness, error) {
		return f.service.CaptureLoadedAccountSpaceWitness(f.ctx, f.token, nativeFilePeerCaptureRequest(f))
	}, func(note loadedNativeCaptureAttempt) {
		nativeFilePeerWrite(t, root, fmt.Sprintf("capture-%s-attempt-%d.json", stage, note.Attempt), map[string]any{
			"contract": "pinkha-native-source-capture-attempt-v1", "attemptLimit": loadedNativeCaptureAttemptLimit,
			"stage": stage, "attempt": note, "newCaptureRequiredAfterRefusal": true,
		})
	})
}

func nativeFilePeerExpect(t *testing.T, captured *LoadedAccountSpaceWitness, state *nativeFilePeerSource) map[string]any {
	t.Helper()
	require.NotNil(t, captured)
	require.NotNil(t, state)
	receipt, err := captured.Receipt()
	require.NoError(t, err)
	require.True(t, receipt.AccountSessionAuthorizedAtFinalCapture)
	require.True(t, receipt.CapturedSnapshotsBoundToUnchangedCheckpoint)
	require.True(t, receipt.AllNativeHeadRowsAccounted)
	require.False(t, receipt.HistorySemanticsValidated)
	require.False(t, receipt.SemanticCompleteness)
	require.False(t, receipt.PermitsDestinationWrites)
	file := captured.File(state.FileID)
	require.NotNil(t, file, "actual captured target payload required")
	variants := file.Variants()
	require.Len(t, variants, len(state.Variants))
	expected := map[string]nativeFilePeerVariantExpectation{}
	for _, variant := range state.Variants {
		_, exists := expected[variant.Path]
		require.False(t, exists)
		expected[variant.Path] = variant
	}
	var total int64
	for _, variant := range variants {
		want, exists := expected[variant.Path()]
		require.True(t, exists)
		require.Equal(t, want.ContentID, variant.ContentID())
		require.Equal(t, want.MetadataID, variant.MetadataID())
		require.Equal(t, want.PlaintextSHA256, variant.ContentSHA256())
		require.Equal(t, want.PlaintextBytes, variant.Size())
		require.Equal(t, want.MetadataSHA256, loadedFixtureHash(variant.Metadata()))
		require.Len(t, variant.Metadata(), want.MetadataBytes)
		reader, err := variant.Open()
		require.NoError(t, err)
		digest := sha256.New()
		size, readErr := io.Copy(digest, reader)
		closeErr := reader.Close()
		require.NoError(t, readErr)
		require.NoError(t, closeErr)
		require.Equal(t, want.PlaintextBytes, size)
		require.Equal(t, want.PlaintextSHA256, hex.EncodeToString(digest.Sum(nil)))
		total += size
	}
	fileReceipt, err := file.Receipt()
	require.NoError(t, err)
	require.True(t, fileReceipt.AllDAGBlocksLocal)
	require.True(t, fileReceipt.AllVariantBytesRead)
	require.Greater(t, fileReceipt.DAGNodes, 4, "multi-leaf actual source file required")
	ownerRef := false
	for _, ref := range captured.FileReferences() {
		if ref.OwnerObjectID == state.FileObjectID && ref.TargetObjectID == state.FileObjectID && ref.FileID == state.FileID && ref.Field == "fileInfo.fileId" {
			ownerRef = true
		}
	}
	require.True(t, ownerRef)
	views := loadedSnapshotJSONViews(t, captured)
	return map[string]any{"nativeJSONViewsVerified": views, "sourceReceipt": receipt, "fileReceipt": fileReceipt, "fullPlaintextBytes": total, "exactMetadataBytesVerified": true, "nativeOwnerReferenceVerified": true}
}

func nativeFilePeerGrant(t *testing.T, acl syncacl.SyncAcl, memberID string) string {
	t.Helper()
	member, err := crypto.DecodeAccountAddress(memberID)
	require.NoError(t, err)
	acl.Lock()
	defer acl.Unlock()
	require.Equal(t, list.AclPermissionsNone, acl.AclState().Permissions(member))
	record, err := acl.RecordBuilder().BuildAccountsAdd(list.AccountsAddPayload{Additions: []list.AccountAdd{{Identity: member, Permissions: list.AclPermissionsReader}}})
	require.NoError(t, err)
	require.NoError(t, acl.ValidateRawRecord(record, nil))
	raw, err := record.MarshalVT()
	require.NoError(t, err)
	id, err := cidutil.NewCidFromBytes(raw)
	require.NoError(t, err)
	// This is the real signed native append and unmodified transport broadcast.
	// No membership, key envelope or tree is injected into the receiving account.
	require.NoError(t, acl.AddRawRecord(&consensusproto.RawRecordWithId{Id: id, Payload: raw}))
	require.Equal(t, id, acl.Head().Id)
	require.Equal(t, list.AclPermissionsReader, acl.AclState().Permissions(member))
	return id
}

// TestLoadedAccountRemoteFilePeer is selected once per process under a sealed
// role. The two online processes have separate wallets, private stores and
// network namespaces. Reopen reuses only the member's own persisted wallet/store.
func TestLoadedAccountRemoteFilePeer(t *testing.T) {
	const root = "/private"
	role, phase, nonce := os.Getenv("PINKHA_SOURCE_FILE_ROLE"), os.Getenv("PINKHA_SOURCE_FILE_PHASE"), os.Getenv("PINKHA_SOURCE_FILE_NONCE")
	require.Contains(t, []string{"owner", "member"}, role)
	require.Contains(t, []string{"online", "reopen"}, phase)
	require.Len(t, nonce, 32)
	rawOwnership, err := os.ReadFile(filepath.Join(root, "ownership.json"))
	require.NoError(t, err)
	var ownership map[string]any
	require.NoError(t, json.Unmarshal(rawOwnership, &ownership))
	require.Equal(t, map[string]any{"protocol": nativeFilePeerProtocol, "nonce": nonce, "role": role, "synthetic_only": true}, ownership)
	f, identity, saved := newNativeFilePeerFixture(t, root, role, phase)
	write := func(label string, body map[string]any) {
		body["protocol"], body["phase"], body["role"], body["nonce"] = nativeFilePeerProtocol, label, role, nonce
		body["identity"] = identity
		body["actualIPv4"] = nativeFilePeerIPv4(t)
		body["walletCreateCalls"], body["walletRecoverCalls"] = 1, 0
		if phase == "reopen" {
			body["walletCreateCalls"], body["walletRecoverCalls"] = 0, 1
		}
		body["fullSpaceMigrationComplete"], body["historySemanticsValidated"] = false, false
		nativeFilePeerWrite(t, root, label+".json", body)
	}
	spaces := app.MustComponent[space.Service](f.service.GetApp())
	if phase == "reopen" {
		require.Equal(t, "member", role)
		require.NotNil(t, saved.Source)
		state := saved.Source
		shared, err := spaces.Get(f.ctx, state.SpaceID)
		require.NoError(t, err)
		require.NoError(t, shared.WaitMandatoryObjects(f.ctx))
		f.space, err = f.core.Get(f.ctx, state.SpaceID)
		require.NoError(t, err)
		loadedSpaceFixtureWarm(t, f)
		require.Empty(t, nativeFilePeerIPv4(t))
		captured, err := nativeFilePeerCapture(t, f, root, "member-offline-reopen")
		require.NoError(t, err)
		result := nativeFilePeerExpect(t, captured, state)
		require.NoError(t, f.service.Stop())
		f.stopped = true
		require.Nil(t, f.service.GetApp())
		result["offlineFreshProcess"], result["accountStopped"], result["testPassed"] = true, true, true
		result["sourceSpaceID"] = state.SpaceID
		write("reopen-final", result)
		return
	}
	state := &nativeFilePeerSource{}
	if role == "owner" {
		shared, err := spaces.Create(f.ctx, &spaceinfo.SpaceDescription{Name: "Owned remote source file", SpaceType: model.SpaceType_SpaceTypeRegular})
		require.NoError(t, err)
		require.NoError(t, shared.WaitMandatoryObjects(f.ctx))
		state.SpaceID = shared.Id()
		f.space, err = f.core.Get(f.ctx, state.SpaceID)
		require.NoError(t, err)
		state.PageID = loadedObjectFixturePage(t, f, "מקור אמיתי — קובץ מועבר בין חשבונות", false)
		payload := make([]byte, 2<<20)
		_, err = rand.Read(payload)
		require.NoError(t, err)
		state.FileObjectID, state.FileID = loadedSpaceFixtureFile(t, f, payload)
		loadedSpaceFixtureWarm(t, f)
		captured, err := nativeFilePeerCapture(t, f, root, "owner-initial")
		require.NoError(t, err)
		capture := captured.File(state.FileID)
		require.NotNil(t, capture)
		for _, variant := range capture.Variants() {
			require.Equal(t, loadedFixtureHash(payload), variant.ContentSHA256())
			state.Variants = append(state.Variants, nativeFilePeerVariantExpectation{
				Path: variant.Path(), ContentID: variant.ContentID(), MetadataID: variant.MetadataID(),
				MetadataSHA256: loadedFixtureHash(variant.Metadata()), MetadataBytes: len(variant.Metadata()),
				PlaintextSHA256: variant.ContentSHA256(), PlaintextBytes: variant.Size(),
			})
		}
		require.Len(t, state.Variants, 1)
		saved.Source = state
		nativeFilePeerWrite(t, root, "own-wallet.private.json", saved)
		nativeFilePeerWrite(t, root, "source-expectation.json", state)
		result := nativeFilePeerExpect(t, captured, state)
		write("identity", map[string]any{"source": state, "createdSource": result})
	} else {
		write("identity", map[string]any{})
	}
	command := nativeFilePeerCommandRead(t, f.ctx, root, "join", nonce)
	require.NotNil(t, command.Peer)
	require.NotEqual(t, identity.AccountID, command.Peer.AccountID)
	require.NotEqual(t, identity.PeerID, command.Peer.PeerID)
	require.NotEqual(t, identity.Namespace, command.Peer.Namespace)
	if role == "owner" {
		nativeFilePeerRoute(t, f, *command.Peer, state.SpaceID)
		acl := f.space.Acl()
		keys := app.MustComponent[accountservice.Service](f.service.GetApp()).Account()
		acl.RLock()
		require.Equal(t, list.AclPermissionsOwner, acl.AclState().Permissions(keys.SignKey.GetPublic()))
		acl.RUnlock()
		head := nativeFilePeerGrant(t, acl, command.Peer.AccountID)
		write("grant", map[string]any{"aclHead": head, "memberAccountID": command.Peer.AccountID, "memberPermission": int32(list.AclPermissionsReader)})
		reroute := nativeFilePeerCommandRead(t, f.ctx, root, "reroute", nonce)
		require.NotNil(t, reroute.Peer)
		require.Equal(t, command.Peer.AccountID, reroute.Peer.AccountID)
		require.Equal(t, command.Peer.PeerID, reroute.Peer.PeerID)
		nativeFilePeerRoute(t, f, *reroute.Peer, state.SpaceID)
		write("rerouted", map[string]any{"memberPeerID": reroute.Peer.PeerID})
		nativeFilePeerCommandRead(t, f.ctx, root, "stop", nonce)
		require.NoError(t, f.service.Stop())
		f.stopped = true
		require.Nil(t, f.service.GetApp())
		write("final", map[string]any{"accountStopped": true, "testPassed": true})
		return
	}
	require.NotNil(t, command.Source)
	require.NotEmpty(t, command.ACLHead)
	state = command.Source
	require.NotEmpty(t, state.SpaceID)
	require.NotEmpty(t, state.FileObjectID)
	require.NotEmpty(t, state.FileID)
	nativeFilePeerRoute(t, f, *command.Peer, state.SpaceID)
	require.NoError(t, spaces.InviteJoin(f.ctx, state.SpaceID, command.ACLHead))
	shared, err := spaces.Get(f.ctx, state.SpaceID)
	require.NoError(t, err)
	require.NoError(t, shared.WaitMandatoryObjects(f.ctx))
	f.space, err = f.core.Get(f.ctx, state.SpaceID)
	require.NoError(t, err)
	keys := app.MustComponent[accountservice.Service](f.service.GetApp()).Account()
	acl := f.space.Acl()
	nativeFilePeerWait(t, f.ctx, "actual signed reader grant", func() bool {
		acl.RLock()
		defer acl.RUnlock()
		return acl.Head().Id == command.ACLHead && acl.AclState().Permissions(keys.SignKey.GetPublic()) == list.AclPermissionsReader
	})
	picker := app.MustComponent[*block.Service](f.service.GetApp())
	var actualFileID string
	// Remote tree lookup requires the actual sender identity in its native context.
	// The owned route and signed Reader grant above bind this peer to the Space.
	treeContext := peer.CtxWithPeerId(f.ctx, command.Peer.PeerID)
	require.NoError(t, cache.DoContextFullID(picker, treeContext, domain.FullID{SpaceID: state.SpaceID, ObjectID: state.FileObjectID}, func(object sb.SmartBlock) error {
		require.Equal(t, state.FileObjectID, object.Id())
		require.Equal(t, state.SpaceID, object.SpaceID())
		require.NotNil(t, object.Tree())
		require.Equal(t, state.FileObjectID, object.Tree().Id())
		actualFileID = object.NewState().GetFileInfo().FileId.String()
		return nil
	}))
	require.Equal(t, state.FileID, actualFileID)
	// Loading the real native object obtains its encrypted key envelope through
	// native tree request. The controller sends only identities and expected hashes.
	loadedSpaceFixtureWarm(t, f)
	saved.Source = state
	nativeFilePeerWrite(t, root, "own-wallet.private.json", saved)
	write("joined", map[string]any{"actualNativeFileObjectID": state.FileObjectID, "actualNativeFileID": actualFileID, "aclHead": command.ACLHead, "memberPermission": int32(list.AclPermissionsReader)})
	nativeFilePeerCommandRead(t, f.ctx, root, "cold", nonce)
	require.Empty(t, nativeFilePeerIPv4(t))
	nativeFilePeerNetwork(t, f, false)
	removed := nativeFilePeerOffload(t, f, state.FileID)
	cold, err := nativeFilePeerCapture(t, f, root, "member-cold")
	require.NoError(t, err)
	require.Nil(t, cold.File(state.FileID))
	missing := false
	for _, gap := range cold.Gaps() {
		if gap.Target == state.FileID && gap.Reason == "native-local-payload-capture-refused" {
			missing = true
		}
	}
	require.True(t, missing)
	coldReceipt, err := cold.Receipt()
	require.NoError(t, err)
	require.False(t, coldReceipt.CurrentFilePayloadCompleteness)
	write("cold", map[string]any{"sourceReceipt": coldReceipt, "removedOwnedLocalNodes": removed, "missingLocalRoot": true, "explicitFileGap": true})
	reconnect := nativeFilePeerCommandRead(t, f.ctx, root, "prefetch", nonce)
	require.NotNil(t, reconnect.Peer)
	require.Equal(t, command.Peer.AccountID, reconnect.Peer.AccountID)
	require.Equal(t, command.Peer.PeerID, reconnect.Peer.PeerID)
	require.Len(t, nativeFilePeerIPv4(t), 1)
	nativeFilePeerRoute(t, f, *reconnect.Peer, state.SpaceID)
	nativeFilePeerNetwork(t, f, true)
	nativeFilePeerConnect(t, f, *reconnect.Peer)
	prefetch, err := f.service.PrefetchLoadedAccountSourceFiles(f.ctx, f.token, LoadedAccountFilePrefetchRequest{
		Source: f.request(), Captured: cold, MaxFiles: 32, MaxDAGNodes: 4000, MaxDAGBytes: 32 << 20, MaxDuration: 90 * time.Second,
	})
	require.NoError(t, err)
	require.Greater(t, prefetch.NativeFetches, 0)
	require.True(t, prefetch.AccountSessionAuthorizedAtFinalRead)
	require.True(t, prefetch.CapturedFileIDsBoundToUnchangedCheckpoint)
	require.True(t, prefetch.EveryFetchedBlockRereadFromLocalStore)
	require.True(t, prefetch.RequiresNewFrozenCapture)
	require.False(t, prefetch.FilePayloadCompleteness)
	require.False(t, prefetch.HasNativeSourceAdmission)
	fresh, err := nativeFilePeerCapture(t, f, root, "member-prefetched")
	require.NoError(t, err)
	result := nativeFilePeerExpect(t, fresh, state)
	result["prefetch"] = prefetch
	result["networkPayloadVerified"] = true
	write("received", result)
	nativeFilePeerCommandRead(t, f.ctx, root, "stop", nonce)
	require.NoError(t, f.service.Stop())
	f.stopped = true
	require.Nil(t, f.service.GetApp())
	write("final", map[string]any{"accountStopped": true, "testPassed": true})
}
