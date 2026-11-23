package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"testing"

	"github.com/anyproto/any-sync/commonspace/object/tree/objecttree"
	"github.com/anyproto/any-sync/util/crypto"
	"github.com/anyproto/anytype-heart/core/block/editor/smartblock"
	"github.com/anyproto/anytype-heart/core/block/source/sourceimpl"
	"github.com/anyproto/anytype-heart/core/domain"
	"github.com/anyproto/anytype-heart/pb"
	"github.com/anyproto/anytype-heart/pkg/lib/pb/model"
	"github.com/anyproto/anytype-heart/pkg/lib/pinkha/semanticanchor"
	"github.com/anyproto/anytype-heart/util/vcs"
	"github.com/gogo/protobuf/proto"
	"github.com/stretchr/testify/require"
)

const semanticPageProtocol = "pinkha-semantic-anchor-native-page-v1"
const semanticPageText = "אבג 😀 text סוף"
const semanticPageAnchor = "1b83759e-e316-4e84-b9f8-10d654f8de72"

// The controller embeds its complete additive native inventory in this
// candidate version. This is never the production139 runtime identity.
var semanticPageSourceSHA = "UNSET"

type semanticPageState struct {
	Account         t2AccountState                `json:"account"`
	CreatePID       int                           `json:"createPID"`
	Nonce           string                        `json:"nonce"`
	Request         semanticanchor.CaptureRequest `json:"request"`
	Receipt         semanticanchor.Receipt        `json:"receipt"`
	BeforeBlock     []byte                        `json:"beforeBlock"`
	AfterBlock      []byte                        `json:"afterBlock"`
	NativeChangeSHA string                        `json:"nativeChangeSHA256"`
	BeforeHeads     []string                      `json:"beforeHeads"`
}

func semanticPageSnapshot(t *testing.T, block *model.Block) semanticanchor.Snapshot {
	t.Helper()
	require.NotNil(t, block)
	text := block.GetText()
	require.NotNil(t, text)
	value := semanticanchor.Snapshot{Text: text.Text, Marks: []semanticanchor.Mark{}}
	for _, mark := range text.GetMarks().GetMarks() {
		require.NotNil(t, mark, "never omit an unsupported native mark")
		require.NotNil(t, mark.Range, "never infer missing native ranges")
		value.Marks = append(value.Marks, semanticanchor.Mark{
			From: mark.Range.From, To: mark.Range.To, Kind: int32(mark.Type), Param: mark.Param})
	}
	require.NoError(t, value.Validate())
	return value
}

func semanticPageShow(rpc *t2AccountRPC, account *t2AccountState, parent, name string) *model.Block {
	rpc.t.Helper()
	request, err := proto.Marshal(&pb.RpcObjectShowRequest{
		SpaceId: account.SpaceID, ObjectId: account.DocumentID, ContextId: account.DocumentID})
	require.NoError(rpc.t, err)
	rpc.calls["ObjectShow"]++
	raw := ObjectShow(request)
	t2WriteFresh(rpc.t, filepath.Join(parent, name+"-object-show.pb"), raw)
	response := &pb.RpcObjectShowResponse{}
	require.NoError(rpc.t, proto.Unmarshal(raw, response))
	rpc.check(response)
	require.NotNil(rpc.t, response.ObjectView)
	require.Equal(rpc.t, account.DocumentID, response.ObjectView.RootId)
	_ = t2ShownDetails(rpc.t, response, account)
	var target *model.Block
	for _, block := range response.ObjectView.Blocks {
		if block.Id == account.BlockID {
			require.Nil(rpc.t, target, "one exact native block is required")
			target = block
		}
	}
	require.NotNil(rpc.t, target)
	return proto.Clone(target).(*model.Block)
}

func semanticPageCurrent(t *testing.T, account *t2AccountState) (*model.Block, []string) {
	t.Helper()
	var block *model.Block
	var heads []string
	err := t2Space(t, account.SpaceID).Do(account.DocumentID, func(object smartblock.SmartBlock) error {
		require.Equal(t, account.SpaceID, object.SpaceID())
		require.Equal(t, account.DocumentID, object.Id())
		picked := object.Pick(account.BlockID)
		require.NotNil(t, picked)
		block = proto.Clone(picked.Model()).(*model.Block)
		heads = slices.Clone(object.Tree().Heads())
		return nil
	})
	require.NoError(t, err)
	slices.Sort(heads)
	return block, heads
}

func semanticPageRequest(t *testing.T, request semanticanchor.CaptureRequest) []byte {
	t.Helper()
	raw, err := json.Marshal(map[string]any{
		"protocolVersion": request.Version, "spaceID": request.SpaceID, "objectID": request.ObjectID,
		"blockID": request.BlockID, "anchorID": request.AnchorID, "from": request.From, "to": request.To,
		"expected": request.Expected,
	})
	require.NoError(t, err)
	return raw
}

func semanticPageCall(rpc *t2AccountRPC, parent, name string, raw []byte, want string) semanticanchor.CaptureWireResponse {
	rpc.t.Helper()
	t2WriteFresh(rpc.t, filepath.Join(parent, name+"-request.json"), raw)
	rpc.calls["PinkhaSemanticAnchorCapture"]++
	response := PinkhaSemanticAnchorCapture(raw)
	t2WriteFresh(rpc.t, filepath.Join(parent, name+"-response.json"), response)
	var decoded semanticanchor.CaptureWireResponse
	require.NoError(rpc.t, json.Unmarshal(response, &decoded))
	require.Equal(rpc.t, uint32(semanticanchor.Version), decoded.ProtocolVersion)
	require.Equal(rpc.t, want, decoded.Outcome)
	if want != "applied" {
		require.Nil(rpc.t, decoded.Receipt)
		require.Empty(rpc.t, decoded.ResponseEvent)
	}
	return decoded
}

func semanticPageMarkEvent(t *testing.T, messages []*pb.EventMessage, blockID string, after semanticanchor.Snapshot) {
	t.Helper()
	matched := 0
	for _, message := range messages {
		value := message.GetBlockSetText()
		if value == nil || value.Id != blockID {
			continue
		}
		matched++
		require.Nil(t, value.Text, "capture must not replace native text")
		require.Nil(t, value.Style)
		require.Nil(t, value.Checked)
		require.Nil(t, value.Color)
		require.Nil(t, value.IconEmoji)
		require.Nil(t, value.IconImage)
		require.NotNil(t, value.Marks)
		block := &model.Block{Content: &model.BlockContentOfText{Text: &model.BlockContentText{
			Text: after.Text, Marks: value.Marks.Value}}}
		require.True(t, after.SameMarks(semanticPageSnapshot(t, block)), "native event must carry every original mark and the single anchor")
	}
	require.Equal(t, 1, matched, "one actual native mark update is required")
}

// Decode the exact signed stored change rather than trusting the in-memory
// objecttree Change.Model. The read key never leaves this function or enters
// an evidence/log file. Cold ObjectShow in the second process is the separate
// production replay proof.
func semanticPageStoredPayload(t *testing.T, value *semanticPageState, parent, phase string, after semanticanchor.Snapshot) string {
	t.Helper()
	var rawSHA string
	err := t2Space(t, value.Account.SpaceID).Do(value.Account.DocumentID, func(object smartblock.SmartBlock) error {
		tree := object.Tree()
		require.Equal(t, value.Account.DocumentID, tree.Id())
		storage := tree.Storage()
		require.Equal(t, tree.Id(), storage.Id())
		stored, err := storage.Get(context.Background(), value.Receipt.ChangeID)
		require.NoError(t, err)
		require.Equal(t, value.Receipt.ChangeID, stored.Id)
		require.True(t, stored.TreeId == "" || stored.TreeId == tree.Id())
		rawSHA = t2Hash(stored.RawChange)
		require.Equal(t, value.Receipt.NativeChangeSHA256, rawSHA)
		t2WriteFresh(t, filepath.Join(parent, phase+"-stored-native-change.bin"), stored.RawChange)
		change, err := objecttree.NewChangeBuilder(crypto.NewKeyStorage(), tree.Header()).Unmarshall(stored.RawTreeChangeWithId(), true)
		require.NoError(t, err, "real native CID/signature verification")
		require.NotEmpty(t, change.ReadKeyId)
		require.Equal(t, value.Receipt.ChangeID, change.Id)
		parents := slices.Clone(change.PreviousIds)
		slices.Sort(parents)
		require.Equal(t, value.BeforeHeads, parents)
		acl := tree.AclList()
		acl.RLock()
		key, ok := acl.AclState().Keys()[change.ReadKeyId]
		if !ok || key.ReadKey == nil {
			acl.RUnlock()
			t.Fatal("actual native read key unavailable")
		}
		keyBytes, keyError := key.ReadKey.Raw()
		acl.RUnlock()
		require.NoError(t, keyError)
		treeKey, err := crypto.NewKeyDeriver(fmt.Sprintf(crypto.AnysyncTreePath, tree.Id())).DeriveKey(keyBytes)
		require.NoError(t, err)
		decrypted, err := treeKey.Decrypt(change.Data)
		require.NoError(t, err)
		decoded, err := sourceimpl.UnmarshalChange(change, decrypted)
		require.NoError(t, err, "unchanged production payload decoder")
		payload, ok := decoded.(*pb.Change)
		require.True(t, ok)
		require.Empty(t, payload.FileKeys, "this text-only fixture must not export secret file keys")
		var messages []*pb.EventMessage
		for _, content := range payload.Content {
			if update := content.GetBlockUpdate(); update != nil {
				messages = append(messages, update.Events...)
			}
		}
		semanticPageMarkEvent(t, messages, value.Account.BlockID, after)
		if payload.Snapshot != nil {
			require.Empty(t, payload.Snapshot.FileKeys)
			require.NotNil(t, payload.Snapshot.Data)
			found := false
			for _, block := range payload.Snapshot.Data.Blocks {
				if block.Id == value.Account.BlockID {
					require.False(t, found)
					found = true
					require.True(t, after.SameMarks(semanticPageSnapshot(t, block)))
				}
			}
			require.True(t, found, "a native snapshot must include the anchored block")
		}
		encoded, err := proto.Marshal(payload)
		require.NoError(t, err)
		require.Contains(t, string(encoded), value.Receipt.Marker)
		t2WriteFresh(t, filepath.Join(parent, phase+"-decoded-native-change.pb"), encoded)
		return nil
	})
	require.NoError(t, err)
	return rawSHA
}

func TestSemanticAnchorNativePageCaptureAndWire(t *testing.T) {
	semanticPagePhase(t, "capture")
}

func TestSemanticAnchorNativePageColdReopen(t *testing.T) {
	semanticPagePhase(t, "cold-reopen")
}

func semanticPagePhase(t *testing.T, phase string) {
	require.Equal(t, phase, os.Getenv("PINKHA_SEMANTIC_PAGE_PHASE"))
	root, parent := os.Getenv("PINKHA_SEMANTIC_PAGE_ROOT"), os.Getenv("PINKHA_SEMANTIC_PAGE_WORK")
	require.True(t, filepath.IsAbs(parent))
	require.Equal(t, filepath.Join(parent, "account-root"), root)
	owner, err := os.ReadFile(filepath.Join(parent, "ownership.json"))
	require.NoError(t, err)
	require.Equal(t, string(owner), os.Getenv("PINKHA_SEMANTIC_PAGE_OWNER_TOKEN"))
	var ownership struct {
		Protocol      string `json:"protocol"`
		Nonce         string `json:"nonce"`
		SyntheticOnly bool   `json:"synthetic_only"`
	}
	require.NoError(t, json.Unmarshal(owner, &ownership))
	require.Equal(t, semanticPageProtocol, ownership.Protocol)
	require.NotEmpty(t, ownership.Nonce)
	require.True(t, ownership.SyntheticOnly)
	require.NotEqual(t, "UNSET", semanticPageSourceSHA)
	require.Len(t, semanticPageSourceSHA, 64)
	require.Equal(t, semanticPageSourceSHA, os.Getenv("PINKHA_SEMANTIC_PAGE_SOURCE_SHA"))
	require.Equal(t, "d98420b1113536afd08cde6de9a5816f6d27ffff", vcs.GitCommit)
	wantVersion := "pinkha-semantic-anchor-native-page-candidate-v1-" + semanticPageSourceSHA
	require.Equal(t, wantVersion, vcs.GitSummary)
	statePath, keyPath := filepath.Join(parent, "state.json"), filepath.Join(parent, "account-key.private")
	value := &semanticPageState{CreatePID: os.Getpid(), Nonce: ownership.Nonce}
	if phase == "capture" {
		entries, err := os.ReadDir(root)
		require.NoError(t, err)
		require.Empty(t, entries, "fresh disposable native account required")
	} else {
		raw, err := os.ReadFile(statePath)
		require.NoError(t, err)
		require.NoError(t, json.Unmarshal(raw, value))
		require.Equal(t, ownership.Nonce, value.Nonce)
		require.NotEqual(t, value.CreatePID, os.Getpid(), "cold reopen requires a different process")
		require.NotEmpty(t, value.Account.AccountID)
		require.Equal(t, filepath.Base(value.Account.AccountID), value.Account.AccountID)
		entries, err := os.ReadDir(filepath.Join(root, value.Account.AccountID))
		require.NoError(t, err)
		require.NotEmpty(t, entries)
	}
	rpc := &t2AccountRPC{t: t, calls: map[string]int{}}
	SetEventHandler(func(*pb.Event) {})
	rpc.invoke(InitialSetParameters, &pb.RpcInitialSetParametersRequest{Platform: "ios", Version: "0.51.0", Workdir: root,
		DoNotSaveLogs: true, DoNotSendLogs: true, DoNotSendTelemetry: true}, &pb.RpcInitialSetParametersResponse{})
	version := &pb.RpcAppGetVersionResponse{}
	rpc.invoke(AppGetVersion, &pb.RpcAppGetVersionRequest{}, version)
	require.Equal(t, wantVersion, version.Version)
	started, stopped := false, false
	shutdown := func() {
		if started && !stopped {
			rpc.invoke(AccountStop, &pb.RpcAccountStopRequest{RemoveData: false}, &pb.RpcAccountStopResponse{})
			require.Nil(t, mw.GetApp(), "actual AccountStop must clear the running application")
			rpc.invoke(AppShutdown, &pb.RpcAppShutdownRequest{}, &pb.RpcAppShutdownResponse{})
			stopped = true
		}
	}
	t.Cleanup(shutdown)
	if phase == "capture" {
		wallet := &pb.RpcWalletCreateResponse{}
		rpc.invoke(WalletCreate, &pb.RpcWalletCreateRequest{RootPath: root}, wallet)
		require.NotEmpty(t, wallet.AccountKey)
		require.NotEmpty(t, wallet.Mnemonic)
		t2WriteFresh(t, keyPath, []byte(wallet.AccountKey))
		secrets, err := json.Marshal([]string{wallet.AccountKey, wallet.Mnemonic})
		require.NoError(t, err)
		t2WriteFresh(t, filepath.Join(parent, "sensitive-needles.private"), secrets)
		created := &pb.RpcAccountCreateResponse{}
		rpc.invoke(AccountCreate, &pb.RpcAccountCreateRequest{Name: "Disposable semantic anchor Page",
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true}, created)
		started = true
		require.NotNil(t, created.Account)
		require.NotEmpty(t, created.Account.Id)
		value.Account.AccountID = created.Account.Id
		rpc.createTarget(&value.Account)
		createdBlock := &pb.RpcBlockCreateResponse{}
		rpc.invoke(BlockCreate, &pb.RpcBlockCreateRequest{ContextId: value.Account.DocumentID,
			TargetId: value.Account.DocumentID, Position: model.Block_Inner, Block: &model.Block{
				Restrictions: &model.BlockRestrictions{},
				Align:        model.Block_AlignRight, BackgroundColor: "yellow",
				Fields: domain.NewDetails().SetString("semanticAnchorControlOpaque", "preserve-native-field").ToProto(),
				Content: &model.BlockContentOfText{Text: &model.BlockContentText{Text: semanticPageText,
					Style: model.BlockContentText_Paragraph, Marks: &model.BlockContentTextMarks{Marks: []*model.BlockContentTextMark{
						{Range: &model.Range{From: 0, To: 3}, Type: model.BlockContentTextMark_Bold},
						{Range: &model.Range{From: 7, To: 11}, Type: model.BlockContentTextMark_Italic},
						{Range: &model.Range{From: 12, To: 15}, Type: model.BlockContentTextMark_TextColor, Param: "red"},
						{Range: &model.Range{From: 7, To: 11}, Type: model.BlockContentTextMark_Link, Param: "https://example.invalid/native-control"},
					}}}}}}, createdBlock)
		value.Account.BlockID = createdBlock.BlockId
		require.NotEmpty(t, value.Account.BlockID)
		before := semanticPageShow(rpc, &value.Account, parent, "capture-before")
		require.Equal(t, semanticPageText, before.GetText().Text)
		require.Equal(t, model.Block_AlignRight, before.Align)
		require.Equal(t, "yellow", before.BackgroundColor)
		require.Equal(t, "preserve-native-field", domain.NewDetailsFromProto(before.Fields).GetString("semanticAnchorControlOpaque"))
		require.Len(t, before.GetText().GetMarks().GetMarks(), 4)
		value.BeforeBlock, err = proto.Marshal(before)
		require.NoError(t, err)
		value.Request = semanticanchor.CaptureRequest{Version: semanticanchor.Version, SpaceID: value.Account.SpaceID,
			ObjectID: value.Account.DocumentID, BlockID: value.Account.BlockID, AnchorID: semanticPageAnchor,
			From: 4, To: 6, Expected: semanticPageSnapshot(t, before)}
		_, value.BeforeHeads = semanticPageCurrent(t, &value.Account)
		for _, scenario := range []string{"changed-unselected-mark", "changed-text", "unknown-authority-field"} {
			request := value.Request
			request.Expected.Marks = slices.Clone(request.Expected.Marks)
			want := "changed"
			if scenario == "changed-unselected-mark" {
				request.Expected.Marks[0].Param += "unreviewed"
			} else if scenario == "changed-text" {
				request.Expected.Text += "!"
			}
			raw := semanticPageRequest(t, request)
			if scenario == "unknown-authority-field" {
				raw = append(append([]byte{}, raw[:len(raw)-1]...), []byte(`,"isOwner":true}`)...)
				want = "invalid"
			}
			semanticPageCall(rpc, parent, "capture-"+scenario, raw, want)
			current, heads := semanticPageCurrent(t, &value.Account)
			require.True(t, proto.Equal(before, current), "refused capture must preserve the complete native block")
			require.Equal(t, value.BeforeHeads, heads, "refused capture must not append native history")
		}
		response := semanticPageCall(rpc, parent, "capture-applied", semanticPageRequest(t, value.Request), "applied")
		require.NotNil(t, response.Receipt)
		value.Receipt = *response.Receipt
		marker, err := value.Request.Validate()
		require.NoError(t, err)
		require.Equal(t, marker, value.Receipt.Marker)
		require.Equal(t, value.Request.SpaceID, value.Receipt.SpaceID)
		require.Equal(t, value.Request.ObjectID, value.Receipt.ObjectID)
		require.Equal(t, value.Request.BlockID, value.Receipt.BlockID)
		require.Equal(t, value.Request.AnchorID, value.Receipt.AnchorID)
		require.Equal(t, value.Request.Expected.Digest(), value.Receipt.BeforeTextMarksSHA256)
		afterBlock := semanticPageShow(rpc, &value.Account, parent, "capture-after")
		after := semanticPageSnapshot(t, afterBlock)
		planned, err := value.Request.Plan(value.Request.Expected)
		require.NoError(t, err)
		require.True(t, planned.SameMarks(after))
		require.Equal(t, after.Digest(), value.Receipt.AfterTextMarksSHA256)
		preserved := proto.Clone(afterBlock).(*model.Block)
		preserved.GetText().Marks = proto.Clone(before.GetText().Marks).(*model.BlockContentTextMarks)
		require.True(t, proto.Equal(before, preserved), "normal Page Apply must preserve every non-mark native block field")
		value.AfterBlock, err = proto.Marshal(afterBlock)
		require.NoError(t, err)
		event := &pb.ResponseEvent{}
		require.NoError(t, proto.Unmarshal(response.ResponseEvent, event))
		require.Equal(t, value.Account.DocumentID, event.ContextId)
		semanticPageMarkEvent(t, event.Messages, value.Account.BlockID, after)
		t2WriteFresh(t, filepath.Join(parent, "capture-response-event.pb"), response.ResponseEvent)
		value.NativeChangeSHA = semanticPageStoredPayload(t, value, parent, phase, after)
		encoded, err := json.MarshalIndent(value, "", "  ")
		require.NoError(t, err)
		t2WriteFresh(t, statePath, encoded)
	} else {
		key, err := os.ReadFile(keyPath)
		require.NoError(t, err)
		rpc.invoke(WalletRecover, &pb.RpcWalletRecoverRequest{RootPath: root, AccountKey: string(key)}, &pb.RpcWalletRecoverResponse{})
		selected := &pb.RpcAccountSelectResponse{}
		rpc.invoke(AccountSelect, &pb.RpcAccountSelectRequest{Id: value.Account.AccountID, RootPath: root,
			NetworkMode: pb.RpcAccount_LocalOnly, DisableLocalNetworkSync: true, PreferredSpaceId: value.Account.SpaceID}, selected)
		started = true
		require.NotNil(t, selected.Account)
		require.Equal(t, value.Account.AccountID, selected.Account.Id)
		rpc.invoke(WorkspaceOpen, &pb.RpcWorkspaceOpenRequest{SpaceId: value.Account.SpaceID}, &pb.RpcWorkspaceOpenResponse{})
		afterBlock := semanticPageShow(rpc, &value.Account, parent, "cold-reopen")
		expectedBlock := &model.Block{}
		require.NoError(t, proto.Unmarshal(value.AfterBlock, expectedBlock))
		require.True(t, proto.Equal(expectedBlock, afterBlock), "fresh process must replay the complete durable anchored native block")
		after := semanticPageSnapshot(t, afterBlock)
		require.Equal(t, value.Receipt.AfterTextMarksSHA256, after.Digest())
		require.Equal(t, value.NativeChangeSHA, semanticPageStoredPayload(t, value, parent, phase, after))
		beforeDuplicate, headsBeforeDuplicate := semanticPageCurrent(t, &value.Account)
		duplicate := value.Request
		duplicate.Expected = after
		semanticPageCall(rpc, parent, "cold-reopen-duplicate", semanticPageRequest(t, duplicate), "alreadyLinked")
		current, heads := semanticPageCurrent(t, &value.Account)
		require.True(t, proto.Equal(beforeDuplicate, current))
		require.Equal(t, headsBeforeDuplicate, heads, "duplicate identity refusal must not append history")
	}
	shutdown()
	require.True(t, stopped)
	stateBytes, err := os.ReadFile(statePath)
	require.NoError(t, err)
	require.False(t, bytes.Contains(stateBytes, []byte("AccountKey")))
	report := map[string]any{
		"protocol": semanticPageProtocol, "phase": phase, "pid": os.Getpid(), "create_pid": value.CreatePID,
		"nonce": ownership.Nonce, "runtime_version": version.Version, "source_manifest_sha256": semanticPageSourceSHA,
		"heart_sha": vcs.GitCommit, "account_id": value.Account.AccountID, "space_id": value.Account.SpaceID,
		"object_id": value.Account.DocumentID, "block_id": value.Account.BlockID, "anchor_id": value.Receipt.AnchorID,
		"marker": value.Receipt.Marker, "native_change_id": value.Receipt.ChangeID,
		"native_change_sha256": value.NativeChangeSHA, "state_sha256": t2Hash(stateBytes), "rpc_calls": rpc.calls,
		"account_stop_verified": true, "closed": true, "test_passed": true,
		"app_capability": "OFF", "apple_acceptance": "NOT_RUN", "editor02_acceptance": "NOT_COMPLETE",
	}
	encoded, err := json.MarshalIndent(report, "", "  ")
	require.NoError(t, err)
	t2WriteFresh(t, filepath.Join(parent, phase+".json"), encoded)
	t.Log("PASS real native Page capture, signed payload and account phase: " + phase)
}
